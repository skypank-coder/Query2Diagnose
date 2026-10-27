"""Import hand-written / corrected variants from native speakers.

Annotators fill copies of annotation/export/variants_to_annotate.csv and save
them under annotation/filled/. Rows with `corrected_text` become new variants:
`genuine` if `written_from_scratch` is yes, otherwise `transformed`. They keep
the original's condition, lang_pair and mentioned attributes (annotators are
asked to express the same facts). Output: data/benchmark/variants_human.jsonl.
"""

from __future__ import annotations

import csv
import re

from core.records import BENCHMARK, Variant, write_jsonl

FILLED = BENCHMARK / "annotation" / "filled"
HUMAN_FILE = BENCHMARK / "variants_human.jsonl"


def main() -> None:
    out: list[Variant] = []
    for path in sorted(FILLED.glob("*.csv")):
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                text = (row.get("corrected_text") or "").strip()
                if not text:
                    continue
                annotator = re.sub(r"\W+", "_", (row.get("annotator") or path.stem).strip().lower())
                scratch = (row.get("written_from_scratch") or "").strip().lower() in ("yes", "y", "1", "true")
                out.append(Variant(
                    variant_id=f"{row['variant_id']}-h-{annotator}",
                    case_id=row["case_id"],
                    condition=row["condition"],
                    lang_pair=row["lang_pair"],
                    text=text,
                    mentioned_attributes=[a for a in row["mentioned_attributes"].split(";") if a],
                    provenance="genuine" if scratch else "transformed",
                    generator=f"human:{annotator}",
                ))
    write_jsonl(HUMAN_FILE, out)
    print(f"{len(out)} human variants from {FILLED.relative_to(BENCHMARK)} -> {HUMAN_FILE.name}")


if __name__ == "__main__":
    main()
