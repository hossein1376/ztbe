# ZTBE research plan

Pass 1, 2026-10-21. Status values:
- **open**: not started
- **lit**: literature collected
- **checked**: claim checked by calculation or experiment
- **blocked**: depends on a decision or data

Citation keys refer to `references/bibliography.md`. Findings R1–R14 are in `notes/spec-review.md`. Section Q refers to `notes/open-questions.md`.

## Prioritized list

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

### FR-04 Irreversible hashing: checked, and it fails as specified

- **Research questions:**
  - What is the offline attack cost for each architecture against a population-prior attacker?
  - Which security notion applies: fuzzy min-entropy (fuller2020when), or min over subsets (shukla2025)?
- **Status:** R2 (sample-then-lock ≤ 2^32 per locker), R3 (Architecture A vacuous), R5 (Architecture C).
- **Next steps:**
  - Run the guessing-curve experiment (Q §8.2 Q1).
  - Write up an ISO/IEC 24745 / 30136-style evaluation plan covering irreversibility, unlinkability (gomezbarrero2018tifs) and renewability.

### FR-05 Noisy verification and S_trust: checked (partly)

- **Research questions:** What operating point (t, k_sub, ℓ) gives FRR ≤ 5% and FAR ≤ 1%? Which metric applies: actions until detection (bours2012), or FCS (sugrim2019)? Does S_trust act as an oracle (R10)?
- **Status:** on CMU, no sample-then-lock setting is usable (R6).
- **Next steps:**
  - Repeat on free-text data.
  - Specify that only binary decisions are exposed.

### FR-06 Drift adaptation: checked (leakage)

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
| §8 | Open questions | lit | See `notes/open-questions.md` |

## Data needed

| Dataset | Use | Access | Status |
|---|---|---|---|
| CMU (killourhy2009) | Quantization, BER | public, no licence (citation requested) | used |
| Clarkson II (murphy2017) | In the wild, keyboard + mouse, long-term drift | on request | **request needed** (email: draft for Hossein, not sent) |
| Aalto 136M (dhakal2018) | Free text, population priors | non-commercial | to download |
| BB-MAS (belman2019) | Cross-device | IEEE DataPort login | to request |
| SapiMouse / Balabit | Mouse | public, licence unclear | to download |
