# Design decisions

Record of choices the paper (`QueryToDiagnose.pdf`, Sec. III) leaves open, with
the 2022–2026 work that supports them. Bracketed numbers are the paper's own
references; other keys are in `paper/references_2022_2026.bib`, which is design
justification only and is not cited in the paper.

Status: decisions 1–11 and the literature-driven adjustments were accepted on
2026-10-28. The fault-schema changes below are new in Phase 1 and await review.

## 1. Under-specified points in the method (accepted)

| # | Under-specified point | Default | Support |
|---|---|---|---|
| 1 | "Agree on every schema field" fails for free-text fields | LLM emits only closed-set schema values or `unmentioned`; samples cluster iff their attribute dicts are equal | [13] Kuhn 2023, [9] Farquhar 2024, `lin2024generating` |
| 2 | p(z\|s) and the prior p(z) | Naive Bayes over the attributes s mentions; uniform p(z) (sources give no base rates; benchmark frequencies would leak labels) | `xu2023bnac`, `choudhury2026bedllm` |
| 3 | Answer likelihood p(a\|q,s,z) in eq. (2) | If s fixes the asked attribute, answer = s's value w.p. 1−ε; else p(value\|z). ε = 0.05; "not sure" w.p. η = 0.05, uninformative | `choudhury2026bedllm`, `balog2024user` |
| 4 | Sources give no probabilities | Typical / possible / atypical tags with cited passages; weights in `configs/hypothesis.yaml` (default 1.0 / 0.25 / 0.01); sensitivity experiment over five weight sets | `capstick2025autoelicit`, `xu2023bnac` |
| 5 | 0.8 / 0.2 fault-state thresholds leave gaps | `unmentioned` is a value; confirmed if a mentioned value ≥ 0.8, unknown if `unmentioned` ≥ 0.8, else uncertain | `sun2024dst`, [1] Huang 2026 |
| 6 | Fig. 2 stops on τ alone; Sec. III-F requires evidence | Follow III-F; an unsafe top fault stops and refers at τ | [4] Wen 2025, [7] MediQ, `abbasiyadkori2024conformal` |
| 7 | Algorithm 1 undefined when Q_t is empty | Stop if no candidates or best E[ΔH] < 0.01 bits; each attribute asked at most once | [1] Huang 2026, `li2025questbench` |
| 8 | "Retrieved passage supports z" | z is in the fault tags (`data/sources/passage_faults.yaml`) of any top-5 chunk | `gao2023alce`, `asai2024selfrag` |
| 9 | How to score A(q) | Share of mock-user replies (3 personas × each true value) that do not parse back to the intended value; cached per template | [5] Zhang & Choi 2025, [2] ClarifyMT, `ni2026survey` |
| 10 | Gold label for REFER | REFER if `user_safe: false`, or if an all-attributes oracle cannot reach τ on z*; report action-level macro-F1 and fault-level top-1 accuracy | [1] Huang 2026, `li2025questbench` |
| 11 | λ, μ tuning objective | Grid λ, μ ∈ {0, 0.1, 0.25, 0.5, 1}; maximise validation action macro-F1, tie-break fewer turns; entropies in bits | — |

## 2. Literature-driven adjustments (accepted)

| Area | Change | Support |
|---|---|---|
| User simulator | Rule-based (question → attribute → gold value), never an LLM judging its own family | `panickssery2024llm`, `balog2024user` |
| Retrieval query | Built from normalised confirmed attributes, not raw text | `zhuang2022characterbert`, [11] Cho 2024 |
| Multilingual retriever | `intfloat/multilingual-e5-small` | `wang2024me5`, `douze2024faiss` |
| Calibration | Smooth ECE reported alongside binned ECE and Brier | `blasiok2024smooth`, `geng2024survey` |
| Question quality | Observed information gain per turn | `pedrozo2026reasoning` |
| Spelling variants | Rules modelled on NL-Augmenter character perturbations | `dhole2023nlaugmenter` |

## 3. Data sources

Policy: iFixit and U.S. public-domain pages only. No manufacturer manuals, not
even locally. Fetched with `make sources`, pinned to page revisions, credited in
`data/sources/LICENSES.md` (generated).

| Source | Licence | Content used |
|---|---|---|
| iFixit: 13 generic-refrigerator troubleshooting pages + 5 background pages + the Refrigerator device page | CC BY-NC-SA 3.0 | 265 section-level passages |
| ENERGY STAR "Refrigerators" (U.S. EPA), Saving Tips section | Public domain (17 U.S.C. 105) | 1 passage (temperature, placement, coils, seals) |

- Licensing split: code MIT; any file reproducing iFixit text CC BY-NC-SA 3.0 (see `NOTICE`).
- iFixit's Terms of Use prohibit training ML/AI models on its content. This
  project trains nothing on it: the hypothesis model is hand-tagged, retrieval
  embeds passages with a pretrained encoder, and the only fitted quantities
  are λ and μ (two scalars, grid-searched on validation). The team has emailed
  legal@ifixit.com to confirm; record the reply here.
- Coverage gaps (sources are U.S.-centric): no error-code tables, nothing on
  voltage stabilisers or direct-cool single-door units, no fan "squeal" noise.
  These rows stay uniform rather than being filled from memory.

## 4. Fault schema changes in Phase 1 (await review)

`data/schema/fault_schema.yaml` v0.2 has 15 faults (13 proposed + 2):

| Change | Reason |
|---|---|
| Added `excess_frost_manual_defrost` (safe) | iFixit separates "defrost a manual-defrost freezer" from "thick ice in an auto-defrost unit means the defrost cycle failed" (`ifx-505020-excessive-frost-buildup`); the first is the common direct-cool complaint in India |
| Split `hot_surroundings` (safe) out of `blocked_airflow` | Separate iFixit causes ("Extreme External Temperatures" vs "Incorrectly Loaded"); one naive-Bayes class for both would expect both signs in every case |
| `control_board_wiring` now names thermostat, thermistor, damper, boards and wiring | Matches the iFixit sections assigned to it; kept as one class because all its parts are unsafe (always REFER) |
| `drain_blockage` includes a cracked drain pan | iFixit lists both under "Refrigerator Leaking Water" |

## 5. Hypothesis model

- Rows in `data/hypothesis_model.yaml` follow the tagging protocol in its header.
  Of 270 (fault, attribute) rows: 67 cite passages, 19 are definitional (each
  with a rationale), 184 are uniform (no evidence).
- Sanity check: `make heatmap` prints provenance counts, I(Z; A) per attribute
  and writes `results/sanity/hypothesis_heatmap.png`.
- Sensitivity: weight sets `base`, `flat`, `sharp`, `soft_atypical`,
  `hard_atypical` in `configs/hypothesis.yaml`; Phase 5 reruns Q2D and B3 on
  each and reports the spread.

## 6. Language pairs

Hindi–English is a second language pair, paired with Kannada–English on the
same underlying cases.

**Conditions (7).** `clean`, `spelling`, `codemixed_kn`, `codemixed_hi`,
`incomplete`, `combined_kn`, `combined_hi`. Every variant carries
`lang_pair: kn-en | hi-en | none` (`none` for clean, spelling, incomplete), so
results group by noise type and by language.

**Coverage.** Hindi variants are generated first for the validation and test
splits (~100–150 cases); train follows if time allows. Kannada and Hindi
variants share underlying cases, so kn-en vs hi-en is a paired comparison.

**Lexicons.** `data/lexicon/kn_en.yaml` and `data/lexicon/hi_en.yaml`
(Romanized Hindi such as "nahi ho raha", "thanda nahi", "awaaz aa rahi hai",
"band nahi ho raha", "bahut", "paani tapak raha", with spellings like
"nai / nahin / nhi"). Each entry records its provenance: `hand`,
`aksharantar` or `comi-lingua`.

**Seed resources (2022–2026), licences checked 2026-10-28.**

| Resource | Pair | Licence (where checked) | Use |
|---|---|---|---|
| Aksharantar (`madhani2023aksharantar`) | hi, kn | Manually collected data CC-BY, mined data CC0 (Hugging Face README) | Attested Romanized spellings of native words |
| COMI-LINGUA (`sheth2025comilingua`) | hi | CC-BY-4.0 (Hugging Face card) | Frequencies of Romanized Hindi spellings in real Hinglish |
| L3Cube-HingCorpus (2022) | hi | No licence in repository | Not used |
| CoLI-Kanglish (`balouchzahi2022coli`) | kn | No licence found | Background only, data not used |

**Annotation.** The variant CSV export has a `lang_pair` column so Hindi- and
Kannada-speaking teammates can hand-write and correct variants. Hand-written
variants are `genuine` or `transformed`; generated ones are `synthetic`.

**Stress set (optional).** ~30 cases mixing Kannada, Hindi and English in one
message (`lang_pair: kn-hi-en`), reported separately and never inside the main
tables.

**Reporting.** Main results and the robustness curve are broken down by the 7
conditions; an extra table compares kn-en vs hi-en on the paired cases
(codemixed and combined). The website demo has example chips in both
languages.

## 7. References policy

- The paper keeps exactly the 15 references in `references.bib`.
- Classic methods (McNemar, Wilcoxon, Holm, bootstrap, Cohen's κ, Brier, ECE)
  are named without citations; no pre-2022 papers are added to any bib.
- Candidate swaps for the authors to consider (not applied):
  - [8] STaR-GATE → `choudhury2026bedllm`. Eq. (3) is sequential Bayesian
    experimental design with an explicit prior and likelihood; BED-LLM is the
    closest formal precedent, while STaR-GATE concerns training, which this
    work does not do.
  - [12] Xu et al. (KG-RAG) → `madhani2023aksharantar`, if Sec. IV describes
    the lexicon seeding; otherwise → `caminha2025hwdiag`, which diagnoses
    hardware faults from free-text user reports (closer domain than
    single-turn ticket retrieval).
  - No swap needed for Hindi: [10] RomanSetu and [15] Zhang et al. (which
    evaluates Hindi–English) already cover Romanized Hindi.
