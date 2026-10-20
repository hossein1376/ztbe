# ZTBE v2: proposed architecture

Status: proposal, 2026-10-21 (Asia/Tehran).

Evidence used:
- `notes/experiments-v2.md`: open-data measurements;
- `notes/design-options.md`: comparison of options;
- `experiments/go-he`: Go costs;
- `references/bibliography.md`.

Every number below is either measured (the source is given) or marked *inferred* or UNVERIFIED.

## 1. Summary

ZTBE v2 is an **on-device continuous behavioural risk signal**. It is not an authenticator and not a key-derivation scheme.

- **On the device**, an agent written in Go:
  - extracts content-blind keystroke and mouse features into windows;
  - scores each window against a template sealed under a non-exportable device key (TPM 2.0 or the OS keystore);
  - fuses the scores over a few windows;
  - emits **signed risk assertions**.
- **The server** sees no behavioural data. It verifies the assertions against a device key that was attested once at enrolment through WebAuthn/TPM. It feeds them into session policy:
  - a low risk score keeps the session alive;
  - a high risk score triggers a **step-up with a phishing-resistant authenticator** (passkey or security key).
- **Template updates** happen only from windows that a recent strong authentication vouches for (supervised). Unsupervised drift tracking is optional and sits behind anchor, velocity and sanitisation guards.

Why this shape:
- Behavioural input carries only **about 2–4 bits** against a population-dictionary attacker. The best single guess succeeds against 3.5–22% of users at a 1% FAR threshold, and against 15–69% at the EER threshold (Aalto; Tappy with in-domain priors; experiments-v2 §6).
- So no keyless or "fuzzy-extractor" construction can protect it offline (design-options §0).
- Per-window accuracy (EER 6–16%, FRR@FAR1% of 20–60%) rules out using it as an authentication factor. That matches NIST SP 800-63B-4: fraud indicators "do not … substitute for an authentication factor", and biometric factors need FMR ≤ 10⁻⁴.

What it *is* good for:
- catching a different person at an unlocked session within minutes;
- doing so without a central biometric database.

## 2. Threat model

| Attacker (design-options §1) | Goal | v2 outcome | Mechanism |
|---|---|---|---|
| A1 DB dump | Steal biometric templates | **Nothing to steal.** The server holds device public keys, counters and risk events only. | On-device template |
| A2 Server compromise | Templates; forged sessions | No templates. Forging risk assertions requires the device key. A2 can of course ignore ZTBE for its own service. | Device-bound signing key |
| A3 Insider | Profiling users from behaviour | Sees only risk bands and timestamps. No features. | Data minimisation; no score API |
| A4 Oracle / hill-climbing | Learn the template, or find an accepted vector | Local only, rate-limited, decision-only output. A4 still needs code execution on the device, which makes it A5. | No score export; rate limits |
| A5 Endpoint malware | Inject synthetic input; read the template | **Not defended.** The template can be read while unsealed in agent memory. Synthetic input can mimic the user (antal2021sapiagent, serwadda2013). | Out of scope. Reduce exposure with PCR-bound sealing, a signed agent and memguard buffers |
| A6 Physical impostor (zero-effort) | Use an unlocked session | Detected with the probabilities in §5.2 within about 4 min of active typing; triggers step-up | Fused score → step-up |
| A6' Mimic | Imitate typing rhythm | Not quantified (no open mimicry data). Expect worse than zero-effort (tey2013) | Step-up remains the real gate |
| A7 Poisoner | Drift the template toward self | With supervised updates the attacker must first pass step-up. Unsupervised mode: 9% takeover over 28 days, equal to the 8–9% no-attack baseline (Tappy) | §6 policy |

Out of scope: account-recovery attacks, phishing of the step-up factor (mitigated by using phishing-resistant authenticators), and legal coercion.

## 3. Components and data flow

```
 ┌──────────────── device (ztbe-agent, Go) ─────────────────┐            ┌──────── server (ztbe-verifier, Go) ───────┐
 │ capture ─► features ─► window(N=200 keys | 60 s active)  │            │                                            │
 │ (gohook/evdev; key→zone,   │                             │            │  verify sig, seq, nonce epoch, device      │
 │  content discarded)        ▼                             │  assertion │  attestation status                         │
 │              score(template) ─► fuse(k=4) ─► risk band ──┼──(mTLS)───►│  risk policy ─► keep / step-up / end      │
 │                  ▲                         sign(devkey) │            │                    │                        │
 │      unseal(TPM/keystore) ◄── sealed blob (1.7 KB)       │            │                    ▼                        │
 │                  ▲                                       │◄───────────┤  WebAuthn step-up (go-webauthn)            │
 │ adapt (supervised) ◄── "strong-auth OK at t" ─────────────┼────────────┤  signed "checkpoint" token                 │
 └───────────────────────────────────────────────────────────┘            └────────────────────────────────────────────┘
```

1. **Enrol**
   - WebAuthn registration of a device-bound credential, with attestation verified via go-webauthn. The agent also creates an assertion-signing key inside the TPM (go-tpm). The key is bound to that credential at registration, and its TPM attestation (AK certify) is checked server-side with go-attestation.
   - The agent collects windows for at least 7 days *or* at least 30 windows, whichever comes later. The template is the mean plus a shrinkage scale (§5.1).
   - The template is sealed (AES-256-GCM, key from the TPM or keystore) and raw events are erased.
2. **Verify** (continuous). Every closed window is scored locally. Every k=4 windows the agent emits `Assertion{device_id, seq, server_epoch_nonce, t_start, t_end, n_windows, band∈{ok,uncertain,high}, model_ver, policy_ver}` and signs it (Ed25519 or P-256, about 200 B).
3. **Server** checks the signature, that `seq` is monotonic, and that the epoch nonce is fresh (rotated every 10 min). It then applies policy:
   - `high` → step-up within 60 s or end the session;
   - two consecutive `uncertain` → step-up.

   The server stores events for at most 30 days (proposed; needs a DPIA).
4. **Adapt.** After a successful step-up, the server returns a signed checkpoint. Windows within T=30 min of that checkpoint may update the template (§6).
5. **Migrate** to a new device by re-enrolling (preferred). Optional escrow: encrypt the template under a key derived through the **WebAuthn PRF extension** (`prf`, webauthn3 §10.1.4, checked) of the user's passkey, so the server stores ciphertext it cannot open. Not validated here.

## 4. Data and storage budget

| Item | Where | Size | Source |
|---|---|---|---|
| Sealed template (μ, σ for 36 features, 4 anchors, metadata) | device | 1,756 B | go-he `plain_test.go` (measured) |
| Population prior (μ, σ, quantile edges 36×15, LDA 36×16) | device (shipped with the model) | about 10 KB float32 (*inferred*) | |
| Device record (pubkey, attestation digest, seq, epoch) | server | under 1 KB (*inferred*) | |
| Risk events (k=4 windows ≈ 4 min of active input) | server | about 200 B per event; one heavy user with 60 active min/day is about 3 KB/day (*inferred*) | |
| Raw events | RAM, current window only | about 200 keystrokes × 24 B (*inferred*) | erased after feature extraction |

## 5. Parameters and why

### 5.1 Features, window, matcher

- **Features:** the 36 content-blind zone features (`experiments/opendata/features.py`) for keyboard, plus 23 mouse features. Keys are mapped to L/R/S/other zones *before* any buffering, which satisfies FR-02.
  - Most stable on all three keystroke sets: median press-press latency and the zone hold means. The within/between ratio is 0.22–0.30 on Aalto, about 0.4 cross-session on LASER, and 0.41–0.51 cross-day on Tappy.
  - Rollover fraction is stable on Aalto and LASER but not on Tappy (ratio 1.19), possibly because of Tappy's timer resolution (experiments-v2 §2).
  - The least stable: the standard-deviation features and burstiness (ratio ≥ 0.9). Keep them only in the scale term or drop them in M3.
- **Window: 200 keystrokes, or 60 s of active typing, whichever comes first.**

  | Window | EER | Data |
  |---|---|---|
  | n50 / n100 / n200 | 14.5 / 10.9 / 8.6% | Aalto, intra-session |
  | n50 → n200 | 21.0 → 14.5% | LASER, cross-session |
  | t30 → t120 | 16.0 → 9.5% | LASER, cross-session |
  | t60 / t120 / t300 | 10.0 / 8.4 / 6.6% | Tappy, cross-day |

  Shorter windows react faster but double the error.
- **Matcher: scaled Manhattan in population z-space**, with the per-user scale `sqrt((n·MAD² + 2·w²)/(n+2))`, where w = 0.8·√(population within-variance).
  - LDA-16 improves EER when the priors are large and in-domain: 8.6 → 6.4% on Aalto n200, 14.5 → 11.1% on LASER n200.
  - It is unstable when they are small or out-of-domain. With about 60 in-domain Tappy users, LDA EER ranges from 8.9% to 16.4%, against 6.8% to 11.7% for SM.
  - So LDA or embeddings come in M3, trained on ZTBE's own consented population.
- **No binarisation.** Binary templates cost accuracy, as the EER numbers below show. Without a fuzzy extractor they buy no security, and O2 keyed transforms are needed only for renewability (M4).

  | Data | Unprotected SM | Best binary variant |
  |---|---|---|
  | Aalto n200 | 8.6% | 5.7% (LDA-LSSC, via LDA) |
  | Tappy n200 | 7.9% | 11.4% |

### 5.2 Decision fusion and operating point

Mean score over k consecutive windows (`fuse.py`, cross-session/cross-day):

| Data (window) | k=1 EER / FRR@FAR1% | k=4 EER / FRR@FAR1% / FAR@FRR5% | k=16 EER / FRR@FAR1% |
|---|---|---|---|
| LASER t30 (cross-session, 20 users) | 14.2% / 53.4% | 11.7% / 41.5% / 16.5% | 9.4% / 25.6% |
| Tappy t60, in-domain priors (cross-day, 63 users) | 11.5% / 58.9% | 8.5% / 41.1% / 14.8% | 7.3% / 39.9% |
| Tappy t60, Aalto priors (125 users) | 10.3% / 47.5% | 7.5% / 36.2% / 11.0% | 6.4% / 27.9% |

- Fusion helps only slowly because errors are **per-user systematic**. The Gini coefficient of per-user FRR rises from 0.6 to 0.8 as k grows (eberz2017's point).
- **Operating point: k=4, threshold at about 5% genuine "uncertain/high" per block.** Measured, that flags **85–89% of zero-effort impostor blocks** (FAR@FRR5% of 11–15%, Tappy).
- For a user with 60 active min/day (15 blocks), that is about **0.75 step-up prompts per day** on average (*inferred*), concentrated on a minority of users.
- Mitigation: track each user's own prompt rate during the first 2 weeks. If it exceeds 2/day, lower that user's sensitivity (a per-user threshold) and log that ZTBE is weak for that user. This is honest degradation instead of nagging.

### 5.3 Mouse

- Measured mouse accuracy with simple features is poor: SapiMouse EER 21–28%, Balabit 28–34%.
- MVP: mouse is only a **presence/liveness** feature (window coverage). It enters the fused score only after M3 shows a gain on Clarkson II.

### 5.4 Thresholds and calibration

- One global threshold per model version, calibrated on the in-domain population.
- Per-user adjustment only in the direction of *less* sensitivity, capped, and logged (§5.2).
- Never lock out on ZTBE alone. The only action is a step-up.

## 6. Adaptation and anti-poisoning

Measured on Tappy (75 users, ≥ 28 days, 200-key windows; design-options §4):

| Policy | FRR at week 8 (pooled) | Takeover after a 28-day boundary-walk attack |
|---|---|---|
| static | 10.9% | 8.0% (= no-attack baseline) |
| naive self-update | 7.4% | 83% |
| spec v1 dual-threshold gate | 10.9% | 83% |
| + anchor | 10.9% | 33% |
| + anchor + velocity + sanitise (rollback + freeze) | 11.0% | 9% |

v2 policy:
1. **Supervised updates (default).** Only windows within T=30 min after a successful WebAuthn step-up or login update the template. Rule: η=0.05 EWMA on μ, and the scale is re-estimated weekly from the last 50 supervised windows. The attacker must beat the step-up factor first, so A7 reduces to A6 + phishing.
2. **Unsupervised mode (opt-in, for low-friction deployments).** Uses the full guard stack:
   - gate at the median genuine score;
   - anchor radius at 0.67 × the verify threshold from the enrolment template;
   - velocity of at most anchor/14 per day;
   - sanitisation: when 10 consecutive updates are aligned (mean cosine > 0.5), roll back to the checkpoint, **freeze** for 200 windows, and raise a `possible-poisoning` event.
3. **Anchors.** Keep the enrolment template plus up to 3 checkpoints taken at strong-auth events (uludag2004-style multi-template). Each probe is scored against the current template. Updates must stay within the radius of *all* anchors.
4. **Time limit** (NIST 800-63B-4 requires one for adaptation). If 180 days pass without a supervised checkpoint, re-enrol. The 180-day value is proposed and needs a policy decision.

## 7. Latency and CPU budget (device and server)

| Step | Cost | Source |
|---|---|---|
| Feature update per event | O(1), sub-µs (*inferred*: about 20 flops) | |
| Score one window (36-D scaled Manhattan, with LDA if enabled) | 0.30 µs | measured, go-he |
| Unseal template (AES-GCM, software key) | 1.5 µs | measured; a TPM unseal is slower but happens once per login (UNVERIFIED for TPM latency) |
| Sign assertion | Ed25519 19.6 µs; P-256 31.3 µs (software). TPM-resident key: not measured | measured |
| Server verify per assertion | Ed25519 44 µs; P-256 68 µs | measured |
| Server load | about 1 assertion / 4 min / active user, so 10k concurrent users ≈ 42 verifications/s, under 1% of one core (*inferred* from the numbers above) | |

For comparison, the rejected server-side options:
- **HE (CKKS):** 9.8 ms server, 393 KB upload, and 787 KB of storage per user.
- **OPRF+lockers:** about 74 ms server and about 255 ms client per verification at ℓ=1500.

Both cost 10³–10⁵ times more than v2, and neither improves accuracy.

## 8. Claims we can and cannot make

**Can:**
- "Behavioural templates never leave the device. The server stores no biometric data."
- "Detects a different person typing on an unlocked session with roughly 85–90% probability within about 4 minutes of active typing, while prompting the genuine user in about 5% of 4-minute blocks." This was measured on open in-the-wild data (Tappy, cross-day). It must be re-measured on the target population.
- "Templates are sealed with a hardware-backed key where available, and are renewable by re-enrolment."
- "Template adaptation is gated by strong authentication."

**Cannot:**
- "Authenticates users" or "replaces MFA". It does not meet NIST/FIDO biometric FMR requirements.
- "Irreversible / ISO 24745-compliant template protection". Irreversibility is not provided on-device; confidentiality, integrity and renewability are.
- "Resistant to malware or synthetic input on the endpoint."
- "Cryptographic key derived from behaviour", or "zero-knowledge" (spec v1 language).
- Any FAR better than about 1% per decision.

## 9. Go MVP

### 9.1 Layout (single module `github.com/hossein1376/ztbe`)

```
cmd/ztbe-agent/        device daemon (systemd user service / launchd / Windows service)
cmd/ztbe-verifier/     server: assertion verification, policy, WebAuthn step-up, checkpoints
cmd/ztbe-eval/         offline evaluator over the same feature code (cross-checks experiments/opendata)
internal/capture/      OS input hooks: gohook (cgo) | evdev (linux, x/sys/unix) | browser bridge (later)
internal/zone/         key→zone mapping per layout; content discarded at source (FR-02)
internal/features/     streaming window features (keystroke 36, mouse 23), fixed-size arrays, no heap churn
internal/model/        prior (versioned, signed), template, scaled-Manhattan scorer, LDA (M3), fusion
internal/adapt/        supervised/unsupervised policies, anchors, sanitiser (port of adapt.py)
internal/seal/         sealing backends: TPM 2.0 (go-tpm, go-tpm-tools), macOS Keychain / Windows DPAPI / Secret Service (go-keyring) fallback; memguard for unsealed buffers
internal/attest/       device signing key, TPM AK certification (go-attestation), assertion encode/sign/verify
internal/wire/         assertion + checkpoint schema (CBOR via fxamacker/cbor or protobuf; versioned)
internal/policy/       server risk policy, step-up triggers, rate limits
internal/webauthn/     RP integration (go-webauthn/webauthn)
```

Licences: lattigo, go-tpm, go-attestation, go-tpm-tools, memguard and tink-go are Apache-2.0; go-webauthn is BSD-3; gohook and go-keyring are MIT; circl is BSD-3 (only needed if O3 is added). fxamacker/cbor is MIT (GitHub API, 2026-10-21).

### 9.2 Milestones

| M | Deliverable | Exit criteria (measurable) |
|---|---|---|
| M0 (1 wk) | `internal/features` + `cmd/ztbe-eval` reproduce `experiments/opendata` | Go and Python features agree within 1e-6 on LASER and Tappy. Same EERs ±0.2 pp |
| M1 (2 wk) | Agent capture → windows → score → fusion, in-memory template | CPU < 1% and RSS < 15 MB while typing (NFR-01). Content-blindness test: no key identity reaches `features` |
| M2 (2 wk) | Seal (TPM + keystore fallback), device key, signed assertions, verifier with seq/nonce checks | Assertion forgery, replay and rollback tests fail closed. TPM unseal and sign latency measured |
| M3 (3 wk) | Clarkson II re-evaluation (when available) and an in-domain population; optional LDA/embedding; mouse fusion test | Cross-session EER and FAR@FRR5% at k=4 on Clarkson II reported. LDA adopted only if it improves by ≥ 1 pp |
| M4 (2 wk) | WebAuthn step-up, supervised adaptation, anchors, sanitiser; optional per-RP keyed transform (O2) for renewability | Poisoning simulation reproduced in Go: takeover ≤ baseline + 2 pp, week-8 FRR ≤ static |
| M5 (2 wk) | Pilot hardening: DPIA inputs, retention, user-visible status, kill switch | Pilot on ≥ 20 consenting users for 4 weeks. Measured per-user prompt rate and Gini |

## 10. Decisions

The full rationale for each decision, and what would change it, is in [`notes/decisions.md`](notes/decisions.md).

1. **Role: decided by Hossein (2026-10-21).** ZTBE is a **risk signal and step-up trigger only**. It is not an authentication factor and never locks a user out on its own.
2. **Trust anchor: decided by research assistant (delegated).** Hardware-backed keys where available, with a software fallback allowed. Every assertion carries `key_protection`, and the relying party weighs it.
3. **Population priors.** Nothing derived from Aalto or Tappy ships. Shipped priors come only from our own consented collection. Until then the MVP uses self-normalised templates.
4. **Adaptation.** Supervised-only by default. Unsupervised mode is opt-in, with the full guard stack. Re-enrol after 180 days without a checkpoint.
5. **Server-side encrypted matching (HE / OPRF).** Out of scope for v2.
6. **Workforce use.** Opt-in volunteer pilots only, plus technical minimisation (3-level bands only, at most 30-day retention, no per-person reporting API). A legal opinion on AI Act Annex III(4)(b) is required before any workforce deployment.
7. **Tappy.** Research measurements only. No shipped models, and no use of health labels.
