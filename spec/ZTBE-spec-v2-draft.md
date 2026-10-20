# ZTBE v2: Specification (draft)

Status: draft, 2026-10-21. It supersedes `ZTBE-spec-v1.0.0-draft.md`. Normative words (MUST, SHOULD, MAY) follow RFC 2119.

Evidence:
- `notes/experiments-v2.md` (open-data experiments; experiment names in brackets below);
- `experiments/opendata/results/userpolicy_*.txt` and `results/power.txt` (this pass);
- `notes/design-options.md`;
- `notes/decisions.md` (D1–D7).

Citation keys refer to `references/references.bib`. Numbers come from our own runs or from sources read at abstract level or better; anything else is marked UNVERIFIED.

---

## 1. Scope and non-goals

**Decision D1.** ZTBE is a continuous **risk signal** and step-up trigger. It is **not an authentication factor**. It never grants access, and it never locks a user out on its own. The worst it can cause is a step-up challenge with a strong authenticator (WebAuthn).

In scope:
- keystroke dynamics on desktops (content-blind, hand-zone features), plus optional mouse dynamics;
- on-device scoring against a device-sealed template;
- signed risk assertions sent to a verifier;
- relay of risk changes to relying parties (RPs) through OpenID SSF/CAEP or through an OAuth step-up challenge.

Non-goals:
- **Identification**, meaning 1:N search, and any cross-service linking of users.
- **Primary or second-factor authentication.** No AAL claim is made; NIST SP 800-63B-4 does not allow it at our error rates (§11).
- **Template protection by fuzzy extractors or BTP schemes as the security boundary.** v1 FR-04 is dropped (§3).
- **Homomorphic or 2PC matching** (D5; costs measured in `experiments/go-he`).
- **Emotion, health or productivity inference.** Tappy PD labels are never used (D7). Emotion inference in the workplace is prohibited under the AI Act (§10).
- **Employee monitoring products** (D6).
- **Touch and mobile keyboards** in v2. Platform and API differences are left to v3.

## 2. Threat model

Assets:
1. the user's behavioural template and features;
2. the integrity of the risk signal;
3. the user's session.

**On-device malware with the user's privileges is out of scope.** Such an attacker can keylog, read the live feature stream, inject input and drive the agent. No behavioural scheme survives this; see rahman2013sfr below.

| # | Adversary | Capability | Goal | ZTBE control | What the control actually gives |
|---|---|---|---|---|---|
| A1 | DB dump (verifier or RP storage) | Reads all server state | Templates, profiling | The server stores **no templates and no features**, only device public keys, attestation results, the band history (≤ 30 days, D6) and sequence state | Nothing behavioural to steal. v1's helper-data leakage problem disappears by construction rather than by a fuzzy extractor. |
| A2 | Server compromise (active) | Runs verifier code | Forge "ok" for a stolen session; read templates | Assertions are signed by a device key (hardware-backed where possible, D2); templates never leave the device | A2 can *ignore* ZTBE for services it controls, but cannot make another RP accept a forged device assertion without the device key. A2 cannot obtain templates. |
| A3 | Session hijack (stolen cookie or token used from another machine) | Valid session, no device key | Use the session | The RP binds the session to the device key (assertions MUST arrive for active sessions, §9.4) | No fresh signed assertions arrive, so the session is degraded after `max_silence`. This is a device-binding control, not a behavioural one. |
| A4 | Unattended terminal (insider walks up to an unlocked machine) | Physical input on the enrolled device | Act as the user | Behavioural score → trust model → band `high` → WebAuthn step-up | Detection probability against **zero-effort** impostors: 72–93% within 5 windows, at 0.3–2.2 false alarms per 60 genuine windows (§6.5, Tappy). Not a guarantee. |
| A5 | Imitation / mimicry (human trains on the victim's rhythm) | Observes the victim, e.g. by shoulder surfing or replaying captured timings | Pass as `ok` | None strong. Partly mitigated by multi-feature, long windows, the trust model and step-up on sensitive operations | Literature (§2.1): mimicry raises FAR several-fold. **ZTBE does not resist a trained, targeted imitator**, and the spec says so. |
| A6 | Synthetic input injection / bots (OS-level injected events, timing forgeries) | Injects events through OS APIs or virtual HID | Pass as `ok`, or poison adaptation | Injected-event provenance check (§4.4), a liveness/synthetic detector as a separate signal, and supervised adaptation only | Provenance flags catch naive injection (OS-flagged events). Hardware-level injection (USB HID emulators) is not detectable by provenance. Detector performance on open data is quoted in §2.1, not measured by us. |
| A7 | Malicious insider (operator or admin of the verifier or RP) | Reads band streams, sets policy | Profile or surveil employees | 3-level band only, no score/feature API, ≤ 30-day retention, purpose limitation in RP terms (D6) | Limits what can be learned per person. It cannot stop an employer from *using* bands punitively; that is a legal and organisational control (§10). |
| A8 | Template poisoning (gradual drift) | Input on the device over days | Shift the template towards the attacker | Supervised-only adaptation (D4); the unsupervised mode needs the full guard stack | Measured: naive or gated updates lead to 83% takeover after 28 days. The full stack gives 9% (equal to the no-attack baseline). Supervised mode reduces A8 to A6+A4 plus defeating the step-up. |

### 2.1 What the attack literature says (untested by us)

| Attack | Source (level) | Setting | Degradation | Countermeasure reported |
|---|---|---|---|---|
| Mimicry with feedback training | tey2013 (F) | 2 fixed 8-char passwords, 84 attackers | FAR 0.24 → 0.63 (easy pw) and 0.20 → 0.42 (hard) with partial information. The 14 best attackers reached 0.99 with full information. | None effective in the paper. The authors question keystroke dynamics as a biometric. |
| Snoop-forge-replay (keylogged timings → synthesised forgery) | rahman2011sfr, rahman2013sfr (A) | **Free-text continuous** verification, 50 users | Up to 87.75% forgery success against configurations with < 11% zero-effort pass rate. 20–100 snooped keystrokes suffice. | None. This is the closest analogue to ZTBE, which is why on-device malware is out of scope. |
| Population-statistics algorithmic attack | serwadda2013 (A) | Password keystrokes, > 3000 users | Mean EER +28.6% to +84.4%. Worse for short strings; some users hit much harder. | Longer strings; test against algorithmic attacks rather than only zero-effort. |
| Robot (Lego) forgery | serwadda2013ccs, serwadda2016robot (A) | **Touch** swipes | EER +339% to +1004% (population-driven). FAR up to 5× (population and user-tailored). | Not keystroke, but shows population-statistics attacks beat zero-effort baselines. |
| Targeted mimicry, touch | khan2016mimicry (A) | 3 touch-IA schemes, 256 pairs | 84% bypass by shoulder surfing (< 2 min observation); 86% with offline training. | The authors conclude touch IA is unsuitable for security. |
| Synthetic forgeries, non-targeted | stefan2012 (A) | 20 users; Markov bots from **other users'** data | Detected by SVM at low false-positive rates | Robust only to non-targeted synthesis. |
| Synthetic forgeries, targeted | gonzalez2022liveness (A) | 3 public datasets | New forgeries reach FAR ≈ 15% with target data (2–3× earlier methods) | CDF-distance liveness detector: FAR/FRR 1–2% when the attacker has only population data |
| GAN / data-driven keystroke synthesis | dealcala2023becaptchatype (A) | 136M keystrokes, 168k subjects | Synthetic data is "very difficult to detect" unless the detector is trained on massive labelled data | Train bot detectors with synthetic samples |
| Mouse synthesis | acien2022becaptchamouse, antal2021sapiagent (A) | Mouse trajectories | Generators produce human-like trajectories | 93% bot-detection accuracy from one trajectory (neuromotor features) |
| Frog-boiling (gradual poisoning) | wang2012frog (M) | Behavioural templates with adaptation | UNVERIFIED (numbers not read) | Our measured guard stack (§8) |

**Consequences for ZTBE:**
1. Zero-effort FAR is an optimistic bound. Every claim in this spec is labelled "zero-effort".
2. The evaluation protocol (§12) MUST add a population-statistics forgery and a targeted forgery (snoop-forge-replay from a held-out sample), and report IAPAR in the ISO/IEC 30107-3 sense.
3. Synthetic-input detection is a *separate* signal (`synthetic_suspect`), not folded into the score.

## 3. Feature set (v1 → v2)

Windows are N keystrokes or T seconds of *active* input. Features are content-blind: each key is mapped to a hand zone (L, R, S = space, M = modifiers), and characters are discarded at capture (v1 FR-02 kept).

ICC and test-window within/between ratio come from [experiments-v2, per-feature table]. Ratio < 0.5 is good; > 1 means within-user variation exceeds between-user variation.

| v1 feature | v2 | Evidence |
|---|---|---|
| Hold/dwell per zone (`hold_mu_{L,R,S}`) | **Keep** | ICC 0.96–0.97; ratio 0.26–0.30 (Aalto), 0.37–0.40 (LASER cross-session), 0.40–0.71 (Tappy) |
| Press-press latency (median, per zone transition) | **Keep** | `pp_median` ICC 0.98, ratio 0.22–0.41. Zone-transition means: ratio 0.37–0.59 (Aalto), 0.54–0.90 (LASER). |
| Release-press flight (per zone transition) | **Keep** (redundant with PP+hold; kept for robustness) | `rp_mu_*` ratio 0.37–0.97; Tappy self-prior ICC for `rp_mu_SR`/`rp_mu_RS` is 0.01–0.03 (unstable) |
| Rollover (RP < 0) fraction | **Keep, conditional** | Among the best features on Aalto/LASER (ratio 0.24/0.39), but on Tappy the ratio is 1.19 (fails). The suspected cause, a ~15.6 ms timer, is untested. MUST be disabled when the measured timer resolution is > 4 ms (agent self-test). The 4 ms cut-off is a proposal. |
| Per-transition SDs (`pp_sd_*`) | **Drop** | Ratio 0.75–1.03 on Aalto (intra-session), but 0.90–1.81 on LASER and Tappy (cross-session or cross-day) |
| Hold SDs | Keep `hold_sd_{L,R}`, drop `hold_sd_S` | L/R ratio 0.52–0.99 (6 of 8 cells ≤ 0.70) vs S ratio 0.66–1.21 |
| Error-correction ratio (backspace fraction) | **Drop** | Ratio 1.01 (Aalto), 1.90 (LASER) |
| Burstiness | **Drop** | ICC 0.30–0.53; ratio 1.09–1.57 |
| Pause fraction | **Drop** | Ratio 0.53–1.60 (fails cross-session) |
| EW-Welford streaming accumulation (v1 §3.2) | **Replace** with fixed windows plus robust per-window statistics (median, mean of trimmed values) | All results are per-window. An EWMA mixes windows across the decision boundary. Memory is trivial either way. |
| Mouse kinematics (velocity/accel/jerk, straightness, click dwell) | **Optional, off by default** | 23 basic features: EER 21–28% (SapiMouse), 28–34% (Balabit). Too weak alone. Keystroke+mouse fusion was **not measured** (no open dataset with both for the same users). |
| Fitts IP | **Drop** | Needs target width, which a content-blind agent does not see |
| Web/DOM navigation Markov matrix, navigation entropy | **Drop** | Not content-blind in practice (routes and DOM states are content). No open data to test. Privacy risk outweighs unknown gain. |
| Circadian / time-of-day encoding | **Drop** | Not a behavioural biometric. It is a policy context that the RP already has. Including it couples the score to schedule changes. |
| v1 FR-04 irreversible hashing (fuzzy commitment, sample-then-lock, BioHash/Bloom) | **Drop as a security boundary** | Population-dictionary guessing opens 3.5–22% of lockers at FAR 1% with one guess (≈ 1–4 bits). Sample-then-lock at usable FRR (k=24: FRR 7.6%) lets one population guess open 52% of targets. Replaced by device sealing (§7). |
| v1 FR-07 unlinkability via salts | Replaced | Templates never leave the device, and the per-RP key is a WebAuthn credential (unlinkable per RP by design) |
| v1 NFR-05 zero raw persistence | **Keep** | Raw events live only in a ring buffer in locked memory. Only the sealed template persists. |

v2 keystroke vector: **21 features**:
- `pp_median`;
- `rollover_frac` (conditional);
- `hold_mu_{L,R,S}`;
- `hold_sd_{L,R}`;
- `pp_mu_{XY}` (8) and `rp_mu_{XY}` (6) for XY ∈ {LL, LR, LS, RL, RR, RS, SL, SR}, minus `rp_mu_SR` and `rp_mu_RS`.

The 36-feature set measured in the experiments is a superset of this. **The reduced set has not been re-run.** Re-running it is task M1-T3 in PLAN.

### 3.1 Input provenance (A6)

The agent MUST record for each window the fraction of events flagged as injected by the OS. Examples:
- Windows: `LLKHF_INJECTED` in the low-level keyboard hook;
- macOS: CGEvent source state ≠ HID system;
- Linux/evdev: events from uinput devices.

Any window with an injected fraction > 0 is *not scored*, and the agent sets `synthetic_suspect=true` in the next assertion. The OS flags named above come from platform API knowledge; **behaviour per OS is UNVERIFIED** in this repo and is MVP task M1-T5.

## 4. Windowing and fusion

- **Window.** `T = 60 s` of active typing (idle gaps > 5 s are removed), or `N = 200` keystrokes, whichever closes first. A window needs ≥ 40 keystrokes to be scored.
  - Measured EER per window: 8.4–10.0% for t60/t120 and 7.9–9.2% for n100/n200 on Tappy cross-day (Aalto priors). For LASER cross-session it is 9.5% (t120) and 14.5% (n200).
- **Score.** Scaled Manhattan against the sealed template: `s = mean_j |z_j − μ_j| / σ_j`.
  - Features are standardised with the population prior (mean, sd) shipped with the model. Per D3, this prior comes from our own consented population. The interim MVP uses self-normalised priors.
  - Scale shrinkage: `σ_j = sqrt((n·MAD_j² + 2·w_j²)/(n+2))`, where `w_j = 0.8·sqrt(pop within-var_j)`.
- **Fusion.** Mean score over the last `K = 4` windows, used for the block threshold (§6). The trust model (§6.4) runs on every window.
  - Measured at K=4: EER 7.5–8.5% and FAR@FRR5% 11–15% (Tappy t60) [fuse_*]. Gains flatten beyond K=4–8 [fuse_laser_n100].

## 5. Enrolment and cold start

Measured with `userpolicy.py`, cold-start section, on Tappy. The template is built from the first m windows; the test set is days ≥ 14. Each run uses 28–37 users and one split, so the numbers are indicative.

| Window type | m=1 | m=2 | m=3 | m=5 | m=8 | m=12 | m=30 |
|---|---|---|---|---|---|---|---|
| n200: keys | 200 | 400 | 600 | 1000 | 1600 | 2400 | 6000 |
| n200: EER per window / per 4-block | 14.1 / 11.3 | 11.0 / 8.2 | 10.4 / 7.5 | 10.5 / 7.5 | 10.2 / 7.1 | 10.3 / 7.2 | 10.0 / 7.2 |
| n100: EER per window / per 4-block | 18.5 / 14.6 (100 k) | 14.4 / 10.1 | 13.1 / 8.8 | 12.4 / 7.8 (500 k) | 12.6 / 8.3 | 13.0 / 8.5 | 12.9 / 9.1 |
| t60: EER per window / per 4-block | 19.8 / 18.7 (1 min) | 12.7 / 9.2 | 12.0 / 8.9 | 10.6 / 7.4 (5 min) | 10.5 / 7.1 | 10.7 / 7.5 | 11.2 / 8.5 |
| t120: EER per window / per 4-block | 20.5 / 18.3 (2 min) | 15.9 / 12.1 | 12.5 / 9.8 | 10.8 / 8.4 (10 min) | 9.9 / 7.0 | 9.3 / 6.0 (24 min) | 8.9 / 5.8 (60 min) |

Findings:
- Count-based windows plateau after **≈ 500–1,000 keystrokes**. Time-based t120 keeps improving to **≈ 25 min of active typing**.
- FRR@FAR1% does not improve with more enrolment data (42–75% throughout). The low-FAR tail is a matcher and feature limit, not an enrolment limit.

Policy:
- **E1.** Enrolment needs ≥ 1,000 scored keystrokes **and** ≥ 15 min of active typing, spread over ≥ 2 calendar days. The calendar-day condition is a proposal, since cross-day variation dominates (LASER cross-session ≈ 2× intra-session EER).
- **E2.** Until E1 is met, assertions carry `status="enrolling"` and no band. RPs MUST treat this as "no signal", not as `ok`.
- **E3.** Enrolment windows are accepted only inside a supervised period: within 30 min after a WebAuthn ceremony (D4).
- **E4.** Re-enrolment is triggered by:
  - the 180-day limit (D4);
  - a persistent-goat condition (§6.6);
  - the user's request.

## 6. Scoring model and threshold policy

### 6.1 Evidence: per-user thresholds

`userpolicy.py` on Tappy cross-day, K=4. Priors come from a disjoint half of the Tappy users (a proxy for our own population).
- Timeline: enrol days 0–6, calibrate days 7–13 (genuine only), test days ≥ 14.
- Each config has 29–40 users, so the numbers are indicative.
- FRR = fraction of genuine blocks flagged; FAR = fraction of impostor blocks not flagged.

| Policy | Pooled FRR | Mean FRR per user | p90 user FRR | Gini FRR | Pooled FAR | p90 target FAR |
|---|---|---|---|---|---|---|
| P0 global threshold (5% of pooled calib. blocks) | 3.7–7.5% | 6.9–12.2% | 17.1–28.9% | 0.66–0.76 | 5.9–14.5% | 12.3–33.3% |
| P1 per-user q95 of own calib. week | 10.7–16.6% | 17.5–22.4% | 38.3–66.7% | 0.52–0.64 | 7.9–9.3% | 15.9–33.7% |
| P2 per-user, floor P0, cap q99 pooled | 3.4–5.7% | 5.7–9.4% | 17.1–27.7% | 0.70–0.76 | 7.9–15.8% | 25.7–35.1% |
| P3 z-norm on calib. scores | 7.8–12.2% | 12.7–19.7% | 34.8–50.0% | 0.55–0.68 | 7.9–12.1% | 24.2–40.2% |
| P5 shrinkage of q95 toward P0 (n0 = 20 blocks) | 5.0–9.2% | 8.6–13.6% | 21.0–30.9% | 0.61–0.69 | 5.9–11.5% | 17.7–25.6% |

Menagerie check, following yager2010 and doddington1998:
- Per-user classes are near chance level. Worms number 2–3, chameleons 3–4, phantoms 2–3 and doves 2–3, against 1.8–2.5 expected under independence.
- The Spearman correlation between a user's mean genuine score and mean impostor score is 0.00–0.25.

Stability of high-error users:
- The calibration-week FRR barely predicts test-period FRR (Spearman 0.04–0.39).
- Of the users above 20% FRR in the calibration week, 0–2 out of 1–5 were still above 20% later.

**Interpretation.** On this data, high error is mostly a **state** (a bad day or week), not a **trait** (a stable "goat"). Per-user thresholds fitted on one week chase noise: P1 and P3 roughly double FRR. Loosening thresholds for apparent goats (P2) buys 0.3–1.8 pp FRR at a cost of 1.3–3.1 pp FAR. This is the lamb trade-off. With ≤ 40 users, the menagerie structure cannot be confirmed or excluded.

### 6.2 Policy (normative)

- **T1. Global operating point.** One threshold `τ_g` per model version, set on our own consented population (D3) so that 5% of genuine K-blocks exceed it. It ships with the model and is signed (`policy_ver`).
- **T2. No per-user thresholds in v2.0.** Per-user calibration MAY be enabled in v2.x only if all three hold:
  - it uses ≥ 50 supervised blocks spanning ≥ 4 weeks;
  - it uses shrinkage toward `τ_g` (P5 form, n0 ≥ 20);
  - it is hard-capped at the pooled q99 (P2 cap).

  T2 is **untested beyond one calibration week**. Collection plan: PLAN phase 3.
- **T3. Abstain band.** The band is a 3-level output (§6.3). `uncertain` is the abstain state; it covers the high-error-state minority without loosening anyone's threshold.
- **T4. Trust model for `high`** (§6.4). A single bad block MUST NOT produce `high`.

### 6.3 Band semantics (per assertion, i.e. per K = 4 windows)

| Band | Condition | Meaning for RP | Measured genuine rate | Measured zero-effort impostor rate |
|---|---|---|---|---|
| `ok` | Block score ≤ τ_g and no trust alarm | No action | ≈ 92.5–96.3% of blocks (1 − P0 FRR) | 5.9–14.5% of impostor blocks get `ok` |
| `uncertain` | Block score > τ_g, no trust alarm | Optional: shorten session lifetime, require step-up for **sensitive operations only** | ≈ 3.7–7.5% of blocks | Most remaining impostor blocks |
| `high` | Trust alarm in this period (§6.4) | Step-up (WebAuthn) now | See §6.5 | See §6.5 |

CAEP mapping: `ok`→LOW, `uncertain`→MEDIUM, `high`→HIGH (openid-caep §3.8).

### 6.4 Trust model (after Mondal & Bours, mondal2015ins / bours2015perf)

Per window i with score `s_i`:

```
trust ← min(100, trust + clip(a·(τ_w − s_i), −P, +R))
alarm ⇔ trust < 50 → band=high; trust ← 100 after a successful step-up
```

Here `τ_w` is the q90 of pooled genuine *window* scores in calibration. Defaults: `a = 40`, `P = 40`, `R = 5`.
- Trust is reset to 100 at every strong authentication.
- Trust is never persisted beyond the session.

### 6.5 Measured trust-model operating points

`userpolicy.py`, Tappy, single-window sequences; zero-effort impostors use 30 consecutive windows of another user.

| τ_w quantile, a, P, R | Genuine alarms per 60 windows (mean / p90 user) | Impostor alarm within 5 / 10 windows | Mean windows to alarm |
|---|---|---|---|
| q80, 40, 40, 5 | 1.35–2.21 / 3.66–5.59 | 83–93% / 91–97% | 2.9–4.8 |
| **q90, 40, 40, 5 (default)** | **0.51–1.49 / 1.88–2.92** | **72–88% / 81–93%** | **4.1–7.6** |
| q90, 25, 30, 3 | 0.32–1.11 / 0.94–1.98 | 57–76% / 72–88% | 5.5–9.8 |
| q95, 50, 50, 5 | 0.32–1.20 / 0.94–1.66 | 60–82% / 72–89% | 5.2–10.4 |

Reading the default row:
- For t60 windows (60 windows ≈ 1 h of active typing), the default gives 1.05 step-ups per active hour for the mean user and 2.78 for the p90 user. Across configs the range is 0.51–1.49 alarms per 60 windows.
- An unattended-terminal impostor is caught within 5 minutes of typing in 72–88% of cases.

That step-up rate is high for daily use. Hence:
- **T5.** The RP SHOULD rate-limit step-ups caused by ZTBE to ≤ 2 per hour per user. Beyond that, it SHOULD fall back to the `uncertain` treatment.
- **T6.** Deployments MAY use the q95 row (fewer alarms, slower detection). The trade-off MUST be stated in the DPIA.

### 6.6 Persistent high-error users

If a user's 14-day rolling ZTBE step-up rate exceeds 3 per day of active use:
1. offer re-enrolment;
2. if the rate is still over the limit 14 days after re-enrolment, **disable ZTBE for that user**. Under D1 this has no penalty; the RP sees `status="disabled"`.

This is the v2 answer to the goat minority: abstain rather than loosen. The thresholds are proposals and untested.

## 7. Template sealing

The template (21 μ + 21 σ as float32, plus anchors; < 1 KB) is sealed at rest. It is decrypted only into locked memory (memguard) for scoring.

| Platform | Mechanism | Go library | Maturity (GitHub API / README, 2026-10-21) | `key_protection` |
|---|---|---|---|---|
| Linux / Windows with TPM 2.0 | Seal an AES-256-GCM template key to a TPM storage key (optional PCR policy). Assertion key: TPM-resident P-256, certified by AK | google/go-tpm, google/go-tpm-tools, google/go-attestation | go-tpm v0.9.8 (2025-12-29); README calls the `tpm2` TPMDirect API a "prototype"; `legacy/tpm2` also available. go-tpm-tools v0.4.11 (2026-10-10). go-attestation v0.6.4 (2026-08-11). All Apache-2.0 | `hw_attested` (AK chain to manufacturer EK cert verified) or `hw_unattested` |
| macOS (Apple silicon, T1/T2) | Secure Enclave P-256 key (keys stay in the PKA; apple-sep). Template key wrapped via ECIES to the SE key, or stored in Keychain with SE access control | facebookincubator/sks (ECDSA-P256 create/sign on TPM 2.0 Linux/Windows and SE on macOS ≥ 10.14); Keychain via cgo | sks: "stable beta", no tagged releases, Apache-2.0. **No Go-native SE attestation**: Apple does not offer third-party SE key attestation on macOS (UNVERIFIED; not found in apple-sep) | `hw_unattested` |
| Android (v3, out of v2 scope) | Android Keystore, TEE or StrongBox; key attestation chain to the Google root; verify server-side and check the revocation list (android-keyattest) | Kotlin/JNI; no mature Go binding identified | — | `hw_attested` |
| Fallback | OS keyring (Keychain, Secret Service, Windows Credential Manager) holding the AES key; assertion key in software | zalando/go-keyring v0.2.8 (MIT) | Mature | `software` |

Rules:
- **S1.** The template key and the assertion key are separate. Neither is exportable when the hardware path is used.
- **S2.** TPM unseal-and-sign latency is **not yet measured** (MVP task M2-T2). The software numbers are AES-GCM seal+open 1.5 µs and Ed25519 sign 19.6 µs.
- **S3.** `key_protection` is self-reported unless it is `hw_attested`. RPs MUST treat `hw_unattested` and `software` as advisory (D2).

## 8. Adaptation and anti-poisoning

Measured on Tappy (75 users, 28-day boundary-walk attack) [adapt_n200]:

| Policy | Week-8 FRR | Takeover |
|---|---|---|
| static | 10.9% | 8% |
| naive | 7.4% | 83% |
| v1 dual-threshold gate | 10.9% | 83% |
| + anchor | 10.9% | 33% |
| full stack (anchor + velocity + sanitise) | 11.0% | 9% |

v1's §6.1 gate alone does not stop poisoning.

**Default mode: supervised (D4).**
- **U1.** Only windows closed within **30 min after a successful WebAuthn ceremony** and with block score ≤ τ_g are update candidates.
- **U2.** μ is updated by EWMA with `η = 0.05` per accepted window. σ is re-estimated weekly from the last 50 supervised windows using the same shrinkage formula.
- **U3.** Anchors are the enrolment template plus ≤ 3 checkpoints taken at strong-auth events. An update is rejected if the new μ is further than `r_anchor = 0.67·τ_v` from *any* anchor, where τ_v is the verify threshold in score units, as in `adapt.py`.
- **U4.** Re-enrolment is required after 180 days without a supervised checkpoint. NIST 800-63B-4 requires time-limited adaptation; the 180-day value is ours.

The supervised mode itself is **not simulated**. The adaptation experiment covers unsupervised policies only. Its security argument is structural: the attacker must first pass a WebAuthn step-up. Its FRR benefit is unmeasured (PLAN M1-T4).

**Opt-in unsupervised mode.** Gate at the median genuine score, plus U3, plus velocity ≤ `r_anchor/14` per day, plus sanitisation: if the last 10 updates have mean cosine alignment > 0.5, roll back to the last checkpoint, freeze for 200 windows, and set `poisoning_suspect=true`. These are exactly the measured parameters.

## 9. Signed risk assertion and RP consumption

### 9.1 Device → verifier: `ZTBE-Assertion` (COSE_Sign1, RFC 9052; CBOR)

```
protected:   { 1 (alg): -7 (ES256) | -8 (EdDSA), 4 (kid): device_key_id }
payload (CBOR map, integer keys for size):
  1  v            uint   schema version (=2)
  2  dev          bstr   device id = SHA-256(device public key)[:16]
  3  seq          uint   strictly increasing per device
  4  nonce        bstr   current verifier epoch nonce (16 B, rotated every 10 min)
  5  t0, 6 t1     uint   window span, Unix seconds
  7  nwin         uint   windows in this assertion (normally K=4)
  8  status       uint   0=active 1=enrolling 2=disabled 3=paused(user)
  9  band         uint   0=ok 1=uncertain 2=high   (absent unless status=active)
  10 flags        uint   bit0 synthetic_suspect, bit1 poisoning_suspect, bit2 rollover_disabled
  11 kp           uint   key_protection: 0=hw_attested 1=hw_unattested 2=software
  12 model, 13 policy   tstr  model_ver, policy_ver (τ_g, trust params)
```

- No score, features, keystroke counts or content are ever included. This is minimisation (D6).
- Size is ≈ 120–200 B. Signing cost is 19.6 µs (Ed25519) or 31.3 µs (P-256) in software.

Verifier checks:
1. signature, with the device key registered at enrolment;
2. `seq` is greater than the last seen value;
3. `nonce` is the current or previous epoch;
4. `t1 ≤ now + 30 s`.

A failed check results in `band := high` with `risk_reason=ASSERTION_INVALID`. A missing assertion for an active session for longer than `max_silence` (default 15 min of reported activity) is surfaced to the RP as MEDIUM.

Go: veraison/go-cose v1.3.0 (**MPL-2.0**, file-level copyleft, acceptable for linking) and fxamacker/cbor v2.9.6 (MIT).

### 9.2 Enrolment binding

1. The user registers a WebAuthn credential with the RP or IdP (go-webauthn v0.18.2, BSD-3).
2. The agent creates the assertion key (TPM, SE or software).
3. It obtains a WebAuthn assertion whose challenge = SHA-256(assertion public key ‖ attestation blob), binding the ZTBE device key to the user's strong authenticator.
4. For TPM, the verifier checks the AK certification of the key (go-attestation).

### 9.3 Verifier → RP: OpenID SSF / CAEP

The verifier acts as an SSF **Transmitter** (openid-ssf, Final 2025). Events are SETs (RFC 8417) delivered by push (RFC 8935) or poll (RFC 8936).

Each band change emits a CAEP **`risk-level-change`** event:
- `current_level` ∈ {LOW, MEDIUM, HIGH};
- `previous_level`;
- `principal = "SESSION"` (or `"USER"`);
- `risk_reason` ∈ {`BEHAVIOUR_DEVIATION`, `SYNTHETIC_INPUT_SUSPECT`, `ASSERTION_INVALID`, `SIGNAL_LOST`}.

The `sub_id` uses RFC 9493 formats, preferably `iss_sub` or opaque.

Only *changes* are sent, not the 4-minute stream, which further minimises the data.

### 9.4 RP behaviour (normative for conforming RPs)

- On **HIGH**, the RP requires step-up. For OAuth resource servers, this means returning `401` with `WWW-Authenticate: Bearer error="insufficient_user_authentication"` and `acr_values` / `max_age` (RFC 9470). The client re-runs the authorisation request, the IdP performs a WebAuthn ceremony (user verification required), and a fresh token is issued.
- A successful step-up resets trust and opens a supervised-adaptation period (U1).
- A failed or abandoned step-up is handled by the RP's existing session policy. **ZTBE does not define a lockout** (D1).
- On **MEDIUM**, the RP MAY shorten the session or token lifetime and MAY require step-up for designated sensitive operations. It MUST NOT terminate the session on MEDIUM alone.
- On **LOW**, no action. LOW MUST NOT raise the session's assurance level (it is not a factor).
- RPs MUST NOT store bands longer than 30 days and MUST NOT expose per-person band reports (D6, contractual).

## 10. Privacy, GDPR and the EU AI Act

Legal analysis below is the research assistant's reading of the sources, not legal advice. D6 requires a legal opinion before any workforce use.

- **Is it biometric data?** GDPR Art. 4(14) covers "behavioural characteristics" from "specific technical processing" which "allow or confirm the unique identification". EDPB Guidelines 3/2019 §5.1 (edpb2019video) set three criteria: nature of data, specific technical processing, and the *purpose of uniquely identifying*. Recital 51, quoted there, covers "unique identification **or authentication**".
  - ZTBE templates and scores are therefore biometric data.
  - Because their purpose is to confirm that the person is the enrolled user (1:1), the conservative reading is that **Art. 9 applies even though ZTBE is only a risk signal**. Calling it a "risk signal" does not change the purpose test. v2 assumes Art. 9.
- **Lawful basis.** Art. 9(2)(a) explicit consent, with a non-biometric alternative of equal convenience (EDPB 3/2019 §5.1 example: "always offer an alternative way"). Here, opting out means no ZTBE, and the RP falls back to its normal session policy.
  - In employment, consent is presumptively not freely given (WP29 / EDPB consent guidance, cited in phase 1 as wp193; employment-context consent guidance itself UNVERIFIED in this repo). This is why D6 limits pilots to volunteers and requires legal review.
- **Minimisation and storage limitation.**
  - Raw events: memory only.
  - Templates: device only, sealed.
  - Server: bands and change events only, ≤ 30 days.
  - No score API.
  - Content-blind capture.
  - EDPB 3/2019 also asks for encrypted templates, separate storage and deletion of intermediate templates. These hold by construction (on-device, sealed; window vectors discarded after scoring).
- **DPIA.** Required (Art. 35: special-category data, systematic monitoring). Template: PLAN phase 3. It MUST include the zero-effort-only caveat (§2.1), the alarm rates (§6.5) and the user-disable path (§6.6).
- **EU AI Act** (euaiact2024, read through the consolidated mirror):
  - Annex III(1)(a) excludes from the high-risk class biometric *verification* whose sole purpose is to confirm that a person is who they claim to be.
  - Annex III(4)(b) lists AI used to monitor and evaluate the behaviour of persons in work relationships as high-risk. A workforce deployment could fall there irrespective of the verification exclusion, hence D6.
  - Art. 5(1) prohibits inferring emotions in the workplace and in education (the text was read; the sub-point letter (f) is UNVERIFIED). ZTBE MUST NOT infer emotion, stress or health.
- **NIST SP 800-63B-4** (non-EU, for US RPs): its biometric definition includes keystroke and mouse, and fraud indicators are not authentication factors. ZTBE claims no AAL.

## 11. Claims ZTBE v2 makes, and does not make

Makes, with the measured, zero-effort, open-data evidence above:
1. a continuous signal with ≈ 7–9% block EER on cross-day free text (indicative, N ≤ 75);
2. detection of a zero-effort walk-up impostor within 5 windows in ≈ 72–88% of cases, at ≈ 0.5–1.5 genuine alarms per 60 windows (t60: ≈ 1 per active hour);
3. no behavioural data at the server;
4. signed and replay-protected assertions.

Does **not** make:
- an authentication factor or AAL claim. The NIST/FIDO biometric bars (FMR ≤ 1/10000; FIDO FAR 1% / 0.01%) are far from our FRR@FAR1% of 20–60%;
- resistance to trained mimicry, snoop-forge-replay or on-device malware;
- template irreversibility as a cryptographic property (it is device sealing);
- fairness across age, disability or keyboard type (not evaluated; stragapede2024kvc is the reference benchmark for future work).

## 12. Evaluation protocol and metrics

Follows eberz2017 and ISO/IEC 19795-1 terminology (iso19795-1; standard text not read, so clause references are UNVERIFIED). Presentation attacks are reported per ISO/IEC 30107-3 (iso30107-3, metadata level).

- **Data splits.**
  - Chronological. Enrolment precedes test by ≥ 7 days.
  - No impostor data from test users is used in training.
  - Priors and τ_g come from a disjoint user set.
  - Report intra-session, cross-day and ≥ 4-week numbers separately.
- **Metrics (all with 95% CIs; clustered by user, §PLAN power analysis).**
  - Per window and per K-block: FMR/FNMR (algorithm) and FAR/FRR (system), EER, FRR@FAR 1%, FAR@FRR 5%. Users are equally weighted (macro) **and** pooled.
  - Per-user distribution: mean, p90, Gini of FRR and FAR; the share of users with FRR > 20%; menagerie classes (yager2010).
  - Continuous: genuine alarms per 60 active windows (mean, p90 user) and impostor windows-to-alarm (the ANIA/ANGA idea of bours2015perf).
  - FTE (enrolment not completed under E1 within 14 days) and FTA (windows < 40 keystrokes).
  - Attacks:
    - zero-effort;
    - population-statistics forgery;
    - targeted snoop-forge-replay with 100 / 200 / 1000 snooped keystrokes;
    - synthetic injection.

    For each: IAPAR, plus APCER/BPCER for the synthetic detector.
  - Adaptation: FRR trajectory over ≥ 8 weeks; takeover rate under a 28-day boundary-walk attack.
  - Cost: CPU per window, memory, assertion size, TPM unseal and sign latency.
- **Reporting.** State the N of users, the number of windows per user, the split seed and the dataset licence. Never report a single best split.

## Appendix A. Parameter table

| Parameter | Default | Source |
|---|---|---|
| Window | 60 s active or 200 keys; ≥ 40 keys | §4, experiments |
| K | 4 windows per assertion | fuse_* |
| τ_g | 5% genuine blocks flagged (own population) | §6.1 P0 |
| Trust | τ_w = q90, a = 40, P = 40, R = 5, alarm < 50 | §6.5 |
| Step-up rate limit | ≤ 2/h per user | §6.5 T5 (proposal) |
| Persistent-goat rule | > 3/day over 14 days → re-enrol → disable | §6.6 (proposal, untested) |
| Enrolment | ≥ 1000 keys, ≥ 15 min, ≥ 2 days, supervised | §5 |
| Adaptation | supervised 30 min, η = 0.05, anchors ≤ 3, r_anchor = 0.67·τ_v, 180-day re-enrol | §8, D4 |
| Epoch nonce | 10 min | §9.1 |
| max_silence | 15 min | §9.1 (proposal) |
| Retention | ≤ 30 days of bands | D6 |
