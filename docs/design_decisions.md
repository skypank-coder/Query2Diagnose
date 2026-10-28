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

## 4. Fault schema changes (await review)

`data/schema/fault_schema.yaml` v0.3: 15 faults (13 proposed + 2), 20 attributes (18 proposed + 2).

| Change | Reason |
|---|---|
| Added `excess_frost_manual_defrost` (safe) | iFixit separates "defrost a manual-defrost freezer" from "thick ice in an auto-defrost unit means the defrost cycle failed" (`ifx-505020-excessive-frost-buildup`); the first is the common direct-cool complaint in India |
| Split `hot_surroundings` (safe) out of `blocked_airflow` | Separate iFixit causes ("Extreme External Temperatures" vs "Incorrectly Loaded"); one naive-Bayes class for both would expect both signs in every case |
| `control_board_wiring` names thermostat, thermistor, damper, boards and wiring | Matches the iFixit sections assigned to it; one class because all parts are unsafe (always REFER) |
| `drain_blockage` includes a cracked drain pan | iFixit lists both under "Refrigerator Leaking Water" |
| Added `noise_location` (inside / back-bottom / none) | Both iFixit noise pages diagnose by where the sound comes from ("Sounds from down low in the rear ... condenser fan or compressor"; "from the freezer area ... evaporator fan") |
| Added `works_in_other_socket` | iFixit's own test separates supply from appliance faults ("Run an extension to another outlet ... Still no power? Your fridge has an electrical issue"); without it every power case was indistinguishable from wiring leakage |
| `ice_buildup` vs `frost_buildup` defined | ice_buildup = solid ice at the bottom (drain); frost_buildup = frost/ice on walls (the "Freezer Ice Building Up" page) |

## 5. Hypothesis model

- `data/hypothesis_model.yaml` v0.4 follows the tagging protocol in its header.
  Of 300 (fault, attribute) rows: 79 cite passages, 17 are definitional (each
  with a rationale), 173 use the single-fault healthy default, 31 are uniform.
- **Single-fault healthy default.** A (fault, attribute) pair without a row
  takes the working-unit value as typical: components a fault does not
  involve behave normally. Without it, a healthy door seal was 50/50 under
  every non-door fault and nothing could be ruled out.
- **Closed world for symptom pages.** For the six symptoms with an iFixit page
  that enumerates its causes, a fault the page does not list gets the
  `unlisted` level (weight 0.05) instead of `possible`.
- **Hedged sources.** Where a passage says a fault *may* cause a sign, or the
  fault has several presentations (stopped vs noisy fan), the unaffected value
  is tagged typical as well.
- Sanity check: `make heatmap` prints provenance counts and I(Z; A) per attribute.
- Sensitivity: weight sets `base`, `flat`, `sharp`, `soft_atypical`,
  `hard_atypical` in `configs/hypothesis.yaml`; Phase 5 reruns Q2D and B3 on each.

## 5b. Benchmark construction

- **Scenarios, not model samples.** 47 scenarios (`data/benchmark/scenarios.yaml`),
  each citing one passage with a verbatim quote (tested), fix the
  fault-specific attributes; every other attribute takes its healthy value.
  Cases are never sampled from the hypothesis model the systems use.
- **Model-free gold labels.** REFER if the fault is unsafe, or if a scenario
  of another fault can produce exactly the same full attribute vector
  (`confusable_faults`). Result: 179 identifiable, 41 underdetermined, 80
  unsafe; 121 of 300 gold actions are REFER.
- **Model ceiling** (diagnostic, not a label): with every attribute known, the
  hypothesis model reaches τ = 0.75 on the true fault for 106 / 179
  identifiable cases with the base weights, 150 with `sharp`, 31 with `flat`.
  The weight choice caps Q2D/B3 accuracy more than question selection can;
  the sensitivity experiment measures this.
- **Omission** (`incomplete`, `combined_*`): keep the symptom; remove a random
  non-empty subset of the scenario-specific mentions, other mentions with
  probability 0.4, the compartment half the time.
- **Spelling noise**: phonetic respellings, keyboard-adjacent substitutions,
  dropped / doubled / swapped letters (`bench/noise.py`).
- **Circularity caveat.** Templates, lexicons and the normaliser were written
  by the same team, so normalisation is likely to help more on synthetic
  variants than on real messages. Lexicons are seeded from external
  resources (below) and results on `genuine` variants are reported separately.

## 5c. Core method implementation (Phase 3)

| Component | Choice |
|---|---|
| LLM | `openai/gpt-oss-20b` on Groq (Llama 3.1 8B was retired); `reasoning_effort: low`, +400 max tokens for hidden reasoning. One client, disk cache keyed by (provider, model, prompt, temperature, seed), budget guard, RPM/TPM throttle, clean stop when the daily quota (1,000 requests/day on the free tier) is exhausted |
| Understanding | Strict JSON prompt over the closed schema (~810 tokens); K = 8 samples at T = 0.7 with distinct seeds; invalid samples retried twice; exact-match clustering on the attribute dict; the normaliser's gloss is passed alongside the original text |
| Normalisation | Lexicon forms (longest match, up to 3 words, language chosen by unambiguous hits) → fuzzy match to Romanized forms (85) and to the schema/template vocabulary (80), then to general passage English (88); English words are never rewritten |
| Answer model | ε = 0.05 wrong value, η = 0.05 "not sure" (uninformative), exactly as decision 3; verified by hand-computed tests |
| E[ΔH] | Exact enumeration of every answer incl. "not sure" over the joint (s, z) belief; a clarification on an attribute that does not separate faults gains exactly H_L (tested) |
| A(q) | Mock users are told what they *observe* (the English template phrase) and answer in their own words; A(q) = share of replies that do not parse back to the intended value. Stored per model in `data/clarity/` |
| Answer parsing | Rules first (not-sure phrases in 3 languages, negation-aware yes/no, fuzzy option and template matching), LLM fallback only when nothing matches |
| Retrieval | `multilingual-e5-small` + FAISS over 299 chunks; query = English phrases of the confirmed facts + the top fault's name. Oracle-fact queries retrieve a passage supporting the true fault in the top 5 for 83 % of cases. iFixit repeats sections verbatim across pages, so Recall@k counts a near-duplicate of the gold passage as a hit |
| Observed limitation | With 15 faults and base weights a single answer mostly eliminates one fault, so H_D falls slowly and τ = 0.75 is often not reached within T_max = 6 (cf. the model ceiling in 5b) |

## 5d. Baselines, ablations and simulator (Phase 4)

| System | Definition |
|---|---|
| B1 `b1_direct` | One LLM call: opening message + 5 passages retrieved with the raw message → fault, DIY/refer, confidence, guidance |
| B2 `b2_llm_questions` | Same LLM and passages; each turn it asks one question or answers; must name the schema attribute it asks about so the rule-based simulator can answer it (otherwise a keyword mapper would unfairly misread its questions); same T_max |
| B3 `b3_infogain_dx` | Q2D pipeline with one greedy interpretation (K = 1, H_L = 0), no clarification, λ = μ = 0 → expected information gain over faults only |
| Q2D `q2d` | Full system, λ and μ from validation tuning |
| `q2d_minus_hl` | K = 1, no clarification, keeps λ, μ |
| `q2d_minus_fault_state` | An LLM re-reads the dialogue each turn and outputs the state; no interpretation sampling, no answer model |
| `q2d_minus_cost_clarity` | λ = μ = 0 |
| `q2d_minus_normalisation` | No lexicon / fuzzy gloss |

Simulator (`sim/user_simulator.py`): question → attribute (structured attribute when given, else ordered keyword rules that map all 19 Q2D questions correctly — tested) → gold value → option label. Never sees the fault. Unmappable questions get "I don't know". Noisy mode: wrong value (10 %), "not sure" (10 %), answers in the variant's language with typos. Main runs use deterministic mode; noisy mode is a robustness run.

## 5e. Evaluation protocol (Phase 5)

| Metric | Definition |
|---|---|
| Action accuracy / macro-F1 | Predicted action (fault id or REFER) vs gold action; REFER is a class; macro over every label in gold ∪ predicted |
| Fault accuracy | Top fault (also reported when referring) vs the hidden fault |
| Slot P/R/F1 | Most probable interpretation vs the gold values of the attributes the variant mentions (agent systems) |
| Status accuracy | Turn-0 fault state: mentioned attribute confirmed with the right value, or unmentioned attribute marked unknown; `uncertain` never counts as correct |
| Informative / redundant questions | Informative: asks about a scenario-specific attribute not already stated; redundant: asks about a stated attribute |
| IG per turn | One shared observer starts from the message's gold facts and applies each answered (attribute, intended value); mean drop in H_D — the same yardstick for B2, B3 and Q2D |
| Accuracy vs turns | Agent transcripts truncated at each budget (forced decision: answer if top ≥ τ, safe and supported, else REFER); B1/B2 at their mean turns |
| Calibration | Confidence in the top fault vs top-fault correctness: 15-bin ECE, Smooth ECE (`relplot`), Brier, reliability bins; selective accuracy vs coverage and AURC |
| Abstention | REFER precision / recall against gold REFER |
| Unsafe advice | Share of unsafe-fault cases answered with DIY guidance instead of REFER |
| Retrieval Recall@k | Gold source passage or any near-duplicate (word-set Jaccard ≥ 0.9; iFixit repeats sections verbatim) among the final top-k |
| Statistics | 95 % case-level bootstrap CIs (1,000 resamples); exact McNemar (action correctness) and Wilcoxon signed-rank (turns), Q2D vs each baseline, Holm-corrected per scope |

- **Cost control.** Greedy calls (B1, B2, B3, `q2d_minus_hl`) use seed 0 for the LLM, so extra seeds only re-sample Q2D's interpretations and the noisy simulator. `q2d_minus_hl` shares B3's parse and `q2d_minus_cost_clarity` shares Q2D's samples through the cache.
- **Pilot profile** (`make pilot`): one test case per fault (15) × 7 conditions, seed 0, K = 4, the four main systems plus the two zero-cost ablations, λ = μ = 0.1 untuned. Fits the Groq free tier (1,000 requests/day for the system model). Reported as a pilot, never as the full grid.
- **A(q) model.** The mock users that estimate A(q) run on `openai/gpt-oss-120b` (a separate quota), not the system model. A(q) is a fixed property of the question templates shared by every Q2D variant; B3 does not use it.
- **Known issue found in the A(q) trials.** The rule-based answer parser read "both the fridge and the freezer" as `freezer` (longest label wins), inflating A(compartment_affected) to 0.33. Fixed after the pilot (the pilot ran the code as committed in Phase 5); A(q) must be re-estimated before the full run.

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

**Lexicons.** `data/lexicon/kn_en.yaml` (64 entries) and
`data/lexicon/hi_en.yaml` (80 entries) are hand-written (Romanized Hindi such
as "nahi ho raha", "thanda nahi", "awaaz aa rahi hai", "band nahi ho raha",
"bahut", "paani tapak raha", with spellings like "nai / nahin / nhi").
`bench/seed_lexicon.py` adds attested spellings to `data/lexicon/seeds.json`,
each with its source and count: 19 new Kannada spellings (Aksharantar) and
334 new Hindi spellings (259 COMI-LINGUA, 75 Aksharantar), e.g. "nehi",
"nhin", "bohut", "bhaut", "aavaaz", "hamesa". Filters: at least 3 letters;
within 2 edits of a hand form of the same entry (1 edit for words of 4 letters
or fewer); not a hand form of another entry; not an English word in the
domain vocabulary; COMI-LINGUA alignments seen at least 3 times.

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
