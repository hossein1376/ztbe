# DPIA outline for ZTBE (pilot and product)

Status: outline, 2026-10-21 (updated for spec v2.2: R8 rewritten, R9 added after review round 2 H1). It is a template to be completed by the controller with its DPO. **It is not legal advice.** A legal opinion is required before any workforce deployment (D6).

Structure follows GDPR Art. 35(7) (description, necessity and proportionality, risks, measures) and the ICO DPIA guidance (ico-dpia). Screening uses the WP248 rev.01 criteria endorsed by the EDPB (wp248dpia).

## 0. Screening: is a DPIA required?

WP248 rev.01 lists nine criteria. "In most cases, a data controller can consider that a processing meeting two criteria would require a DPIA."

| # | WP248 criterion | ZTBE | Notes |
|---|---|---|---|
| 1 | Evaluation or scoring | **Yes** | Continuous scoring of typing behaviour against a template |
| 2 | Automated decision with legal or similar significant effect | Partly | Step-up only. No access is granted or denied by ZTBE alone (D1). Repeated step-ups could become significant at work → assess |
| 3 | Systematic monitoring | **Yes** | Continuous, for as long as the session is unlocked |
| 4 | Sensitive data | **Yes** | Biometric data (Art. 4(14)). We assume Art. 9 applies (spec §10) |
| 5 | Large scale | Depends | Pilot: no. Product: likely |
| 6 | Matching or combining datasets | No | Bands are not combined with other data (D6). The RP contract forbids it |
| 7 | Vulnerable data subjects | **Yes at work** | WP248 names employees, because of the power imbalance |
| 8 | Innovative technology | **Yes** | Behavioural biometrics with device-sealed templates |
| 9 | Prevents exercising a right or using a service | No, if the opt-out works (§5) | — |

**Result: a DPIA is required** (criteria 1, 3, 4 and 8 in every setting; 7 at work).

## 1. Description of processing

| Item | Pilot (research) | Product |
|---|---|---|
| Purpose | Measure same-device impostor detection and genuine burden (`docs/pilot-protocol.md`) | Continuous session risk signal → step-up (D1) |
| Data subjects | Adult volunteers recruited independently of any employer relationship | Users of an RP that has enabled ZTBE |
| Data on device | Key-zone timing in RAM (current window), sealed template, and in research mode per-window feature vectors (spec §3.3) | RAM window, sealed template |
| Data at server | Device public key, attestation result, seq state, band history ≤ 30 days; in research mode, uploaded window vectors (pseudonymous ID) | Same, without window vectors |
| Not collected | Characters and text; per-event streams (except the consented copy task); screen; applications; URLs | Same |
| Recipients | Research team only | RPs receive CAEP risk-level changes (LOW/MEDIUM/HIGH) and proofs |
| Retention | Window vectors: until the end of analysis plus ≤ 12 months, then deleted (proposal); consent records as required by law | Bands ≤ 30 days; templates until disable, re-enrolment or 180 days |
| Transfers | None planned (state the hosting region) | Depends on the deployment |
| Technology | `spec/ZTBE-spec-v2-draft.md` §13 | — |

## 2. Necessity and proportionality

- **Lawful basis (Art. 6) and condition (Art. 9).**
  - Pilot and consumer: explicit consent, Art. 9(2)(a), with a real alternative.
  - Employment: consent is generally not freely given. EDPB 05/2020 para 21 (edpb2020consent): "the EDPB deems it problematic for employers to process personal data of current or future employees on the basis of consent". WP29 Opinion 2/2017 says the same.
  - WP29 2/2017 §5.4.1 states that software "logging keystrokes and mouse movements" for remote-work security is "disproportionate", and a legitimate-interest basis is "very unlikely" (wp29opinion2017work, p. 16).
  - ZTBE processes timing, not content, and keeps it on the device. **Whether that makes it proportionate is the central legal question for workforce use. Counsel MUST answer it before any workforce deployment.** Until then: volunteers only (D6).
  - Art. 9(2)(b) (employment law) requires a Member State legal basis. Check national law, and works-council rights where they apply (e.g. Germany BetrVG §87(1) no. 6, cited in review round 1; UNVERIFIED by us).
- **Necessity.** Are less intrusive means enough?
  - Screen-lock timers;
  - sender-constrained sessions (DBSC / DPoP / mTLS, spec §9.5);
  - shorter session lifetimes;
  - step-up on sensitive operations only.

  The DPIA MUST justify why the residual walk-up risk (A4) needs ZTBE on top of these.
- **Minimisation.** Spec §10: no content, no server templates, no score API, ≤ 30-day bands, and window vectors only in research mode.
- **Accuracy and its consequences.**
  - Quote spec §11: zero-effort, different-device numbers only.
  - The genuine burden is about 0.9 step-ups per active hour for the mean user and about 2.5 at the p90 user (spec §6.5).
  - Same-device detection is unknown.
- **Transparency.** End-user notice (`docs/consent-templates.md` §2). A visible status indicator in the agent UI.
- **Rights.**
  - Access: the template lives on the device. The agent shows the status and enrolment state; DSAR answers explain that no template exists at the server.
  - Erasure: disable deletes the template and the server records (`DELETE /user/v1/ztbe`).
  - Objection and withdrawal: as easy as enrolment (Art. 7(3)).
  - Art. 22: no solely automated decision with legal or similarly significant effect, because ZTBE only triggers step-up (D1).

## 3. Risks to individuals (likelihood × severity; to be scored by the controller)

| # | Risk | Source | Initial assessment (proposal) |
|---|---|---|---|
| R1 | Repurposing for performance or behaviour monitoring of employees | A7, AI Act Annex III(4)(b) | Possible × high |
| R2 | Discriminatory burden on older users, motor-impaired users, AT users, non-native typists | Gini 0.71–0.73; untested subgroups (spec §10) | Likely × medium |
| R3 | Health inference from typing (e.g. Parkinson's) | adams2017tappy; D7 | Remote with minimisation × high |
| R4 | Content leakage from timing data | song2001ssh; research mode | Remote in product; possible in research without §3.3 → mitigated |
| R5 | Template theft from the device | A1/A2 do not apply; device compromise is out of scope | Remote × medium |
| R6 | Friction harm: repeated step-ups, stress, lost work | §6.5 alarm rates; SIGNAL_LOST | Likely × low–medium |
| R7 | False sense of security leading to weaker other controls | D1 framing | Possible × medium |
| R8 | Function creep to identification (1:N), and **cross-RP linking or profiling** through device identifiers or proof contents (review round 2 H1) | Non-goal; proofs are visible to web origins | Remote for 1:N (no server templates). Cross-RP linking: possible before v2.2 (global `dev`/`kid`, flags in proofs, unscoped registry); remote after D18 |
| R9 | Disclosure of assistive-technology use or remote-work status to RPs or websites | Proof and assertion flags before v2.2 | Possible × high before D18; remote after (reason never leaves the device) |

## 4. Measures

| Risk | Measure | Where |
|---|---|---|
| R1 | 3-level band only; no per-person reports; ≤ 30-day retention; contractual purpose limitation; no workforce deployment without a legal opinion | D6, spec §9.8 |
| R2 | Subgroup reporting and release gate; assistive-input class; opt-out without reason or penalty; disable rule for persistent high error | spec §3.1, §6.6, §10 |
| R3 | No health labels; no emotion or health inference (AI Act Art. 5(1)(f)); priors not trained on clinical data | D7, D3 |
| R4 | Window vectors only; copy-task exception under separate consent | spec §3.3 |
| R5 | TPM / SE sealing; memguard; no export | spec §7 |
| R6 | T5 rate limit (≤ 2/h); `uncertain` does not force step-up; pilot measures SIGNAL_LOST and the fraction of time stale. The HIGH latch (D19) means a genuine false alarm or network blip costs exactly one step-up, or a lock/unlock | spec §6.5, §9.6, §9.9 |
| R7 | RP guide: LOW never raises assurance | docs/interfaces.md §4 |
| R8 | On-device templates. **Pairwise** device IDs (`pdid`) and per-RP proof keys; the global device ID never reaches an RP. The extension answers only user-linked origins. The registry is scoped to the calling RP's own subjects. SSF subjects are pairwise. Proofs carry no `seq` or version strings | spec §1, §7, §9.5, §9.7, D18 |
| R9 | Assistive/remote reasons are kept on the device and in the user-visible local log. Verifier and RPs see only `unscored` / `no_signal`, which is the same value as paused or enrolling | spec §3.1, §9.5, D18 |

## 5. Consultation and sign-off

- DPO advice recorded.
- Data subjects' views: the pilot's exit questionnaire includes acceptability items (`docs/pilot-protocol.md`).
- Works council or employee representatives: required before any workplace use.
- Prior consultation with the supervisory authority (Art. 36) if a high residual risk remains. For workforce use this is likely until counsel's opinion says otherwise.
- Review the DPIA at every `policy_ver` change, and at least yearly.

## Sources

wp248dpia, edpb2020consent, wp29opinion2017work, edpb2019video, ico-dpia, ico-biometric, ico-monitoring, euaiact2024, nist80063b4 (`references/references.bib`).
