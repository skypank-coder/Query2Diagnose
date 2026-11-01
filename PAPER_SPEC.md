# PAPER_SPEC.md — Query2Diagnose research paper rules

> Put this file in the repo root next to `paper/`. Claude Code must read it before touching anything in `paper/`, and must follow it over any other instruction about the paper.

## Team (authors of the paper, in this order)

| # | Name | Email |
|---|---|---|
| 1 | Saatwik Kumar Yadav | saatwikkumaryadavbtech24@rvu.edu.in |
| 2 | Rachana Bhaskar Gowda | rachanabhaskargowdabtech24@rvu.edu.in |
| 3 | Priyanshu Kumar Senapati | priyanshukumarsenapatibtech24@rvu.edu.in |
| 4 | S Md Adil Ahmed | smdadilahmedbtech24@rvu.edu.in |

**Affiliation (shared by all four):** School of Computer Science and Engineering, RV University, Bengaluru, India
**Programme:** B.Tech Computer Science and Engineering

Use these exact names and spellings everywhere: the paper's author block, the website's Home and Paper pages, the README, the BibTeX citation block for our own paper, and the footer of every generated figure or report that names authors. Never add or remove a name, change the order, or abbreviate a name (no initials). USNs are not printed anywhere.

Citation block for our own paper (website, README):

```bibtex
@misc{yadav2026query2diagnose,
  author = {Saatwik Kumar Yadav and Rachana Bhaskar Gowda and Priyanshu Kumar Senapati and S Md Adil Ahmed},
  title  = {{Query2Diagnose}: Uncertainty-Aware Interactive Troubleshooting from Noisy, Code-Mixed and Incomplete User Descriptions},
  note   = {School of Computer Science and Engineering, RV University, Bengaluru, India},
  year   = {2026}
}
```

---

## 1. Files and template

- Template: **IEEE conference** (`\documentclass[conference]{IEEEtran}`), the official IEEEtran class. Do not change margins, fonts, column widths or line spacing.
- Main file: `paper/query2diagnose_paper.tex`
- Bibliography: `paper/references.bib`, style `\bibliographystyle{IEEEtran}`, loaded with `\bibliography{references}` at the end.
- Generated content goes in `paper/tables/*.tex` and `paper/figures/*.pdf`, pulled in with `\input{}` and `\includegraphics{}`. Never paste numbers by hand into the main `.tex`.
- The paper must compile on **Overleaf** with pdfLaTeX + BibTeX, with zero errors, zero undefined references or citations, and no overfull boxes wider than 5pt.
- Packages allowed: `cite, amsmath, amssymb, amsfonts, algorithmic, graphicx, textcomp, xcolor, array, tikz, booktabs`. Ask before adding any other package.

## 2. Exact structure (the order our faculty gave us)

The faculty list numbers every item; in IEEE format items 1–4 are front matter and are not numbered sections. The numbered sections therefore start at Introduction = I.

| Faculty item | In the paper | Rules |
|---|---|---|
| 1. Title | `\title{}` | No symbols, maths, abbreviations (except the system name), or footnotes. Keep the current title unless I approve a change. |
| 2. Author details | `\author{}` | Exactly as in §3 below. |
| 3. Abstract | `\begin{abstract}` | One paragraph, 150–250 words. No symbols, maths, citations, footnotes or abbreviations that aren't defined in it. State the problem, gap, method, benchmark and (once available) the main measured result with its number. |
| 4. Keywords | `\begin{IEEEkeywords}` | 5–8 terms, lower case, alphabetical order, comma separated. |
| 5. Introduction | `\section{Introduction}` → **I** | Motivating example, gap, research questions RQ1–RQ4, contributions, paper outline. |
| 6. Related Work | `\section{Related Work}` → **II** | Grouped by theme with `\subsection`. Ends with the comparison table and a positioning paragraph. |
| 7. Methodology | `\section{Methodology}` → **III** | Problem formulation, system overview figure, input understanding, fault state, question selection, algorithm, retrieval/stopping/safety, benchmark design, planned comparisons. |
| 8. Experimental Setup | `\section{Experimental Setup}` → **IV** | Filled only from the real pipeline (see §6). |
| 9. Results & Discussion | `\section{Results and Discussion}` → **V** | Filled only from the real pipeline (see §6). |
| 10. Conclusion & Future Work | `\section{Conclusion and Future Work}` → **VI** | No new results; summary, limitations, future work. |
| 11. References | BibTeX | Exactly 15 entries, see §4. |

No other numbered sections. Allowed extras, unnumbered and only if I ask: `\section*{Acknowledgment}`. Limitations go inside Section V or VI, not as their own section.

## 3. Author block — use exactly this

One block per author, two authors per row (`\linebreakand` starts the second row; it is defined in the preamble). In each block: the name, then the author's own email directly below it, then the school, university and city. No USNs. (Changed on 2026-11-01 at the team's request; it replaced the earlier single-line block.)

```latex
\author{
\IEEEauthorblockN{Saatwik Kumar Yadav}
\IEEEauthorblockA{saatwikkumaryadavbtech24@rvu.edu.in\\
\textit{School of Computer Science and Engineering}\\
\textit{RV University}\\
Bengaluru, India}
\and
\IEEEauthorblockN{Rachana Bhaskar Gowda}
\IEEEauthorblockA{rachanabhaskargowdabtech24@rvu.edu.in\\ ... same three lines ...}
\linebreakand
\IEEEauthorblockN{Priyanshu Kumar Senapati}
\IEEEauthorblockA{priyanshukumarsenapatibtech24@rvu.edu.in\\ ... same three lines ...}
\and
\IEEEauthorblockN{S Md Adil Ahmed}
\IEEEauthorblockA{smdadilahmedbtech24@rvu.edu.in\\ ... same three lines ...}
}
```

- Name order is fixed as above.
- Email pattern: full name in lower case with no spaces, followed by `btech24@rvu.edu.in`.
- No `\thanks{}`, no funding footnote, no ORCID.

## 4. References — hard rules

- **Exactly 15** references in `references.bib`, all cited at least once in the text, none cited that aren't in the list.
- **Only papers published 2023–2026** (the recent past four years). No pre-2023 papers, including classic methods. Name classic methods (McNemar test, Wilcoxon signed-rank test, Holm correction, bootstrap, Cohen's κ, Brier score, ECE) in plain text **without** a citation.
- Prefer peer-reviewed venues (ACL/EMNLP/NAACL/Findings, NeurIPS, ICLR, COLM, SIGIR, TACL, Nature). arXiv preprints are allowed only for 2025–2026 papers with no published version yet.
- Every entry must be verified against the official page (ACL Anthology, publisher, proceedings, arXiv). Full author list where the source gives it; include `pages` and `doi` when the source lists them. Never guess a field; leave it out instead.
- Current 15 keys (keep unless I approve a swap): `huang2026mtinfoseek, luo2025clarifymt, deoliveira2025infoquest, wen2025abstention, zhang2025clarify, hu2024uot, li2024mediq, andukuri2024stargate, farquhar2024nature, husain2024romansetu, cho2024garag, xu2024kgrag, kuhn2023semantic, liu2023ambient, zhang2023codeswitchers`.
- Extra papers you find go in `docs/design_decisions.md` and `paper/references_extra.bib`, never into the paper's bibliography. To swap one in, propose: the paper to remove, the paper to add, and a one-line reason; wait for my approval. The count stays at 15.
- Citation style: `\cite{key}` placed before the punctuation, e.g. "...as shown in \cite{hu2024uot}." Multiple: `\cite{a,b}`. Write "Hu \textit{et al.} \cite{hu2024uot} proposed..." not "In \cite{hu2024uot}..." at the start of sentences, and never "Ref. [3]".

## 5. IEEE style rules

- Define every abbreviation at first use in the main text, even if it appears in the abstract (e.g. "large language models (LLMs)").
- Equations: numbered, defined with `\label{eq:...}`, referenced as `\eqref{eq:...}`; write "Equation \eqref{eq:x}" only at the start of a sentence. Every symbol defined right before or right after its equation. Use `align`/`equation`, never `eqnarray`.
- Figures: caption **below**, referenced as "Fig.~\ref{fig:...}" (even at sentence start). Vector PDF only, readable when printed in black and white, axis labels written as words with units in parentheses, minimum 8pt text.
- Tables: caption **above**, title-case caption, referenced as "Table~\ref{tab:...}". Table footnotes use letters. One-column tables must fit `\columnwidth` (use `\resizebox` only as a last resort).
- Algorithm: `algorithmic` inside a `figure` environment, as now.
- Use `\label` after `\caption`, and soft references only (no hard-coded numbers like "(3)" or "Table 2").
- Numbers: "0.25" not ".25"; percentages with one decimal place; report mean ± 95% CI for every main metric.
- Spelling: be consistent. Use **British/Indian English** throughout (modelling, normalisation, behaviour).
- Remove every piece of IEEE template guidance text. No red placeholder text left in the final version.

## 6. Results integrity (most important)

- Sections IV and V, the abstract's result sentence, and the conclusion's claims may only contain numbers produced by `eval/` from saved run logs. Every table and figure is generated by `eval/export_latex.py`.
- Every reported number must be traceable: `REPRODUCE.md` lists the command and run ID that produced it.
- If a result is negative or not significant, report it as it is and discuss it. Never drop a baseline, condition, seed or metric because it looks bad. Any exclusion must be stated with its reason in Section IV.
- Never write "significantly" unless a significance test supports it; give the test and p-value (Holm-corrected).
- Section IV must state: models and versions, decoding settings, K, λ, μ, τ, T_max, ε, η, seeds, dataset sizes per split / condition / language pair / provenance, inter-annotator agreement, simulator design, hardware, total API cost and runtime.
- Section V must contain: main results table (systems × conditions), robustness curve, kn-en vs hi-en comparison, ablation table, accuracy-vs-turns, calibration, H_L/H_D trajectory, safety (unsafe-advice rate), and an error analysis with real transcript examples.
- Limitations are stated honestly: simulated users, synthetic vs genuine variants, one appliance, two language pairs, hand-built hypothesis model, iFixit-only sources.

## 7. Language pairs

- The paper covers **two** code-mixed pairs: Romanized Kannada–English (kn-en) and Romanized Hindi–English (hi-en). Update the abstract, introduction, benchmark design, Table II and the Conclusion accordingly, and remove Hindi from Future Work.
- Conditions: clean, spelling, codemixed_kn, codemixed_hi, incomplete, combined_kn, combined_hi.
- Any mixed Kannada + Hindi + English stress set is reported separately, never inside main tables.

## 8. Writing style — must read as written by us

- Plain, direct academic English, active voice where natural ("We propose", "We measure").
- Vary sentence length. Explain with our concrete example (the refrigerator, "fridge cooling agalla compressor sound ide", and a Hindi equivalent such as "fridge thanda nahi kar raha, awaaz aa rahi hai").
- Every claim is either cited, shown in our results, or clearly worded as our hypothesis.
- **Do not use** these words or patterns: delve, crucial, pivotal, paramount, seamless(ly), robust (except in its technical sense with a metric), leverage (as a verb), harness, unlock, cutting-edge, state-of-the-art (unless citing a benchmark result), groundbreaking, revolutionize, game-changer, landscape, realm, tapestry, intricate, multifaceted, holistic, comprehensive (more than once), furthermore/moreover at the start of consecutive paragraphs, "It is worth noting that", "In today's world", "plays a vital role", "In conclusion," em-dash chains, or rule-of-three lists in every paragraph.
- No bullet lists in the body except the research questions in Section I.
- Do not copy sentences from any source, including our own concept notes or other papers; paraphrase fully and cite.
- Before finishing any edit, re-read the changed paragraphs and rewrite any sentence that sounds generic or could appear in any paper.

## 9. Length and layout

- Target **6 pages** in two-column IEEE format including references; stay within **8**. (If our faculty gives a different limit, I will update this line.)
- Figures and tables placed `[t]` (top of column) after their first mention; wide figures use `figure*`.
- No empty space left in the final version (the `\vspace` placeholders in IV and V are removed once those sections are written).

## 10. Workflow for Claude Code

1. Read this file and `paper/query2diagnose_paper.tex` before any paper edit.
2. Make paper edits only when I ask, and only in the sections named. Show me a diff summary afterwards.
3. After each edit: compile (pdfLaTeX → BibTeX → pdfLaTeX × 2), confirm zero errors / undefined refs, count the references (must be 15), check the banned-word list with a grep, and report the page count.
4. Keep `docs/method_decisions.md` in sync: whenever the code differs from the paper's Methodology, list the difference so I can approve updating the paper.
5. Never commit the paper with placeholder text or hand-typed results.
