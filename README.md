# ZTBE research

Research base for the **ZeroTrace Behavioral Engine (ZTBE)** spec v1.0.0-draft: a privacy-preserving continuous behavioural authentication engine built on fuzzy extractors and cancelable templates.

## Layout

| Path | Content |
|---|---|
| [`spec/ZTBE-spec-v1.0.0-draft.md`](spec/ZTBE-spec-v1.0.0-draft.md) | The spec under review, unchanged. Transcribed verbatim from the provided attachment. No hash of the original was available, so byte identity is not machine-verified. |
| [`PLAN.md`](PLAN.md) | Research plan by FR-01..07, NFR-01..05, spec §3–6 and §8, with a prioritized list |
| [`notes/spec-review.md`](notes/spec-review.md) | Critical review: 14 findings (R1–R14) with sanity numbers |
| [`notes/open-questions.md`](notes/open-questions.md) | §8 questions: literature, candidate answers, settling experiments |
| [`references/bibliography.md`](references/bibliography.md) | Spec citation audit (Part A), FOSS licence and Go equivalents check (A.2), 82 new sources by topic (Part B) |
| [`references/references.bib`](references/references.bib) | BibTeX, 98 entries, keys match bibliography.md |
| [`experiments/`](experiments/) | `sanity/` closed-form checks (Python stdlib), `go-bench/` Go benchmarks of Rep, Bloom and storage, `cmu-quantization/` spec Stage-1 on the CMU keystroke data |
| `papers/` | Not created. No PDFs are redistributed, because none of the full texts used was confirmed CC-BY. Links only. |

## Status (2026-10-21)

- **Bibliography: pass 1 done.**
  - Every entry was checked against Crossref, the publisher, or the DOI landing page. Unconfirmed fields are marked UNVERIFIED.
  - About 28 sources were read at abstract or full-text level.
- **Spec review: pass 1 done.** Main problems:
  - Storage versus NFR-04.
  - Offline security of sample-then-lock is ≤ 2^32 per locker.
  - The Architecture A bound is vacuous.
  - Update protocols leak Δw.
  - Architecture C is LSH.
  - Real cross-session BER is 0.30–0.40.
- **Experiments:** sanity checks and CMU quantization only. Free-text, in-the-wild data (Clarkson II, Aalto) are next (PLAN item 1).
- **Not done:**
  - No ZTBE implementation.
  - The Python/River RSS was not measured.
  - Dataset access requests have not been sent.
