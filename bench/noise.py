"""Rule-based spelling noise for the `spelling` and `combined_*` conditions:
phonetic respellings, keyboard-adjacent substitutions, dropped and doubled
letters, swapped neighbours (character perturbations in the style of
NL-Augmenter). Seeded through the caller's random.Random."""

from __future__ import annotations

import random
import re

PHONETIC = {
    "compressor": ["compresser", "compresor", "kompressor"],
    "fridge": ["fridg", "frige", "fridje"],
    "refrigerator": ["refrigirator", "refridgerator", "frigerator"],
    "cooling": ["kooling", "coolng", "colling"],
    "freezer": ["freezar", "frezer", "freeser"],
    "water": ["watr", "woter"],
    "noise": ["noice", "nois"],
    "sound": ["sond", "saund"],
    "door": ["dor", "doar"],
    "frost": ["frst", "forst"],
    "running": ["runing", "runnin"],
    "leaking": ["leeking", "leakin"],
    "light": ["lite", "ligt"],
    "temperature": ["temprature", "tempreture"],
    "thermostat": ["thermostate", "termostat"],
    "coils": ["coyls", "coil"],
    "socket": ["soket", "sockt"],
    "display": ["dispaly", "disply"],
    "properly": ["proprly", "properley"],
    "because": ["bcoz", "bcz"],
    "nothing": ["nthing", "nothng"],
    "humming": ["huming", "hummin"],
}

ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
NEIGHBOURS: dict[str, str] = {}
for r, row in enumerate(ROWS):
    for c, ch in enumerate(row):
        near = [row[c - 1] if c > 0 else "", row[c + 1] if c + 1 < len(row) else ""]
        for rr in (r - 1, r + 1):
            if 0 <= rr < len(ROWS) and c < len(ROWS[rr]):
                near.append(ROWS[rr][c])
        NEIGHBOURS[ch] = "".join(n for n in near if n)


def _perturb(word: str, rng: random.Random) -> str:
    lower = word.lower()
    if lower in PHONETIC and rng.random() < 0.6:
        return rng.choice(PHONETIC[lower])
    i = rng.randrange(1, len(word))   # keep the first letter, as most typos do
    op = rng.choice(["adjacent", "drop", "double", "swap"])
    if op == "adjacent" and word[i].lower() in NEIGHBOURS:
        return word[:i] + rng.choice(NEIGHBOURS[word[i].lower()]) + word[i + 1:]
    if op == "drop":
        return word[:i] + word[i + 1:]
    if op == "double":
        return word[:i] + word[i] + word[i:]
    if i + 1 < len(word):
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    return word[:i]


def add_typos(text: str, rate: float, rng: random.Random) -> str:
    """Perturb each word of 3+ letters with probability `rate`; then, half the
    time, drop capitals and final punctuation as hurried typists do."""
    tokens = re.split(r"(\W+)", text)
    out = [_perturb(t, rng) if t.isalpha() and len(t) >= 3 and rng.random() < rate else t for t in tokens]
    noisy = "".join(out)
    if rng.random() < 0.5:
        noisy = noisy.lower().rstrip(".")
    return noisy
