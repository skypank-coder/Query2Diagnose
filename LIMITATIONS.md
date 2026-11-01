# Limitations

Written to be adapted for the paper. Each point names where it shows up in the
repository so it can be checked.

## Users are simulated
- Answers come from a rule-based simulator that maps a question to a schema
  attribute and reads the hidden ground truth (`sim/user_simulator.py`). Real
  users misread questions, answer partially, change the subject and give up.
  The noisy mode (wrong value, "not sure", code-mixed answers with typos) only
  approximates this. A consented study with real users is needed before any
  claim about deployed behaviour.
- The simulator answers in option-label phrasing that the answer parser was
  written against, so answer parsing is easier in simulation than with real
  replies.

## Variants are synthetic until annotated
- All 1,740 variants and the 30 stress items are generated from templates
  (`provenance: synthetic`). Kannada and Hindi templates were written by the
  team and still need native-speaker correction through the annotation CSV.
- Templates, lexicons and the normaliser come from the same team, so
  normalisation probably helps more on synthetic text than on real messages.
  Lexicons were seeded from external resources (Aksharantar, COMI-LINGUA) to
  reduce this, and results on `genuine` variants must be reported separately
  once they exist. Cohen's κ is "not run yet" until two annotators label the
  shared sheet.

## One appliance, two language pairs, U.S.-centric sources
- Only domestic refrigerators; 15 fault categories; 47 scenarios (2-4 per
  fault). Faults outside the schema (ice makers, water dispensers, levelling
  noise) are not modelled.
- Only Romanized Kannada-English and Hindi-English (Hindi on validation and
  test only so far); no native-script input; the trilingual stress set is 30
  items.
- iFixit and ENERGY STAR describe U.S. appliances. Error codes, voltage
  stabilisers and Indian direct-cool single-door units are thinly covered;
  the corresponding hypothesis-model rows stay uniform rather than being
  filled from memory.

## The hypothesis model is hand-built
- Qualitative tags (typical / possible / atypical / unlisted) turned into
  probabilities by fixed weights; results depend on these weights (the
  sensitivity experiment measures how much). With every attribute known, the
  model reaches τ on the true fault for only part of the identifiable cases
  (the "model ceiling", `docs/design_decisions.md` §5b), which caps B3 and Q2D.
- Naive Bayes assumes attributes are independent given the fault, which they
  are not (no power ⇒ compressor and fans off). Correlated evidence is
  double-counted.
- The single-fault healthy default is shared by the model and the benchmark
  generator. It is a standard diagnostic assumption, but real appliances can
  have several problems at once.

## Gold labels and evaluation
- "Underdetermined" is defined against the 47 scenarios: a case is REFER if
  another fault's scenario produces the same attribute vector. A larger
  scenario set would change some labels.
- Recall@k counts near-duplicate passages as hits because iFixit repeats
  sections verbatim; the threshold (Jaccard ≥ 0.9) is a choice.
- A(q) is an estimate: an LLM (gpt-oss-120b) role-plays three user personas.
  A first estimate was inflated for the compartment question by an answer
  parser bug; it was fixed and A(q) re-estimated before the pilot.

## What the full run shows about the method
From `results/runs/20261029T170525Z` (all 7 conditions, 3 seeds; see
`REPRODUCE.md`). These are properties of the method with this LLM, simulator
and hypothesis model, not code errors.
- **Over-referral.** Q2D's abstention recall is 0.97 but its precision is
  0.48: about half of its referrals were cases it could have answered. Most
  dialogues end at T_max = 6 with the correct fault on top but below τ = 0.75,
  so its action macro-F1 (0.19) is the lowest of the four main systems even
  though its fault top-1 (0.65) is far above B2's (0.36).
- **Calibration has two sides.** In the confidence bins from 0.25 to 0.84
  accuracy exceeds confidence (under-confident), while the top bin
  (confidence 0.96, 79 dialogues) has accuracy 0.53 (over-confident).
- **No measurable gain from H_L, cost/clarity or normalisation here.**
  Removing H_L scores 0.22 against 0.19 with overlapping intervals; λ = μ = 0
  won the validation grid, so cost/clarity is inactive; removing
  normalisation changes nothing. Q2D also asks more questions than B3 and B2
  (5.7 against 5.5 and 5.2 mean turns; Wilcoxon p < 0.001).
- **Hypothesis weights dominate.** With the `sharp` weight set, Q2D reaches
  0.42 macro-F1 and B3 0.41 (seed 0), above B2's 0.37, but that set was
  compared on the test split, so it cannot be claimed as a result. Choosing
  the weights or τ on validation would have to be declared and rerun.
- **Retrieval is weak.** Recall@5 of the gold passage is 0.28 for Q2D and
  0.12 for B1/B2, so many answers are grounded in a related rather than the
  source passage.

## Compute
- One system LLM: `gpt-oss-20b` (open weights) run locally under Ollama on a
  12 GB laptop GPU. Results with a second, different model would show
  whether the comparison holds across LLMs.
- No noisy-simulator run yet; every reported number uses the deterministic
  simulator.
- iFixit's Terms of Use prohibit training ML models on its content. No model
  is trained here; λ and μ are two scalars grid-searched on validation.
  Confirmation from iFixit was requested by the team.
