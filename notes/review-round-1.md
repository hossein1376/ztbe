# ZTBE — independent review, round 1

Reviewer: Grok Bot (acting for Hossein), 2026-10-21 (Asia/Tehran, UTC+3:30). Reviewed at commit `b54be19` plus the fix commits listed in §6.
Scope: spec v2 draft, PROPOSAL, PLAN, notes/*, experiments/opendata/*, references/*.
Convention: **UNVERIFIED** marks anything I could not check against a primary source or a re-run. I invented no numbers. Every number below is either copied from a results file in this repo (named), or comes from a run I made and committed (named).

---

## 0. Summary

- **Reproducibility is good.** I re-ran the experiments below on the same data. Each output equals the committed file byte for byte, except header text and an optional section I did not request:
  - `userpolicy` for t60, t120, n100 and n200;
  - `adapt` n200;
  - `fuse` tappy t60;
  - `run_keystroke` laser t120, run without `--guess`.

  I spot-checked about 60 numbers in the spec and PROPOSAL against `results/`. All matched except one stale cold-start row (t60), which I fixed. A few ranges and wordings were also wrong; I fixed those too.
- **The citations are in good shape.** I checked a random sample of 28 bib entries against Crossref and the publishers, and all 28 are correct. I checked 26 claim–source pairs. Two were misattributions or overreaches (rahman2011 vs rahman2013; sapiagent "mimics the user"). The rest are accurate.
- **The main problems are threats to validity and design holes, not arithmetic.** Ranked:
  1. **Device confound (M1).** Tappy and Aalto impostors typed on *different hardware*. The walk-up attacker (A4) types on the *victim's* hardware. Timer quantisation alone varies between Tappy users (§2.3), so the headline detection numbers are probably optimistic for A4, by an unknown amount.
  2. **Unsupervised adaptation is broken by an adaptive attacker (M3).** I ran a jittered boundary-walk attacker against the full guard stack. It reaches **31.6% takeover at 28 days**, against a 5.3% no-attack baseline on the same pairs. Spec A8 says "9%, equal to baseline". The same stack also gives *no* FRR benefit: 11.0% vs 10.9% static, from `adapt_n200.txt`.
  3. **A3 is not mitigated (D-b).** Assertions are not bound to requests or tokens. A stolen cookie keeps receiving the victim device's valid `ok` assertions.
  4. **A walk-up attacker can pause or kill the agent and only ever reach MEDIUM (D-a).** This attacker is the main one the system targets.
  5. **Thresholds are chosen on test or same-user data in several places (M2), and the protocol is small-n (M4).**
- **Verdict (details in §5).** More *desk* research has low marginal value. More *empirical and engineering* work is warranted, in this order:
  1. Fix the four design holes. This is spec text only.
  2. Re-run the evaluation with disjoint calibration, bootstrap CIs and the spec's own window definition. This takes hours on existing data.
  3. Run a small same-device-impostor pilot. This is the one experiment that can kill or confirm the project.
  4. Run an OS capture spike.

---

## 1. Internal consistency

### 1.1 Fixed in this round (trivial; see §6 for commits)

| Where | Was | Now | Source of truth |
|---|---|---|---|
| spec §5, t60 cold-start row | Stale numbers | 19.8/18.7, 12.7/9.2, 12.0/8.9, 10.6/7.4, 10.5/7.1, 10.7/7.5, 11.2/8.5 | `results/userpolicy_t60_K4.txt`; re-run is identical |
| spec A4, §6.5, §11 | Detection stated without window type; A4 used q80-row rates | Per window type; t60 80% within 5 windows; across types 72–88% at 0.51–1.49 alarms/60 windows (default row) | `results/userpolicy_*_K4.txt` |
| spec A6 | "§4.4" (does not exist) | §3.1 | — |
| spec §3, Aalto `pp_sd` ratio | 0.75–1.03 | 0.75–1.22 | experiments-v2 per-feature table |
| spec U3 / App. A, PROPOSAL §6 | r_anchor 0.67 | 0.675 | `adapt.py` |
| spec §2.1 | rahman2011 credited with 20–100 keys | 2011: 50–200 keys, 87.75%; 2013: 20–100 keys | Publisher abstracts |
| experiments-v2 (+ `.head.md`), PROPOSAL §5.1 | "SD features ratio ≥ 0.9 on every dataset" | ≥ 0.9 cross-session/cross-day; 0.75–1.22 on Aalto intra-session | Per-feature table |
| decisions.md "Implications" | D2→§8, D4→§7 | D2→§7, D4→§8 and §5 E3, D7→§1/§12 | spec v2 headings |
| bibliography.md, design-options | Key `fido-bio` (not in references.bib) | `fidobio` | references.bib |
| PLAN | "≈90–105 users" | 87–104 | `results/power.txt` |
| README | "154 entries", v1 framing, "pass 2" | 181 entries, v2 framing, link to this review | `grep -c '^@' references.bib` = 181 |

### 1.2 Not fixed: PROPOSAL vs spec v2 disagreements (substantive; needs an editorial decision)

PROPOSAL predates spec v2. I added a banner to PROPOSAL saying spec v2 governs where they differ, but the content still disagrees:

| Topic | PROPOSAL | spec v2 |
|---|---|---|
| Enrolment complete | 7 days or 30 windows | E1: ≥ 1000 keys, ≥ 15 min active, ≥ 2 calendar days |
| Uncertain band | Two consecutive uncertain → step-up | Uncertain gates sensitive ops only |
| High band | Step-up within 60 s or end session | §9.4: RP MUST NOT terminate on MEDIUM; HIGH → step-up |
| Per-user sensitivity | §5.2 lowers sensitivity per user | T2 rejects per-user thresholds (measured) |
| Template | 36 float64 features, ~1.7 KB | 21 float32 features, < 1 KB |
| Attacker IDs | A3 insider, A4 oracle, A5 malware, A6 impostor, A7 poisoner | A1–A8 with different meanings (design-options uses PROPOSAL numbering) |
| Headline detection | "85–90% within ~4 min" (per-block FAR@FRR5% flag rate) | 72–88% trust-model alarm within 5 windows |
| Prompt burden | 0.75 prompts/day | 1.05 per active hour (mean user) |
| Milestones | M0–M5 in §9.2 | PLAN 3a M0–M5 with different content and durations |
| Assertion | No `status`/`flags`/`kp` fields; mTLS channel | §9 COSE fields; channel unspecified |

Recommendation: shrink PROPOSAL to a motivation and decision record that points to the spec for every normative item. Do not maintain two specs.

### 1.3 Other stale or inconsistent statements (not fixed)

1. **notes/open-questions.md** is entirely v1-framed (lockers, K_app, fuzzy extractor) and has no banner. Either archive it or prefix it with "v1; superseded".
2. **design-options §4**: "Per-user thresholds are needed… see PROPOSAL §9". This is superseded by spec T2.
3. **spec §4**: "Gains flatten beyond K=4–8 [fuse_laser_n100]". The cited file shows EER 14.0 → 13.3 → 11.1 and FAR@FRR5% 25.0 → 24.6 → 15.3 for K = 4 → 8 → 16, which is not flat. The K=16 figures also suffer survivorship: only users with enough windows remain.
4. **spec §5**: "FRR@FAR1% does not improve with more enrolment (42–75% throughout)". It does improve from m=1 to m≈3–5 (t120: 70.2 → 43.7), then flattens. The conclusion "the tail is a matcher limit" survives; the sentence does not.
5. **spec §3**: the ICC column is the *population (Aalto-prior) ICC*. It is numerically identical across the aalto, laser and tappy columns of the per-feature table. It is presented next to per-dataset ratios as if it were per-dataset stability evidence. Label it as "population ICC on Aalto".
6. **spec §3**: `rp_mu_SR`/`rp_mu_RS` are dropped for a self-prior ICC of 0.01–0.03, yet `rp_mu_LR` (Tappy self-prior ICC 0.13) is kept. Make the rule explicit.
7. **spec A8 and decisions D4**: "full stack 9% = baseline" holds only for the non-adaptive attacker (see M3).
8. **spec §10**: "DPIA template: PLAN phase 3". PLAN has only an exit criterion ("DPIA draft complete"); no template exists anywhere.
9. **spec §6.2 T1 / §12** require τ calibration on *disjoint* users. The §6 numbers use the eval users' own calibration week (see M2). Either change the text or the experiment.
10. **Links**: I found no broken relative links. Every relative path in the `*.md` files resolves.
11. **Missing files**: none of the files referenced in experiments/README are missing. The `data/` directory is external by design.

---

## 2. Correctness

### 2.1 Numbers spot-checked (all match unless noted)

| # | Claim (location) | Checked against | Result |
|---|---|---|---|
| 1 | §6.1 table, all 4 window types, P0/P1/P3 FRR/FAR ranges | `userpolicy_{t60,t120,n100,n200}_K4.txt` | Match; re-run identical |
| 2 | Menagerie counts (§6) | Same files | Match |
| 3 | Trust table (default/q80/q95 detection, alarms) | Same files | Match |
| 4 | Cold start n100/n200/t120 rows (§5) | Same files | Match; **t60 row was stale, fixed** |
| 5 | Power: ρ, design effect, 87–104 users | `power.txt` | Match (PLAN was "90–105", fixed) |
| 6 | Fusion K=4: EER 7.5–8.5%, FAR@FRR5% 11–15% (Tappy t60) | `fuse_tappy_t60.txt` | Match; re-run identical |
| 7 | §3 within/between ratios (hold, pp_median, zone transitions, burstiness) | experiments-v2 per-feature table | Match, except Aalto `pp_sd` (fixed) |
| 8 | §8 adaptation table (week-8 FRR, takeover for naive/gated/full) | `adapt_n200.txt` | Match; re-run identical |
| 9 | LASER t120 EER/FRR@FAR1% | `laser_t120.txt` | Match; re-run identical |
| 10 | PROPOSAL window-size table, LDA table, binary/quantised table | `results/*` | Match |
| 11 | "Tappy timer ~15.6 ms" (experiments-v2 / PROPOSAL) | Raw Tappy archive (`tappy_timer.py`) | **Contradicted**: per-user quantum varies (§2.3) |
| 12 | Step-up burden 1.05 per active hour, p90 user 2.8 | `userpolicy_t60_K4.txt` | Match |

### 2.2 Spec v2 math

- **Shrinkage scale** `s = sqrt((n·MAD² + 2w²)/(n+2))`, with `w = 0.8·sqrt(within)`. This is a pseudo-count prior of weight 2 on the population within-user scale. It is coded consistently (`evallib.py`). One terminology issue: "MAD" in the code is the *mean* absolute deviation, not the median. The spec should say "mean absolute deviation", because the robustness properties differ.
- **Scaled Manhattan + K-block mean.** Correct as implemented. Averaging K window scores assumes roughly independent windows. Adjacent windows from one session are correlated, so the K-block FAR understates the attacker's real chance. The design effect in `power.py` partly covers the FRR side; for FAR it is not addressed.
- **Trust model** (Mondal–Bours style): the reward/penalty piecewise-linear update and the lockout threshold are coded as the spec states. Three simulation caveats:
  1. Impostor runs start at trust = 100.
  2. Genuine trust runs over the whole concatenated test period and is reset only after an alarm, never per session or per day, although the spec resets per session and at strong auth.
  3. "Mean windows to alarm" is right-censored at 30.
- **Guessing entropy.** It is explicitly an upper estimate from a population dictionary, which is fine. The `inf` for the Tappy Aalto-prior is correctly flagged.
- **Power / design effect.** `DE = 1 + (m−1)ρ` with equal cluster sizes. ρ is a point estimate from 28–40 users, and planning uses the max of 4 point estimates. That is not conservative: use the upper bootstrap CI of ρ. Unequal cluster sizes (heavy vs light typists) increase DE further.
- **COSE.** `alg -8 (EdDSA)` is deprecated by RFC 9864 in favour of fully specified `-19 (Ed25519)`. Whether go-cose v1.3.0 supports -19 is **UNVERIFIED**.

### 2.3 Methodology issues (ranked)

**M1. Device confound (high).** Tappy participants typed on their own computers; Aalto is an online test. A zero-effort impostor window therefore differs from the genuine user's in keyboard, OS, timer source and polling, not only in person. A4 (walk-up) uses the victim's device.
- **Evidence of device signal.** I ran `tappy_timer.py` on hold times from the first two monthly files of each user with ≥ 500 keys, 195 users. Users are on different clocks:

  | Hold-time quantum | Users |
  |---|---|
  | 3.906 ms | 106 |
  | 15.625 ms | 7 |
  | 7.8125 ms | 2 |
  | Finer or irregular | 80 |

  (`results/tappy_timer.txt`.) A quantum is itself a device fingerprint, and hold-time distributions inherit it.
- **LASER**, a lab study (shared hardware is likely but **UNVERIFIED**), is much worse: n200 EER 14.5% vs Tappy 7.9%. This is confounded by n=20 and by task differences, but it points the same way.
- **Consequence.** The §6 detection rates (72–88%) and the A4 row should be labelled "different-device zero-effort". The decisive experiment is same-device impostors: people typing on the victim's machine. Nothing in open data substitutes for it.

**M2. Thresholds on test or same-user data (high).**
- (a) EER, FRR@FAR1% and FAR@FRR5% are a-posteriori global thresholds on the test set. This is standard for ROC summaries, but they are reported as if they were operating points.
- (b) In `adapt.py`, `thr_v` is the EER threshold computed from week-2 genuine windows, which are also replay test data, against impostor windows drawn from any period.
- (c) `userpolicy.py` τ_g/τ_w come from the same eval users' calibration week. There is no test leakage, but this violates the spec's own "disjoint users" rule (§6.2 T1, §12).
- **Fix.** Calibrate on a disjoint user fold (k-fold over users) and report on held-out users. This is cheap.

**M3. Adaptation security (high).** I wrote `adapt_adaptive.py`. It reuses `adapt.py` verbatim (same pairs, templates and guard stack). The attacker walks toward their own mean in steps sized by λ·σ with random jitter, so that consecutive updates are *not* aligned, which evades the cosine sanitiser. Run on n200, 225 pairs; the no-attack baseline is 5.3% (`results/adapt_adaptive_n200.txt`):

| λ | Takeover at 1 d | 7 d | 14 d | 28 d | 56 d |
|---|---|---|---|---|---|
| 0 (≈ original attacker) | 5.8% | 13.8% | 6.2% | 6.7% | 9.8% |
| 2 | 5.8% | 8.4% | 12.0% | 16.0% | 23.6% |
| 3 | 5.3% | 12.0% | 19.6% | **31.6%** | 32.0% |

- At λ=3 the median attacker acceptance at 28 days is 16%. The attack saturates near the anchor-only bound (U3 radius), so **U3 is the only guard that holds**, and it holds at roughly a third of pairs.
- The original attacker's takeover is non-monotonic in attack length: 14.2% at 7 d vs 9.3% at 28 d in `adapt_n200.txt`. That points to noise or sanitiser timing effects, not robustness.
- **The full stack's FRR benefit is nil:** week-8 FRR 11.0% vs static 10.9%.
- Further gaps between the simulation and the spec:
  - The "checkpoint" in the simulation is a batch-start snapshot, not a strong-auth anchor.
  - Only the enrolment anchor is simulated (spec U3 allows ≤ 4).
  - σ is frozen, while U2 re-estimates it weekly.
- **Recommendation:** delete opt-in unsupervised mode from v2, or mark it "not recommended; no measured benefit, adaptive attack succeeds". Keep supervised mode, and measure its FRR benefit (PLAN M1-T4) before claiming one.

**M4. Small n and no CIs (medium).** The userpolicy runs use 28–40 users and a single split. Ranges in the spec are min–max over 4 window configs *on the same users*, not confidence intervals. Menagerie and Gini conclusions on ≤ 40 users are indicative at best. Bootstrap over users (cheap) and report 95% CIs on every headline number.

**M5. Policy comparisons at unequal FAR (medium).** P0, P1 and P3 are compared at their own thresholds; for example, P1 has lower FAR than P0 on n100 and t60. "Per-user thresholds double FRR" (T2) is therefore partly a threshold shift. Compare at matched pooled FAR, or plot DETs.

**M6. Pooled vs macro (medium).** Pooled metrics are dominated by heavy typists. In `adapt_n200.txt` the macro per-user window FRR is 21–30% while pooled is about 8–11%. Spec §12 promises both; the §6 headline numbers are pooled only.

**M7. Cold-start selection (low–medium).** Only users with ≥ 30 pre-test windows are included (heavy typists), and the EER per m uses an a-posteriori threshold.

**M8. LASER "cross-session" (low).** Session 2 is the same day (about 10 min after session 1) and switches task (free ↔ transcribed). It is not a clean cross-day measure, yet it is used to motivate "≥ 2 calendar days".

**M9. Spec parameters were never run (medium).**
- The experiments drop windows with < 20 keys and cap idle gaps at 1.5 s. The spec says ≥ 40 keys and removes gaps > 5 s.
- The spec's hybrid window ("T=60 s or N=200, whichever first") is untested.
- The 21-feature v2 set is untested; the experiments use the 36-feature set.

  All three are cheap to run.

**M10. Population (low, but a fairness flag).** Tappy is older adults on Windows, about a third with Parkinson's disease. Separability of impostors with motor impairment, and FRR for such users, is unknown. NIST 800-63B-4 asks for FMR performance "for all demographic groups".

### 2.4 Design issues found while checking the math

- **D-a. Agent pause/kill (high).** `status=3 paused(user)` exists. The agent is a user-level process. Silence leads only to MEDIUM after `max_silence` (15 min "of reported activity", which is undefined when the agent is silent). A walk-up attacker can pause or kill the agent and act at MEDIUM. Pausing should require a WebAuthn ceremony, or immediately raise HIGH for sessions bound to that device. Agent death should map to HIGH, not MEDIUM, for sessions with sensitive scopes.
- **D-b. A3 session hijack (high).** The RP "binds the session to the device key", but nothing binds *requests* to the device. A stolen cookie used elsewhere coexists with the victim device's valid assertions. Fix with sender-constrained tokens (DPoP, RFC 9449, or mTLS, RFC 8705) using the same hardware key, or put a hash of the session/token into each assertion *and* require proof of possession on requests. Until then, mark A3 "not mitigated".
- **D-c. Invalid assertion → HIGH (medium).** Without channel authentication, anyone who can post to the verifier can force step-ups (DoS). Authenticate the channel (mTLS with the device key), drop invalid assertions, count them, and alert, rather than escalating the user's band.
- **D-d. Injected-input policy vs accessibility (medium).**
  - "Injected fraction > 0 → not scored, `synthetic_suspect=true`" will fire for on-screen keyboards, dictation, AutoHotkey-style tools, password-manager auto-type, RDP/VNC/Citrix sessions, and some KVM switches.
  - These are disproportionately assistive-tech users and VDI enterprises.
  - The spec needs an explicit "unscored, not suspect" class and an allowlist mechanism.
- **D-e. Research-mode privacy (medium).** Per-event (zone, down, up) logs reveal word lengths (space zone) and hand-alternation patterns. Keystroke-timing text inference is established in the literature (e.g., Song, Wagner & Tian, USENIX Security 2001 — *not in references.bib; add and verify*). The PLAN 3b consent text and DPIA must treat raw zone streams as potentially content-revealing, not "content-blind".
- **D-f. Multiple keyboards per user (medium).** A laptop with an external keyboard, or a docked/undocked machine, is not addressed. Expect an FRR spike on device change. Consider per-input-device templates keyed by a non-secret HID class.

---

## 3. Citations

### 3.1 Random sample of bib entries (28 entries, `random.seed(20261021)` over the 181 keys)

Method: for each DOI I compared title, first author, year, venue and pages with the Crossref API; for the rest I fetched the URL.

| Outcome | Count | Notes |
|---|---|---|
| DOI resolves; metadata matches | 24 | `canetti2021joc`: Crossref "issued" is 2020 (online first), print volume 34 is 2021. Acceptable. |
| URL entry, page resolves and matches | 3 | `tey2013` (NDSS PDF, read in full), `ico-biometric`, `openid-ssf` |
| Could not verify | 1 | `iso24745`: ISO site returns HTTP 403 to automated fetches. The standard number/year (ISO/IEC 24745:2022) is **UNVERIFIED** by me. |

No fabricated or mismatched entries were found in the sample.

### 3.2 Claim–source pairs

| # | Claim (where) | Source | Verdict |
|---|---|---|---|
| 1 | Mimicry with training raises FAR substantially (spec §2.1) | tey2013, full PDF | ✓ |
| 2 | 87.75% of attempts succeed on 50 users | rahman2011sfr, abstract | ✓, but the spec attributed "20–100 keys" to it → **misattribution, fixed** (50–200 keys) |
| 3 | 20–100 key snoop-forge | rahman2013sfr, abstract | ✓ |
| 4 | Population attack EER +28.6% to +84.4%, > 3000 users | serwadda2013 | ✓ |
| 5 | Lego/robot attack FAR up 339–1004% | serwadda2013ccs | ✓ |
| 6 | Robot (touch) up to 5× FAR | serwadda2016robot | ✓ |
| 7 | Mimicry 84%/86% success, < 2 min | khan2016mimicry | ✓ |
| 8 | Liveness: synthetic keystrokes ~15% detection error; 1–2% with specific detectors | gonzalez2022liveness | ✓ |
| 9 | BeCAPTCHA-Type: synthetic keystrokes hard to detect; 136M keystrokes / 168k users base | dealcala2023becaptchatype | ✓ |
| 10 | BeCAPTCHA-Mouse 93% from one trajectory, 58 users | acien2022becaptchamouse | ✓ |
| 11 | SapiAgent "can mimic the user" (PROPOSAL A5) | antal2021sapiagent | **Overreach.** It generates *human-like*, not *user-specific* trajectories. Reword to "humanlike synthetic mouse input". |
| 12 | Gini / systematic errors argument | eberz2017 | ✓ |
| 13 | ANIA/ANGA metrics | bours2015perf | ✓ |
| 14 | Menagerie classes (worm/chameleon/phantom/dove) | yager2010 | ✓ (code mapping consistent) |
| 15 | Tappy: PD detectable from typing; own computers, unsupervised | adams2017tappy + PhysioNet page | ✓ |
| 16 | Tappy licence ODC-By 1.0 | PhysioNet | ✓ |
| 17 | Aalto 168k volunteers; non-commercial licence | dhakal2018 + dataset page | ✓ |
| 18 | FMR ≤ 1:10000 for biometrics | nist80063b4 | ✓, and the text adds "for all demographic groups" plus FNMR < 5% (SHOULD). Spec should quote both. |
| 19 | Behavioural signals as fraud indicators do not substitute for authentication | nist80063b4 | ✓ |
| 20 | Local comparison SHOULD; adaptation time limit SHALL; non-biometric alternative SHALL; keystroke/mouse in biometric definition | nist80063b4 | ✓ |
| 21 | FIDO lab FAR 1% / 0.01%, FRR 7% / 5% | fidobio v4.1 | ✓ |
| 22 | CAEP risk-level-change (§3.8): fields, LOW/MEDIUM/HIGH, SESSION principal | openid-caep | ✓ |
| 23 | Art. 9 biometric = "for the purpose of uniquely identifying"; always offer an alternative | edpb2019video paras 76–77, Example 3, para 86 | ✓ |
| 24 | Annex III(1)(a) excludes 1:1 verification; Annex III(4)(b) workforce monitoring is high-risk; Art. 5(1)(f) emotion recognition at work prohibited | euaiact2024 | ✓ (5(1)(f) letter now marked verified) |
| 25 | Landscape: LexisNexis acquired BehavioSec (2022) | Press release 2022-05-03 | ✓ |
| 26 | BioCatch patent portfolio | Company press, 71 (Feb 2022) → 84 (Aug 2022); US 11,630,893 assigned to BioCatch | ✓ (counts are company claims) |

**UNVERIFIED** (abstract or text not reachable to me): `stefan2012` and `mondal2015ins` specifics; `wang2012frog` (the spec already marks it); TypingDNA, Plurilock and other vendor claims in design-options; go-cose support for COSE alg -19; whether Apple Managed Device Attestation can serve a third-party agent key (it exists for MDM-managed Apple-silicon Macs on macOS 14+).

Go libraries: the licences and latest versions in PLAN match GitHub as of today:
- go-cose: MPL-2.0, v1.3.0
- fxamacker/cbor: MIT, v2.9.6
- sks: Apache-2.0, no releases
- go-keyring: MIT, v0.2.8
- go-webauthn: BSD-3, v0.18.2
- go-tpm: v0.9.8
- go-tpm-tools: v0.4.11
- go-attestation: v0.6.4
- memguard: Apache-2.0
- gohook: MIT

go-cose has had no release since 2024; treat it as a maintenance risk.

---

## 4. Coverage gaps (prioritised)

**P0 — blocks a credible MVP**
1. **Same-device impostor evaluation** (M1). PLAN 3b should make it the primary protocol: each participant types on ≥ 1 other participant's machine. Even a 10–20-person pilot answers the key question.
2. **Agent integrity and session binding** (D-a, D-b, D-c). A threat model for the agent itself (STRIDE): pause/kill, update channel, local IPC, debugger attach, the user-level vs service split.
3. **Per-OS capture spec** (all items below **UNVERIFIED** until a spike measures them):
   - **Windows:** low-level hook vs Raw Input; `LLKHF_INJECTED`; timestamp source (hook `time` field resolution vs QPC at callback).
   - **macOS:** CGEventTap with the Input Monitoring TCC prompt; Secure Input mode blanks password fields and some apps.
   - **Linux:** X11 XInput2 vs Wayland (no global hook; evdev needs the `input` group).
   - For each: what "injected" means.

   A one-to-two-week spike settles all of these and the rollover feature.
4. **Evaluation harness.** One harness: user-fold calibration, bootstrap CIs, macro + pooled metrics, attack generators (population-stats, snoop-forge-replay, adaptive poisoning), and a fixed report template. Today each script re-implements its own split.

**P1 — needed before any pilot with real users**

5. **Privacy artefacts.** The DPIA outline the spec claims exists; consent text for product mode and a separate one for research mode; retention schedule; DSAR handling for on-device templates; works-council/co-determination for workplace deployment. For example, German BetrVG §87(1) no. 6 covers technical monitoring; jurisdiction-specific details are **UNVERIFIED**.
6. **Accessibility and fairness** (D-d, M10). An assistive-tech policy, per-group FMR/FNMR reporting, and a non-biometric alternative path (also an EDPB and NIST requirement).
7. **Interfaces.**
   - CDDL for the assertion;
   - verifier API (enrol, nonce, assertion, checkpoint);
   - SSF stream config with example SETs;
   - RP integration guide;
   - error codes;
   - an OpenAPI document.
8. **Browser vs native decision.**
   - Browser SDK: no install, origin-scoped, coarsened timers, `isTrusted` does not reveal OS-level injection. This is what most vendors ship (**UNVERIFIED** per vendor).
   - Native agent: global capture, needs OS permissions and endpoint management, and carries a higher privacy burden.

   Write this down as a decision.

**P2 — valuable, not blocking**

9. **Multi-keyboard/device switching** (D-f), and keyboard layouts/IME (zone mapping by scancode).
10. **Landscape and FTO.** A proper vendor/OSS survey (BioCatch, LexisNexis/BehavioSec, TypingDNA, Plurilock, TwoSense, Zighra, ThreatMark — all beyond §3.2 **UNVERIFIED**), and a freedom-to-operate search on continuous keystroke auth + step-up + on-device templates. BioCatch alone reported 84 patents in 2022. This is not legal advice; get counsel.
11. **Operations.**
    - Privacy-preserving production telemetry: aggregate step-up and alarm rates only;
    - `policy_ver` rollout and rollback;
    - kill switch.
12. **Usability of step-up burden.** About 1 prompt per active hour for the mean user and 2.8 at the p90 user. Is that acceptable? A short survey or study would tell us.

---

## 5. Verdict and remaining work

**Is more research valuable?** Yes, but of a different kind.
- The literature review, standards and regulatory mapping, and open-data experiments have reached diminishing returns.
- The remaining uncertainty that decides go/no-go is empirical and cannot be resolved from open data: same-device impostor separability, real FRR on our users' hardware, and capture feasibility per OS.
- There are also four cheap spec fixes that change the security story.

**Ranked remaining work** (value ÷ cost)

| Rank | Item | Cost | Why |
|---|---|---|---|
| 1 | Spec fixes D-a (pause/kill), D-b (request binding/DPoP), D-c (invalid-assertion DoS), COSE -19 | Hours | Closes real holes; text only |
| 2 | Withdraw or relabel unsupervised adaptation; update A8/D4 with the adaptive result | Hours | The current claim is refuted |
| 3 | Re-run with user-fold calibration, bootstrap CIs, matched-FAR policy comparison, macro metrics, the spec's window definition and the 21-feature set (M2, M4–M6, M9) | 1–2 days | Makes every §5–§6 number defensible |
| 4 | Same-device impostor pilot (10–20 people) | 2–4 weeks | Go/no-go for A4 |
| 5 | OS capture spike (Win/macOS/Linux; injected flag; timestamp precision; TCC/Secure Input; Wayland) | 1–2 weeks | Determines what is buildable |
| 6 | Accessibility/injected-input policy; fairness reporting plan | Days | Legal and ethical requirement; affects D-d |
| 7 | DPIA outline + consent texts (product and research) | Days | Prerequisite for any pilot |
| 8 | Interfaces: CDDL, verifier API, SSF config, RP guide | Days | MVP |
| 9 | Browser vs native decision record | 1 day | Scopes the MVP |
| 10 | Landscape survey + FTO search | 1–2 weeks (+ counsel) | Commercial risk |
| 11 | Supervised-adaptation FRR benefit (PLAN M1-T4) | Days | Only matters if adaptation stays |
| 12 | PROPOSAL consolidation into the spec; archive open-questions v1 | Hours | Hygiene |

**Low value — skip or defer**
- More HE/2PC/OPRF/fuzzy-extractor work (v1 path, rejected).
- Further window-size, matcher or LDA sweeps on Tappy/Aalto: different-device data cannot answer the A4 question, so more tuning risks overfitting the confound.
- Mouse experiments on SapiMouse/Balabit, and anything more on Balabit.
- Clarkson II re-runs (still own-machine data; at best moderate value).
- Broadening the bibliography: it is already accurate and sufficient.
- LASER-only analyses (n=20).

---

## 6. Changes committed in this round

| Commit | Change |
|---|---|
| 34da6f6 | spec §5: t60 cold-start row corrected to the results file |
| c7a41f6 | spec §2/§6.5/§11: detection per window type; A4 uses the default trust row; user counts |
| 5923313 | spec: §3.1 cross-ref, Aalto pp_sd range, r_anchor 0.675 |
| a08829e | spec §2.1/§10: rahman2011 vs rahman2013; AI Act Art. 5(1)(f) verified |
| a472bff | decisions.md: spec section pointers |
| 0324630 | bibliography/design-options: `fidobio` key |
| 7e9a30d | experiments-v2 (+head): SD-feature instability statement |
| 450e59e | PROPOSAL: SD ratio ranges; r_anchor 0.675 |
| 14d5b16 | PLAN: 87–104 users |
| 11ab25f | New: `adapt_adaptive.py` + result; `tappy_timer.py` + result |
| (README, PROPOSAL banner, this file) | See `git log`; committed together with this review |

### How to reproduce the new results
```
cd experiments/opendata
python3 adapt_adaptive.py            # needs $DATA/derived tappy n200 npz; ~minutes
python3 tappy_timer.py               # needs $DATA/tappy/Archived-Data.zip; seconds
```
