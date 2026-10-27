"""Download the source documents listed in data/sources/manifest.yaml.

iFixit pages come from the public API (one request per page, 3 s apart) and
are stored trimmed to the fields we need, pinned to their revision id. Pages
already on disk are skipped unless --refresh is given, so the corpus does not
drift between runs. Public-domain pages are reduced to the listed sections.

Run with `python -I -m bench.fetch_sources` (downloaded files are untrusted).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone

import requests
import yaml
from bs4 import BeautifulSoup

from core.paths import SOURCES_MANIFEST, SOURCES_RAW

USER_AGENT = "Query2Diagnose-research/0.1 (non-commercial academic project, RV University)"
DELAY_S = 3.0
MAX_TRIES = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get(session: requests.Session, url: str) -> requests.Response:
    for attempt in range(1, MAX_TRIES + 1):
        resp = session.get(url, timeout=30)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        wait = float(resp.headers.get("Retry-After", 30 * attempt))
        print(f"  429 from server, waiting {wait:.0f}s (attempt {attempt}/{MAX_TRIES})")
        time.sleep(wait)
    raise RuntimeError(f"rate-limited after {MAX_TRIES} tries: {url}")


def fetch_ifixit(session: requests.Session, cfg: dict, refresh: bool) -> None:
    out_dir = SOURCES_RAW / "ifixit"
    out_dir.mkdir(parents=True, exist_ok=True)
    for page in cfg["pages"]:
        ns, title = page["namespace"], page["title"]
        path = out_dir / f"{ns.lower()}__{title}.json"
        if path.exists() and not refresh:
            print(f"skip   {title} (on disk)")
            continue
        api_url = f"{cfg['api']}/{ns}/{title}"
        d = _get(session, api_url).json()
        url = (f"https://www.ifixit.com/Device/{title}" if ns == "CATEGORY"
               else f"https://www.ifixit.com/Wiki/{title}")
        record = {
            "source": "ifixit",
            "namespace": d["namespace"],
            "title": d["title"],
            "display_title": d.get("display_title") or d["title"],
            "wikiid": d["wikiid"],
            "revisionid": d["revisionid"],
            "langid": d.get("langid"),
            "modified_date": datetime.fromtimestamp(d["modified_date"], timezone.utc).isoformat(),
            "url": url,
            "api_url": api_url,
            "authors": [a.get("username") for a in d.get("authors") or []],
            "license": cfg["license"],
            "license_url": cfg["license_url"],
            "terms_url": cfg["terms_url"],
            "fetched_at": _now(),
            "contents_raw": d["contents_raw"],
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"saved  {title} (rev {record['revisionid']})")
        time.sleep(DELAY_S)


def _section_text(soup: BeautifulSoup, heading: str) -> str | None:
    """Paragraph and list text inside the container that holds the heading
    whose text equals `heading` (each section on the page is its own panel)."""
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        if tag.get_text(" ", strip=True).lower() != heading.lower():
            continue
        parts = []
        for el in tag.parent.find_all(["p", "li"]):
            text = el.get_text(" ", strip=True).replace("\xa0", " ")
            if text and text not in parts:
                parts.append(("- " if el.name == "li" else "") + text)
        return "\n".join(parts) if parts else None
    return None


def fetch_public_domain(session: requests.Session, items: list[dict], refresh: bool) -> None:
    out_dir = SOURCES_RAW / "public_domain"
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        path = out_dir / f"{item['id']}.json"
        if path.exists() and not refresh:
            print(f"skip   {item['id']} (on disk)")
            continue
        html = _get(session, item["url"]).text
        soup = BeautifulSoup(html, "html.parser")
        sections = {h: _section_text(soup, h) for h in item["sections"]}
        missing = [h for h, t in sections.items() if not t]
        if missing:
            raise RuntimeError(f"{item['id']}: sections not found on page: {missing}")
        record = {
            "source": "public_domain",
            "id": item["id"],
            "url": item["url"],
            "publisher": item["publisher"],
            "license": item["license"],
            "fetched_at": _now(),
            "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "title": soup.title.get_text(strip=True) if soup.title else item["id"],
            "sections": sections,
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"saved  {item['id']}")
        time.sleep(DELAY_S)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true", help="re-download pages already on disk")
    args = ap.parse_args()
    manifest = yaml.safe_load(SOURCES_MANIFEST.read_text(encoding="utf-8"))
    with requests.Session() as session:
        session.headers["User-Agent"] = USER_AGENT
        fetch_ifixit(session, manifest["ifixit"], args.refresh)
        fetch_public_domain(session, manifest["public_domain"], args.refresh)


if __name__ == "__main__":
    main()
