# ZTBE research

Research base for the **ZeroTrace Behavioral Engine (ZTBE)**. It started as a review of spec v1.0.0-draft (fuzzy extractors and cancelable templates). That design was rejected. The current direction is [spec v2](spec/ZTBE-spec-v2-draft.md): on-device keystroke scoring that emits a signed risk signal, with WebAuthn step-up. It is a risk signal, not an authentication factor.

## Start here

1. [`spec/ZTBE-spec-v2-draft.md`](spec/ZTBE-spec-v2-draft.md) **v2.2** is the single normative spec (D14).
2. [`notes/decisions.md`](notes/decisions.md) holds D1–D22.
3. [`PLAN.md`](PLAN.md) lists the remaining work, which is empirical.
4. [`docs/pilot-protocol.md`](docs/pilot-protocol.md) is the next experiment.

## Layout

| Path | Content |
|---|---|
| [`spec/ZTBE-spec-v2-draft.md`](spec/ZTBE-spec-v2-draft.md) | **v2.2, normative.** Threat model A1–A10, the 21-feature rule, provenance/assistive/remote/multi-keyboard rules, research mode, matched-FAR results, trust model, sealing, no adaptation (D8), COSE −9/−19, agent split, heartbeat/SIGNAL_LOST, pause grants, mTLS ingestion, pairwise per-RP ZTBE-Proof session binding, signal state machine (HIGH latch, stale), SSF/CAEP, GDPR/AI Act/fairness, claims and limits L1–L5, eval protocol, Go layout, parameters |
| [`spec/ZTBE-spec-v1.0.0-draft.md`](spec/ZTBE-spec-v1.0.0-draft.md) | Original v1 spec, unchanged (rejected design) |
| [`docs/interfaces.md`](docs/interfaces.md) | CDDL wire formats, OpenAPI sketch, error codes, CAEP mapping and example SET, RP integration guide |
| [`docs/pilot-protocol.md`](docs/pilot-protocol.md) | Same-device feasibility pilot: two stages (16 + 16), D21 go/stop rule with simulated operating characteristics, genuine same-task control |
| [`docs/dpia-outline.md`](docs/dpia-outline.md) | DPIA outline: WP248 screening, Art. 35(7) structure, risks and measures. Not legal advice |
| [`docs/consent-templates.md`](docs/consent-templates.md) | Pilot consent form and layered end-user notice. Not legal advice |
| [`notes/decisions.md`](notes/decisions.md) | D1 (Hossein); D2–D22 (research assistant), each with rationale and what would change it |
| [`notes/experiments-v2.md`](notes/experiments-v2.md) | Open-data results (Aalto, LASER-2012, Tappy, SapiMouse, Balabit); §9 has round-2 re-runs with CIs |
| [`notes/collector-tradeoffs.md`](notes/collector-tradeoffs.md) | Native agent vs browser vs OS frameworks, per OS (timers, injection flags, permissions, MDM) |
| [`notes/landscape.md`](notes/landscape.md) | Vendors, OSS and patents. Not legal advice |
| [`notes/review-round-1.md`](notes/review-round-1.md) | Independent review that drove round 2 |
| [`notes/review-round-2.md`](notes/review-round-2.md) | Final desk review: round-1 resolution, new holes H1–H9, must-fix list, D17 verdict |
| [`PROPOSAL.md`](PROPOSAL.md) | Short non-normative rationale, with pointers to where content moved |
| [`PLAN.md`](PLAN.md) | Remaining empirical work (E1–E3), Go milestones M0–M5, FR/NFR history |
| [`notes/design-options.md`](notes/design-options.md) | Historical: options O0–O8 with an attacker-by-option matrix |
| [`notes/spec-review.md`](notes/spec-review.md) | Historical: v1 review, findings R1–R14 |
| [`notes/archive/`](notes/archive/) | Archived v1 open questions |
| [`references/bibliography.md`](references/bibliography.md) | Citation audit, FOSS/licence checks, sources by topic B.1–B.16 |
| [`references/references.bib`](references/references.bib) | BibTeX, 199 entries; keys match bibliography.md |
| [`experiments/`](experiments/) | `sanity/`, `go-bench/`, `cmu-quantization/`, `go-he/`, `opendata/`. `opendata/` holds eval2.py, adapt_supervised.py, power.py, window_duration.py and pilot_oc2.py (pilot_ci.py / pilot_oc.py are earlier versions); results are in `results/`, and no data is committed (`fetch.sh`) |
| `papers/` | Not created. No PDFs are redistributed. Links only |

## Headline numbers (Tappy, 81 users, spec config; 95% bootstrap CIs over users; zero-effort, **different-device** impostors)

**Block errors at τ_g:**

| Metric | Value |
|---|---|
| FRR, pooled | 5.3% [3.7, 7.5] |
| FRR, macro | 7.9% [5.3, 11.0] |
| FRR, p90 user | 25.4% [12.9, 33.3] |
| FAR | 11.7% [8.9, 15.4] |
| FRR at matched FAR 10% | 6.8% [4.3, 11.2] |

**Trust model:**

| Metric | Value |
|---|---|
| Genuine alarms per 60 windows, pooled | 0.64 [0.41, 0.93] |
| Genuine alarms per 60 windows, macro | 0.93 [0.49, 1.54] |
| Genuine alarms per 60 windows, p90 user | 2.46 [1.09, 3.46] |
| Impostor alarm within 5 windows | 81.6% [76.9, 86.2] |
| Impostor alarm within 10 windows | 88.0% [84.1, 91.7] |

**Other results:**
- Supervised adaptation: Δ FRR +0.2 [−1.2, +1.7] pp, which is no measurable benefit.
- Power: FRR 5% ± 2 pp needs 164–177 users; FAR 10% ± 3 pp needs 119–131.
- **Main limitation:** user and device are confounded in all open data (spec L1). The same-device pilot is the next step.

## Status: desk phase complete (2026-10-21)

Two independent reviews agree that more desk research adds little (D17; `notes/review-round-2.md` §6). Their must-fix items H1, H2, H3 and H9 are fixed in spec v2.2, `docs/interfaces.md`, `docs/dpia-outline.md` and `docs/pilot-protocol.md` v2 (D18–D21). The should-fix items H4–H8 are covered by D22.

**What's next** (empirical; PLAN "Round 2 outcome"):

| # | Work | Needs |
|---|---|---|
| E1 | Same-device impostor pilot. A dry run, then stage 1 with 16 participants, then stage 2 with 16 more if inconclusive (D21) | Ethics approval, DPIA, consent, volunteers, M5 research build |
| E2 | Keyboard-capture prototype on Windows, macOS and Linux: provenance flags, assistive tools, timers, hook timeouts, extension fingerprinting (M1 T1/T5/T6) | Hardware and OS test matrix |
| E3 | Supervised-adaptation FRR on real WebAuthn-anchored data (H4 of Phase 3b) | 8 weeks of data; only after an E1 "go" |

Also open: a legal opinion on workplace proportionality (WP29 2/2017 §5.4.1) before any workforce use, and an FTO review by counsel (`notes/landscape.md`).

## Status (2026-10-21, round 2 complete)

Round 2 (autonomous, Hossein asleep) addressed the review: spec v2.1, D8–D15, re-runs with CIs, governance docs, interfaces, landscape. What remains needs people and hardware (PLAN E1–E3).

### Earlier status (pass 3 + review round 1)

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
