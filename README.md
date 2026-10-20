# ZTBE research

Research base for the **ZeroTrace Behavioral Engine (ZTBE)**. It started as a review of spec v1.0.0-draft (fuzzy extractors and cancelable templates). That design was rejected. The current direction is [spec v2](spec/ZTBE-spec-v2-draft.md): on-device keystroke scoring that emits a signed risk signal, with WebAuthn step-up. It is a risk signal, not an authentication factor.

## Layout

| Path | Content |
|---|---|
| [`spec/ZTBE-spec-v1.0.0-draft.md`](spec/ZTBE-spec-v1.0.0-draft.md) | The spec under review, unchanged. Transcribed verbatim from the provided attachment. No hash of the original was available, so byte identity is not machine-verified. |
| [`spec/ZTBE-spec-v2-draft.md`](spec/ZTBE-spec-v2-draft.md) | **v2 spec draft (pass 3).** Risk signal, not a factor (D1). Threat model A1–A8, feature keep/drop with evidence, threshold and trust policy, cold start, sealing, COSE assertion, CAEP/RFC 9470, GDPR/AI Act, eval protocol |
| [`notes/decisions.md`](notes/decisions.md) | Decisions D1–D7 with rationale and what would change each |
| [`PROPOSAL.md`](PROPOSAL.md) | **Phase 2: recommended architecture v2.** On-device scoring, sealed template, signed risk assertions, WebAuthn step-up. Includes the threat model, parameters justified by measurements, budgets, honest claims, Go MVP plan and decisions needed |
| [`notes/experiments-v2.md`](notes/experiments-v2.md) | Phase 2 open-data results (Aalto, LASER-2012, Tappy, SapiMouse, Balabit) |
| [`notes/design-options.md`](notes/design-options.md) | Phase 2 options O0–O8 (keyless FE, keyed/OPRF, HE, 2PC, embeddings, on-device + attestation, threshold) with an attacker-by-option matrix |
| [`PLAN.md`](PLAN.md) | Research plan by FR-01..07, NFR-01..05, spec §3–6 and §8, with a prioritized list |
| [`notes/spec-review.md`](notes/spec-review.md) | Critical review: 14 findings (R1–R14) with sanity numbers |
| [`notes/open-questions.md`](notes/open-questions.md) | §8 questions: literature, candidate answers, settling experiments |
| [`references/bibliography.md`](references/bibliography.md) | Spec citation audit (Part A), FOSS licence and Go equivalents check (A.2), Part B sources by topic: B.1–B.9 from pass 1, B.10–B.14 and Go libraries from pass 2 |
| [`references/references.bib`](references/references.bib) | BibTeX, 181 entries, keys match bibliography.md |
| [`experiments/`](experiments/) | `sanity/`, `go-bench/`, `cmu-quantization/` (pass 1); `opendata/` (pass 2 evaluation, with `fetch.sh` because no data is committed); `go-he/` (pass 2 Go crypto costs) |
| `papers/` | Not created. No PDFs are redistributed, because none of the full texts used was confirmed CC-BY. Links only. |

## Status (2026-10-21, pass 3 + review round 1)

Independent review: [`notes/review-round-1.md`](notes/review-round-1.md). It covers consistency, re-runs, citation checks, gaps and a ranked work list. The earlier status notes below are kept for history.

- **Pass 2 done.**
  - Measured open-data results: per-window keystroke EER of 6–16% cross-session and cross-day; FRR@FAR1% of 20–60%; guessing entropy of about 1–4 bits.
  - Spec v1's keyless-FE design is rejected.
  - `PROPOSAL.md` gives the v2 architecture.
  - Still open: Clarkson II, the TPM latency measurement and mimicry data. Decisions D1–D7 are made (`notes/decisions.md`).
  - Pass 3: `spec/ZTBE-spec-v2-draft.md`; `experiments/opendata/userpolicy.py` (thresholds, trust model, cold start) and `power.py`; PLAN phase 3 (Go MVP and consented data collection).

### Pass 1 status

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
