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

## D4. Adaptation: decided by research assistant, 2026-10-21

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

## Implications recorded in PROPOSAL §10 and `spec/ZTBE-spec-v2-draft.md`

- D1 → spec §1 (scope and non-goals), §9 (relying-party consumption).
- D2 → spec §7 (sealing tiers).
- D3 → spec §4 (priors).
- D4 → spec §8 (adaptation) and §5 E3 (supervised enrolment).
- D5 → spec non-goals.
- D6 → spec §10 (privacy).
- D7 → spec §1 non-goals and §12 (evaluation data policy).
