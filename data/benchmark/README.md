# Benchmark

Refrigerator troubleshooting cases rendered under seven input conditions.
Rebuild everything with `mingw32-make benchmark` (Linux/macOS: `make benchmark`).

| File | Contents |
|---|---|
| `scenarios.yaml` | 47 hand-written scenarios; each cites one source passage and quotes it verbatim |
| `templates/{en,kn,hi}.yaml` | Phrase templates (English, Romanized Kannada-English, Romanized Hindi-English) |
| `cases.jsonl` | 300 underlying cases (20 per fault): hidden fault, full attribute vector, clean description, gold action |
| `splits.json` | Case-level 60/20/20 split, stratified by fault |
| `variants.jsonl` | 1,740 variants: 5 conditions for every case, Hindi conditions for val + test |
| `variants_stress.jsonl` | 30 Kannada + Hindi + English test cases (reported separately) |
| `variants_human.jsonl` | Native-speaker variants imported from `annotation/filled/` (genuine / transformed) |
| `annotation/export/` | Regenerated sheets for annotators (never edit these in place) |

Every generated record has `provenance: synthetic`; human-written variants are
`genuine` (written from scratch) or `transformed` (a corrected synthetic one).

## Gold labels (no dependence on the hypothesis model)

- `gold_action = REFER` if the fault is unsafe (`user_safe: false`).
- `gold_action = REFER` if the case is *underdetermined*: a scenario of another
  fault can produce exactly the same full attribute vector, so no question in
  the schema can separate them (`confusable_faults` lists them).
- Otherwise `gold_action` is the fault.

`oracle_posterior` (the hypothesis model's p(fault | every attribute)) is a
diagnostic of the model's ceiling, not a label.

## For annotators (Kannada and Hindi speakers)

1. Copy `annotation/export/variants_to_annotate.csv` to
   `annotation/filled/<your_name>.csv`.
2. Keep only rows in your language (`lang_pair` = `kn-en` or `hi-en`).
3. For each row you change, write the message the way you would actually type
   it in `corrected_text`, expressing the same facts as `clean_description`.
   Put `yes` in `written_from_scratch` if you wrote it fresh rather than
   editing `generated_text`. Fill `annotator`.
4. Run `mingw32-make annotations` to import them.

**Agreement (Cohen's κ).** Two annotators each fill a copy of
`annotation/export/kappa_sheet.csv` independently:
`label_meaning_preserved` (yes / partly / no) and `label_primary_symptom`
(one of the schema values). Then run
`python -I -m bench.validate --kappa annotation/filled/kappa_A.csv annotation/filled/kappa_B.csv`.
