# Landscape: commercial systems, open source, and a desk-level prior-art note

Date: 2026-10-21 (round 2). Sources were fetched on that date. Vendor figures are **the vendors' own public claims**, not verified performance. "UNVERIFIED" marks claims seen only in a search snippet or secondary source.

## 1. Commercial systems

| Vendor / product | What it is (vendor's words, paraphrased) | Public claims (as stated, unverified by us) | Collection point | How ZTBE differs |
|---|---|---|---|---|
| **BioCatch** (Connect, behavioural intelligence) | Fraud and financial-crime detection for banks, from behavioural, device, network and transaction signals | "18 billion user sessions analyzed per month", "3,000+ behavioral and device signals", "<500 ms to assess risk", 680M accounts / 1.7B devices, "350+" banks (biocatch.com, fetched 2026-10-21). Patent portfolio 84 (Aug 2022, company press; review round 1) | SDK in bank web and mobile apps (RP-scoped) | Fraud scoring on a server with thousands of signals. ZTBE is device-scoped, keystroke-only, on-device, and exports a 3-level band only |
| **LexisNexis BehavioSec** (acquired 2022-05-03; review round 1) | "Real-time behavioral and device intelligence from login to logout": mouse, typing rhythm, touch, device handling; bots, RATs, scams | "Does not collect or store any user inputs or PII. All behavioral analysis is done locally and anonymously" (product FAQ). **But** the LexisNexis ThreatMetrix processing notice (last updated April 2026, <https://risk.lexisnexis.com/corporate/processing-notices/threatmetrix>) says that with BehavioSec "behavioral data, including mouse movements, touch screen inputs, keystroke and key pressed data is collected"; key-pressed data may be masked, and both masked and unmasked key-pressed data are deleted within 24 hours. Treat the FAQ claim as marketing. Integrates with ThreatMetrix via one API; behavioural score + reason codes + raw data to the customer | Web collector script and mobile SDK | Delivers scores, reason codes and **raw data** to the business. ZTBE has no score API and delivers no raw data, by design (D6) |
| **TypingDNA ActiveLock** | Continuous endpoint verification by typing; locks the desktop or alerts on mismatch; Windows, Mac, Linux (beta) | "Unauthorized use can be detected in under 100 keystrokes"; "completely offline. Typing biometric data does not leave the computer"; v3.5 adds mouse and optional face; logs include "keyboard id", "typing pattern characteristics (e.g. speed)", score and result; continues to train after enrolment | Native endpoint agent | Closest product to ZTBE's A4 use case. Differences: ZTBE never locks on its own (D1), exports signed bands to RPs via SSF/CAEP rather than logs, has no adaptation by default (D8), and publishes its error rates with CIs and threat model. ActiveLock's local logs contain per-event-derived characteristics, which ZTBE avoids (§3.3) |
| **TypingDNA Verify 2FA** | Typing-biometric second factor: type a few generated words; SMS/email OTP fallback | (product page, search summary) | Browser | A login-time factor. ZTBE is explicitly *not* a factor (D1) |
| **Twosense** | Continuous authentication for workforce and clinical settings: keystroke cadence, mouse, app usage | "Verifies identity once a second"; "1M+ authentications, 17,000+ users, 170+ apps"; "No enrollment required"; "CAEP signal propagates"; step-up, termination or SIEM alerts | Endpoint software | Also emits CAEP; the nearest architectural peer. Differences: ZTBE requires a supervised enrolment of ≥ 7 days (cold-start FAR 44% → 20% → 12%, spec §5) where Twosense says "no enrollment"; ZTBE does not use app usage (not content-blind); ZTBE treats workforce use as legally gated (D6) |
| **Plurilock** (DEFEND) | Behavioural continuous authentication (keyboard and pointer) | The DEFEND product page now redirects to a services homepage (fetched 2026-10-21). Product status and the "every 3–5 seconds" claim (search snippet) are **UNVERIFIED** | Endpoint, incl. VDI (snippet) | — |
| **Zighra** | "ContinuousMFA" with behavioural verifiers, trust levels and on-device learning; now positioned for "explainable AI at the tactical edge" | "10X faster than traditional approaches" (product page). SensifyID SDK (2017 press release, not read) | Mobile SDK | Mobile and sensors; ZTBE is desktop keystrokes |
| ThreatMark, Callsign, others | Not researched in this round | — | — | — |

Observations:
- Vendors split into **RP-scoped fraud SDKs** (BioCatch, BehavioSec), which are server-side and multi-signal, and **endpoint continuous-auth agents** (TypingDNA ActiveLock, Twosense, Plurilock).
- None of the pages read publish FAR/FRR with confidence intervals, a threat model, or same-device impostor results.
- ZTBE's differentiators are protocol and governance, not accuracy:
  - signed device-bound bands;
  - challenge-bound proofs (A3);
  - SSF/CAEP;
  - no server-side behavioural data;
  - a published evaluation.

## 2. Open source

Searched GitHub on 2026-10-21 (`gh search repos`; stars and licence from the API).

| Repo | Stars | Licence | What it is |
|---|---|---|---|
| njanakiev/keystroke-biometrics | 41 | MIT | Notebook-style keystroke biometrics experiments |
| s3cur3/KeystrokeDynamics.JS | 37 | none | Browser proof of concept for login-time keystroke auth |
| DilshanSenarath/BehaveFormer | 26 | MIT | Research code (spatio-temporal transformer, behavioural biometrics) |
| vmonaco/kboc, vmonaco/pohmm-keystroke | 12 / 8 | BSD-3 | Competition and research code (KBOC; POHMM) |
| BiDAlab/TypeNet | 7 | none | TypeNet research code |
| geeknik/sigint | 3 | CC-BY-SA-4.0 | "A keystroke dynamics biometric dead man's switch for Linux" (evdev; design stage per its README summary) |
| jayadevgh/KeyGuard | 5 | none | Local continuous verification prototype |

**Finding.** There is no maintained open-source continuous keystroke authentication *system* (agent + protocol + RP integration). What exists is research code and demos. An open ZTBE reference implementation would be new. Licences matter for reuse: several repos have none, so no reuse rights.

## 3. Desk-level prior-art / patent note — NOT LEGAL ADVICE

This is a quick look by a research assistant at a handful of documents found on Google Patents and the USPTO Official Gazette. It is **not** a freedom-to-operate (FTO) analysis, not a validity or infringement opinion, and not legal advice. Patent claims must be read in full by a qualified patent attorney. **Recommendation: engage patent counsel for an FTO search before any commercial release.** Status data comes from Google Patents, which says it "has not performed a legal analysis".

| Number | Title | Assignee (as listed) | Priority / grant | Status (Google Patents) | Why it is relevant |
|---|---|---|---|---|---|
| US 10,289,819 B2 | Active authentication of users | Kryptowire (A2 Labs) | Prov. 2015-08-12; granted 2019-05-14 | Active | Continuous authentication with enforcement after "a pre-defined number of deviations within a pre-defined time window". Claim 1 is tied to touch, accelerometer, gyroscope, application context and **power** measurements |
| US 12,248,544 B2 | User authentication based on biometric data | Hewlett-Packard Development Co. | PCT filed 2020-02-20; issued 2025-03-11 (Official Gazette) | Granted | Claim 1: keystroke/mouse behavioural comparison, then on failure a **physiological** biometric check before mitigation (e.g. lock). ZTBE falls back to WebAuthn, not a physiological biometric |
| US 11,914,690 B2 | Systems and methods for using typing characteristics for authentication | TypingDNA Inc. | Prov. 2021-02-08; granted 2024-02-27; adj. expiry 2042-04-08 | Active | Login-time typing of risk-chosen reference text, then an in-page OTP. ZTBE does not prompt for text |
| US 11,630,893 B2 | (title not recorded in review round 1) | BioCatch | — | — | Verified assigned to BioCatch (review round 1). BioCatch claims 84 patents (2022) |
| US 2015/0169854 A1 | Capturing cognitive fingerprints from keystroke dynamics for active authentication | Iowa State University Research Foundation | Filed 2013-12-16 | **Abandoned** (2017-01-25, failure to respond to office action) | Word-level digraph features for active authentication. Abandoned, so published prior art |
| US 5,229,764 A | Continuous biometric authentication matrix | Matchett, Noel D. | Priority 1991-06-20; published 1993-07-20 | Not checked. Expired by term is likely (filed 1991) but **UNVERIFIED** | Early continuous-biometric prior art |
| US 2014/0250523 A1 | Continuous Authentication, and Methods, Systems, and Software Therefor | Carnegie Mellon University | Priority 2012-10-11; published 2014-09-04 | UNVERIFIED | Listed as a citation on Google Patents; not read |
| US 2020/0358787 A1 | Access Control Authentication Scheme Based On Continuous Authentication | IBM | Priority 2019-05-08; published 2020-11-12 | UNVERIFIED | Continuous auth driving access control. Listed as a citation; not read |
| US 2016/0259924 A1 | System and method for behavioural biometric authentication using program modelling | Zighra Inc. | Priority 2015-03-03 | UNVERIFIED | Listed as a citation; not read |
| US 12,314,361 B2 | Identifying users based on typing behavior | Citrix Systems | Priority 2021-10-07; published 2025-05-27 | UNVERIFIED | Listed as a citing document; not read. Possibly relevant to VDI |
| US 8,230,232 B2 | System and method for determining a computer user profile from a motion-based input device | Plurilock (per a PRWeb press release; patent record not opened) | UNVERIFIED | UNVERIFIED | Mouse-based profiling |

Desk-level observations (for counsel, not conclusions):
1. The general idea of continuous behavioural authentication triggering re-authentication is old: it is in 1990s–2010s publications and the academic literature (e.g. bours2015perf, mondal2015ins), and several applications are abandoned or expired. Claims in force tend to be narrow combinations: specific sensor sets, OTP flows, fallback modalities.
2. Areas where ZTBE should ask counsel specifically:
   - device-sealed templates with signed risk bands;
   - RP-challenge-bound behavioural proofs;
   - CAEP emission of behavioural risk;
   - per-keyboard templates;
   - injected-input classification.

   We found no document claiming exactly these, but we searched for under an hour, so this means nothing legally.
3. BioCatch (84+ patents), Plurilock, TypingDNA, Zighra, HP, IBM and Citrix all hold or held filings in adjacent space. A professional FTO search should cover at least their portfolios, plus CPC G06F 21/316 ("authentication by observing the pattern of computer usage").
