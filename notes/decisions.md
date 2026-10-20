# Decision log

Format: ID, date, status, decision, rationale (with evidence), what would change it.

Status values:
- **decided by Hossein**
- **decided by research assistant**: Hossein delegated decisions 2–7 on 2026-10-21. Each can be reopened.

## D1. Role of ZTBE: decided by Hossein, 2026-10-21

**Decision.** ZTBE is a **continuous risk signal and step-up trigger**. It is **not** an authentication factor. It never grants access on its own and never locks a user out on its own. Its only actions are "keep session", "request step-up" and, per relying-party policy, "end session after a failed or absent step-up".

**Rationale.**
- Per-window FRR@FAR1% is 20–60%, and the guessing entropy is about 1–4 bits (`notes/experiments-v2.md`).
- NIST SP 800-63B-4 requires FMR ≤ 1/10000 for biometric factors and states that fraud indicators do not substitute for an authentication factor (nist80063b4).

**What would change it.** Nothing realistic. That would need FMR ≤ 10⁻⁴ at FNMR ≤ 5% on independent cross-session data.

## D2. Trust anchor for the template and assertion keys: decided by research assistant, 2026-10-21

**Decision.**
- Use hardware-backed keys **where available**:
  - TPM 2.0 on Windows and Linux;
  - Secure Enclave on macOS;
  - Android Keystore with StrongBox/TEE on Android.
- **Allow a software fallback** (OS keyring, or a file key protected by the OS user account).
- Every assertion carries `key_protection ∈ {hw_attested, hw_unattested, software}`. Relying-party policy decides how much weight to give each.

**Rationale.**
- ZTBE is only a risk signal (D1). Excluding devices without a TPM would lose coverage without gaining much security.
- On-device malware is out of scope in either case.
- Labelling the protection level keeps the claims honest.

**What would change it.** A deployment where ZTBE signals drive automated high-impact actions, such as payment approval. Then require `hw_attested`.

## D3. Population priors: decided by research assistant, 2026-10-21

**Decision.**
- **No model artefacts derived from Aalto (non-commercial) or Tappy (contains PD subjects, see D7) ship in any product build.**
- Shipped priors (z-score μ/σ, within-user variance, quantile edges, and any LDA or embedding) come only from **ZTBE's own consented collection** (PLAN "Data collection").
- Until that data exists, the MVP runs with **self-normalised templates**: per-user μ/σ with a shrinkage floor set from the user's own enrolment variance. Open data is used only to measure, never to ship.

**Rationale.**
- Aalto's licence is research and non-commercial only (dhakal2018 page).
- The experiments show priors must be in-domain anyway. With Aalto priors on Tappy, the binary variants collapse to EER 24.7% (experiments-v2 §3).

**What would change it.** A commercial licence from Aalto, or another commercially usable population set of at least about 1000 users.

## D4. Adaptation: decided by research assistant, 2026-10-21 — SUPERSEDED by D8 (round 2)

> Superseded. The "full stack 9% = baseline" result held only against a non-adaptive attacker. A jittered attacker reaches 31.6% takeover at 28 days (review round 1, M3), and the stack gives no FRR benefit. See D8. The original text is kept below for the record.

**Decision.**
- **Supervised adaptation only, by default.** The template updates only from windows observed within 30 min after a successful strong authentication (login or step-up).
- Unsupervised self-update is **off**. It can be enabled per deployment, and then only with the full guard stack: gate, anchor, velocity limit, and sanitiser with rollback + freeze.
- Re-enrol after **180 days** without a supervised checkpoint.

**Rationale.**
- In the Tappy simulation, gating alone gave 83% attacker takeover. With the full guard stack takeover was 9%, equal to the no-attack baseline.
- The FRR gain from unsupervised updates was small: week-8 FRR fell from 10.9% to 7.4%, and only with ungated updates.
- NIST 800-63B-4 requires a time limit on adaptation.

**What would change it.**
- Clarkson II, or our own data, showing much larger long-term drift than Tappy, meaning FRR growth over 8 weeks well above 5 percentage points.
- Very infrequent strong authentications in the target deployment.

## D5. Server-side encrypted matching (HE / OPRF): decided by research assistant, 2026-10-21

**Decision.** **Out of scope for v2.** No server-side behavioural matching in any form. The lattigo and circl benchmarks stay in `experiments/go-he` as reference only.

**Rationale.**
- O7 (on-device) already removes the A1, A2 and A3 exposure.
- HE adds a decryptor service and about 393 KB of upload per probe, and it does not solve the oracle problem (pagnin2014, li2021ckks).
- It brings no accuracy gain.

**What would change it.** A hard requirement for roaming users on untrusted or shared devices where no device key can be provisioned.

## D6. Workforce and EU AI Act: decided by research assistant, 2026-10-21

**Decision.**
1. Pilots run only with **opt-in volunteers** who give explicit consent.
2. ZTBE is not offered for employee monitoring.
3. The product is built so its outputs **cannot serve as performance or behaviour evaluation**:
   - no per-user score history leaves the device;
   - assertions carry only a 3-level band;
   - server-side retention is at most 30 days;
   - there is no export or reporting API per individual;
   - purpose limitation is written into the relying-party terms.
4. A legal opinion on AI Act Annex III(4)(b) and GDPR Art. 9/88 is required **before any workforce deployment**. Until then, assume such a deployment *could* be high-risk.

**Rationale.**
- Annex III(1)(a) excludes pure verification, but Annex III(4)(b) covers AI used "to monitor and evaluate the performance and behaviour of persons" at work (euaiact2024, text read via a mirror).
- Technical minimisation lowers the risk regardless of the legal outcome.

**What would change it.** A legal opinion, or Commission guidelines on Art. 6 / Annex III, that classifies continuous security-only verification as outside III(4)(b).

## D7. Tappy (PD subjects): decided by research assistant, 2026-10-21

**Decision.**
- Use Tappy only for **research measurements** (cross-day drift, adaptation, poisoning), with the ODC-By attribution.
- Never use it for shipped models or thresholds.
- Never infer or report health status.
- PD/control labels are not used in any experiment.

**Rationale.**
- The data concerns health. Typing models can encode motor impairment (adams2017tappy shows PD is detectable from typing).
- Shipping such models would risk incidental health inference.

**What would change it.** Nothing planned.

## Implications recorded in `spec/ZTBE-spec-v2-draft.md` (v2.1)

- D1 → spec §1 (scope and non-goals), §9 (relying-party consumption).
- D2 → spec §7 (sealing tiers).
- D3 → spec §4 (priors).
- D4 → superseded by D8.
- D5 → spec non-goals.
- D6 → spec §10 (privacy).
- D7 → spec §1 non-goals and §12 (evaluation data policy).
- D8 → spec §8, A8, App. A.
- D9 → spec §9.1, §14.
- D10 → spec §2 (A3, A9, A10), §9.3–§9.6.
- D11 → spec §3–§5, App. A.
- D12 → spec §1, §9.3, §14; `notes/collector-tradeoffs.md`.
- D13 → spec §3.1–§3.3, §10.
- D14 → PROPOSAL.md, notes/archive/.
- D15 → PLAN.md, `docs/pilot-protocol.md`.

---

# Round 2 decisions (2026-10-21, Hossein asleep; delegated "choose sensible options")

## D8. Adaptation off by default; unsupervised mode withdrawn: decided by research assistant, 2026-10-21

**Decision.**
- v2 ships a **static template**. It is replaced by re-enrolment after 180 days, on persistent high error (spec §6.6), or on request.
- **Supervised** adaptation (updates only within 30 min after WebAuthn) stays as an **experimental** option, off by default.
- **Unsupervised** adaptation is **withdrawn**. It is not offered at all.

**Rationale.**
- The unsupervised full guard stack is broken by an adaptive (jittered) attacker: 31.6% takeover at 28 days vs a 5.3% baseline (`adapt_adaptive_n200.txt`). Its FRR benefit is nil (11.0% vs 10.9%).
- Supervised updates show no FRR benefit either. The paired Δ vs static at weeks 6–8 is +0.2 pp [−1.2, +1.7] at 2 updates/day and +1.3 pp [−0.3, +3.1] at 10/day (`adapt_supervised_t60.txt`, 86 users).
- Static FRR does not drift over 8 weeks on Tappy (4.8% → 4.8% pooled).
- No adaptation means no A8 surface, and simpler code.

**What would change it.** Own pilot data showing static FRR growth of ≥ 3 pp over 8 weeks, together with a supervised-mode reduction whose CI excludes zero.

## D9. COSE algorithms and library: decided by research assistant, 2026-10-21

**Decision.**
- Assertions and proofs use **ESP256 (−9)** for hardware keys and **Ed25519 (−19)** for software keys. Verifiers reject −7 and −8.
- COSE_Sign1 is implemented in-house on fxamacker/cbor (MIT). go-cose is dropped.

**Rationale.**
- RFC 9864 (Proposed Standard, Oct 2025) deprecates the polymorphic −7/−8.
- TPM 2.0 and the Secure Enclave both support P-256; Ed25519 is not available in either.
- veraison/go-cose (MPL-2.0, last release v1.3.0 of 2024-09-27) has no −9/−19. Issue #224 and PR #225 were open as of 2026-10-21.
- COSE_Sign1 with one signer is small (Sig_structure + deterministic CBOR), and dropping go-cose removes the MPL dependency and a maintenance risk.

**What would change it.** go-cose releasing −9/−19 support with an active release cadence. Then switch to it and keep our test vectors.

## D10. Agent integrity and session binding: decided by research assistant, 2026-10-21

**Decision.**
1. Split the agent into a **system service** (keys, scoring, signing, network) and a **per-session capture helper**.
2. Send a **heartbeat** every 60 s while unlocked. Silence for 150 s, or `capture_lost`, maps to **HIGH** (`SIGNAL_LOST`) for the device's sessions. RPs may downgrade it to MEDIUM for non-sensitive scopes only.
3. **Pause** requires a verifier-issued grant obtained with WebAuthn (≤ 60 min).
4. The device–verifier channel is **mTLS with the device key**. Invalid assertions are **dropped and counted**, never escalated. Repeated invalid assertions → operator alert and MEDIUM.
5. **A3 control**: the RP issues a challenge, and the local agent returns an origin- and challenge-bound COSE proof. No proof → step-up. RPs SHOULD also sender-constrain sessions (DBSC for browsers; DPoP RFC 9449 or mTLS RFC 8705 for API clients).

**Rationale.** These close review holes D-a, D-b and D-c:
- the walk-up attacker could pause or kill the agent and only ever reach MEDIUM;
- a stolen cookie coexisted with the victim device's valid assertions;
- anyone could force step-ups with invalid assertions.

Pull proofs work with any RP and do not depend on DBSC adoption. DBSC (W3C ED 2026-09-08; Chrome 146 on Windows) and DPoP bind the credential itself.

Cost: genuine silence (crash, network loss, unannounced sleep) now causes step-ups. The rate is unknown and is a pilot metric.

**What would change it.**
- A pilot `SIGNAL_LOST` rate above about 1 per user per day. Then lengthen the silence timer or downgrade to MEDIUM by default.
- Native DBSC support for federated IdP sessions making pull proofs redundant for browsers.

## D11. Spec parameters confirmed by re-run: decided by research assistant, 2026-10-21

**Decision.**
- Keep the hybrid window (60 s active or 200 keys, idle > 5 s removed, ≥ 40 keys), K = 4, the 21-feature set and the global threshold (P0).
- Change enrolment E1 to **≥ 20 scored windows and ≥ 7 calendar days**.
- Make the feature-drop rule explicit: ratio > 1.0 cross-session, or Tappy self-prior ICC < 0.05.

**Rationale** (user-fold calibration, bootstrap CIs; `eval2_*`):
- The 21 features are non-inferior to the 34: FRR @FAR 10% 6.8% [4.3, 11.2] vs 6.6% [4.4, 9.6].
- P0 beats P1 and P3 at matched FAR (6.6% vs 11.1% and 11.0%). P5 is close (7.5%) and gives no benefit.
- Cold-start FAR is 44% at 1 window, 20% at 20 windows, and 11–12% with a full week, so a short enrolment is a security hole rather than an FRR problem.

**What would change it.** Pilot same-device data showing another window or feature set better at matched FAR, with non-overlapping CIs.

## D12. Collector: native agent, browser only as proof relay: decided by research assistant, 2026-10-21

**Decision.**
- v2 collects keystrokes with a **native agent**, in this order: Windows first (LL hook for provenance plus Raw Input for device identity), then macOS (CGEventTap with Input Monitoring), then Linux (evdev read by the root service, mapped to the active logind seat; X11/Wayland-independent).
- A browser extension exists only to relay RP challenges to the agent (spec §9.5).
- An in-page JavaScript collector is **deferred** to a possible v3 "RP-scoped" profile.

**Rationale** (`notes/collector-tradeoffs.md`):
- The A4 use case is the device, not a single site, and a page sees keystrokes only while focused.
- `isTrusted` cannot reveal OS-level injection.
- Browser timestamps are coarsened to ≥ 100 µs. That is adequate for timing but irrelevant to the other two points.
- The native path gives the OS injection flags, device identity and global coverage. The price is OS permissions and endpoint management, and a higher privacy burden, which D6 and the DPIA handle.

**What would change it.**
- A target deployment of consumer web RPs without endpoint management. Then a JS collector, accepting lower coverage and no provenance.
- The capture spike showing that macOS or Windows provenance is unusable.

## D13. Injected input, accessibility, research-mode minimisation: decided by research assistant, 2026-10-21

**Decision.**
- Classify input as physical, injected-allowlisted or injected-unknown.
  - Only physical input is scored.
  - Allowlisted assistive or automation input → **no signal**, never suspect, for users with an assistive profile (set in a supervised period). For other users, a switch to allowlisted input outside supervision → MEDIUM (`UNSCORED_CHANGE`). Otherwise a walk-up attacker could evade by using an on-screen keyboard.
  - Unknown injection → `synthetic_suspect` → MEDIUM (not HIGH).
- No scoring inside remote-desktop guests.
- Opt-out without a stated reason and without penalty.
- Per-keyboard-class templates; new keyboards are enrolled only in supervised periods.
- Research mode stores per-window feature vectors only, never per-event zone streams; the one exception is a separately consented copy-typing task on prescribed text.
- Per-subgroup fairness reporting is mandatory.

**Rationale.**
- The v2.0 rule ("any injected event → suspect") penalises on-screen keyboard, dictation and VDI users.
- Keystroke timing is a known content side channel (song2001ssh).
- NIST 800-63B-4 asks for biometric performance "for all demographic groups".

**What would change it.**
- Capture-spike evidence that assistive tools cannot be distinguished from attack tools on some OS. Then that OS gets "unscored" for all injected input.

## D14. One normative document: decided by research assistant, 2026-10-21

**Decision.**
- `spec/ZTBE-spec-v2-draft.md` (v2.1) is the only normative text.
- PROPOSAL.md becomes a short rationale pointing to spec sections.
- `notes/open-questions.md` (v1) moves to `notes/archive/` with a header.

**Rationale.** Review round 1 §1.2 listed 10 contradictions between PROPOSAL and the spec. Two specs drift.

**What would change it.** Nothing.

## D15. Go/no-go criterion for the same-device pilot: decided by research assistant, 2026-10-21

> **Decision rule SUPERSEDED by D21** (review round 2 H9: the stop rule almost never fired). The meanings of go and stop and the 1.5/h burden threshold are kept.

**Decision.** The pilot (`docs/pilot-protocol.md`) is a feasibility test with these pre-registered outcomes:
- **Stop** (abandon A4 as a claim) if the same-device zero-effort impostor alarm-within-10-windows rate has a 95% CI upper bound below 60%.
- **Go** if its lower bound is ≥ 70% **and** the genuine step-up rate (macro) is ≤ 1.5 per active hour.
- Otherwise: inconclusive; extend to the powered study (≈ 120–180 users).

**Rationale.**
- The open-data different-device figure is 88.0% [84.1, 91.7] within 10 windows. A same-device drop to < 60% would make A4 detection worse than a screen-lock timer.
- 1.5 step-ups per hour is about the round-1 p90-user burden. More than that for the mean user is not a usable product.
- The thresholds are judgement calls, recorded before data collection to avoid moving goalposts.

**What would change it.** Hossein's product judgement on acceptable burden.

**Addendum (2026-10-21, research assistant).** The rule's resolvable range at pilot size is in `experiments/opendata/results/pilot_ci.txt`. With 20 participants × 3 impostors × 3 segments, and an *assumed* intra-victim ρ of 0.1–0.3, "go" needs an observed rate ≥ 79–83% and "stop" needs ≤ 46–50%. The rule is unchanged. Rates in between are inconclusive by design.

## D16. Pilot design parameters: decided by research assistant, 2026-10-21

> **Partly SUPERSEDED by D21.** Size is now 16 + 16 in two stages; segments are 2 per 45-min session (was 3 per 30 min); a genuine same-task control session is added. The other items (zero-effort primary arm, notification-only, frozen parameters, storage, subgroup rule) stand.

**Decision** (`docs/pilot-protocol.md`):
- **Size and pairing:** N = 10–20 (target 16). Round robin with 3 impostors per victim and 3 ten-window segments per 30-minute session.
- **Primary arm:** zero-effort only; the mimicry arm is reported separately.
- **Burden measurement:** step-ups are shown as notifications only.
- **Frozen parameters:** all spec Appendix A values; no re-tuning on pilot data.
- **Data and subgroups:** window vectors only; ≤ 12 months retention; subgroups with < 10 users are reported as "insufficient n".

**Rationale.**
- Same-device impostors are the only way to measure L1.
- 3×3 maximises attempts per participant-hour while keeping sessions short.
- Notification-only avoids disrupting real work and still counts burden.
- Freezing parameters keeps D15 honest.

**What would change it.**
- An ethics board objecting to the study-account template copy. The fallback is a supervised handover in the victim's account.
- Pilot ρ much higher than 0.3. Then more victims are needed rather than more segments.

## D17. Round-2 stopping point: decided by research assistant, 2026-10-21

**Decision.** Stop desk research after round 2.

**Rationale.** The open questions that change the design all need new data:
- the same-device rate (L1);
- capture behaviour per OS (E2);
- the supervised-adaptation benefit (E3);
- legal proportionality at work (counsel).

Further literature or open-data runs only re-bound these (e.g. the timer-quantum bound on L1).

**What would change it.** A public dataset with multiple users per physical keyboard and device identifiers. That would let L1 be measured without a pilot.


---

# Review round 2 decisions (2026-10-21, after `notes/review-round-2.md`)

## D18. Pairwise identifiers and minimal proofs (H1): decided by research assistant, 2026-10-21

**Decision.**
- **Per-RP keys and IDs.** Each linked RP gets its own proof key and a pairwise device ID, `pdid = HMAC-SHA-256(k_verifier, rp_id ‖ dev)[:16]`. The global `dev` and the device key stay between the device and the verifier.
- **Linking.** Linking is user-initiated in the agent or extension UI, with explicit origin approval. The RP redeems a one-time code with its own `rp_sub`, which the verifier checks against the user (pairwise `sub` or an IdP ID token).
- **Extension.** It registers content scripts only for linked origins and exposes no web-accessible resources.
- **Proof contents.** Proofs carry only `sig` ∈ {low, medium, high, no_signal}, a coarse `age`, `kp`, `aud`, `chal` and `iat`. There is no `seq`, no flags and no version strings.
- **Assistive and remote state.** Both become `status=unscored` in assertions. The reason stays on the device, in the user-visible local log.
- **Registry and SSF.** The registry is scoped to the calling RP's own subjects (`/rp/v1/subjects/{rp_sub}/devices`). SSF `sub_id` uses the RP's `rp_sub` and that RP's `pdid`.

**Rationale.**
- Spec §1 promises no cross-service linking, and DPIA R8 relied on it. Round-2 proofs broke both: any page could get a global `kid` plus disability-adjacent flags.
- DBSC, which ZTBE cites, has the same goal of no stable device identifiers.
- The per-RP key cost is one extra TPM/SE key per linked RP. HMAC pairwise IDs are standard practice (cf. OIDC pairwise `sub`).

**What would change it.**
- A measured need for RPs to correlate one device across their own multiple origins. That would be handled by linking those origins under one `rp_id`, not by global IDs.
- Evidence that extension presence is fingerprintable anyway (PLAN E2). That would not undo D18, but it would need its own mitigation.

## D19. HIGH latches (H2): decided by research assistant, 2026-10-21

**Decision.**
- A trust alarm or `SIGNAL_LOST` puts the device and the verifier into a latched HIGH. The latch has two exits only:
  - (a) a WebAuthn assertion verified by the verifier (`/user/v1/stepup`, reason `STEP_UP_OK`);
  - (b) an OS lock followed by an unlock (`UNLOCK`).
- Scored `ok` blocks, resumed heartbeats and new days do not clear it.
- RPs MUST NOT clear a pending ZTBE step-up on a later LOW or MEDIUM.
- The state machine is spec §9.9.

**Rationale.** Without a latch, a walk-up attacker who keeps typing through one more period, or who restores the network after a block, can see HIGH replaced by LOW before the RP enforces it. "Only changes are sent" makes this order-dependent.

**Cost.** A genuine false alarm or a network blip costs exactly one step-up, or one lock/unlock. This is already counted in the alarm rates.

**What would change it.** Pilot evidence that latched `SIGNAL_LOST` from benign network loss dominates the burden. Then `SIGNAL_LOST` could latch only for sensitive scopes, while trust alarms stay latched.

## D20. Unscored periods go stale (H3): decided by research assistant, 2026-10-21

**Decision.**
- A period with no scored window does not refresh the band.
- After `T_stale` = 10 min of unlocked time since `max(last scored window, unlock, verified WebAuthn)`, the state becomes MEDIUM `NO_RECENT_SCORE`. This covers mouse-only use, fewer than 40 keys per window, and an unattended unlocked screen.
- Proofs carry a coarse `age`. For sensitive operations RPs SHOULD require `age ≤ 1`, i.e. the last score is at most 5 min old.
- The non-typing walk-up limit is stated in A4 and L5. Mouse scoring stays out of scope for v2.

**Rationale.**
- "Last band forever" would let a mouse-only attacker inherit the victim's LOW until the screen locks.
- MEDIUM, not HIGH, because the genuine user is often reading.
- MEDIUM only gates sensitive operations, so the burden stays bounded.
- The 10 min and 5 min values are proposals; the pilot measures the stale fraction and the age distribution.

**What would change it.** A pilot stale fraction high enough that MEDIUM events become noise; then lengthen `T_stale` and rely on `age` alone. Or adding mouse scoring, which would shrink unscored time.

## D21. Pilot decision rule redesigned (H9): decided by research assistant, 2026-10-21

**Decision** (`docs/pilot-protocol.md` §1).

**Design.** A two-stage feasibility pilot:
- **Stage 1:** 16 complete participants. Go if the conservative CI lower bound ≥ 70%, burden ≤ 1.5 and the task is valid. Stop if `p̂` < 60%. Otherwise run stage 2.
- **Stage 2:** 16 more participants, analysed cumulatively (N = 32). Go under the same condition. Stop if `p̂` < 70%. Otherwise inconclusive.
- **Sessions:** 3 impostors × 2 ten-window segments per victim, in 45-min sessions (60 min if the dry run requires).
- **Conservative CI:** the union of a victim-cluster bootstrap and Wilson on `n_eff` (ρ̂ floored at 0.1). The same CI is used in planning (`pilot_oc2.py`) and in the decision.
- **Burden:** the macro point estimate of step-ups per active-typing hour.
- **Genuine control:** a same-task control session, with a task-validity rule of at most +10 pp over the natural-use rate.
- **Dry run:** checks window yield first, against 59.5 s per window on Tappy.

**Operating characteristics** (simulated; ρ 0.1–0.3, impostor sd 0–0.8; `results/pilot_oc2.txt`):

| True alarm-within-10 | P(stop) | P(go) | Other |
|---|---|---|---|
| ≤ 0.60 | ≥ 0.97 | — | — |
| 0.65 | 0.84–0.89 | ≤ 0.01 | — |
| 0.75 | 0.10–0.22 | 0.18–0.24 | indifference zone |
| 0.80 | — | 0.48–0.72 | — |
| 0.85 | — | 0.83–0.97 | — |
| 0.88 | — | 0.94–1.00 | — |

- Wrong-direction errors are ≤ 0.05.
- Coverage of the conservative CI is 0.88–0.98.
- The round-2 rule had P(stop | 0.55) = 0.13–0.17.

**Rationale.**
- Hossein asked for a 10–20 person pilot, and stage 1 keeps that.
- Stage 2 runs only when needed. It is triggered in 5–94% of simulated pilots depending on the true rate, and in ≥ 61% when the true rate is 0.65–0.80.
- A futility rule on the point estimate is the only way to make "stop" reachable at this n.

Two alternatives were rejected:
- **Single stage with N = 20:** weaker, with P(go | 0.85) of only 0.60–0.84.
- **20 + 20:** marginally better, but 25% more participants.

**What would change it.** A dry-run yield below 20 windows per 60 min, which means S = 1: re-simulate and amend before recruitment. Or Hossein preferring a lower stop risk in the 0.75 zone, which means a stage-2 stop threshold of 0.65 at the cost of more inconclusive outcomes.

## D22. Should-fix bundle (H4–H8): decided by research assistant, 2026-10-21

**Decision.**
- **H4 request binding.** Any "A3 mitigated" claim requires sender-constrained sessions (DBSC, DPoP or mTLS). Periodic proofs alone protect only sensitive operations.
- **H5 assertion hygiene.**
  - `stale-seq`, `bad-nonce` and `future-time` are hygiene failures. They are logged and do not count toward `integrity_suspect`; only signature, `kid`, alg and format failures count.
  - The device refetches the epoch on reconnect, drops stale queued assertions, and persists `seq = max(last + 1, unix_ms·2^10)`.
  - The effective outcome of persistent failures (`SIGNAL_LOST`) is documented.
- **H6 COSE.** A 7-item implementation checklist in spec §9.1:
  - DER → raw r‖s;
  - verify over the received bytes;
  - alg ↔ key type;
  - strict decoding;
  - randomised-ECDSA test caveat;
  - negative fuzzing;
  - a key-use argument. TLS 1.3 CertificateVerify and the COSE Sig_structure are domain-separated by construction (RFC 8446 §4.4.3 prefix vs CBOR "Signature1"). The same algorithm is used for both, and proofs use separate per-RP keys.
- **H7.** Assistive-profile evasion, MEDIUM-not-HIGH for profile-less users, threshold gaming and the non-typing window are stated as limitation L5.
- **H8 paused.** Paused with a grant means `no_signal` in proofs, `age = 3` and no CAEP event. Expiry falls back to `active` with stale rules. Pausing while HIGH requires WebAuthn and so clears the latch legitimately.

**Rationale.** These are cheap text fixes that close the remaining reviewer findings without new research.

**What would change it.** Implementation experience (M2/M3), e.g. if clock-derived `seq` proves fragile on some platform.
