> **ARCHIVED (v1, superseded).** This file answers the open questions of spec v1 (fuzzy extractors, lockers, K_app, server-side matching). v2 dropped that architecture; see `spec/ZTBE-spec-v2-draft.md` and `notes/decisions.md` D5/D14. Kept for the record; do not use for design.

# §8 open questions: literature, candidate answers, settling experiments

Pass 1, 2026-10-21. Keys refer to `references/bibliography.md`. "R#" refers to `notes/spec-review.md`.

---

## 8.1 Q1: Missing modalities. Per-modality profiles or an erasure-capable FE?

**What the literature says**
- For a code with minimum distance d, e errors and s erasures are correctable iff 2e + s < d. So an erasure costs half as much as an error. The spec's formula is right, but its wording ("consume half the capacity") is ambiguous.
- Binary BCH can do errors-and-erasures decoding (standard trick: decode twice with erasures set to 0 and to 1).
- `klauspost/reedsolomon` (Go) is **erasure-only** and does not correct errors. `maruel/rs` corrects errors. Neither has been checked for combined errors and erasures. See the bibliography A.2 Go table.
- Multimodal continuous-authentication work fuses modality scores rather than concatenating bits. Mondal & Bours (mondal2017) fuse keystroke and mouse in a trust model. Gomez-Barrero et al. (gomezbarrero2018fusion) fuse at the Bloom-filter template level.
- For sample-then-lock, subsets are fixed at Gen. A locker whose subset touches a missing modality simply fails.

**Candidate answers**
1. **Per-modality locker groups (recommended for evaluation).** Draw the subsets I_i within a single modality's bit range, and lock the same R in all groups. Rep tries only the groups whose modality is present. This needs no erasure decoding. The cost is that security is the minimum over groups, and the weakest modality (nav) sets the bar (R2).
2. Separate per-modality templates T_key, T_mouse, T_nav with score/decision fusion. This is simpler and matches the literature, but it gives no single key.
3. Concatenated w with errors-and-erasures BCH (Architecture A only). The R3 entropy problem remains.

**Experiments that would settle it**
- On Clarkson II (murphy2017, keyboard + mouse in the wild), measure:
  - the fraction of 30 s windows containing each modality;
  - per-modality cross-session BER;
  - FRR and FAR of options 1 and 2 against a full-vector baseline.
- Compute the per-modality Daugman DoF to see whether any single modality alone can carry the security.

## 8.1 Q2: Device or peripheral switching. Should the key be salted by a hardware fingerprint?

**What the literature says**
- Zheng et al.'s angle-based mouse features were designed to be less sensitive to hardware and environment (zheng2011).
- BB-MAS records the same subjects on desktop, tablet and phone (belman2019), so it supports cross-device studies.
- Shadman et al. (shadman2025) survey dataset conditions.
- A HID or screen-resolution category is low-entropy, client-asserted context, not a secret. It selects a profile, so it gives no security, and an attacker can choose it freely.

**Candidate answers**
- Keep k device-contextual profiles, selected by a *non-secret* device-class label, each with its own lockers. Treat the label as an index, not as salt entropy.
- On a new device class: cold start (8.3 Q1) with step-up MFA.
- Prefer hardware-invariant features (angles, curvature, normalised timing ratios) to reduce the number of profiles needed.

**Experiments that would settle it**
- On BB-MAS, compute within-device and cross-device BER per feature. Rank features by cross-device stability.
- On Balabit/SapiMouse (different hardware), check the stability of angle features against velocity and jerk features.

## 8.2 Q1: True min-entropy, and whether Rep should include Argon2id

**What the literature says**
- No source supports "20–45 bits" (R12).
- Monrose et al. report guessing entropy ≈ 10.5 over 20 users, which is an expected number of guesses, not bits (monrose2002).
- Ballard, Kamara, Reiter (ballard2008usenix) show that standard entropy estimates for behavioural biometric keys are "clearly misleading". In one system that claimed > 40 bits, 22% of keys fell to the first guess and about 50% within 2^15 guesses.
- The correct measure is fuzzy min-entropy (fuller2020when). For sample-then-lock it is the minimum over subsets of H∞(W_I) (shukla2025).
- Population-statistics attacks on keystrokes are real (serwadda2013; tey2013).
- Our CMU numbers: impostor HD distribution DoF of 9–89 for n = 31–186 bits [CMU]. This is an optimistic upper bound for an attacker without priors.

**Argon2id arithmetic** [S§1b]
- A 20 ms Rep budget at ℓ=1500 gives 13.3 µs per locker, which is far too small for any memory-hard setting.
- A slow KDF must therefore be applied *once*, not per locker. For example, lock R' and set R = Argon2id(R', salt). This slows only the final check, not the subset search. The attacker's per-locker brute force (2^32 × HKDF) is unaffected, because the locker check (zero padding) does not need R.
- Making each locker check slow, with cost c per locker, multiplies the attacker's per-locker work by c. The genuine worst case is ℓ·c, so the 20 ms budget caps c at about 13.3 µs. Compared with the measured ~1.6–1.8 µs for HKDF, that is ≈ 8.5×, or **≈ 3 extra bits** (32 → ~35 bits of work per locker). Argon2 per locker is therefore either too slow for the budget or makes almost no difference.

**Candidate answers**
- Accept that offline security is about 2^20–2^32 work per user. Make the database secret-dependent: lockers keyed with a server-side pepper held in an HSM, or a device-held key. That turns the scheme into a two-factor scheme, which is the honest framing.
- Use online-only verification with rate limiting. This changes the threat model from "DB dump" to "online".

**Experiments that would settle it**
1. Estimate H∞ and fuzzy min-entropy of w on Aalto and Clarkson II with a population-prior attacker. Generate guesses from a population model, as in Ballard's "guessing distance", and report the success-vs-guesses curve.
2. For sample-then-lock, find the minimum over 1500 random 32-bit subsets of the empirical subset min-entropy.
3. Benchmark the actual attacker cost: GPU HKDF-SHA256 per locker against our CPU figure of 1.56–1.78 µs per locker (worst-case Rep / 1500 across two runs; `go-bench/results.txt` holds the 2.66 ms run).

## 8.2 Q2: Custody of K_app (Architecture C)

**What the literature says**
- With a stolen token, BioHashing reduces to plain biometrics (kong2006). Pre-images are found by a genetic algorithm (lacharme2013).
- The Bloom layer adds little when K_app is known: there is an O(N_b) accepting pre-image [S§4], and the hermans2014 and bringer2015 attacks apply.
- ISO/IEC 24745 requires renewability, which assumes a secret transform parameter.

**Candidate answers** (in order of preference)
1. Keep K_app in an HSM or TPM-bound key on the server, and compute the BioHash inside a trusted service. This works only if raw z̃ may reach the server, which conflicts with the client-side design (§7.1).
2. Keep K_app on the client in a platform keystore (TPM, Secure Enclave, Android Keystore), so it never sits in the DB. A DB dump then reveals nothing useful, but a compromised client reveals everything.
3. Derive K_app from a user token, which is two-factor. Revocation means changing the token.

All three assume an honest client. If the client is compromised, the attacker gets raw telemetry anyway.

**Experiment**
- Implement the known-K_app attack (sign-LSH inversion by LP/feasibility, §4.1) on CMU vectors. Measure the reconstruction error and whether the reconstructed z̃ passes verification. This quantifies what K_app custody buys.

## 8.3 Q1: Cold start. How many interactions, and where is provisional state stored?

**What the literature says**
- Within a single session, CMU BER is about 0.16 (m=1). Across sessions it is 0.36. Enrolling from one session underestimates drift, so the enrolment must span several sessions or days [CMU baseline].
- Shen et al. study authentication accuracy against observation length for mouse (shen2013).
- SapiMouse reports 0.94 AUC with 15 s of mouse data (antal2021sapimouse).
- Continuous-authentication evaluation should count actions until detection (bours2012).
- Adaptive systems need enough labelled genuine data before self-update is safe (pisani2019; rattani2009).

**Candidate answers**
- Enrol over at least 3 sessions on different days, with enrolment authenticated by another factor.
- Keep the provisional EW-Welford state on the client in an OS keystore-protected blob (Keychain, DPAPI, libsecret). Do not use IndexedDB, which the page origin and any XSS can read.
- Note that NFR-05 ("0 bytes of feature vectors to non-volatile storage") forbids storing provisional state at all, even encrypted. Either amend NFR-05 to "encrypted at rest, keyed by a non-exportable device key", or require enrolment within one RAM session.

**Experiment**
- On CMU and Clarkson II, measure the BER of probes on day d against templates enrolled from the first s sessions, for s = 1..4. Find the smallest s at which BER stabilises.

## 8.3 Q2: Abrupt legitimate change (injury, accessibility, new device)

**What the literature says**
- WP193 (wp193) notes that behavioural traits change over time and requires fallback procedures.
- The adaptive-biometrics survey (pisani2019) discusses supervised versus unsupervised updates.
- Template sanitization (biggio2015spm) rolls back biased drift.
- An abrupt legitimate change and an attacker look the same to the template. Only out-of-band evidence (MFA) can tell them apart.

**Candidate answers**
- Fall back to MFA, followed by a supervised re-enrolment that mints a new T and a new anchor.
- Archive the old profile for a limited time, as a recovery template. It is still biometric personal data, so define a retention period and erase it afterwards. Do not let it accept by itself.
- Revoke it immediately if the change was triggered by suspected compromise.

**Experiment**
- Simulate step changes (other hand, other device on BB-MAS) and measure how many windows pass before the gate excludes them, and whether V_max clamping ever lets them in. Then run the matched attacker (biggio2015spm-style boundary walk) against the same §6 parameters. Success means legitimate changes need MFA and attacks never succeed without it.
