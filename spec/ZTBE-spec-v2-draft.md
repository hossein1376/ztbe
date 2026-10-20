# ZTBE v2.1: Specification (draft)

Status: draft v2.1, 2026-10-21 (round 2). It supersedes `ZTBE-spec-v1.0.0-draft.md` and the v2.0 draft (see git history). This is the **single normative document**; `PROPOSAL.md` is now only a rationale note. Normative words (MUST, SHOULD, MAY) follow RFC 2119.

Changes in v2.1 (round 2, after `notes/review-round-1.md`):
- agent integrity: no unauthenticated pause, heartbeat, silence → HIGH (§9.3, §9.6);
- session binding: RP-challenge-bound proofs plus sender-constrained sessions, so A3 is mitigated when the RP enforces it (§9.5);
- invalid assertions are dropped and counted; they no longer raise the band (§9.4);
- COSE algorithms ESP256 (−9) / Ed25519 (−19) per RFC 9864 (§9.1);
- adaptation off by default; unsupervised mode withdrawn (§8, D8);
- every number in §4–§6 re-measured with user-fold calibration, bootstrap CIs, matched-FAR comparison and the spec's own window and feature rules (`eval2.py`);
- device confound stated as the key limitation (§11);
- injected-input and accessibility policy, multi-keyboard rule, research-mode minimisation (§3.1–§3.3);
- PROPOSAL content (architecture, budgets, Go layout) folded in (§13–§14).

Evidence:
- `notes/experiments-v2.md` (§9 "Round 2" holds the re-runs);
- `experiments/opendata/results/eval2_*.txt`, `adapt_supervised_*.txt`, `adapt_adaptive_n200.txt`, `power.txt`;
- `notes/decisions.md` (D1–D17), `notes/collector-tradeoffs.md`, `docs/interfaces.md`, `docs/dpia-outline.md`, `docs/pilot-protocol.md`.

Citation keys refer to `references/references.bib`. Numbers come from our own runs or from sources read at abstract level or better. Anything else is marked UNVERIFIED.

**Reading the numbers.** Unless stated otherwise:
- data: Tappy, cross-day (enrol days 0–6, calibrate days 7–13, test days ≥ 14);
- configuration: the spec configuration (hybrid window `hyb`, 21 features `v21`, K = 4);
- thresholds: τ calibrated on a **disjoint user fold** (2 folds);
- brackets: 95% percentile bootstrap CI over users (B = 1000);
- impostors: **zero-effort and on a different device** (see §11 L1).

---

## 1. Scope and non-goals

**D1.** ZTBE is a continuous **risk signal** and step-up trigger. It is **not an authentication factor**. It never grants access, and it never locks a user out on its own. The worst it can cause is a step-up challenge with a strong authenticator (WebAuthn).

In scope:
- keystroke dynamics on desktops, captured by a **native agent** (D12) as content-blind hand-zone features;
- optional mouse dynamics (off by default);
- on-device scoring against a device-sealed template;
- signed risk assertions sent to a verifier;
- RP-challenge-bound presence proofs (§9.5);
- relay of risk changes to relying parties (RPs) through OpenID SSF/CAEP.

Non-goals:
- **Identification**, meaning 1:N search, and any cross-service linking of users.
- **Primary or second-factor authentication.** No AAL claim is made (§11).
- **Template protection by fuzzy extractors or BTP schemes as the security boundary.** v1 FR-04 is dropped (§3).
- **Homomorphic or 2PC matching** (D5).
- **Emotion, health or productivity inference** (D7; AI Act Art. 5(1)(f), §10).
- **Employee monitoring products** (D6).
- **Touch and mobile keyboards; scoring inside remote-desktop guests** (§3.1).

## 2. Threat model

Assets:
1. the user's behavioural template and features;
2. the integrity of the risk signal;
3. the user's session.

**On-device malware with the user's privileges is out of scope.** Such an attacker can keylog, read the live feature stream, inject input and drive the agent. No behavioural scheme survives this (rahman2013sfr). An attacker with local **administrator** rights can stop the agent service; the system treats that as signal loss (§9.6), not as tamper-proofing.

| # | Adversary | Capability | Goal | ZTBE control | What the control actually gives |
|---|---|---|---|---|---|
| A1 | DB dump (verifier or RP) | Reads all server state | Templates, profiling | The server stores **no templates and no features**: device public keys, attestation results, band history (≤ 30 days, D6), sequence state | Nothing behavioural to steal, by construction |
| A2 | Server compromise (active) | Runs verifier code | Forge "ok"; read templates | Assertions and proofs are signed by a device key (D2); templates never leave the device; RPs verify proofs against device keys themselves (§9.5) | A2 can ignore ZTBE for services it controls. It cannot make another RP accept a forged proof without the device key, and cannot obtain templates |
| A3 | Session hijack (stolen cookie or token used on another machine) | Valid session, no device key | Use the session | (a) RP-challenge-bound presence proof on sensitive operations and every `proof_interval` (§9.5); (b) sender-constrained session where available: DBSC for browsers, DPoP (RFC 9449) or mTLS (RFC 8705) for API clients | **Mitigated only if the RP enforces §9.5.** The thief cannot produce a proof bound to the RP's challenge and origin, so the RP steps up. Residual risk: relay through code on the victim's device (out of scope). Not behavioural |
| A4 | Unattended terminal (insider walks up to an unlocked, enrolled machine) | Physical input on the device | Act as the user | Score → trust model → band `high` → WebAuthn step-up. The attacker cannot pause the agent without WebAuthn (§9.6). Stopping it yields `SIGNAL_LOST` → HIGH | Zero-effort, **different-device** impostors: alarm within 5 windows in 81.6% [76.9, 86.2] of runs (within 10: 88.0%), at 0.64 [0.41, 0.93] genuine alarms per 60 windows (§6.5). **The same-device rate is unknown (§11 L1). Not a guarantee** |
| A5 | Imitation / mimicry | Observes the victim; replays captured timings | Pass as `ok` | None strong. Partly mitigated by long windows, the trust model and step-up on sensitive operations | Mimicry raises FAR several-fold (§2.1). **ZTBE does not resist a trained, targeted imitator** |
| A6 | Synthetic input injection / bots | Injects events through OS APIs or virtual HID | Pass as `ok` | Injected events are never scored (§3.1). Unexplained injection sets `synthetic_suspect` | OS flags catch API-level injection. Hardware HID emulators are not detectable by provenance. Detector performance is quoted from the literature (§2.1), not measured |
| A7 | Malicious operator (verifier or RP admin) | Reads band streams, sets policy | Profile or surveil employees | 3-level band only; no score or feature API; ≤ 30-day retention; purpose limitation (D6) | Limits what can be learned per person. It cannot stop punitive use; that is a legal and organisational control (§10) |
| A8 | Template poisoning | Input on the device over days | Shift the template towards the attacker | **No adaptation by default** (D8). Optional supervised adaptation only (§8) | With no adaptation there is nothing to poison. Supervised updates require the attacker to pass WebAuthn first. The withdrawn unsupervised stack was broken by a jittered attacker: 31.6% takeover at 28 days vs a 5.3% baseline (`adapt_adaptive_n200.txt`) |
| A9 | Agent DoS via forged traffic | Can reach the verifier endpoint | Force step-ups | mTLS with the device key (§9.4); invalid assertions are dropped and counted, never escalated | An outsider cannot change a user's band |
| A10 | Signal suppression | Stops, pauses or blocks the agent (incl. network) | Act without being scored | Heartbeat every 60 s; silence while unlocked → `SIGNAL_LOST` → HIGH; pause only with a WebAuthn-backed grant (§9.6) | Converts suppression into a step-up. Cost: genuine crashes and network loss also cause step-ups (rate to be measured in the pilot) |

### 2.1 What the attack literature says (untested by us)

| Attack | Source (level) | Setting | Degradation | Countermeasure reported |
|---|---|---|---|---|
| Mimicry with feedback training | tey2013 (F) | 2 fixed 8-char passwords, 84 attackers | FAR 0.24 → 0.63 (easy pw) and 0.20 → 0.42 (hard) with partial information. The 14 best attackers reached 0.99 with full information | None effective in the paper |
| Snoop-forge-replay | rahman2011sfr, rahman2013sfr (A) | **Free-text continuous** verification, 50 users | Up to 87.75% forgery success with 50–200 snooped keystrokes (rahman2011sfr); effective with 20–100 (rahman2013sfr) | None. Closest analogue to ZTBE; hence malware is out of scope |
| Population-statistics attack | serwadda2013 (A) | Password keystrokes, > 3000 users | Mean EER +28.6% to +84.4% | Test against algorithmic attacks, not only zero-effort |
| Robot (Lego) forgery | serwadda2013ccs, serwadda2016robot (A) | **Touch** swipes | EER +339% to +1004%; FAR up to 5× | — |
| Targeted mimicry, touch | khan2016mimicry (A) | 3 touch-IA schemes, 256 pairs | 84% bypass by shoulder surfing; 86% with offline training | — |
| Synthetic forgeries, non-targeted | stefan2012 (A) | 20 users; Markov bots from other users' data | Detected by SVM at low false-positive rates | Robust only to non-targeted synthesis |
| Synthetic forgeries, targeted | gonzalez2022liveness (A) | 3 public datasets | FAR ≈ 15% with target data | Liveness detector: FAR/FRR 1–2% with population-only attacker |
| GAN keystroke synthesis | dealcala2023becaptchatype (A) | 136M keystrokes, 168k subjects | "Very difficult to detect" without massive labelled data | Train detectors with synthetic samples |
| Mouse synthesis | acien2022becaptchamouse, antal2021sapiagent (A) | Mouse trajectories | Generators produce **humanlike** (not user-specific) trajectories | 93% bot detection from one trajectory |
| Timing side channel | song2001ssh (F) | Inter-keystroke timing of SSH packets | Timing leaks information about keys typed; password search sped up by a factor of 50 | Motivates §3.3: per-event timing streams are content-revealing |
| Frog-boiling | wang2012frog (M) | Adaptive templates | UNVERIFIED (numbers not read) | No adaptation by default (D8) |

Consequences:
1. Zero-effort FAR is an optimistic bound. Every claim here is labelled "zero-effort".
2. The evaluation protocol (§12) MUST add a population-statistics forgery and a targeted snoop-forge-replay, and report IAPAR (ISO/IEC 30107-3 sense).
3. Synthetic-input detection is a separate signal (`synthetic_suspect`), not folded into the score.

## 3. Feature set

Windows close on active input (§4). Features are content-blind: each key is mapped by **scancode** (layout- and IME-independent) to a hand zone (L, R, S = space, M = modifiers). Characters are never materialised by the agent (v1 FR-02).

**Feature rule (explicit).** A candidate feature is dropped if either holds:
- its test-window within/between-user ratio is **> 1.0** in any cross-session or cross-day column (LASER, Tappy self-prior, Tappy) of the per-feature table (`notes/experiments-v2.md`);
- its Tappy self-prior ICC is **< 0.05**.

One exception: `rollover_frac` (Tappy self-prior ratio 1.19) is kept, but only when the agent's measured timer resolution is ≤ 4 ms (agent self-test). The 4 ms cut-off is a proposal.

The ICC values quoted below are the **population ICC under the Aalto prior**. They are not per-dataset stability evidence; the ratios are.

| v1 feature | v2 | Evidence (ratio; lower is better) |
|---|---|---|
| Hold per zone `hold_mu_{L,R,S}` | **Keep** | 0.26–0.30 (Aalto), 0.37–0.40 (LASER), 0.40–0.71 (Tappy) |
| Press-press latency (`pp_median`, zone-transition means `pp_mu_XY`) | **Keep** | `pp_median` 0.22–0.41; `pp_mu_*` 0.37–0.92 |
| Release-press flight `rp_mu_XY` | **Keep, except `rp_mu_SR`, `rp_mu_RS`** | Ratio ≤ 0.97. Tappy self-prior ICC is 0.03 / 0.01 for SR/RS (dropped by rule) and 0.13 for LR (kept) |
| Rollover fraction | **Keep, conditional** (timer ≤ 4 ms) | 0.24 (Aalto), 0.39 (LASER), 1.19 (Tappy self-prior) |
| Hold SDs | Keep `hold_sd_{L,R}`; drop `hold_sd_S` | L/R ≤ 0.99. S reaches 1.21 (Tappy self-prior) |
| Per-transition SDs `pp_sd_*` | **Drop** | 0.90–1.81 cross-session |
| Modifier hold `hold_mu_M` | **Drop** | 1.39 (LASER) |
| Backspace fraction, burstiness, pause fraction | **Drop** | 1.90, 1.57, 1.60 (LASER) |
| EW-Welford streaming (v1 §3.2) | **Replace** with fixed windows | An EWMA mixes windows across the decision boundary |
| Mouse kinematics | **Optional, off by default** | EER 21–28% (SapiMouse), 28–34% (Balabit). Fusion with keystrokes not measured |
| Fitts IP, DOM navigation, circadian encoding | **Drop** | Not content-blind, or not behavioural |
| v1 FR-04 irreversible hashing | **Drop as a security boundary** | Population-dictionary guessing opens 3.5–22% of lockers at FAR 1% with one guess. Replaced by device sealing (§7) |
| v1 FR-07 unlinkability via salts | Replaced | Templates never leave the device; per-RP keys are WebAuthn credentials |
| v1 NFR-05 zero raw persistence | **Keep** | Raw events live only in a ring buffer in locked memory |

**v2 keystroke vector: 21 features.**
- `pp_median`;
- `rollover_frac` (conditional);
- `hold_mu_{L,R,S}`;
- `hold_sd_{L,R}`;
- `pp_mu_XY` for the 8 transitions XY ∈ {LL, LR, LS, RL, RR, RS, SL, SR};
- `rp_mu_XY` for 6 of them: LL, LR, LS, RL, RR, SL.

**Measured.** The 21-feature set is **non-inferior** to the 34-feature superset (`eval2_hyb_{v21,all}_all.txt`):
- pooled FRR at matched FAR 10%: 6.8% [4.3, 11.2] (v21) vs 6.6% [4.4, 9.6] (all);
- impostor alarm within 5 windows: 81.6% vs 77.3%.

### 3.1 Input provenance, assistive technology and remote sessions (A6, accessibility)

Each event is classified at capture:

| Class | How it is recognised (per OS, `notes/collector-tradeoffs.md`) | Scored? | Effect |
|---|---|---|---|
| `physical` | Not flagged as injected; from a HID keyboard device | Yes | — |
| `injected-allowlisted` | Flagged as injected, and the source matches the deployment allowlist: on-screen keyboard, dictation, AT software, password-manager auto-type, configured KVM tools | No | Excluded from features and from the 40-key minimum. If allowlisted events are > 50% of a period's events, the assertion carries `unscored_assistive` and **no band**. RPs MUST treat this as "no signal", **never as suspect** |
| `injected-unknown` | Flagged as injected, source not allowlisted or unidentifiable | No | Sets `synthetic_suspect` → CAEP **MEDIUM** with reason `SYNTHETIC_INPUT_SUSPECT`. It is not HIGH, because benign tools are common |

OS signals used:
- Windows: `LLKHF_INJECTED` and `LLKHF_LOWER_IL_INJECTED` in the low-level hook (Microsoft KBDLLHOOKSTRUCT docs);
- macOS: the event-source Unix PID field (`kCGEventSourceUnixProcessID`) and the source state;
- Linux: whether the evdev node is a `uinput` virtual device.

How assistive tools actually appear on each OS is **UNVERIFIED** and is the MVP capture-spike task (PLAN M1-T5).

Further rules:
- **Evasion guard (assistive profile).** A walk-up attacker could switch to an on-screen keyboard to get "no signal". Therefore `unscored_assistive` is treated as "no signal" only if the user's **assistive profile** is set. The profile is set during a supervised period (§5 E3), by the user's declaration, or because allowlisted input was observed there. For other users, a switch from scored input to allowlisted injected input outside a supervised period yields **MEDIUM** (reason `UNSCORED_CHANGE`). That step-up is for sensitive operations only, never HIGH. The profile is a local flag in the sealed template. It is not sent to the server except as the per-period flag.
- **Remote sessions.** The agent MUST NOT score input inside a remote-desktop or VDI guest; Windows `GetSystemMetrics(SM_REMOTESESSION)` reports this. It reports `status=active`, flag `remote_session`, and no band. Deployments that need ZTBE for VDI run the agent on the **client endpoint**, where the physical keyboard is.
- **Opt-out without penalty.** A user who relies on assistive input, or who does not want ZTBE, can disable it (status `disabled`). The RP's non-biometric session policy then applies: the GDPR alternative (EDPB 3/2019) and the NIST 800-63B-4 non-biometric alternative. The reason for opting out is **not recorded**.
- The agent MUST NOT infer disability, health or emotion from provenance or timing (D7).

### 3.2 Multiple keyboards (D-f)

- The agent keys templates by a local **keyboard class**: a hash of the HID vendor/product ID plus an internal/external bit.
  - Windows: Raw Input `RAWINPUTHEADER.hDevice` → device info;
  - macOS: IOHID device;
  - Linux: the evdev node.
- The class ID never leaves the device.
- At most 3 classes per user.
- A **new** keyboard class may be enrolled **only inside a supervised period** (§5 E3). Outside one, input from an unenrolled class is scored against the user's primary template, and the assertion sets `device_change`. Otherwise a walk-up attacker could plug in a keyboard and get "enrolling" (no signal).
- Expect higher FRR on device change. This is unmeasured (pilot §12).

### 3.3 Research mode minimisation (D-e)

Per-event (zone, down, up) streams reveal word lengths (via the space zone) and timing structure. Keystroke timing is a known text side channel (song2001ssh). Therefore:
- **Product mode** stores nothing but the sealed template.
- **Research mode** (pilot) stores only **per-window feature vectors**. Each carries a window start coarsened to the hour, a key count in buckets of 50, and the keyboard class index. It MUST NOT store per-event streams or zone sequences.
- The one exception is a lab **copy-typing task** on prescribed, non-personal text, under its own consent item (`docs/pilot-protocol.md`).
- Consent and DPIA texts MUST NOT describe raw zone streams as "content-blind".

## 4. Windowing, matcher and fusion

- **Window (`hyb`).** Closes at `T = 60 s` of active typing or `N = 200` keystrokes, whichever comes first. Idle gaps > 5 s are removed from active time and are not counted as intervals. A window needs ≥ 40 scored keystrokes. Implemented in `extract_tappy_v2.py`.
- **Score.** Scaled Manhattan against the template: `s = mean_j |z_j − μ_j| / σ_j`.
  - `z` is standardised with the population prior (D3).
  - `σ_j = sqrt((n·MAD_j² + 2·w_j²)/(n+2))`, where **MAD is the mean absolute deviation** (not the median), n is the number of enrolment windows, and `w_j = 0.8·sqrt(pop within-var_j)`.
- **Fusion.** The block score is the mean over the last `K = 4` windows; the block threshold is applied to it (§6). The trust model (§6.4) runs on every window.
- **Caveats.**
  - Adjacent windows are correlated, so the K-block FAR **understates** an attacker's chance relative to independent blocks. The design effect is applied to FRR planning (`power.py`), but not to FAR.
  - Fusion with K > 4 is not flat: on LASER n100, EER falls 14.0 → 13.3 → 11.1 for K = 4 → 8 → 16 (`fuse_laser_n100`). The K = 16 figure suffers survivorship (only heavy typists remain). K = 4 is kept for latency (≈ 4 min per assertion).

Window types compared (same users and folds; `eval2_*_all_all.txt`; pooled FRR at matched FAR 10%):

| Window | Users | FRR @FAR 10% | Impostor alarm ≤ 5 windows | Genuine alarms / 60 windows |
|---|---|---|---|---|
| hyb (spec) | 81 | 6.6% [4.4, 9.6] | 77.3% [72.0, 82.1] | 0.44 [0.28, 0.66] |
| t60 | 81 | 6.0% [4.0, 8.7] | 78.1% [73.8, 82.7] | 0.49 [0.32, 0.73] |
| s60 (60 s, no key cap) | 81 | 6.7% [4.3, 9.3] | 76.8% [71.4, 81.7] | 0.42 [0.27, 0.65] |
| n100 | 82 | 6.0% [3.9, 8.4] | 75.6% [70.9, 80.4] | 0.38 [0.22, 0.64] |
| n200 | 67 | 4.6% [2.8, 7.5] | 83.0% [77.6, 87.5] | 0.44 [0.24, 0.75] |
| t120 | 63 | 4.5% [2.6, 7.5] | 87.9% [83.5, 91.7] | 0.60 [0.35, 1.02] |

All CIs overlap. Longer windows detect faster per window, but each window takes longer. `hyb` is kept because it bounds the time per window (≤ 60 s active).

## 5. Enrolment and cold start

Measured in `eval2` §E (hyb, all features): the template comes from the first m windows, with τ_g from the other user fold using m-window templates.

| m (windows) | 1 | 2 | 3 | 5 | 8 | 12 | 20 | full week 1 |
|---|---|---|---|---|---|---|---|---|
| users | 107 | 105 | 105 | 104 | 97 | 94 | 82 | 81 |
| FAR at fold τ_g | 44.3% | 35.9% | 35.6% | 24.9% | 23.7% | 26.7% | 19.7% | 11.4% [8.6, 15.0] |
| FRR at fold τ_g | 7.0% | 9.0% | 7.9% | 4.3% | 3.6% | 3.5% | 4.0% | 5.3% |

With the 21 features: 43.6% (m = 1) → 19.4% (m = 8) → 18.8% (m = 20).

**Finding.** Cold start is a **FAR (security)** problem, not an FRR problem. A short enrolment produces a wide σ, so it accepts impostors. The users with ≥ 20 pre-test windows are heavier typists (selection effect).

Policy:
- **E1.** Enrolment completes when **both** hold: ≥ 20 scored windows, and ≥ 7 calendar days since the first enrolment window.
- **E2.** Until E1 is met, assertions carry `status=enrolling` and no band. RPs MUST treat this as "no signal", not as `ok`.
- **E3.** Enrolment windows (and new keyboard classes, §3.2) are accepted only inside a supervised period: within 30 min after a WebAuthn ceremony, or after OS unlock if the deployment's policy says so.
- **E4.** Re-enrolment is triggered by 180 days of template age (D8), a persistent high-error condition (§6.6), or the user's request.

LASER's "cross-session" data is **same-day** (session 2 ≈ 10 min after session 1, with a task switch). It is not used to motivate the calendar-day rule; the Tappy cross-day numbers are.

## 6. Scoring model and threshold policy

### 6.1 Evidence: threshold policies at matched FAR (`eval2_hyb_*`)

- FRR = fraction of genuine K-blocks flagged; FAR = fraction of impostor blocks not flagged.
- Pooled = all blocks; macro = mean over users.

**Nominal settings** (τ from the other fold; hyb, 34 features, 81 users):

| Policy | FRR pooled | FRR macro | FRR p90 user | Gini FRR | FAR pooled |
|---|---|---|---|---|---|
| P0 global τ_g (5% of other-fold calibration blocks) | 5.3% [3.8, 7.3] | 7.6% [5.1, 10.7] | 20.0% [13.2, 31.9] | 0.73 [0.65, 0.78] | 11.4% [8.6, 15.0] |
| P1 per-user q95 of own calibration week | 12.1% [8.5, 17.0] | 19.1% [14.3, 23.9] | 50.0% [37.0, 82.8] | 0.61 | 9.2% [5.7, 13.2] |
| P5 shrinkage of q95 toward τ_g (n0 = 20) | 6.8% [5.1, 9.1] | 8.8% [6.3, 11.8] | 20.8% [13.8, 44.4] | 0.66 | 10.9% [7.7, 14.3] |
| P3 z-norm (z = 1.645) | 11.7% [8.8, 15.8] | 15.2% [11.3, 19.7] | 40.0% [25.0, 55.6] | 0.62 | 9.5% [6.2, 13.4] |

**Matched pooled FAR** (each policy's knob swept; review M5):

| Policy | FRR pooled @FAR 10% | FRR macro @FAR 10% | FRR pooled @FAR 5% |
|---|---|---|---|
| P0 | **6.6% [4.4, 9.6]** | 8.9% [5.6, 12.2] | 14.1% [8.9, 22.2] |
| P1 | 11.1% [6.9, 18.2] | 18.5% [13.5, 24.8] | 26.0% [15.4, 37.2] |
| P5 | 7.5% [4.9, 10.5] | 9.4% [6.7, 14.2] | 15.4% [11.4, 22.0] |
| P3 | 11.0% [6.6, 17.4] | 14.7% [9.8, 20.5] | 21.9% [14.5, 31.5] |

Spec configuration (hyb, v21): P0 FRR 5.3% [3.7, 7.5] pooled, 7.9% [5.3, 11.0] macro, p90 user 25.4% [12.9, 33.3]; FAR 11.7% [8.9, 15.4]; FRR @FAR 10% 6.8% [4.3, 11.2].

**Interpretation.**
- At equal FAR, per-user thresholds from one week (P1, P3) cost about 1.7× the FRR of a global threshold. Shrinkage (P5) is close to P0 (CIs overlap) and gives no benefit.
- Errors are concentrated: Gini 0.73, and the p90 user has about 3–4× the pooled FRR.
- Round 1 found that per-user high error is mostly a state, not a trait (calibration-week FRR barely predicts later FRR; Spearman 0.04–0.39 on 28–40 users). That is consistent with this, but was not re-tested on the larger fold.

### 6.2 Policy (normative)

- **T1. Global operating point.** One threshold `τ_g` per model version, set on users **disjoint** from those it is applied to (our own consented population, D3), so that 5% of genuine K-blocks exceed it. It ships with the model, signed (`policy_ver`).
- **T2. No per-user thresholds in v2.** Matched-FAR evidence is against them (§6.1). They may be reconsidered only with ≥ 4 weeks of supervised calibration, and a measured matched-FAR benefit with a CI excluding zero.
- **T3. Abstain band.** `uncertain` is the abstain state (§6.3).
- **T4. Trust model for `high`** (§6.4). A single bad block MUST NOT produce `high`.

### 6.3 Band semantics (per assertion, i.e. per K = 4 windows)

| Band | Condition | Meaning for RP | Genuine blocks (pooled, spec config) | Zero-effort impostor blocks |
|---|---|---|---|---|
| `ok` | Block score ≤ τ_g and no trust alarm | No action | ≈ 94.7% (1 − FRR 5.3% [3.7, 7.5]) | 11.7% [8.9, 15.4] get `ok` |
| `uncertain` | Block score > τ_g, no trust alarm | MAY require step-up for **sensitive operations only** | ≈ 5.3% | Most of the rest, until the trust alarm |
| `high` | Trust alarm in this period, or `SIGNAL_LOST` (§9.6) | Step-up (WebAuthn) now | §6.5 | §6.5 |

CAEP mapping: `ok` → LOW, `uncertain` → MEDIUM, `high` → HIGH (openid-caep §3.8).

### 6.4 Trust model (after Mondal & Bours, mondal2015ins / bours2015perf)

Per window i with score `s_i`:

```
trust ← min(100, trust + clip(a·(τ_w − s_i), −P, +R))
alarm ⇔ trust < 50  → band=high
```

- `τ_w` is the q90 of genuine window scores of disjoint calibration users. Defaults: `a = 40`, `P = 40`, `R = 5`.
- Trust is reset to 100 at every strong authentication, at OS unlock, at the first window of each day, and after an alarm.
- Trust is never persisted beyond the session.

### 6.5 Measured trust-model operating points (default parameters, reset per day)

| Config | Genuine alarms / 60 windows: pooled; macro; p90 user | Impostor alarm within 5 / 10 / 30 windows |
|---|---|---|
| **hyb v21 (spec)** | **0.64 [0.41, 0.93]; 0.93 [0.49, 1.54]; 2.46 [1.09, 3.46]** | **81.6% [76.9, 86.2] / 88.0% [84.1, 91.7] / 93.0% [89.6, 95.7]** |
| hyb all | 0.44 [0.28, 0.66]; 0.70 [0.32, 1.23]; 1.74 [0.81, 2.44] | 77.3% [72.0, 82.1] / 85.2% [81.1, 89.1] / 92.1% [88.8, 95.2] |
| t60 all | 0.49 [0.32, 0.73]; 0.84 [0.43, 1.36]; 1.90 [1.02, 3.70] | 78.1% [73.8, 82.7] / 86.2% / 92.2% |

What this means for the spec configuration:
- A hyb window is ≤ 60 s of active typing, so 60 windows is at most about one active hour.
- The **mean user** sees roughly 0.9 ZTBE step-ups per active hour (macro); the **p90 user** sees about 2.5.
- A zero-effort different-device walk-up impostor is flagged within 5 windows (≤ 5 min of active typing) in about 4 of 5 runs, and about 7% are not flagged within 30.
- Impostor runs start at trust = 100, and "within 30" is right-censored.

Rules:
- **T5.** The RP SHOULD rate-limit ZTBE-caused step-ups to ≤ 2 per hour per user. Beyond that it SHOULD fall back to the `uncertain` treatment.
- **T6.** Deployments MAY choose slower or faster trust parameters. The trade-off MUST be stated in the DPIA. Round-1 sensitivity rows (single split, same-user calibration) are in `notes/experiments-v2.md`.

### 6.6 Persistent high-error users

If a user's 14-day rolling ZTBE step-up rate exceeds 3 per day of active use:
1. offer re-enrolment;
2. if the rate is still over the limit 14 days later, **disable ZTBE for that user** (no penalty under D1; the RP sees `status=disabled`).

The thresholds are proposals, untested.

## 7. Template sealing

The template (21 μ + 21 σ as float32 per keyboard class, plus metadata; < 1 KB per class) is sealed at rest. It is decrypted only into locked memory (memguard) for scoring.

| Platform | Mechanism | Go library (GitHub, 2026-10-21) | `key_protection` |
|---|---|---|---|
| Linux / Windows with TPM 2.0 | AES-256-GCM template key sealed to a TPM storage key. Assertion key: TPM-resident **P-256**, certified by the AK | google/go-tpm v0.9.8, go-tpm-tools v0.4.11, go-attestation v0.6.4 (Apache-2.0). The go-tpm README calls the `tpm2` TPMDirect API a "prototype" | `hw_attested` (AK chain verified) or `hw_unattested` |
| macOS (Apple silicon, T2) | Secure Enclave **P-256** key; template key wrapped to it or kept in the Keychain with SE access control | facebookincubator/sks ("stable beta", Apache-2.0); Keychain via cgo | `hw_unattested`. Third-party SE key attestation on macOS is UNVERIFIED |
| Fallback | OS keyring holds the AES key; **Ed25519** assertion key in software | zalando/go-keyring v0.2.8 (MIT) | `software` |

Rules:
- **S1.** The template key and the assertion key are separate. Neither is exportable on the hardware path.
- **S2.** TPM unseal-and-sign latency is **not yet measured** (M2-T2). Software: AES-GCM seal+open 1.5 µs; Ed25519 sign 19.6 µs; P-256 sign 31.3 µs.
- **S3.** `key_protection` is self-reported unless `hw_attested`. RPs MUST treat `hw_unattested` and `software` as advisory (D2).

## 8. Adaptation (D8)

Evidence:
- **Unsupervised full guard stack** (gate, anchor, velocity, sanitiser): no FRR benefit (week-8 FRR 11.0% vs 10.9% static). It is broken by a jittered boundary-walk attacker: 31.6% takeover at 28 days vs a 5.3% no-attack baseline (`adapt_adaptive_n200.txt`, 225 pairs).
- **Supervised adaptation** (proxy: the first S windows of each day; t60; 86 users; `adapt_supervised_t60.txt`):

| Updates per day | Paired Δ pooled window FRR, weeks 6–8, vs static |
|---|---|
| S = 2 | +0.2 pp [−1.2, +1.7] |
| S = 5 | +0.5 pp [−0.8, +1.8] |
| S = 10 | +1.3 pp [−0.3, +3.1] |

Static FRR at weeks 6–8 is 5.0%. hyb gives the same picture (`adapt_supervised_hyb.txt`). Static FRR shows no drift over 8 weeks on Tappy.

Policy:
- **U0.** **Adaptation is off by default.** The template is static. It is replaced by re-enrolment (E4) after 180 days, on persistent high error, or on request. NIST 800-63B-4 requires time-limited adaptation; with no adaptation the template age limit plays that role.
- **U1. Supervised mode (experimental, MAY).** Only windows closed within 30 min after a successful WebAuthn ceremony, with block score ≤ τ_g, update μ by EWMA (η = 0.05). There is one anchor (the enrolment template), and an update is rejected if μ moves further than `r_anchor = 0.675·τ_v` from it. It is labelled experimental because the measured benefit is nil. Enable it only for a population with measured drift.
- **U2. Unsupervised mode is withdrawn** from v2. It MUST NOT be offered.

## 9. Agent, assertions, proofs and RP consumption

### 9.1 Device → verifier: `ZTBE-Assertion` (COSE_Sign1, RFC 9052; CBOR)

```
protected:   { 1 (alg): -9 (ESP256) | -19 (Ed25519), 4 (kid): device_key_id }
payload (CBOR map, integer keys):
  1  v       uint  schema version (=2)
  2  dev     bstr  SHA-256(device public key)[:16]
  3  seq     uint  strictly increasing per device
  4  nonce   bstr  current verifier epoch nonce (16 B, rotated every 10 min)
  5  t0, 6 t1 uint window span, Unix seconds
  7  nwin    uint  scored windows in this assertion (0 for a heartbeat)
  8  status  uint  0=active 1=enrolling 2=disabled 3=paused 4=locked 5=capture_lost
  9  band    uint  0=ok 1=uncertain 2=high (present only if status=active and scored)
  10 flags   uint  bit0 synthetic_suspect, bit1 (reserved), bit2 rollover_disabled,
                   bit3 unscored_assistive, bit4 remote_session, bit5 device_change, bit6 idle
  11 kp      uint  0=hw_attested 1=hw_unattested 2=software
  12 model, 13 policy  tstr  model_ver, policy_ver
  14 pgrant  bstr  SHA-256 of the verifier pause grant (present only if status=paused)
```

The full CDDL is in `docs/interfaces.md`.

**Algorithms (D9).** RFC 9864 deprecates the polymorphic COSE identifiers −7 (ES256) and −8 (EdDSA). The fully specified replacements are **ESP256 (−9)** and **Ed25519 (−19)**.
- ESP256 is the default: TPM 2.0 and the Secure Enclave both support P-256.
- Ed25519 is used for software keys.
- Verifiers MUST reject −7 and −8.
- veraison/go-cose (v1.3.0, MPL-2.0; last release 2024-09-27) supports neither −9 nor −19. Its issue #224 and PR #225 ("Add fully specified algorithms") were still open on 2026-10-21.
- ZTBE therefore implements COSE_Sign1 itself on fxamacker/cbor (MIT, v2.9.6): ≈ 200 lines, Sig_structure per RFC 9052 §4.4, deterministic encoding, tested against RFC 9052 examples re-signed with −9/−19. This also removes the MPL dependency.

Assertion rules:
- No score, features, keystroke counts or content are ever included (D6).
- Size is ≈ 120–200 B.

### 9.2 Enrolment binding

1. The user registers a WebAuthn credential with the RP or IdP (go-webauthn v0.18.2, BSD-3).
2. The agent service creates the assertion key (TPM, SE or software) and obtains an mTLS client certificate for it from the verifier (§9.4).
3. It obtains a WebAuthn assertion whose challenge = SHA-256(assertion public key ‖ attestation blob). This binds the device key to the user's strong authenticator and to the user's account at the verifier.
4. For TPM, the verifier checks the AK certification of the key (go-attestation).

### 9.3 Agent architecture and liveness (D-a)

- **Two processes.**
  - `ztbe-svc` is a system service (Windows LocalSystem service, macOS launchd daemon, Linux root systemd unit). It holds the keys, seals, scores, signs, sends heartbeats and talks to the network.
  - `ztbe-capture` is a per-session helper. It exists because Windows hooks and macOS event taps must run in the interactive session. It forwards zone events over local IPC.
  - The service authenticates the helper by OS peer credentials (named-pipe client token, XPC audit token, `SO_PEERCRED`) and code signature.
  - Standard users cannot stop the service.
- **Capture loss.** If the helper dies, its tap is disabled (macOS `tapDisabledByTimeout`), or the Input Monitoring permission is revoked, the service sends `status=capture_lost` at once.
- **Heartbeat.** While the OS session is unlocked, the service sends an assertion at least every `hb = 60 s`, even with no typing (`nwin=0`, flag `idle`).
- **Lock, sleep, logout.** The service sends `status=locked` on these OS notifications. Trust resets at unlock (§6.4).
- **Pause.** `status=paused` requires a **pause grant**. The verifier issues it only after a WebAuthn ceremony by the user. It is valid for ≤ 60 min, signed by the verifier, and referenced in `pgrant`. Without a valid grant the verifier treats `paused` as `capture_lost`.
- **Disable / consent withdrawal.** Through the user's account page, after WebAuthn, the same way consent was given (GDPR Art. 7(3)). The verifier then sends `status=disabled` for all of the user's devices.

### 9.4 Verifier ingestion (D-c)

- **Channel.** The device–verifier channel uses TLS 1.3 with client authentication by the device key (a verifier-issued certificate from enrolment; the TPM or SE key is used as a `crypto.Signer`). Connections without a registered client certificate are rejected at the TLS layer.
- **Checks.**
  1. Signature against the registered device key, and `kid` matching the mTLS identity.
  2. `seq` > last seen.
  3. `nonce` is the current or previous epoch.
  4. `t1 ≤ now + 30 s`.
  5. `pgrant` is valid if `status=paused`.
- **Failure handling.** A failed check → **drop, count, never change the band**. If more than 10 invalid assertions arrive from one authenticated device within 1 h, the verifier alerts the operator and sets the device's `integrity_suspect` state (CAEP MEDIUM, reason `ASSERTION_INVALID`). It does not set HIGH.

### 9.5 Session binding: RP-challenge-bound presence proofs (D-b, A3)

Push events (§9.7) tell an RP that risk changed. They do not prove that a *request* comes from the enrolled device. For that, conforming RPs use **pull proofs**:

1. On a sensitive operation, and at least every `proof_interval` (default 5 min) for sessions under ZTBE policy, the RP issues a random `chal` (≥ 16 B), bound server-side to the session.
2. The RP's client obtains a **`ZTBE-Proof`** from the local agent:
   - browsers: the ZTBE browser extension, via native messaging; the extension passes the requesting **origin** as seen by the browser;
   - native and API clients: local IPC with peer-credential checks.
3. The proof is a COSE_Sign1 by the device key, with the payload of §9.1 plus:
   - `15 aud` (RP origin or client_id);
   - `16 chal`;
   - `17 iat`.

   It carries the **current** status, band and flags.
4. The RP verifies the proof against the device key registered for this user (from the verifier's device registry API, `docs/interfaces.md`). It checks `aud`, `chal`, `iat ≤ 60 s` old, and that the device belongs to the session's user.
5. **No valid proof** (no agent, wrong device, wrong origin, timeout) → treat as HIGH (step-up). This is the A3 control. A thief on another machine cannot produce a proof. A phishing page in the victim's browser gets a proof with the wrong `aud`.

In addition, RPs SHOULD sender-constrain the session itself:
- browsers: DBSC (W3C Editor's Draft, 2026-09-08). Chrome 146 on Windows has shipped it (Google, 2026-04-09). macOS support is reported from Chrome 147 (secondary source; UNVERIFIED);
- OAuth clients: DPoP (RFC 9449) or mTLS certificate-bound tokens (RFC 8705).

Proofs bind the *ZTBE signal* to the device. Sender-constraining binds the *session credential* to a device. Both are needed for a clean A3 story, and neither is behavioural.

### 9.6 Silence and signal loss (D-a, A10)

- If no valid assertion arrives for `2·hb + 30 s = 150 s` and the last status was `active` (not `locked`, `paused` with a valid grant, or `disabled`), the verifier sets **`SIGNAL_LOST` → CAEP HIGH** for the device's sessions. The same applies to `status=capture_lost`.
- RPs MAY downgrade `SIGNAL_LOST` to MEDIUM for scopes they classify as non-sensitive. They MUST NOT for sensitive scopes.
- The genuine cost (crashes, network loss, sleep without notification) is unmeasured and is a pilot metric (`docs/pilot-protocol.md`).

### 9.7 Verifier → RP: OpenID SSF / CAEP

The verifier is an SSF **Transmitter** (openid-ssf, Final). Events are SETs (RFC 8417) delivered by push (RFC 8935) or poll (RFC 8936). Each change emits a CAEP **`risk-level-change`**:
- `current_level` ∈ {LOW, MEDIUM, HIGH};
- `previous_level`;
- `principal` = `DEVICE` (the verifier does not know RP session IDs; RPs map devices to sessions via verified proofs, `docs/interfaces.md` §3);
- `risk_reason` ∈ {`BEHAVIOUR_OK`, `BEHAVIOUR_DEVIATION`, `SYNTHETIC_INPUT_SUSPECT`, `UNSCORED_CHANGE`, `SIGNAL_LOST`, `ASSERTION_INVALID`}. "No signal" states (enrolling, disabled, unscored, remote, locked) are not risk events.

`sub_id` uses RFC 9493 formats (`iss_sub` or `opaque`). Only changes are sent. The mapping with example SETs is in `docs/interfaces.md`.

### 9.8 RP behaviour (normative for conforming RPs)

- **HIGH** → step-up. OAuth resource servers return `401` with `WWW-Authenticate: Bearer error="insufficient_user_authentication"` and `acr_values` / `max_age` (RFC 9470). The IdP runs a WebAuthn ceremony with user verification. A successful step-up resets trust (and opens a supervised period if U1 is enabled).
- A failed or abandoned step-up is handled by the RP's existing session policy. **ZTBE defines no lockout** (D1).
- **MEDIUM** → the RP MAY shorten session lifetime and MAY require step-up for designated sensitive operations. It MUST NOT terminate the session on MEDIUM alone.
- **LOW** → no action. LOW MUST NOT raise the session's assurance level.
- **No signal** (`enrolling`, `disabled`, `unscored_assistive`, `remote_session`) → the RP's normal non-ZTBE policy applies. It MUST NOT be treated as suspect.
- Bands MUST NOT be stored for longer than 30 days, and per-person band reports MUST NOT be exposed (D6).

## 10. Privacy, GDPR and the EU AI Act

This is the research assistant's reading of the sources, not legal advice. D6 requires a legal opinion before any workforce use. The full DPIA outline is in `docs/dpia-outline.md`, and consent and notice texts are in `docs/consent-templates.md`.

- **Biometric data and Art. 9.**
  - GDPR Art. 4(14) covers "behavioural characteristics" processed by "specific technical processing" that "allow or confirm the unique identification".
  - EDPB 3/2019 §5.1 (edpb2019video) sets three criteria, including the purpose of uniquely identifying. Recital 51, as quoted there, covers "identification or authentication".
  - Conservative reading: **Art. 9 applies** even though ZTBE is only a risk signal.
- **Lawful basis.**
  - Consumer and volunteer settings: Art. 9(2)(a) explicit consent, with a non-biometric alternative (§3.1).
  - Employment: consent is generally not freely given. EDPB Guidelines 05/2020 §3.1.1 para 21 (edpb2020consent) and WP29 Opinion 2/2017, pp. 6–7 (wp29opinion2017work), say that for most processing at work the lawful basis "cannot and should not be the consent of the employees".
  - WP29 2/2017 §5.4.1 also calls software that logs "keystrokes and mouse movements" **disproportionate**, and says a legitimate-interest basis is "very unlikely". ZTBE captures timing, not content. Whether that distinction suffices is a question for counsel; we do not assume it does.
  - Art. 9(2)(b) needs Member State law. Hence D6: no workforce deployment without a legal opinion.
- **Minimisation.**
  - raw events in memory only;
  - templates sealed on the device;
  - the server holds bands and change events only, for ≤ 30 days;
  - no score API;
  - research mode stores window vectors only (§3.3).
- **DPIA.** Required. At least these WP248 rev.01 criteria apply: sensitive data, systematic monitoring, innovative technology, and, at work, vulnerable data subjects (wp248dpia: "a processing meeting two criteria would require a DPIA" in most cases).
- **EU AI Act** (euaiact2024):
  - Annex III(1)(a) excludes biometric verification whose sole purpose is to confirm identity;
  - Annex III(4)(b) lists monitoring and evaluating the behaviour of persons in work relationships as high-risk, hence D6;
  - Art. 5(1)(f) prohibits emotion inference at work and in education.
- **NIST SP 800-63B-4** (for US RPs):
  - the biometric definition includes keystroke and mouse;
  - fraud indicators are not authentication factors;
  - biometric factors need FMR ≤ 1/10000 "for all demographic groups", and FNMR SHOULD be < 5%.

  ZTBE claims no AAL.
- **Fairness reporting** (D-d, review M10). Every evaluation and pilot MUST report FRR, FAR and alarm rate per subgroup: age band, self-reported motor or typing impairment, keyboard type (laptop vs external), primary typing language and layout, and handedness. Subgroups with < 10 users are reported as "insufficient n", not as a rate. Release gate (proposal): a subgroup whose genuine-alarm rate has a 95% CI entirely above 2× the overall point estimate blocks the release.

## 11. Claims ZTBE v2 makes, and does not make

Makes, with zero-effort, open-data, different-device evidence:
1. A continuous signal whose K-block FRR is 5.3% [3.7, 7.5] (pooled; macro 7.9%) at an impostor-block acceptance of 11.7% [8.9, 15.4], on cross-day free text. This is from Tappy only, 81 evaluated users, with user-fold calibration.
2. Alarm on a zero-effort walk-up impostor within 5 windows (≤ 5 min of active typing) in 81.6% [76.9, 86.2] of runs. The genuine cost is 0.64 [0.41, 0.93] alarms per 60 windows pooled, 0.93 macro, 2.46 at the p90 user.
3. No behavioural data at the server.
4. Signed, replay-protected assertions, and RP-challenge-bound presence proofs.

Key limitations:
- **L1. Device confound (the main one).**
  - Tappy impostors typed on their own computers; the walk-up attacker (A4) types on the victim's.
  - Bound attempted: impostor blocks from attackers whose **timer quantum equals** the target's are accepted *less* often than the rest (hyb: 9.6% [6.2, 13.4] vs 12.2% [8.6, 16.2]; same/different ratio 0.59–0.90 across window types).
  - Restricting to the 3.906 ms quantum users only gives P0 FAR 9.5–12.8%.
  - So the **timer quantum** does not drive separability, but keyboard switch feel, layout, OS key repeat and posture remain unbounded.
  - **The same-device impostor rate is unknown** and is the go/no-go experiment (`docs/pilot-protocol.md`).
- **L2. Small n.** 63–82 users per configuration; one dataset of mostly older adults, about a third with Parkinson's disease (Tappy).
- **L3. Zero-effort only.** The attacks in §2.1 are not evaluated.
- **L4. Window correlation.** Block FAR does not correct for within-session correlation (§4).

Does **not** make:
- an authentication factor or AAL claim. FRR@FAR1% is far above NIST/FIDO bars;
- resistance to trained mimicry, snoop-forge-replay or on-device malware;
- template irreversibility as a cryptographic property (it is device sealing);
- fairness across age, disability or keyboard type (not evaluated; §10 reporting plan).

## 12. Evaluation protocol and metrics

Follows eberz2017 and ISO/IEC 19795-1 terminology (iso19795-1; clauses UNVERIFIED). Presentation attacks follow ISO/IEC 30107-3.

- **Splits.**
  - Chronological; enrolment precedes test by ≥ 7 days.
  - τ_g, τ_w and priors come from **disjoint users** (k-fold over users).
  - Report intra-session, cross-day and ≥ 4-week results separately.
  - **Impostors on the target's device** are the primary condition; different-device impostors are secondary.
- **Metrics** (95% bootstrap CIs over users; `eval2.py` is the reference harness):
  - per K-block: FRR and FAR at the shipped τ_g; FRR at matched FAR 10% and 5%; EER only as a summary;
  - pooled **and** macro;
  - per-user mean, p90 and Gini;
  - continuous: genuine alarms per 60 windows (pooled, macro, p90); impostor alarm within 5/10/30 windows;
  - operations: step-up rate per active hour; `SIGNAL_LOST` rate per day; FTE (E1 not met in 14 days); FTA;
  - subgroups (§10);
  - attacks: zero-effort (same device), population-statistics forgery, snoop-forge-replay with 100/200/1000 keys, synthetic injection. For each, IAPAR; APCER/BPCER for the synthetic detector;
  - cost: CPU per window, memory, assertion size, TPM unseal and sign latency.
- **Sample size.** With the upper bootstrap ρ (ρ_FRR = 0.36, ρ_FAR = 0.30), FRR 5% ± 2 pp needs 164–177 users and FAR 10% ± 3 pp needs 119–131 (`results/power.txt`). The 10–20 person pilot is therefore a **go/no-go feasibility test**, not an estimate.
- **Reporting.** N of users, windows per user, seeds, dataset licences. Never report a single best split.

## 13. Architecture, data flow and budgets (from PROPOSAL)

```
 ┌───────────── device ──────────────────────────────┐        ┌──────── ztbe-verifier ─────────┐     ┌──── RP / IdP ────┐
 │ ztbe-capture (per session)  ─IPC─►  ztbe-svc       │  mTLS  │ verify sig/seq/nonce, registry │ SSF │ CAEP receiver    │
 │ key→zone, provenance class         window→score→   ├───────►│ silence timer → SIGNAL_LOST    ├────►│ step-up (RFC 9470│
 │                                    trust→band→sign │        │ pause grants (after WebAuthn)  │     │ + WebAuthn)      │
 │ browser ext. / app ─IPC─► proof(aud, chal) ────────┼────────┼────────────────────────────────┼────►│ pull proof check │
 └────────────────────────────────────────────────────┘        └────────────────────────────────┘     └──────────────────┘
```

| Item | Where | Size / cost | Source |
|---|---|---|---|
| Sealed template (21 μ, 21 σ float32 per keyboard class, metadata) | device | < 1 KB per class (*inferred* from 42×4 B + overhead) | — |
| Population prior (μ, σ, within-var for 21 features) | device, shipped | < 1 KB (*inferred*) | — |
| Raw events | RAM, current window only | ≈ 200 × 24 B (*inferred*) | — |
| Device record | server | < 1 KB (*inferred*) | — |
| Heartbeat + assertion traffic | network | ≈ 1 per 60 s per unlocked device, ≈ 200 B each | §9.1 |
| Score one window | device | 0.30 µs (36-D, measured; 21-D is smaller) | go-he |
| Sign | device | Ed25519 19.6 µs; P-256 31.3 µs (software); TPM not measured | measured |
| Verify | server | Ed25519 44 µs; P-256 68 µs | measured |
| Server load | server | 10k unlocked devices ≈ 170 verifications/s with 60 s heartbeats (*inferred*: 10,000/60), about 1 core-second/s at P-256 | — |

## 14. Go MVP layout

```
cmd/ztbe-svc/          device service: seal, score, trust, sign, heartbeat, mTLS client
cmd/ztbe-capture/      per-session capture helper (Windows LL hook + Raw Input; macOS CGEventTap; Linux evdev via svc)
cmd/ztbe-verifier/     ingestion, device registry, silence timer, pause grants, SSF transmitter
cmd/ztbe-eval/         offline evaluator over the same feature code (cross-checks experiments/opendata)
internal/capture/      provenance classes (§3.1), keyboard class (§3.2), scancode→zone
internal/features/     the 21 window features, fixed arrays
internal/model/        prior, template, scaled Manhattan, K-fusion, trust model
internal/seal/         TPM (go-tpm), SE (sks), keyring fallback; memguard buffers
internal/cose/         in-house COSE_Sign1 (ESP256, Ed25519) on fxamacker/cbor
internal/wire/         CDDL-defined assertion/proof structs, deterministic CBOR
internal/ssf/          SET construction (RFC 8417), push/poll delivery
internal/policy/       verifier policy, rate limits
```

Licences: go-tpm family, memguard and sks are Apache-2.0; go-webauthn is BSD-3; go-keyring and fxamacker/cbor are MIT. go-cose (MPL-2.0) is no longer needed. Milestones are in PLAN.md.

## Appendix A. Parameter table

| Parameter | Default | Source |
|---|---|---|
| Window | 60 s active or 200 keys, whichever first; idle > 5 s removed; ≥ 40 keys | §4, `extract_tappy_v2.py` |
| Features | 21 (§3); rollover only if timer ≤ 4 ms | §3 |
| K | 4 windows per block | §4 |
| τ_g | 5% of genuine blocks of disjoint users flagged | §6.2 T1 |
| Trust | τ_w = q90 (disjoint), a = 40, P = 40, R = 5, alarm < 50; reset per day, at unlock and at strong auth | §6.4 |
| Step-up rate limit | ≤ 2/h per user | T5 (proposal) |
| Persistent-error rule | > 3/day over 14 days → re-enrol → disable | §6.6 (proposal) |
| Enrolment | ≥ 20 scored windows and ≥ 7 calendar days, supervised | §5 E1 |
| Adaptation | off; template age ≤ 180 days | §8, D8 |
| Heartbeat `hb` | 60 s while unlocked | §9.3 |
| Silence → SIGNAL_LOST | 150 s | §9.6 |
| Pause grant | ≤ 60 min, after WebAuthn | §9.3 |
| `proof_interval` | 5 min, plus every sensitive operation; proof age ≤ 60 s | §9.5 |
| Epoch nonce | 10 min | §9.1 |
| Invalid-assertion alert | > 10 per device per hour | §9.4 |
| COSE alg | −9 (hardware), −19 (software) | §9.1, D9 |
| Retention | ≤ 30 days of bands | D6 |
