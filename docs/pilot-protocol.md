# Same-device feasibility pilot: protocol

Status: protocol v2, 2026-10-21 (research assistant). It implements D21, which replaces the D15/D16 decision rule after review round 2 H9, and spec §12. Governance documents: `docs/dpia-outline.md` and `docs/consent-templates.md` §1.

## 1. Question and outcomes

**Primary question.** When a different person types on the *victim's own device and keyboard* (attacker A4, zero-effort walk-up), how often does the shipped configuration raise an alarm within 10 windows?

This removes the open-data device confound (spec L1). Different-device Tappy gives 88.0% [84.1, 91.7]. The same-quantum subset bound does **not** indicate that the different-device figure is optimistic: impostors whose timer quantum matches the target's are accepted *less* often, not more (same/different FAR ratio 0.86 in the spec config, 0.79 with all features; 0.59–0.90 across runs; spec §11 L1). Timer quantum is only a weak device proxy, so this cannot rule out a same-device penalty either. That is why the pilot is needed.

**Framing (D21).** This is a **two-stage feasibility pilot with a decision gate**, not an estimation study. It answers "is same-device detection clearly good, clearly bad, or in between?". It cannot estimate FRR or FAR to ± 2 pp; that needs 164–177 / 119–131 users (spec §12).

**Primary statistic.** `p̂` = alarm-within-10 rate over complete impostor segments (§4), as the mean over victims of each victim's segment rate (victim-weighted).

**Interval (used for both planning and decision).** The **conservative 95% CI** is the union of:
- a percentile cluster bootstrap over victims (B = 10,000; seed reported);
- a Wilson interval on `n_eff = n / (1 + (m − 1) ρ̂)`, where ρ̂ is the one-way ANOVA intra-victim ICC, floored at 0.1.

The lower bound is the smaller of the two and the upper bound the larger. The same CI is simulated in `experiments/opendata/pilot_oc2.py`. `pilot_ci.py` (Wilson only, round 2) is superseded.

**Pre-registered rule (D21).**

| Stage | n (complete victims) | Go | Stop (futility) | Otherwise |
|---|---|---|---|---|
| 1 | 16 | CI lower ≥ 70% **and** burden ≤ 1.5 **and** task valid | `p̂` < 60% | run stage 2 |
| 2 (cumulative) | 32 (16 new, own round robin) | CI lower ≥ 70% **and** burden ≤ 1.5 **and** task valid | `p̂` < 70% | **inconclusive** → powered study, claim unvalidated |

- **Go** → build the powered study (PLAN Phase 3b).
- **Stop** → drop the A4 detection claim (D15 meaning unchanged).
- **Burden** (fixed statistic): the **point estimate** of the macro mean of per-participant genuine ZTBE step-ups per **active-typing hour** in natural use, weeks 3–4. Its bootstrap CI and the p90 participant are reported but not used in the rule. For reference, on Tappy the macro rate is 0.93 [0.49, 1.54] alarms per 60 windows, which is ≈ per active-typing hour (61 windows/h, spec §6.5). A burden over 1.5 blocks "go" (→ stage 2 or inconclusive) but never triggers "stop".
- **Task valid:** the genuine same-task control (§4) must not exceed the participant's own natural-use alarm-within-10 segment rate by more than 10 percentage points (point estimates, macro). Otherwise the result is labelled **task-confounded** and "go" is withheld (→ stage 2 or inconclusive). "Stop" still applies: a detector that fails on a semi-natural typing task has not been shown to work.

**Operating characteristics** (`results/pilot_oc2.txt`, design B; 2,000 simulated pilots per row).
- Assumptions, not data: beta-binomial victim clustering ρ ∈ {0.1, 0.2, 0.3}, crossed impostor effect sd ∈ {0, 0.8} (logit), 3 impostors × 2 segments per victim. Burden and task validity are assumed to pass. All segments are assumed complete. The simulation uses B = 1,000 bootstrap resamples, while the analysis uses 10,000.

| True alarm-within-10 | P(go) | P(stop) | P(inconclusive) | P(decided at stage 1) | CI coverage |
|---|---|---|---|---|---|
| 0.50 | 0.00 | 1.00 | 0.00 | 0.87–0.95 | 0.94–0.96 |
| 0.55 | 0.00 | 1.00 | 0.00 | 0.73–0.78 | 0.92–0.97 |
| 0.60 | 0.00 | 0.97–0.99 | 0.01–0.03 | 0.50–0.53 | 0.93–0.96 |
| 0.65 | 0.00–0.01 | 0.84–0.89 | 0.10–0.15 | 0.20–0.28 | 0.92–0.95 |
| 0.70 | 0.03–0.05 | 0.52–0.58 | 0.38–0.45 | 0.06–0.15 | 0.88–0.94 |
| 0.75 | 0.18–0.24 | 0.10–0.22 | 0.58–0.66 | 0.12–0.14 | 0.90–0.96 |
| 0.80 | 0.48–0.72 | 0.00–0.05 | 0.28–0.48 | 0.27–0.39 | 0.92–0.97 |
| 0.85 | 0.83–0.97 | 0.00 | 0.03–0.17 | 0.51–0.76 | 0.93–0.96 |
| 0.88 | 0.94–1.00 | 0.00 | 0.00–0.06 | 0.70–0.91 | 0.95–0.98 |

- **Reading.**
  - A clearly poor detector (≤ 65%) is stopped with probability ≥ 0.84.
  - A detector at the open-data level (≈ 85–88%) gets "go" with probability ≥ 0.83.
  - Wrong-direction errors are ≤ 0.05 at these points: go at ≤ 70% or stop at ≥ 80%.
  - 70–80% is the indifference zone, where any outcome is acceptable and inconclusive is common.
  - At 75%, P(stop) reaches 0.10–0.22. This is the price of a usable futility rule at n ≤ 32.
- **Coverage** of the conservative CI is 0.88–0.98. The minimum is at a true 0.70 with a crossed impostor effect: the CI models victim clustering only.
- **For comparison**, the round-2 rule (one stage, N = 16, bootstrap CI, stop on upper bound < 60%) had P(stop) of only 0.13–0.17 at a true 55%, and P(go) of 0.87–0.92 at a true 88% (`results/pilot_oc.txt`, review round 2). Variants are in `pilot_oc2.txt`:
  - single stage N = 20: P(stop | 0.55) 0.73–0.80;
  - two-stage 20 + 20: P(go | 0.85) 0.91–0.99.

**Secondary outcomes (descriptive, with CIs):**
- genuine same-task alarm-within-10 rate and the impostor − genuine contrast (cluster bootstrap);
- fraction of unlocked time in the stale state (`NO_RECENT_SCORE`, spec §9.9) and the distribution of proof `age`;
- latched-HIGH episodes per day and how each was cleared (step-up vs lock/unlock);
- same-device block FAR at τ_g;
- genuine alarms per 60 windows (pooled, macro, p90);
- step-ups per active hour;
- `SIGNAL_LOST` per day;
- FTE (E1 not met within 14 days);
- capture-spike metrics (§5);
- acceptability questionnaire.

## 2. Participants

- **Stage 1: 16 complete participants** (recruit ≈ 20 for attrition). **Stage 2 if needed:** 16 more, run as a separate round-robin cohort. Maximum 32 complete.
- Recruited openly, not through a line-management chain (D6). Flat payment, not tied to performance (tey2013).
- **Device mix:** at least 4 Windows, 4 macOS and 2 Linux (X11 or console; Wayland is excluded, see collector-tradeoffs). At least 3 participants use an external keyboard as their main keyboard.
- **Fairness subgroups (optional self-report, consent D):** age band (< 30, 30–49, ≥ 50), handedness, primary typing language, typing-related condition (yes / no / prefer not).
  - The pilot is **descriptive only** for subgroups. n is far too small for inference. As spec §10 requires, a subgroup with < 10 users is reported as "insufficient n" with counts only. The self-reported condition item is used only for this table: it is never linked to scores in any output and never inferred (D7).
- **Exclusions:** none on ability. Assistive-input users are welcome; their sessions are classified per spec §3.1 and reported separately.

## 3. Timeline

**Dry run (before stage 1; window-yield check, review H9).**
- Three research-team members do the §4 session task on their own devices. Only window counts are kept.
- The design assumes 2 complete 10-window segments per session, i.e. **20 scored windows**.
- A hyb window averages 59.5 s of active typing on Tappy (`results/window_duration.txt`). So 20 windows need ≈ 20 min of active typing, which is ≈ 44% of a 45-min session. The task's typing density is **UNVERIFIED**.
- Decision rule, fixed before recruitment:
  - if the median yield in 45 min is ≥ 20 scored windows, keep 45 min;
  - otherwise use 60 min;
  - if 60 min still yields < 20, use **1 segment per session**, re-run `pilot_oc2.py` with S = 1, and amend the pre-registration before stage 1.

**Per participant:**

| Week | Activity |
|---|---|
| 0 | Consent; install the research-mode build (M5); timer self-test; keyboard class registered |
| 1–2 | Natural use. Enrolment E1 (≥ 20 scored windows and ≥ 7 days, supervised after WebAuthn). The template is sealed at E1 |
| 3–4 | Natural use (genuine test). Product-mode scoring runs and states are logged; **no real step-ups**, shown as a notification only (to measure burden without disrupting work) |
| 3–4 | **3 impostor sessions** on other participants' devices, plus **1 genuine control session** on the participant's own device (§4), scheduled in counterbalanced order |
| 4 | Copy-typing task (consent C, optional); exit questionnaire; uninstall; deletion check |

## 4. Impostor sessions (same device)

- **Pairing.** Round robin: each participant acts as impostor on 3 other participants' devices and is the victim of 3 others. Pairs are assigned by a script with a fixed seed, balanced across OS where possible.
- **Setup.**
  - The impostor logs in to a **separate study OS account** on the victim's machine. That account has the victim's sealed template copied in by the research build. This is research mode only; product templates are not exportable (spec §7).
  - Alternative where account copying is impossible: the victim unlocks, then hands over in front of the experimenter. The session is the victim's own account with a study-only browser profile.
- **Task.** 45 minutes of semi-natural typing (60 min if the dry run requires):
  - 15 min free composition (prompts supplied, nothing personal);
  - 15 min email-style replies to supplied messages;
  - 15 min free choice from supplied tasks.
  - **Segments.** A segment is 10 consecutive *scored* windows. At each segment start the research build sets trust to 100 and clears the latch, simulating a fresh walk-up. A segment is an **alarm** if the trust model alarms within its 10 windows. The session ends after 2 complete segments or at the time limit.
  - An incomplete segment (< 10 scored windows) with an alarm counts as an alarm. One without an alarm is **excluded** and reported. The exclusion count is a pre-specified check: more than 20% excluded means the yield assumption failed.
- **Genuine control session (review H9).**
  - Each participant does the **same task** once on their own device and account, with the same segmentation.
  - Its alarm-within-10 rate is the genuine same-task rate. It separates detection from task effects (task-validity rule, §1).
- **Zero-effort only for the primary outcome.**
  - Optional mimicry arm (consent E plus a separate tick): the impostor watches 2 minutes of the victim's typing video **without** timing feedback.
  - This is reported separately and does not count toward the D21 rule.
- **Labels.** The experimenter logs start and end times. Genuine windows during that interval are excluded.

## 5. Capture-spike metrics (PLAN M1-T5/T6)

Recorded per device:
- timer resolution: QPC or `mach_absolute_time` or evdev, versus hook timestamps;
- percentage of events with provenance `injected-*`;
- assistive-tool behaviour (on-screen keyboard, dictation, IME) per OS;
- hook timeouts (`tapDisabledByTimeout`) and LL-hook removals;
- `capture_lost` events;
- RDP and remote sessions detected;
- CPU and RSS per hour;
- fraction of unlocked time with no scored window for > 10 min (stale), and the time-since-last-scored-window distribution (checks `T_stale` and `max_score_age`, spec §9.9);
- invalid assertions split into hygiene and integrity failures (spec §9.4).

These numbers replace the UNVERIFIED entries in spec §3.1 and `notes/collector-tradeoffs.md`.

## 6. Data and storage

- Research mode (spec §3.3): **window feature vectors only**, with timestamps, band and provenance class.
  - The per-event zone timing stream is stored **only** for the copy task under consent C.
  - No characters, text, app names or URLs.
- Pseudonymous participant code. The key file is held separately by the PI.
- Encrypted at rest; access logged.
- Deleted ≤ 12 months after the study ends.
- No public release without separate consent.

## 7. Analysis

- **Primary.** `p̂` and the conservative CI (§1) over complete impostor segments, applied to the D21 rule at stage 1 and, if reached, stage 2. Report both component intervals, ρ̂, and the number of excluded segments.
  - Also report, as sensitivity analyses that are not used in the rule, a two-way (victim × impostor) bootstrap and the segment-weighted rate.
- **Burden.** The rule statistic is fixed in §1: the macro point estimate of step-ups per active-typing hour. Also report its bootstrap CI, the pooled rate and the p90 participant. Alarms per 60 windows use the `eval2.py` definitions.
- **Genuine control.** Same-task genuine alarm-within-10 (macro), the natural-use segment rate, and the impostor − genuine contrast with a cluster-bootstrap CI.
- **Comparison.** Run the same pipeline on Tappy different-device pairs and state the same-device − different-device difference. This difference is the confound estimate.
- **Pre-specified secondary checks.**
  - Effect of keyboard class (laptop vs external) on genuine FRR.
  - `SIGNAL_LOST`, latched-HIGH episodes and the stale fraction.
  - Whether any assistive-input session produced HIGH. It must not; any HIGH there is a bug.
- **No re-tuning on pilot data.** τ_g, τ_w, a, P, R and `T_stale` are frozen at the spec Appendix A values. Post-hoc variants are reported as exploratory.
- **Stage 2 is not peeked at.** It is analysed once, cumulatively.

## 8. Ethics and safety checklist

- [ ] Ethics board approval.
- [ ] DPIA completed (`docs/dpia-outline.md`).
- [ ] Consent form `docs/consent-templates.md` §1 adapted.
- [ ] Separate study accounts. Impostors never see the victim's files.
- [ ] Kill switch tested. Withdrawal deletes data within 30 days.
- [ ] Research build signed. Telemetry endpoint restricted to the study server.
