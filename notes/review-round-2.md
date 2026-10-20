# ZTBE — independent review, round 2 (final desk round)

Reviewer: Grok Bot (research assistant). Date: 2026-10-21 (Asia/Tehran, UTC+3:30). Scope: `main` at 482f20e (round-2 work, 16 commits after round-1's 2168912). Fixes from this review are listed in §7.

## 0. Summary

- **Round 1 is resolved.** All ten methodology issues (M1–M10) and all six design issues (D-a–D-f) are addressed, either fixed or stated as a limitation with a measurement plan (§1). The PROPOSAL/spec split and the stale v1 notes are cleaned up.
- **Numbers.** Every round-2 figure I checked in the spec, README, decisions and DPIA matches the results files. Cheap re-runs (eval2 hyb, power, pilot_ci) reproduce byte for byte (§3). I found three labelling/direction errors and fixed them.
- **Citations.** The B.16 additions and the landscape/interfaces/DPIA/consent claims check out, with one vendor contradiction (BehavioSec) and one version nuance (DBSC Chrome 145 vs 146), both fixed (§4).
- **New holes from the round-2 fixes** (§2). The fixes for D-a–D-c introduced a **privacy leak**: the browser proof path exposes a global device ID and sensitive flags to any website (H1). There are also three logic gaps: the HIGH band does not latch (H2), a non-typing walk-up attacker is never scored (H3), and the pilot's stop rule almost never fires (H9).
- **Verdict on D17** (§6): **agree; stop desk research.** The repo is a comprehensive desk-phase resource. Four must-fix items remain, all text-only spec/protocol edits, and none needs more desk research: H1, H2, H3 and H9.

---

## 1. Round-1 issues: resolution

| Round-1 issue | Status | Evidence |
|---|---|---|
| M1 device confound | **Resolved as limitation + plan** | Spec §11 L1, README "Main limitation", A4 row labelled "different-device"; same-device pilot (`docs/pilot-protocol.md`, D15/D16); timer-quantum bound in eval2 §D. The bound's direction was misstated in pilot-protocol §1 (**fixed**, 39ab7b1) and its spec figures were from the 34-feature run (**fixed**, 033d048) |
| M2 thresholds on test / same users | **Resolved** | `eval2.py`: 2 user folds, τ_g/τ_w from the other fold; A-posteriori EER kept only as a labelled ROC summary |
| M3 adaptive poisoning | **Resolved** | D8: adaptation off by default, unsupervised withdrawn (spec §8 U2 "MUST NOT be offered"); A8 row cites 31.6%; D4 marked superseded |
| M4 small n, no CIs | **Resolved** | 81 users, user bootstrap B = 1000 on every headline number. Residual: the bootstrap resamples targets only (attackers not clustered) → FAR CIs slightly narrow (minor, §3) |
| M5 unequal FAR | **Resolved** | Spec §6.1 matched-FAR table (FAR 10%) |
| M6 pooled vs macro | **Resolved** | Pooled, macro and p90 user throughout |
| M7 cold-start selection | **Resolved** | Spec §5 uses all users with ≥ m windows, operating-point FRR at τ_g |
| M8 LASER "cross-session" | **Resolved** | Spec §5 says same-day, task switch |
| M9 spec parameters never run | **Resolved** | `extract_tappy_v2.py` (hyb, ≥ 40 keys, idle > 5 s removed), v21 feature set; spec config is the headline |
| M10 population / fairness | **Resolved as plan** | Spec §10/§12 subgroup reporting; pilot "insufficient n" rule (D16) |
| D-a pause/kill | **Resolved** (new gaps H2, H3, H8) | Service/helper split, heartbeat 60 s, silence 150 s → SIGNAL_LOST → HIGH, WebAuthn pause grant (§9.3, §9.6) |
| D-b session hijack | **Resolved in design** (new gaps H1, H4) | Pull proofs (aud/chal/iat) + SHOULD DBSC/DPoP/mTLS (§9.5) |
| D-c invalid → HIGH | **Resolved** (new gap H5) | mTLS; drop/count; > 10/h → MEDIUM `ASSERTION_INVALID` (§9.4) |
| D-d injected input vs accessibility | **Resolved** (residual H7) | Provenance classes, allowlist, assistive profile, evasion guard (§4) |
| D-e research-mode privacy | **Resolved** | Window vectors only; zone stream only under consent C for the copy task; Song et al. cited (song2001ssh ✓) |
| D-f multiple keyboards | **Resolved** | Per-keyboard-class templates, `device_change` flag |
| §1.2 PROPOSAL vs spec (10 rows) | **Resolved** | PROPOSAL is now a 55-line non-normative rationale (D14) pointing to the spec |
| §1.3.1 open-questions v1 | **Resolved** | Moved to `notes/archive/open-questions-v1.md` |
| §1.3.2 design-options per-user line | **Resolved** | Struck through, points to T2 |
| §1.3.3 "flat beyond K=4" | **Resolved** | Spec §4 states "not flat" + survivorship |
| §1.3.4 FRR@FAR1% sentence | **Resolved** | Removed; §5 rewritten |
| §1.3.5 ICC label | **Resolved** | Spec §3 "population ICC under the Aalto prior" |
| §1.3.6 rp_mu rule | **Resolved** | Spec §3 table states the rule |
| §1.3.7 A8 / D4 | **Resolved** | See M3 |
| §1.3.8 DPIA template | **Resolved** | `docs/dpia-outline.md` |
| §1.3.9 T1 disjoint users | **Resolved** | eval2 user folds |
| §2.2 MAD wording | **Resolved** | Spec §4 "mean absolute deviation" |
| §2.2 window correlation in FAR | **Resolved as limitation** | Spec §4, L4 |
| §2.2 trust-sim caveats | **Resolved** | Reset per day in eval2; impostor start 100 and right-censoring stated (§6.5) |
| §2.2 power ρ point estimate | **Partly resolved** | Upper bootstrap ρ used (164–177 / 119–131 users). Residual: ρ still comes from the round-1 `userpolicy_*` counts (28–40 users, old window rules), not the eval2 hyb run. Re-estimate from pilot data anyway |
| §2.2 COSE −8 deprecated | **Resolved** | ESP256 (−9) / Ed25519 (−19), in-house COSE_Sign1 (D9); new pitfalls in H6 |
| §3 go-cose maintenance risk | **Resolved** | go-cose dropped. Re-checked: issue #224 (RFC 9864 support) and PR #225 still open; last release v1.3.0 on 2024-09-27 (Asia/Tehran) |
| §3 SapiAgent overreach | **Resolved** | Spec §2.1 "humanlike (not user-specific)" |
| §3 NIST "all demographic groups" + FNMR | **Resolved** | Spec §10 |
| §3 `iso24745` UNVERIFIED | **Open** (minor) | Still not verifiable by me (ISO blocks automated fetches) |
| §4 P0.3 per-OS capture | **Resolved at desk level** | `notes/collector-tradeoffs.md`, D12; measurements remain for the spike (E2) |
| §4 P1.7 interfaces | **Resolved** | `docs/interfaces.md` (CDDL, OpenAPI, SETs, RP guide) |
| §4 P1.8 browser vs native | **Resolved** | D12 |
| §4 P2.10 landscape / FTO | **Resolved at desk level** | `notes/landscape.md` (vendors, OSS, patents); not legal advice, counsel still needed |
| §4 P2.11 operations | **Partly resolved** | Kill switch (PLAN M5) and step-up/SIGNAL_LOST telemetry (spec §12). `policy_ver` rollout/rollback is still unspecified (minor) |
| §4 P2.12 burden usability | **Resolved as plan** | Pilot exit questionnaire; D15 burden criterion |

---

## 2. New security and logic holes from the round-2 fixes (D9–D16)

Severity: **MUST-FIX** means it must be fixed before build or pilot; the rest are should-fix or "state as limitation".

**H1 — MUST-FIX. Proof path leaks a global device ID and sensitive flags to any website.** (§9.5, interfaces §3)
- Any page can `postMessage` the extension. It gets back a validly signed proof with `aud` set to its own origin. The proof contains:
  - `dev` / `kid`, which are global (SHA-256 of the device key);
  - `band`;
  - `flags`, including `unscored_assistive` (disability-adjacent) and `remote_session`.
- So any site can link a user across sites, and can learn the user's assistive status and risk band.
- `/rp/v1/devices/{user}` lets any RP with client credentials list any user's device keys.
- The SET example also carries a global opaque device ID to every RP.
- This contradicts spec §1 (no cross-service linking), DPIA R8 ("no cross-RP identifiers"), and the privacy model of DBSC, which ZTBE cites (DBSC "should not leak any stable device identifiers"; it uses a new key per session).
- **Fix:**
  - pairwise device IDs and per-RP proof keys (or per-RP kids under an attested parent key);
  - the extension answers only origins that are enrolled RPs, after a one-time user approval;
  - in proofs, reduce assistive/remote to a single "no signal" value;
  - scope the registry to the RP's own pairwise subjects.

**H2 — MUST-FIX. The HIGH band does not latch.**
- After an alarm, trust resets to 100 (§6.4), so the next period's assertion can be `ok` → LOW.
- `SIGNAL_LOST` likewise clears on the next heartbeat.
- With "only changes are sent" (§9.7), an RP that processes HIGH → LOW in order may clear the pending step-up before it is enforced. A walk-up attacker only needs to keep typing for one more period.
- **Fix:** HIGH latches at the verifier, for both events and proofs, until a successful step-up or OS unlock. RPs MUST NOT clear a pending step-up on a later LOW.

**H3 — MUST-FIX (state it, and specify the band). A non-typing walk-up attacker is never scored.**
- Heartbeats with `nwin=0` carry no band, and windows with < 40 keys are not scored. The spec does not say what band the verifier or proof reports when there are no scored windows.
- If it is "last band", a mouse-only attacker, or one who types < 40 keys per window, inherits the victim's LOW until lock.
- **Fix:**
  - define the band reported for unscored periods;
  - add a coarse "time since last scored window" field to proofs;
  - let RPs require recent scoring for sensitive operations;
  - state the limitation in A4.
- Mouse scoring is out of scope for v2, which is fine, but say so in A4.

**H4. Periodic proofs do not bind requests.**
- A proof every 5 min shows only that *some* holder of the session reached the device.
- A thief sharing the cookie rides along on non-sensitive requests while the victim's browser answers the periodic proofs.
- Only per-operation proofs, or DBSC/DPoP, bind requests. Say this explicitly in A3, and raise DBSC/DPoP from SHOULD to a precondition for any "A3 mitigated" claim.
- Minor: "no proof → HIGH" lets a thief with the cookie force step-ups on the victim (nuisance, not compromise).

**H5. Invalid-assertion counter false positives.**
- Genuine conditions produce bursts of invalid assertions:
  - queued assertions after > 20 min offline (only the current or previous 10-min epoch is accepted);
  - `seq` lost on reinstall or restore;
  - clock skew (`t1 ≤ now + 30 s`);
  - a cleared TPM.
- Any of these can cross > 10/h → MEDIUM. Also, "never change the band" is true only in name: dropped heartbeats → silence → SIGNAL_LOST → HIGH.
- **Spec should require:**
  - refetch the epoch on reconnect;
  - discard, not send, stale queued assertions;
  - persist `seq` monotonically (e.g. time-based high bits);
  - document SIGNAL_LOST as the effective outcome.

**H6. In-house COSE pitfalls (D9).** Add these to the M2 T4 test plan:
1. ESP256 signatures are raw `r‖s` (64 B), while Go `crypto.Signer` / TPM / SE return DER. Convert.
2. Verify the received protected-header bstr; never re-encode it.
3. Check `alg` against the registered key type.
4. Reject unknown critical headers.
5. ECDSA is randomised, so the "RFC 9052 examples re-signed" tests can only check Sig_structure bytes and verification, not signature bytes.
6. RFC 9864 Security Considerations: "A cryptographic key MUST be used with only a single algorithm unless the use of the same key with different algorithms is proven secure". The device key signs both TLS 1.3 CertificateVerify and COSE. It is the same curve and hash, but different protocols, so add a short domain-separation argument or use two keys.

**H7. Assistive and on-screen-keyboard rule (D13): residual evasion.**
- For users with the assistive profile, a walk-up attacker using the on-screen keyboard gets "no signal": no A4 protection at all.
- For other users the guard yields MEDIUM `UNSCORED_CHANGE`, not HIGH, so the attacker avoids step-up on non-sensitive operations.
- Mixing physical and allowlisted input to stay just above or below the > 50% allowlisted threshold is gameable.
- State all three in A4/L-section. That is acceptable for v2, but it must be visible.

**H8. Pause and disable.**
- The spec does not define what RPs see during `paused` (no signal? MEDIUM?), or what a proof carries while paused.
- `DELETE /user/v1/ztbe` was not marked as requiring WebAuthn in the OpenAPI (**fixed**, 50562ee). Otherwise a walk-up attacker with a live IdP session could disable ZTBE.

**H9 — MUST-FIX before data collection. Pilot statistics (D15/D16).** I simulated the rule (`experiments/opendata/pilot_oc.py`, `results/pilot_oc.txt`; beta-binomial victim clustering ρ = 0.2, optional crossed impostor effect sd 0.8 logit; 2000 pilots per row; B = 1000 cluster bootstrap):

| N | true alarm-within-10 | P(go) | P(stop) | P(inconclusive) | CI coverage |
|---|---|---|---|---|---|
| 16 | 0.55 | 0.00 | 0.13–0.17 | 0.83–0.87 | 0.90–0.93 |
| 16 | 0.65 | 0.01 | 0.01 | 0.98–0.99 | 0.89–0.92 |
| 16 | 0.75 | 0.17–0.21 | 0.00 | 0.79–0.83 | 0.90–0.93 |
| 16 | 0.80 | 0.41–0.49 | 0.00 | 0.51–0.59 | 0.89–0.90 |
| 16 | 0.88 | 0.87–0.92 | 0.00 | 0.08–0.13 | 0.88–0.89 |
| 10 | 0.88 | 0.76–0.83 | 0.00 | 0.17–0.24 | 0.85–0.86 |

(ranges = without/with impostor effect; ρ and sd are assumptions)

- **The stop rule almost never fires.** Even at a true rate of 55%, P(stop) is only 0.11–0.18 at N = 10–20. The pilot effectively outputs "go" or "inconclusive".
- **"Go" is unlikely unless the true rate is ≥ ~85%.** At a true 75–80%, P(go) is 0.17–0.57.
- **The percentile cluster bootstrap under-covers** (0.85–0.94; worst at N = 10).
- **Other issues:**
  - Impostor ("wolf") effects are crossed with victims and not modelled.
  - The protocol has **no genuine control under the same 30-minute task**, so detection is confounded with task.
  - The burden criterion does not say whether it uses a point estimate or a CI bound.
  - §2 of the protocol plans with Wilson intervals, but §7 decides on the bootstrap.
  - "Trust reset every 10 windows → 3 independent segments" assumes ≥ 30 windows in 30 minutes. A hyb window is ≈ 60 s of *active* typing (measured 59.5 s mean, `results/window_duration.txt`), so a 30-minute semi-natural task may not yield 30 windows (UNVERIFIED: task typing density).
- **Fix:**
  - add a futility rule on the point estimate (e.g. stop if the point estimate is < 60%), or state explicitly that the pilot can only show "go";
  - add genuine same-task control segments;
  - use the more conservative of the bootstrap and Wilson-on-n_eff, or a two-way (victim × impostor) bootstrap;
  - state the burden statistic (suggest the point estimate, with p90 reported);
  - check window yield in a dry run, and lengthen the session or use 2 segments if it falls short.

**Minor logic notes**
- §6.5 "per active hour" now defined as active typing hour (measured ≈ 61 hyb windows/h; **fixed**, 2d6d916).
- D15 burden 1.5/h vs measured macro 0.93 [0.49, 1.54] per 60 windows. The upper CI is at the threshold already on open data.
- `adapt_supervised`: all point estimates are ≥ 0 (adaptation slightly *raises* FRR; hyb S=2 +1.9 pp). "No measurable benefit" (README) is correct; "possibly harmful" is also consistent with the data.

---

## 3. Numbers spot-check and re-runs

| Claim (location) | Results file | Result |
|---|---|---|
| Headline P0 FRR/FAR/p90/Gini, matched FAR (README, spec §6.1/§6.3) | `eval2_hyb_v21_all.txt` | Match |
| Trust: alarms per 60 windows, alarm within 5/10 (README, §6.5, A4) | same | Match |
| §3 v21 vs all: 6.8 [4.3, 11.2] vs 6.6 [4.4, 9.6]; 81.6 vs 77.3 | `eval2_hyb_{v21,all}_all.txt` | Match |
| §4 window table (hyb/t60/s60/n100/n200/t120) | `eval2_*_all_all.txt` | Match |
| §5 cold start (43.6 → 19.4 → 18.8) | `eval2_hyb_*` §E | Match |
| §6.1 "p90 ≈ 3–4× pooled", "Gini 0.73" | `eval2_hyb_all_all` vs `_v21_` | True for 34 features only; spec config is 4.8× and Gini 0.71. **Fixed** (042a32e) |
| §8 supervised deltas (+0.2/+0.5/+1.3 pp; static 5.0%) | `adapt_supervised_*.txt` | Match |
| §11 L1 quantum bound 9.6% vs 12.2% | `eval2_hyb_all_all` | From the 34-feature run; spec config is 10.5% [6.8, 14.6] vs 12.2% [8.9, 16.4], ratio 0.86. **Fixed** (033d048) |
| §11 L1 ratio range 0.59–0.90; q3.9 FAR 9.5–12.8% | eval2 runs | Match |
| §12 power: ρ 0.36/0.30; 164–177 / 119–131 users | `power.txt` | Match (see §1 residual on ρ source) |
| D15 addendum resolvable ranges | `pilot_ci.txt` | Match |
| DPIA "Gini 0.71–0.73" | eval2 | Match |

**Re-runs** (in a scratch copy, so `results/` was not overwritten): `eval2.py` hyb v21 and all; `power.py`; `pilot_ci.py`. All are byte-identical to the committed files.

**New:**
- `pilot_oc.py` (§2 H9).
- `window_duration.py`: 66,739 hyb windows, the same count as `tappy_hyb.npz`; mean 59.5 s active typing per window; 9.7% close at 200 keys first.

**Methodological residual:** the eval2 bootstrap resamples targets, not attackers. The FAR CIs ignore attacker clustering and are somewhat narrow. Note this in §12; it is not blocking.

---

## 4. Citations and factual claims (B.16 + new docs)

| Claim / key | Source checked | Verdict |
|---|---|---|
| rfc9864: ESP256 = −9, Ed25519 = −19, −7/−8 deprecated | RFC text | ✓ (also: single-algorithm-per-key MUST, see H6) |
| openid-caep §3.8.1 fields; principal values; levels | CAEP 1.0 Final | ✓ |
| `sub_id` "complex" format in interfaces.md | openid-ssf §3.3 | ✓, but spec §9.7 said "RFC 9493 (iss_sub or opaque)". **Fixed** (ceb232f): it is an SSF complex subject with RFC 9493 members |
| rfc9449 DPoP, rfc8705 mTLS-bound tokens, rfc8610 CDDL, rfc9457 problem details | RFC index | ✓ |
| w3c-dbsc ED 2026-09-08; privacy goal | W3C ED | ✓ |
| google2026dbsc: Chrome 146 on Windows | Google blog 2026-04-09 | ✓; but the Chrome for Developers post says **Chrome 145**. **Fixed** (1166cbf). macOS-147 claim stays UNVERIFIED |
| go-cose no −9/−19 support; no release since 2024 | GitHub #224, PR #225, releases | ✓ |
| ms-kbdllhook: LLKHF_INJECTED 0x10, LOWER_IL 0x02; `time` = GetMessageTime | Microsoft docs | ✓ |
| ms-gettickcount: 10–16 ms resolution | Microsoft docs | ✓ |
| w3c-hrtime: 100 µs / 5 µs isolated, may be coarser + jitter | W3C HR-Time | ✓ |
| apple-pppc: profiles can only deny ListenEvent; `AllowStandardUserToSetSystemService` | Apple docs | ✓ |
| linux-input: evdev, `input` group | kernel docs | ✓ |
| song2001ssh: Herbivore, ~50× search reduction | USENIX Sec 2001 | ✓ |
| edpb2020consent para 21 (employment consent problematic) | EDPB 05/2020 | ✓ |
| wp29opinion2017work (WP249): consent not a basis at work; keystroke/mouse recording "disproportionate" (§5.4.1) | WP249 PDF pp. 6–7, 16 | ✓ |
| wp248dpia "two criteria" rule | — | ✓ from memory, **not re-fetched** this round |
| ico-dpia, ico-monitoring | ICO pages | ✓ (summary level) |
| Patents: TypingDNA US 11,914,690 B2 (active, exp. 2042-04-08); HP US 12,248,544 B2; ISU US 2015/0169854 A1 (abandoned 2017-01-25); Matchett US 5,229,764; CMU US 2014/0250523; IBM US 2020/0358787; Zighra US 2016/0259924; Citrix US 12,314,361 | Google Patents | ✓ dates and status. HP issue date (2025-03-11) not visible in the fetched text: UNVERIFIED. Kryptowire US 10,289,819 not checked |
| TypingDNA ActiveLock: < 100 keystrokes, offline, keeps training | Vendor page | ✓ |
| Twosense: per-second, no enrolment, CAEP | Search summary only | ✓ (summary level; UNVERIFIED in detail) |
| BehavioSec "does not collect or store any user inputs or PII" | Product FAQ ✓; **contradicted** by the LexisNexis ThreatMetrix processing notice (Apr 2026: keystroke and key-pressed data collected, deleted within 24 h) | **Fixed** (790b3ff): both cited |
| DPIA / consent templates: Art. 9 reading, Art. 7(3), EDPB/WP249 on employment, layered notice | Sources above | ✓ consistent; still "not legal advice" (D6) |

No fabricated citations found. `iso24745` remains UNVERIFIED (ISO blocks automated fetches).

---

## 5. Cross-file consistency and links

- **Links:** every relative Markdown link and backticked repo path resolves. The one hit, `notes/open-questions.md` in D14, describes the move to `notes/archive/` and is intended. All bib keys cited in the spec and new docs exist in `references.bib` (199 entries, as README says).
- **Fixed in this round:**
  - pilot-protocol §1 quantum-bound direction (39ab7b1);
  - spec §11 L1 feature-set label (033d048);
  - spec §6.1 Gini/p90 label (042a32e);
  - spec §9.7 vs interfaces `sub_id` (ceb232f);
  - interfaces `DELETE /user/v1/ztbe` WebAuthn (50562ee);
  - PLAN M5 "user can pause" → WebAuthn grant (b90922a);
  - PLAN pass-2 table marked historical: template 1.7 KB, "9% = baseline", PROPOSAL milestones (5239ed0).
- **Not fixed (substantive, see §2):**
  - DPIA R8 "no cross-RP identifiers" is false while H1 stands;
  - pilot-protocol §2 (Wilson) vs §7 (bootstrap);
  - spec §9.8 "no signal" list omits `paused` (H8).

---

## 6. Verdict on D17 (stop desk research)

**Agree.** The repo is now a comprehensive desk-phase resource:
- a normative spec with measured operating points and CIs;
- a decision log D1–D17 with "what would change it";
- interfaces (CDDL, OpenAPI, SETs);
- per-OS collector trade-offs;
- landscape with an FTO starting list;
- DPIA outline and consent texts;
- a pilot protocol with a pre-registered rule;
- reproducible experiments.

What remains is empirical, as D17 says: same-device rate, capture per OS, supervised-adaptation benefit, and legal proportionality.

**Must-fix before build or pilot.** These are text edits, not research:
1. **H1:** pairwise device IDs / per-RP proof keys, origin allowlist with user approval, no assistive/remote flags in proofs, registry scoping; then re-check DPIA R8.
2. **H2:** HIGH latches until step-up or unlock (verifier, events and proofs; RP MUST NOT clear on later LOW).
3. **H3:** define the band for unscored periods, add scoring freshness to proofs, state the non-typing attacker limit in A4.
4. **H9:**
   - add a futility rule or state that the pilot is go-only;
   - add genuine same-task controls;
   - make the CI method conservative;
   - define the burden statistic;
   - dry-run the window yield.

**Should-fix:** H4 (state the request-binding limit), H5 (epoch/seq rules), H6 (COSE test plan + key-use note), H7 (state the limits), H8 (paused semantics), the `policy_ver` rollout note, and the eval2 attacker clustering note.

---

## 7. Commits in this round

| Commit | Change |
|---|---|
| 033d048 | spec §11 L1: quantum-bound figures labelled by feature set (spec config 10.5% vs 12.2%, ratio 0.86) |
| 39ab7b1 | pilot-protocol §1: direction of the timer-quantum bound |
| 50562ee | interfaces: `DELETE /user/v1/ztbe` requires WebAuthn |
| ceb232f | spec §9.7: `sub_id` is an SSF complex subject |
| 1166cbf | spec §9.5 / bibliography: DBSC Chrome 145 vs 146 |
| 790b3ff | landscape: BehavioSec FAQ vs LexisNexis processing notice |
| 042a32e | spec §6.1: Gini and p90/pooled labelled by feature set |
| b90922a | PLAN M5: pause needs a WebAuthn grant |
| 2d6d916 | spec §6.5: "active hour" = active typing; `window_duration.py` |
| 115efae | `pilot_oc.py` + `results/pilot_oc.txt` |
| 5239ed0 | PLAN: pass-2 outcome table marked historical |

**Reproduce:**

```
cd experiments/opendata
python3 pilot_oc.py
python3 window_duration.py > results/window_duration.txt
```

`window_duration.py` needs the Tappy archive under `$DATA`.
