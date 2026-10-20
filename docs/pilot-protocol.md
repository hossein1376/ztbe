# Same-device feasibility pilot: protocol

Status: protocol v1, 2026-10-21 (research assistant). It implements D15 (go/no-go) and spec §12. Governance documents: `docs/dpia-outline.md` and `docs/consent-templates.md` §1.

## 1. Question and outcomes

**Primary question.** When a different person types on the *victim's own device and keyboard* (attacker A4, zero-effort walk-up), how often does the shipped configuration raise an alarm within 10 windows?

This removes the open-data device confound (spec L1). Different-device Tappy gives 88.0% [84.1, 91.7]. The same-quantum subset bound does **not** indicate that the different-device figure is optimistic: impostors whose timer quantum matches the target's are accepted *less* often, not more (same/different FAR ratio 0.86 in the spec config, 0.79 with all features; 0.59–0.90 across runs; spec §11 L1). Timer quantum is only a weak device proxy, so this cannot rule out a same-device penalty either. That is why the pilot is needed.

**Pre-registered outcomes (D15):**

| Outcome | Rule |
|---|---|
| **Stop** | 95% CI upper bound < 60% for alarm-within-10 → drop the A4 detection claim |
| **Go** | CI lower bound ≥ 70% **and** macro genuine step-ups ≤ 1.5 per active hour → build the powered study (PLAN Phase 3b) |
| Inconclusive | anything else → extend to the powered study, with the claim still marked unvalidated |

**Resolvable range** (`experiments/opendata/pilot_ci.py`, `results/pilot_ci.txt`):
- Assumptions: Wilson intervals, 3 impostors × 3 segments per victim, intra-victim correlation ρ **assumed** at 0.1–0.3.
- With 20 participants, "go" needs an observed rate ≥ 79–83% and "stop" needs ≤ 46–50%. With 10 participants, ≥ 83–88% and ≤ 41–46%.
- Observed rates in between are inconclusive by design. A pilot of this size cannot estimate FRR or FAR to ± 2 pp; that needs 164–177 / 119–131 users (spec §12).

**Secondary outcomes (descriptive, with CIs):**
- same-device block FAR at τ_g;
- genuine alarms per 60 windows (pooled, macro, p90);
- step-ups per active hour;
- `SIGNAL_LOST` per day;
- FTE (E1 not met within 14 days);
- capture-spike metrics (§5);
- acceptability questionnaire.

## 2. Participants

- **N = 10–20** adult volunteers (target 16, which leaves ≥ 12 after attrition).
- Recruited openly, not through a line-management chain (D6). Flat payment, not tied to performance (tey2013).
- **Device mix:** at least 4 Windows, 4 macOS and 2 Linux (X11 or console; Wayland is excluded, see collector-tradeoffs). At least 3 participants use an external keyboard as their main keyboard.
- **Fairness subgroups (optional self-report, consent D):** age band (< 30, 30–49, ≥ 50), handedness, primary typing language, typing-related condition (yes / no / prefer not).
  - The pilot is **descriptive only** for subgroups. n is far too small for inference. As spec §10 requires, a subgroup with < 10 users is reported as "insufficient n" with counts only. The self-reported condition item is used only for this table: it is never linked to scores in any output and never inferred (D7).
- **Exclusions:** none on ability. Assistive-input users are welcome; their sessions are classified per spec §3.1 and reported separately.

## 3. Timeline (per participant)

| Week | Activity |
|---|---|
| 0 | Consent; install the research-mode build (M5); timer self-test; keyboard class registered |
| 1–2 | Natural use. Enrolment E1 (≥ 20 scored windows and ≥ 7 days, supervised after WebAuthn). The template is sealed at E1 |
| 3–4 | Natural use (genuine test). Product-mode scoring runs and bands are logged; **no real step-ups**, shown as a notification only (to measure burden without disrupting work) |
| 3–4 | **Impostor sessions** (§4), scheduled |
| 4 | Copy-typing task (consent C, optional); exit questionnaire; uninstall; deletion check |

## 4. Impostor sessions (same device)

- **Pairing.** Round robin: each participant acts as impostor on 3 other participants' devices and is the victim of 3 others. Pairs are assigned by a script with a fixed seed, balanced across OS where possible.
- **Setup.**
  - The impostor logs in to a **separate study OS account** on the victim's machine. That account has the victim's sealed template copied in by the research build. This is research mode only; product templates are not exportable (spec §7).
  - Alternative where account copying is impossible: the victim unlocks, then hands over in front of the experimenter. The session is the victim's own account with a study-only browser profile.
- **Task.** 30 minutes of semi-natural typing:
  - 10 min free composition (prompts supplied, nothing personal);
  - 10 min email-style replies to supplied messages;
  - 10 min free choice from supplied tasks.
  - **Trust is reset every 10 windows**, giving 3 independent alarm-within-10 segments per session.
- **Zero-effort only for the primary outcome.**
  - Optional mimicry arm (consent E plus a separate tick): the impostor watches 2 minutes of the victim's typing video **without** timing feedback.
  - This is reported separately and does not count toward D15.
- **Labels.** The experimenter logs start and end times. Genuine windows during that interval are excluded.

## 5. Capture-spike metrics (PLAN M1-T5/T6)

Recorded per device:
- timer resolution: QPC or `mach_absolute_time` or evdev, versus hook timestamps;
- percentage of events with provenance `injected-*`;
- assistive-tool behaviour (on-screen keyboard, dictation, IME) per OS;
- hook timeouts (`tapDisabledByTimeout`) and LL-hook removals;
- `capture_lost` events;
- RDP and remote sessions detected;
- CPU and RSS per hour.

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

- **Primary.** Alarm-within-10 over impostor segments. The 95% CI comes from a cluster bootstrap over victims (10,000 resamples; seeds reported).
  - Also report a Wilson interval on n_eff with ρ estimated from the data.
  - D15 is applied to the bootstrap CI.
- **Burden.** Genuine step-ups per active hour per participant, as macro mean with bootstrap CI and p90. Alarms per 60 windows use the same definitions as `eval2.py`.
- **Comparison.** Run the same pipeline on Tappy different-device pairs and state the same-device − different-device difference. This difference is the confound estimate.
- **Pre-specified secondary checks.**
  - Effect of keyboard class (laptop vs external) on genuine FRR.
  - The `SIGNAL_LOST` rate.
  - Whether any assistive-input session produced HIGH. It must not; any HIGH there is a bug.
- **No re-tuning on pilot data.** τ_g, τ_w, a, P and R are frozen at the spec Appendix A values. Post-hoc variants are reported as exploratory.

## 8. Ethics and safety checklist

- [ ] Ethics board approval.
- [ ] DPIA completed (`docs/dpia-outline.md`).
- [ ] Consent form `docs/consent-templates.md` §1 adapted.
- [ ] Separate study accounts. Impostors never see the victim's files.
- [ ] Kill switch tested. Withdrawal deletes data within 30 days.
- [ ] Research build signed. Telemetry endpoint restricted to the study server.
