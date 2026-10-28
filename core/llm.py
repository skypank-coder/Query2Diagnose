"""Provider-agnostic LLM client: OpenAI-compatible APIs (OpenAI, Groq, Ollama),
Anthropic, and an offline mock for tests.

Every call is cached on disk under .cache/llm keyed by (provider, model,
messages, temperature, seed, max_tokens, json mode), so reruns are free and
deterministic. Non-cached calls are throttled (requests and tokens per minute),
retried on 429 / 5xx, costed from configs/llm.yaml, and stopped once the
process has spent MAX_USD_PER_RUN.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache

import requests
import yaml

from core.paths import CONFIGS, ROOT

CACHE_DIR = ROOT / ".cache" / "llm"


class BudgetExceeded(RuntimeError):
    pass


class QuotaExhausted(RuntimeError):
    """The provider asked us to wait longer than max_retry_wait_s (daily quota used up)."""


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


@lru_cache(maxsize=1)
def llm_config() -> dict:
    return yaml.safe_load((CONFIGS / "llm.yaml").read_text(encoding="utf-8"))


@dataclass
class Settings:
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    max_usd: float
    rpm: int
    tpm: int
    timeout_s: int
    max_retries: int

    @classmethod
    def from_env(cls, provider: str | None = None, model: str | None = None) -> Settings:
        load_env()
        cfg = llm_config()
        provider = provider or os.getenv("LLM_PROVIDER") or cfg["defaults"]["provider"]
        model = model or os.getenv("LLM_MODEL") or cfg["defaults"]["model"]
        key_var = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
        base = os.getenv("OLLAMA_BASE_URL") if provider == "ollama" else None
        return cls(
            provider=provider,
            model=model,
            base_url=base or cfg["base_urls"].get(provider),
            api_key=os.getenv(key_var) if key_var else None,
            max_usd=float(os.getenv("MAX_USD_PER_RUN", "1.0")),
            rpm=int(os.getenv("LLM_RPM", cfg["rate_limits"]["rpm"])),
            tpm=int(os.getenv("LLM_TPM", cfg["rate_limits"]["tpm"])),
            timeout_s=cfg["defaults"]["timeout_s"],
            max_retries=cfg["defaults"]["max_retries"],
        )

    def price(self) -> dict[str, float]:
        prices = llm_config()["prices_per_million"]
        return prices.get(self.model, prices["default"])


@dataclass
class Response:
    text: str
    input_tokens: int
    output_tokens: int
    cached: bool
    cost_usd: float


@dataclass
class Ledger:
    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    by_task: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict:
        return {"calls": self.calls, "cache_hits": self.cache_hits, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "cost_usd": round(self.cost_usd, 4),
                "by_task": dict(self.by_task)}


class _Throttle:
    def __init__(self, rpm: int, tpm: int):
        self.rpm, self.tpm = rpm, tpm
        self.events: deque[tuple[float, int]] = deque()
        self.lock = threading.Lock()

    def wait(self, tokens: int) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                while self.events and now - self.events[0][0] > 60:
                    self.events.popleft()
                used = sum(t for _, t in self.events)
                if len(self.events) < self.rpm and used + tokens <= self.tpm:
                    self.events.append((now, tokens))
                    return
                wait = 60 - (now - self.events[0][0]) + 0.05 if self.events else 0.5
            time.sleep(max(wait, 0.05))


def _estimate_tokens(messages: list[dict]) -> int:
    return sum(len(m["content"]) for m in messages) // 4 + 8


class LLMClient:
    def __init__(self, settings: Settings | None = None, cache: bool = True):
        self.settings = settings or Settings.from_env()
        self.cache = cache
        self.ledger = Ledger()
        self._throttle = _Throttle(self.settings.rpm, self.settings.tpm)
        self._mock = None
        if self.settings.provider == "mock":
            from core.mock_llm import MockLLM
            self._mock = MockLLM()

    @property
    def name(self) -> str:
        return f"{self.settings.provider}/{self.settings.model}"

    def complete(self, messages: list[dict], *, temperature: float = 0.0, seed: int = 0,
                 max_tokens: int = 400, json_mode: bool = False, task: str = "generic") -> Response:
        key_payload = {"provider": self.settings.provider, "model": self.settings.model, "messages": messages,
                       "temperature": temperature, "seed": seed, "max_tokens": max_tokens, "json": json_mode}
        key = hashlib.sha256(json.dumps(key_payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = CACHE_DIR / key[:2] / f"{key}.json"
        self.ledger.by_task[task] = self.ledger.by_task.get(task, 0) + 1
        if self.cache and path.exists():
            hit = json.loads(path.read_text(encoding="utf-8"))
            self.ledger.cache_hits += 1
            return Response(hit["text"], hit["input_tokens"], hit["output_tokens"], True, 0.0)

        if self._mock is not None:
            text = self._mock.complete(messages, temperature=temperature, seed=seed, task=task)
            tin, tout = _estimate_tokens(messages), len(text) // 4 + 1
        else:
            if self.ledger.cost_usd >= self.settings.max_usd:
                raise BudgetExceeded(f"spent ${self.ledger.cost_usd:.4f} >= MAX_USD_PER_RUN={self.settings.max_usd}")
            extra = llm_config().get("model_params", {}).get(self.settings.model, {}).get("extra_max_tokens", 0)
            self._throttle.wait(_estimate_tokens(messages) + max_tokens + extra)
            text, tin, tout = self._call_api(messages, temperature, seed, max_tokens, json_mode)
        price = self.settings.price()
        cost = (tin * price["input"] + tout * price["output"]) / 1e6
        self.ledger.calls += 1
        self.ledger.input_tokens += tin
        self.ledger.output_tokens += tout
        self.ledger.cost_usd += cost
        if self.cache:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"text": text, "input_tokens": tin, "output_tokens": tout,
                                        "model": self.name, "request": key_payload}, ensure_ascii=False),
                            encoding="utf-8")
        return Response(text, tin, tout, False, cost)

    def _call_api(self, messages, temperature, seed, max_tokens, json_mode) -> tuple[str, int, int]:
        s = self.settings
        if s.provider in ("openai", "groq") and not s.api_key:
            raise RuntimeError(f"{s.provider} selected but its API key is not set in .env")
        max_wait = llm_config().get("max_retry_wait_s", 120)
        last = "no response"
        for attempt in range(s.max_retries):
            try:
                if s.provider == "anthropic":
                    return self._anthropic(messages, temperature, max_tokens)
                return self._openai_compatible(messages, temperature, seed, max_tokens, json_mode)
            except _InvalidGeneration:
                return "", 0, 0       # the model produced no valid JSON: callers treat it as an invalid reply
            except _Retryable as e:
                last = f"HTTP {e.status}"
                if e.wait and e.wait > max_wait:
                    raise QuotaExhausted(f"{s.provider} asks to wait {e.wait:.0f}s; quota exhausted, resume later")
                time.sleep(e.wait + 0.5 if e.wait else min(2 ** (attempt + 1), 60))
            except (requests.ConnectionError, requests.Timeout) as e:
                last = type(e).__name__
                time.sleep(min(2 ** (attempt + 1), 60))
        raise RuntimeError(f"{s.provider}: giving up after {s.max_retries} retries (last: {last})")

    def _openai_compatible(self, messages, temperature, seed, max_tokens, json_mode):
        s = self.settings
        params = dict(llm_config().get("model_params", {}).get(s.model, {}))
        extra = params.pop("extra_max_tokens", 0)
        body = {"model": s.model, "messages": messages, "temperature": temperature, "seed": seed,
                "max_tokens": max_tokens + extra, **params}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {s.api_key}"} if s.api_key else {}
        r = requests.post(f"{s.base_url}/chat/completions", json=body, headers=headers, timeout=s.timeout_s)
        _raise_for(r)
        data = r.json()
        usage = data.get("usage") or {}
        return (data["choices"][0]["message"]["content"] or "", usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0))

    def _anthropic(self, messages, temperature, max_tokens):
        s = self.settings
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        body = {"model": s.model, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [m for m in messages if m["role"] != "system"]}
        if system:
            body["system"] = system
        headers = {"x-api-key": s.api_key or "", "anthropic-version": "2023-06-01"}
        r = requests.post(f"{s.base_url}/messages", json=body, headers=headers, timeout=s.timeout_s)
        _raise_for(r)
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", []))
        usage = data.get("usage") or {}
        return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


class _InvalidGeneration(Exception):
    """The provider rejected the model's own output (e.g. Groq json_validate_failed)."""


class _Retryable(Exception):
    def __init__(self, status: int, wait: float | None):
        self.status, self.wait = status, wait


def _seconds(text: str | None) -> float | None:
    """'2.805s', '1m26.4s', '450ms' or '12' -> seconds."""
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        parts = re.findall(r"([\d.]+)(ms|h|m|s)", text)
        scale = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}
        return sum(float(n) * scale[u] for n, u in parts) if parts else None


def _raise_for(r: requests.Response) -> None:
    if r.status_code == 429 or r.status_code >= 500:
        wait = _seconds(r.headers.get("retry-after"))
        if wait is None and r.status_code == 429:
            h = r.headers
            waits = [_seconds(h.get("x-ratelimit-reset-tokens"))]
            if h.get("x-ratelimit-remaining-requests") == "0":
                waits.append(_seconds(h.get("x-ratelimit-reset-requests")))
            wait = max((w for w in waits if w is not None), default=None)
        raise _Retryable(r.status_code, wait)
    if r.status_code == 400 and "json_validate_failed" in r.text:
        raise _InvalidGeneration(r.text[:200])
    if r.status_code >= 400:
        raise RuntimeError(f"LLM API error {r.status_code}: {r.text[:300]}")


def parse_json(text: str) -> dict | None:
    """First JSON object in a model reply (tolerates code fences and chatter)."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                try:
                    obj = json.loads(text[start:i + 1])
                    return obj if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    break
        start = text.find("{", start + 1)
    return None
