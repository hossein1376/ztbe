# opendata: Eberz-style evaluation on open keystroke and mouse datasets

This directory contains the code behind `notes/experiments-v2.md`. Python 3.13 with numpy (plus pandas for `extract_mouse.py`). It is single-threaded except `extract_aalto.py`, which uses `NPROC` workers. All randomness is seeded (20261021 or fixed per script).

**No raw or derived data is committed.** `fetch.sh` downloads the raw data into `$DATA` (default `/workspace/data`), and every derived `.npz` goes to `$DATA/derived/`.

## Datasets and licences

| Dataset | Licence / terms | Used for |
|---|---|---|
| Aalto 136M Keystrokes (dhakal2018) | Research and non-commercial use, with attribution | Population priors (μ, σ, quantile edges, LDA), the attacker dictionary, and intra-session evaluation (3000 users disjoint from 20000 population users) |
| CMU LASER-2012 free vs transcribed (killourhy2012laser) | No explicit licence; cite | **Cross-session** evaluation: 20 users, enrol on session 1, test on sessions 2–4 |
| Tappy, PhysioNet (adams2017tappy) | ODC-By 1.0. Includes Parkinson's-disease subjects | **Cross-day** evaluation (enrol in week 1, test from day 14) and the adaptation/poisoning simulation |
| SapiMouse (antal2021sapimouse) | Data page shows no licence; the repo is Apache-2.0 | Mouse: enrol on the 3-min session, test on the 1-min session |
| Balabit Mouse Challenge (balabit2016) | No licence file | Mouse: training sessions → labelled test sessions. The labelled illegal sessions serve as real foreign-user impostors. |

Not used:
- Buffalo (on request only).
- Clarkson I/II (on request, being requested separately).
- KeyRecs (single session).
- KEasyLogger on Zenodo (contains only aggregated digraph statistics).
- MSU Typing Behavior (non-commercial; not needed).

## Pipeline

```
DATA=/workspace/data ./fetch.sh all
python3 extract_aalto.py      # streams the 1.57 GB zip; QWERTY full/laptop keyboards only; ~162k users
python3 extract_laser.py
python3 extract_tappy.py
python3 extract_mouse.py      # SapiMouse + Balabit
./run_all.sh                  # every run_keystroke.py configuration -> results/<tag>.{txt,json}
python3 adapt.py n200         # adaptation + poisoning on Tappy -> results/adapt_n200.txt
python3 fuse.py laser t30     # k-window decision fusion -> results/fuse_<ds>_<cfg>.txt
python3 aggregate.py          # markdown tables for notes/experiments-v2.md
```

## Files

| File | Contents |
|---|---|
| `features.py` | Content-blind features (spec FR-02). Each key is mapped to a hand zone (L/R/S/other) and the character is discarded. **36 keystroke features**: hold mean/sd per zone, press-press mean/sd and release-press mean for 8 zone transitions, rollover fraction, median PP, pause fraction (gap > 1.5 s), burstiness, backspace fraction, modifier hold. The 34 *common* features drop the last two (not in Tappy). **23 mouse features**: velocity, acceleration, jerk, angular velocity, curvature, straightness, movement duration/length, click dwell, pause fraction, 8-direction histogram. Windows are N keystrokes (`n50/n100/n200/n400`) or T seconds of *active* typing (`t30…t300`; idle gaps capped at 1.5 s), non-overlapping. Windows with fewer than 20 keys or 30 moves are dropped. |
| `evallib.py` | Population prior (z-score, equiprobable quantile edges, Fisher ratio, ICC), LDA-16, Gray / LSSC (thermometer) / DROBA bit allocation, ROC metrics, Gini, Daugman DoF, sample-then-lock rates, the per-locker population attack, greedy dictionary guessing |
| `run_keystroke.py` | One dataset × window configuration (see *Protocol*) |
| `adapt.py` | Template update policies × poisoning attack (Tappy) |
| `fuse.py` | Score averaging over k consecutive windows |

## Protocol (after eberz2017)

- **Chronological split.** Enrolment data always comes from earlier than test data. The splits are cross-session (LASER), cross-day with at least a 7-day gap (Tappy), first half versus second half of the only session (Aalto: optimistic, so it is labelled *intra-session*), and 3-min versus 1-min sessions (SapiMouse).
- **No impostor data in training.** Templates use only the user's own enrolment windows. Priors and LDA come from **disjoint** population users: Aalto for Aalto and LASER; Aalto or half of the Tappy users (`PRIOR=self`) for Tappy; 60 disjoint users for SapiMouse. Balabit is the exception: its priors come from the same 10 users' training data (optimistic, and flagged as such).
- **Impostors.**
  - Zero-effort: the test windows of 30 other evaluation users.
  - Balabit additionally uses its labelled illegal sessions.
  - The guessing attacker uses population templates (see entropy below).
- **Global threshold**, reported as EER, FRR@FAR=1%, FRR@FAR=0.1% and FAR@FRR=10%. The **Gini coefficient** of per-user FRR and per-attacker FAR captures how errors concentrate on a few users.
- **Template.** μ is the mean of the enrolment windows. The per-feature scale is a shrinkage blend of the user's MAD and the population within-user spread (`Tsd`, see `run_keystroke.py`). Unprotected matchers: scaled Manhattan (Killourhy–Maxion style), and Euclidean distance in LDA-16 space.
- **Binary variants:**
  - Gray m=1/2/3 on equiprobable population bins.
  - LSSC S=4/8 thermometer codes.
  - A population mask: top-16 features by Fisher ratio.
  - LDA-16 → sign bits, or LSSC S=8 (112 bits).
  - DROBA with user-specific allocation (L=64), and a 1-bit DROBA-style top-16 user-specific mask.

  Hamming distance is compared against a global threshold.
- **Entropy.**
  - **Guessing curve.** The attacker holds 4000 population templates (disjoint users) and greedily picks the template that is accepted by the most targets at the verifier's own threshold. P_k is the fraction of targets broken within k guesses, and −log2 P1 is reported as an **upper estimate of fuzzy min-entropy** (Fuller et al.: the probability of the best single guess landing inside the acceptance ball).
  - Assumptions: the attacker can inject arbitrary feature vectors; the dictionary is finite and drawn from the same domain; the threshold is the system's. Results are **upper bounds**, since a bigger dictionary or a better attacker lowers them.
  - The sample-then-lock per-locker attack and Daugman DoF are also reported.
- **Caveats.**
  - LASER has only 20 users, so its P1 has a resolution of 0.05.
  - Tappy with Aalto priors suffers domain shift: the Aalto dictionary fails on Tappy, so its "∞ bits" is an artefact. Use `_selfprior`.
  - Tappy timer resolution is about 15.6 ms.
  - Aalto is transcription typing in one session.
  - Mouse features are deliberately simple.
