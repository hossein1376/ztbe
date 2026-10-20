# ZTBE research plan

Passes 1–3 and round 2, 2026-10-21. Status values:
- **open**: not started
- **lit**: literature collected
- **checked**: claim checked by calculation or experiment
- **blocked**: depends on a decision or data

Citation keys refer to `references/bibliography.md`. Findings R1–R14 are in `notes/spec-review.md`. Section Q refers to `notes/archive/open-questions-v1.md` (archived). The normative spec is `spec/ZTBE-spec-v2-draft.md` v2.1; decisions are D1–D15 in `notes/decisions.md`.

## Round 2 outcome and remaining work (2026-10-21)

Review `notes/review-round-1.md` was addressed by spec v2.1 and D8–D15. **The remaining work is empirical.** Further desk research adds little until the three items below produce data.

| # | Remaining item | Why it can't be done from the desk | Protocol / exit |
|---|---|---|---|
| E1 | **Same-device impostor pilot**, 10–20 people | Every open dataset confounds user with device (spec L1). The bound (FAR ratio 0.79; 0.59–0.90) is not a measurement | `docs/pilot-protocol.md`; D15 go/stop. Resolvable range in `results/pilot_ci.txt` |
| E2 | **Keyboard-capture prototype** (M1 T1, T5, T6): ztbe-capture plus ztbe-svc on Windows, macOS and Linux | Provenance flags, assistive-tool behaviour, MDM/TCC, hook timeouts and timer quanta are partly UNVERIFIED (spec §3.1, `notes/collector-tradeoffs.md`) | Capture-spike metrics in pilot-protocol §5. Injected events flagged on 3 OSes; CPU < 1%; RSS < 15 MB |
| E3 | **Supervised-adaptation FRR** | Tappy simulation: Δ +0.2 [−1.2, +1.7] pp (no measurable benefit). Real WebAuthn-anchored supervision needs ≥ 8 weeks of data | Powered study (Phase 3b) H4. Adaptation stays off (D8) unless H4 is met |

**Round-2 changes to the milestones below:**
- **M0 T1.** Ship only the 21-feature set (D11).
- **M1 T3 and T4.** Done in Python: `eval2.py` and `adapt_supervised.py`.
- **M1 split.** M1 becomes ztbe-svc plus ztbe-capture (D10). It adds the heartbeat (60 s) and `capture_lost`.
- **M2 T4.** In-house COSE (D9).
- **M3 additions:**
  - mTLS ingestion and the invalid-assertion counter (spec §9.4);
  - silence → `SIGNAL_LOST` (§9.6);
  - pause grants (§9.3);
  - ZTBE-Proof verification (§9.5; `docs/interfaces.md`).
- **M4.** Supervised only, behind a flag (D8).
- **M5.** Research mode stores window vectors only (§3.3). It adds the assistive profile and the remote-session skip (§3.1).

**Sequencing.**
1. M0 and M1 (with the E2 spike) first.
2. Then M2, plus a minimal M3 that is enough to run the pilot. M5 research mode is needed for E1.
3. Run E1.
4. Only on "go": M3 in full (SSF), M4 experiments and the Phase 3b powered study, sized at **≥ 177 completers**. That means ≈ 220 recruited at 20% attrition; this replaces the earlier 130.

**Governance before E1:** the DPIA (`docs/dpia-outline.md`), consent (`docs/consent-templates.md`) and ethics approval. Any workforce use additionally needs a legal opinion on WP29 2/2017 §5.4.1 (spec §10).

## Pass 3 outcome and next phase (2026-10-21)

Decisions D1–D7 are recorded in `notes/decisions.md`. D1 is Hossein's; D2–D7 were decided by the research assistant. The spec is `spec/ZTBE-spec-v2-draft.md`.

| Item | Status | Result |
|---|---|---|
| Per-user threshold policy | **checked** (Tappy, 29–40 users per config) | One-week per-user thresholds double FRR (P1 pooled 10.7–16.6% vs P0 3.7–7.5%). Calibration-week FRR barely predicts later FRR (Spearman 0.04–0.39). Policy: global τ_g, an `uncertain` abstain band, a trust model for `high`, and disabling ZTBE for persistent goats (spec §6). |
| Cold start | **checked** (Tappy) | Count windows plateau after ≈ 500–1000 keys; t120 improves up to ≈ 25 min. Enrolment rule: ≥ 1000 keys, ≥ 15 min, ≥ 2 days. **Superseded in round 2** by E1: ≥ 20 scored windows and ≥ 7 days (spec §5, D11). |
| Mimicry / synthetic attacks | **lit** | Snoop-forge-replay reaches up to 87.75% success on free-text continuous keystroke verification (rahman2011sfr). Trained mimicry: FAR 0.24 → 0.63 (tey2013). Out of scope for strong claims; added to the eval protocol (spec §2.1, §12). |
| Signalling | **specified** | COSE_Sign1 assertion → verifier → CAEP `risk-level-change` (LOW/MEDIUM/HIGH) → RFC 9470 step-up |
| Sample size | **checked** (`experiments/opendata/power.py`) | Intra-user error correlation is ρ ≤ 0.20, so 87–104 users are needed for ±2 pp on a 5% FRR (20–200 blocks per user) (and ≥ 86 even with unlimited data per user). **Superseded in round 2:** with the bootstrap upper ρ, 164–177 (FRR) and 119–131 (FAR) users. |

### Phase 3a: Go MVP (agent + scoring library + verifier)

Single module `github.com/hossein1376/ztbe`; layout as in spec §14 (the round-2 changes are listed in the next section). Durations assume one engineer.

| M | Scope | Tasks | Exit criteria |
|---|---|---|---|
| **M0** scoring lib (1 wk) | `internal/features`, `internal/model`, `cmd/ztbe-eval` | T1: port the window features (the 36-feature superset, plus the 21-feature v2 set). T2: scaled Manhattan with shrinkage, K-fusion, trust model. T3: golden tests against `experiments/opendata` | Go and Python feature vectors agree within 1e-6 on LASER and Tappy. EER and trust-model table within ±0.2 pp of `userpolicy_*.txt` |
| **M1** agent, local only (2 wk) | `internal/capture`, `internal/zone`, `cmd/ztbe-agent` | T1: hooks (evdev on Linux, gohook on macOS/Windows). T2: zone mapping, characters dropped at source. **T3: re-run the experiments with the 21-feature set** (spec §3). **T4: simulate supervised adaptation** (spec §8), since FRR benefit is unmeasured. **T5: injected-event provenance per OS** (spec §3.1). T6: timer-resolution self-test (rollover gate) | CPU < 1% of one core and RSS < 15 MB while typing. A property test shows no key identity reaches `features`. On each OS, injected events are flagged and not scored |
| **M2** sealing + assertions (2 wk) | `internal/seal`, `internal/attest`, `internal/wire` | T1: TPM 2.0 seal/unseal (go-tpm-tools) and an AK-certified P-256 assertion key (go-attestation). **T2: measure TPM unseal and sign latency.** T3: macOS SE key via sks, plus go-keyring fallback. T4: COSE_Sign1 encoding (~~go-cose~~ → in-house on fxamacker/cbor, alg −9/−19, D9) | `key_protection` correctly reported on 3 platforms. Fuzzed malformed assertions are all rejected |
| **M3** verifier (2 wk) | `cmd/ztbe-verifier`, `internal/policy` | T1: enrolment binding via WebAuthn (go-webauthn). T2: seq / nonce-epoch / silence checks. T3: SSF transmitter, emitting CAEP `risk-level-change` SETs over RFC 8935 push. T4: sample RP showing an RFC 9470 step-up | Replay, rollback, forged-key and stale-nonce tests fail closed. An end-to-end walk-up demo triggers step-up |
| **M4** adaptation + policy (1 wk) | `internal/adapt` | Supervised windows (30 min after WebAuthn, experimental, off by default), ~~unsupervised guard stack~~ (withdrawn, D8), 180-day re-enrolment, persistent-goat rule | The Go port reproduces `adapt_n200.txt` within ±2 pp. Supervised mode shows week-8 FRR ≤ static |
| **M5** pilot build (1 wk) | Packaging, status UI, kill switch, data-collection mode (phase 3b) | The user can pause (WebAuthn-backed grant, spec §9.3), disable and delete. Research mode uploads only encrypted feature vectors | Security review checklist passed. DPIA draft complete |

### Phase 3b: own consented data collection

Purpose:
- build the in-domain population prior and τ_g that D3 requires;
- evaluate cross-day, 8-week and attack performance with CIs.

**Protocol**
- Participants are adult volunteers, recruited openly (not through an employer chain, per D6). Mixed OS and keyboard types (laptop, external, ergonomic) and mixed typing proficiency.
- Instrument: the M5 agent in *research mode*. It captures only the zone-mapped timings needed for features: per window, the feature vector plus per-event (zone, down, up) timestamps. Characters are never captured. Timer resolution and OS are logged.
- Duration: 8 weeks of natural use, at least 3 active days per week. Weeks 1–2 enrolment and calibration, weeks 3–8 test. This mirrors the `userpolicy.py` timeline, with longer calibration to test T2.
- Supervised labels: each WebAuthn login marks a 30-minute supervised period.
- Attack sessions (separate consent, scheduled):
  - zero-effort walk-up on a lab machine;
  - population-statistics forgery generated offline;
  - snoop-forge-replay with 100 / 200 / 1000 keystrokes of the victim's timings. The victim consents to their timings being used for forgeries.
  - Mimicry sub-study: 30 attackers × 3 victims, with a Mimesis-style feedback UI (tey2013). The 30-attacker figure is a proposal, sized to give ≥ 90 attacker–victim pairs.
- Synthetic injection: OS-level injection by a test harness on lab machines only, to measure provenance flags and the synthetic detector (APCER/BPCER).

**Consent and governance**
- Ethics board (IRB or equivalent) approval before recruitment. A DPIA (Art. 35) covering research mode.
- Explicit Art. 9(2)(a) consent. Separate opt-ins for: (1) natural-use collection, (2) attack sessions as attacker, (3) use of the participant's timings to build forgeries against them.
- Withdrawal at any time, with deletion of the participant's data within 30 days.
- Data minimisation:
  - pseudonymous ID;
  - no characters, no application or window titles, no URLs;
  - demographics limited to optional age band, handedness, typing language and a self-reported typing-related condition, as required for fairness reporting (spec §10; round 2 replaces the earlier "no health or disability data"). These items are covered by separate consent and are never inferred (D7).
- Storage:
  - encrypted at rest;
  - access logged;
  - research retention 24 months (proposal);
  - no release of per-event data. A public release, if any, contains window feature vectors only and needs separate consent.
- Payment, if any, is flat and not performance-based, to avoid incentive effects. tey2013 found that monetary incentives change attacker success.

**Size targets** (`experiments/opendata/power.py`, results/power.txt)
- Intra-user error correlation from Tappy: ρ_FRR ≤ 0.19 and ρ_FAR ≤ 0.20. Design effect: 1 + (m − 1)·ρ.
- Required users:
  - FRR 5% ± 2 pp (95% CI): 104 users at 20 blocks each, 87 at 200 blocks. The floor is 86 users however much data each provides.
  - FRR 5% ± 1 pp: ≈ 350–415 users.
  - Block FAR 10% ± 3 pp: 80–94 targets.
- Low-FAR claims: FAR ≤ 1% at 95% needs ≥ 300 independent zero-error impostor attempts (rule of 3). Cross-user pairs are correlated per attacker and target, so impostor attempts must be counted at the effective sample size.
- **Target** (superseded in round 2 by ≥ 177 completers / ≈ 220 recruited): recruit 130 participants, expecting ≈ 20% attrition, so that ≥ 100 complete 8 weeks with ≥ 50 test blocks each. Of these, 40 also join attack sessions; the mimicry sub-study uses 30 attackers.
- Priors and τ_g come from a disjoint 50% of participants (a 2-fold swap), as in the experiments.

**Analysis plan.** Spec §12, with every metric reported with clustered CIs. Pre-registered hypotheses:
- H1: block EER ≤ 9% at K = 4 on weeks 3–8.
- H2: per-user thresholds with ≥ 4 weeks of calibration and shrinkage (T2) do not reduce p90 user FRR by ≥ 3 pp → keep the global threshold.
- H3: snoop-forge-replay with 200 keystrokes raises block FAR by ≥ 3× over zero-effort (expected from rahman2011sfr).
- H4: supervised adaptation gives week-8 FRR ≤ static.

## Pass 2 outcome (2026-10-21)

> Historical (pass 2). Superseded where it differs from spec v2.1: the architecture now lives in the spec, not `PROPOSAL.md` (D14); row 4's template is < 1 KB per keyboard class (spec §7); row 6's "9% = baseline" held only against a non-adaptive attacker, and adaptation is now off by default with unsupervised mode withdrawn (D8, spec §8); row 9's milestones are Phase 3a above.

The direction has changed. Spec v1, a keyless FE that derives keys from behaviour, is **rejected on measured evidence**. The replacement is the v2 architecture in `PROPOSAL.md`: on-device scoring, a sealed template, signed risk assertions, and WebAuthn step-up. Evidence: `notes/experiments-v2.md` and `notes/design-options.md`.

| P | Item | Status | Result / next |
|---|---|---|---|
| 1 | Cross-session BER/EER on free text, Eberz protocol | **checked** (Aalto, LASER, Tappy, SapiMouse, Balabit) | Per-window EER 6–16% (keystroke), 21–34% (mouse). FRR@FAR1% 20–60%. Clarkson II still needed (M3). |
| 2 | Entropy that matters | **checked** | Upper estimate of guessing entropy: about 1–4 bits at the verifier's threshold. No keyless design is viable. |
| 3 | Threat model decision | **proposed** | O7 on-device + attestation (design-options §2). Needs Hossein's decision (PROPOSAL §10). |
| 4 | Storage vs architecture | **resolved** by v2 | 1.7 KB sealed template on the device; no biometric data on the server |
| 5 | Δw leakage of updates | **moot** in v2 | No helper data exists |
| 6 | Anti-poisoning | **checked** (simulation) | Gating alone: 83% takeover. Gate + anchor + velocity + sanitise (rollback + freeze): 9% (= baseline). Supervised updates by default. |
| 7 | Quantizer choice | **checked** | LSSC beats Gray, and the population mask helps cross-session. In v2 no binarisation is used. |
| 8 | Architecture C | **dropped** | |
| 9 | Go prototype | **planned** | PROPOSAL §9 milestones M0–M5. Crypto costs measured in `experiments/go-he`. |
| 10 | GDPR / DPIA / AI Act | **lit** | NIST 800-63B-4 and the AI Act text checked. Annex III(4)(b) workforce question goes to legal review. |

New open items:
- Per-user threshold policy for the high-FRR minority (Gini 0.6–0.9).
- In-domain, commercially licensed population priors.
- Mimicry and synthetic-injection evaluation (no open data).
- TPM unseal/sign latency on real hardware.
- Clarkson II re-run of every table.

Pass-1 sections below are kept for traceability. Statuses that changed in pass 2 are marked "(pass 2)".

## Prioritized list (pass 1)

| P | Item | Why first | Area |
|---|---|---|---|
| 1 | Measure cross-session BER on free-text, in-the-wild data (Clarkson II, Aalto) with an Eberz-style protocol | Every architecture's parameters depend on it. CMU already shows 0.30–0.40 versus the assumed 0.15–0.25 (R6). | FR-03/05, §4.2 |
| 2 | Estimate the entropy that matters: fuzzy min-entropy, guessing curves, and per-subset min-entropy | It decides whether *any* keyless FE can meet FR-04 (R2, R3, §8.2 Q1) | FR-04, §4.3, §8.2 |
| 3 | Decide the threat model: keyless FE or keyed/two-factor (pepper, HSM, device key) | R2, R3 and R5 suggest keyless offline security is ≤ ~32 bits. This decision unblocks the architecture. | FR-04, FR-07, §8.2 Q2 |
| 4 | Fix storage versus architecture (NFR-04 against lockers, CBF, hybrid) | It is a hard contradiction (R1) | NFR-04, §5.4 |
| 5 | Replace the update protocols that leak Δw (§5.2, §5.1-A) with re-Gen on sample-then-lock only, and quantify leakage across epochs | R4 | FR-06, §5 |
| 6 | Redesign the anti-poisoning envelope: anchor tolerance, sanitization, provenance | R9. The 0.423n window is large. | FR-06, §6 |
| 7 | Choose a quantizer: empirical edges, LSSC or m=1 with DROBA, and population-level masks | R8, R11 | §4.2 |
| 8 | Decide whether Architecture C is kept, and if so under which custody model, or drop it | R5 | §4.3-C, §5.3 |
| 9 | Go prototype of the Gen/Rep, quantizer and update loop against the NFRs | Mostly feasible already (R14). Needed for end-to-end numbers. | NFR-01..05 |
| 10 | GDPR/DPIA framing and licence clean-up | R13. These are needed before any pilot. | §7.2, compliance |

---

## Functional requirements

### FR-01 Multi-modal telemetry ingestion: lit

- **Research questions:** What share of 30 s windows contains each modality in real use? What are the capture overhead and jitter of browser versus OS hooks?
- **Next steps:**
  - Modality-presence statistics on Clarkson II (murphy2017).
  - Evaluate the Go hooks (gohook) and UserALE (apache/flagon monorepo).

### FR-02 Content-blind filtering: open

- **Research questions:** How much accuracy is lost by mapping keys to C zones rather than key identity (gunetti2005)? Does the remaining data still allow content inference, e.g. through timing side channels?
- **Next steps:**
  - On Aalto (dhakal2018), compare EER for raw digraphs against zone digraphs for C ∈ {6, 8, 10}.
  - Note the RAM impact on NFR-01 (R14).

### FR-03 Streaming feature extraction: checked (formula)

- **Research questions:** Choice of N_eff. Do the features need to be stationary within a window? Is time-of-day appropriate as a feature (privacy)?
- **Status:** the EW-Welford recursion is verified [S§6], and burstiness matches goh2008.
- **Next steps:** sweep N_eff against cross-session BER. Decide whether to drop or coarsen the time-of-day feature.

### FR-04 Irreversible hashing: checked, and it fails as specified (pass 2: measured, ≤ ~4 bits; design rejected)

- **Research questions:**
  - What is the offline attack cost for each architecture against a population-prior attacker?
  - Which security notion applies: fuzzy min-entropy (fuller2020when), or min over subsets (shukla2025)?
- **Status:** R2 (sample-then-lock ≤ 2^32 per locker), R3 (Architecture A vacuous), R5 (Architecture C).
- **Next steps:**
  - Run the guessing-curve experiment (Q §8.2 Q1).
  - Write up an ISO/IEC 24745 / 30136-style evaluation plan covering irreversibility, unlinkability (gomezbarrero2018tifs) and renewability.

### FR-05 Noisy verification and S_trust: checked (pass 2: the best free-text sample-then-lock setting, k=24 on Aalto, gives FRR 7.6% and FAR 7.6%)

- **Research questions:** What operating point (t, k_sub, ℓ) gives FRR ≤ 5% and FAR ≤ 1%? Which metric applies: actions until detection (bours2012), or FCS (sugrim2019)? Does S_trust act as an oracle (R10)?
- **Status:** on CMU, no sample-then-lock setting is usable (R6).
- **Next steps:**
  - Repeat on free-text data.
  - Specify that only binary decisions are exposed.

### FR-06 Drift adaptation: checked (pass 2: boundary-walk poisoning and sanitisation simulated on Tappy)

- **Research questions:** What does an observer of T^(1..k) learn under re-Gen sample-then-lock? Which update rule converges without impostor intrusion (didaci2014; rattani2009)?
- **Status:** the §5.2 and §5.1-A leaks are demonstrated [S§7]. The anti-poisoning envelope is in R9.
- **Next steps:**
  - Simulate updates over CMU sessions 1→8 with majority vote (§5.1-2).
  - Implement the boundary-walk attacker (biggio2015spm) and template sanitization.

### FR-07 Unlinkability and revocability: lit

- **Research questions:** Are two sample-then-lock templates of the same user linkable when the subsets are independent? Does the reliability mask M_rel link them (R11)? Is Architecture C linkable (hermans2014)?
- **Next steps:** compute the Gomez-Barrero D↔sys unlinkability metric (gomezbarrero2018tifs) on the CMU templates for each architecture.

## Non-functional requirements

| ID | Status | Research questions | Next steps |
|---|---|---|---|
| NFR-01 RAM | checked (estimate) | Session state is 1.9–4.3 KB (R14). Daemon footprint in Go versus Python. | Measure the RSS of the Go prototype. Avoid River/CPython in the daemon. |
| NFR-02 CPU | open (trivially feasible) | Per-event cost at 20 ev/s | Benchmark the Go feature-extraction path |
| NFR-03 latency | checked | Rep 1.8–2.7 ms at ℓ=1000–1500. Bloom distance 170 ns [GO]. | Reduce allocations. Re-measure at the real ℓ after item 1. |
| NFR-04 storage | checked: contradiction | ≤2 KB is infeasible for B and C as specified (R1) | Decide the budget. Use the PRF-derived subsets and nonces design. |
| NFR-05 zero persistence | lit | Go GC copies, swap, core dumps, and provisional cold-start state (Q §8.3 Q1) | Prototype with memguard and `runtime/secret` (experimental). Reconcile with cold start. |

## Spec sections

| § | Topic | Status | Questions / next steps |
|---|---|---|---|
| §3 | Feature space, EW-Welford | checked | Features are non-Gaussian [CMU] (belman2019). Use empirical priors. Licence of the population-prior data: Aalto is non-commercial (bibliography B.2). |
| §4.1 | LSH critique | checked | Correct. Apply it to Architecture C as well (R5). |
| §4.2 | Quantization | checked | Gaussian edges are imbalanced (up to 0.52). Gray wrap-around (R8). Mask leaks (R11). Next: compare LSSC (lim2013lssc), DROBA (chen2009droba) and an analytic BER model (kelkboom2010). |
| §4.3-A | Syndrome FE | checked | The bound needs β ≥ 515 at 15% BER (R3). Look at computational FEs (fuller2013comp; apon2017; wen2018) as alternatives. |
| §4.3-B | Sample-then-lock | checked | FRR bound (R7), cap of 2^k_sub (R2). Follow the shukla2025 methodology and feap. |
| §4.3-C | BioHash + Bloom | checked | R5. Decide whether to drop or keep it with keyed custody. |
| §5.1 | Verify-adapt-rehash | checked (A leaks) | Keep it for B only. Formalise its reusability (canetti2021joc fn. on ℓ·ρ composability). |
| §5.2 | Syndrome shifting | checked: insecure | Remove, or keep as an explicitly keyed scheme with a proof (kelkboom2011; blanton2013) |
| §5.3 | Counting BF | lit | Counter-delta leakage (R5.4). Quantify it from DB snapshots. |
| §5.4 | Comparison matrix | checked | Storage and "IT security" entries are wrong (R1, R4) |
| §6 | Anti-poisoning | checked | 0.423n envelope, anchor infeasible (R9). Add sanitization (biggio2015spm) and multi-template anchors (uludag2004). |
| §8 | Open questions | lit | See `notes/archive/open-questions-v1.md` (archived; superseded by spec v2.1 §11 L1–L4) |

## Data needed

| Dataset | Use | Access | Status |
|---|---|---|---|
| CMU (killourhy2009) | Quantization, BER | public, no licence (citation requested) | used |
| Clarkson II (murphy2017) | In the wild, keyboard + mouse, long-term drift | on request | being requested (outside this repo) |
| Aalto 136M (dhakal2018) | Free text, population priors | non-commercial | **used** (pass 2; 162k QWERTY users) |
| BB-MAS (belman2019) | Cross-device | IEEE DataPort login | to request |
| SapiMouse / Balabit | Mouse | public, licence unclear | **used** (pass 2) |
| CMU LASER-2012 (killourhy2012laser) | Cross-session free text | public, no licence | **used** (pass 2) |
| Tappy (adams2017tappy) | Cross-day, weeks | ODC-By 1.0 | **used** (pass 2; adaptation) |
| Buffalo (sun2016buffalo) | Free text, multi-session | on request | not requested |
