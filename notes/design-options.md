# ZTBE design options: comparison with evidence (phase 2)

Date: 2026-10-21. Inputs:
- measurements in `notes/experiments-v2.md` (open data, Eberz-style protocol) and `experiments/go-he` (Go crypto costs);
- sources in `references/bibliography.md` (B.10–B.14 are new).

Levels used for sources: **A** = abstract read, **F** = full text read, **M** = metadata only. A claim marked UNVERIFIED has no checked source.

## 0. The constraint everything else follows from

Measured on open data, with the attacker holding a dictionary of templates from disjoint population users and making greedy max-coverage guesses (`experiments/opendata/evallib.py: greedy_guessing`):

| Setting | Success with 1 guess at the verifier's own threshold | −log2 P1 (upper estimate of fuzzy min-entropy) | Guesses for 50% success |
|---|---|---|---|
| Aalto, 200-keystroke windows, unprotected scaled-Manhattan, FAR=1% threshold | 0.108 | 3.2 bits | 45 |
| Same, LDA-16 + LSSC S=8 (112-bit binary template), FAR=1% | 0.064 | 4.0 bits | 44 |
| Same, at the EER threshold | 0.27–0.37 | 1.4–2.0 bits | 2–4 |

All other datasets and window lengths are within the same few-bit range (see `experiments-v2.md` §6).

These are **upper** estimates: a larger dictionary or a smarter attacker only lowers them. Phase 1 (R2, R3) reached the same conclusion analytically.

Consequences:
1. Any design whose security against an *offline* attacker rests on the secrecy or entropy of the behavioural input gives about **2–4 bits**. Keyless fuzzy extractors, fuzzy commitment, sample-then-lock without a key, fuzzy vaults and Fuzzy PAKE (dupont2018fpake) are all bounded by the same input entropy.
2. All real security must come from **keys**: device-bound, server/HSM-held, or split between parties. The behavioural signal contributes only an *online* FAR at a rate-limited verifier.
3. At realistic operating points (FRR@FAR1% is 20–50% per window, `experiments-v2.md` §4), the behavioural score is a **risk signal**, not an authenticator. NIST SP 800-63B-4 says the same in two places (nist80063b4, F):
   - Its biometric definition explicitly includes keystroke patterns and mouse movements, which must meet FMR ≤ 1/10000 and be used only together with a physical authenticator.
   - Fraud/risk indicators "do not … substitute for an authentication factor".

   FIDO biometric certification needs a lab FAR of 1% at FRR 7%, or 0.01% at FRR 5% (fidobio, A). ZTBE windows are nowhere near either point.

## 1. Attackers

| ID | Attacker | Capabilities |
|---|---|---|
| A1 | DB dump | Copy of server storage (templates, helper data, ciphertexts, logs). No keys held in HSM or KMS, and no runtime memory. |
| A2 | Server compromise | Code execution on the verifier. Sees runtime memory and probes, can call HSM APIs, but cannot export HSM keys. |
| A3 | Insider / operator | Read access to data and dashboards. Can run queries and may call internal APIs. A3 is weaker than A2 but persistent. |
| A4 | Verification oracle | Submits chosen probes (synthetic feature vectors) and observes accept/reject, or a score. This covers centre-search (pagnin2014), hill-climbing, and population-dictionary guessing (§0). |
| A5 | Endpoint compromise | Malware on the user's device. Can inject synthetic input (antal2021sapiagent, serwadda2013), read process memory, and tamper with the agent. |
| A6 | Physical impostor | Uses the unlocked session at the keyboard: zero-effort, or mimicry (tey2013). |
| A7 | Poisoner | A6 or A5 over time: steers template adaptation toward themselves (biggio2012, biggio2015spm). |

## 2. Options

Throughout, "behavioural template" means the per-user model: the mean and spread of 36 content-blind features, or an LDA-16 projection of them.

### O0 Keyless fuzzy extractor / fuzzy commitment / sample-then-lock (spec v1). **Reject.**

- **Model:** helper data is public, and the key is extracted from the behaviour.
- **Measured:**
  - Sample-then-lock on the best binary template (LDA-16 LSSC, n=112): k=24 gives FRR 7.6% and FAR 7.6% (Aalto n200).
  - One population-mode guess opens at least one of 1500 lockers for 52% of users (k=24) and 15% of users (k=32, where FRR is 30.5%).
  - Offline guessing at the FAR=1% threshold gives ≤ 4 bits (§0).
- **Verdict:** A1 recovers the key or template almost immediately. No parameter choice fixes this (phase-1 R2/R3, now measured).

### O1 Plain template, encrypted at rest under a server KMS/HSM key (envelope encryption)

- **Model:** confidentiality rests on the KMS key, and matching happens in plaintext inside the verifier.
- **Protection by attacker:**
  - A1: protected, if the KMS is separate.
  - A2: not protected. Templates are decrypted for every match.
  - A3: partly protected by access control and audit.
  - A4: protected only by rate limits and by returning accept/reject without a score.
- **Cost:** about 1.7 KB per user sealed (36 features × (μ, σ) + 4 anchors, float64, AES-GCM). Sealing plus opening takes 1.5 µs and scoring 0.3 µs (go-he `plain_test.go`).
- **ISO 24745:** confidentiality yes, integrity yes (AEAD). Irreversibility no. Unlinkability across services only through separate keys and feature normalisation. Renewability: re-keying does *not* renew the biometric.
- **GDPR:** a central biometric database with Art. 9 implications (gdpr2016, ico-biometric).
- **Go:** stdlib `crypto/aes` and `crypto/cipher`; `tink-go` for envelope encryption and KMS.
- **Verdict:** a baseline only. Use it for the *server-side escrow* in O7, not as the main path.

### O2 Keyed transform / BioHashing with a secret token, "done right"

- **Model:** a per-user secret seed S defines a transform, such as a random orthonormal projection or permutation followed by LSSC quantisation, or PolyProtect for embeddings (hahn2022polyprotect). Only the transformed template is stored.
  - "Done right" means S is **non-exportable**: it lives in a TPM, Secure Enclave or HSM and is applied inside it, or it is derived by OPRF from an HSM key (rfc9497).
  - S is rotated on revocation, and accuracy is reported **under the stolen-token assumption** (teoh2008, kong2006, lacharme2013).
- **What the data says:**
  - The transform costs little accuracy. LDA-16 LSSC S=8 is effectively a population projection plus thermometer code, with EER 5.7% against 8.6% unprotected (Aalto n200).
  - Under a stolen token, though, the protection is gone. Linear transforms with output dimension ≥ 36 are invertible, and the guessing results in §0 apply directly to the transformed domain (4.0 bits).
- **Protection by attacker:**
  - A1: protected only while S stays secret.
  - A2: if S is in the HSM, A2 becomes an online oracle; otherwise it gets everything.
  - A3: like A2.
  - A4: not protected beyond FAR and rate limits.
- **ISO 24745:** renewability and unlinkability come from S. Irreversibility **only** while S stays secret. The standard's own framing treats this as a keyed scheme.
- **Go:** stdlib, plus go-tpm or a cloud KMS for S. No library is needed for the transform itself (about 50 lines).
- **Verdict:** this buys renewability and unlinkability cheaply. Use it *inside* O7 so the device-stored template is renewable and differs per relying party. It is not a security boundary on its own.

### O3 Server pepper via OPRF/HSM (Pythia-style) + sample-then-lock ("keyed FE")

- **Model:**
  - Locker keys are derived as `OPRF_k(subset bits)`, where the OPRF key k lives in an HSM or rate-limited service (everspaugh2015, rfc9497).
  - Offline brute force needs k. The server sees only blinded inputs and learns nothing about the bits.
  - The client opens lockers locally and proves possession of the recovered key, for example by signing a challenge.
- **Protection by attacker:**
  - A1: protected (lockers are useless without k).
  - A2/A3 with HSM-only access: reduced to an online oracle limited by the HSM rate limit.
  - A2 that extracts k: back to O0 (≤ 4 bits).
  - A4: the online FAR of the locker scheme. Measured at k=24 it is **7.6% per verification**.
- **Cost:** each verification needs ℓ OPRF evaluations. With ℓ=1500 (the operating point measured in O0), that is about 74 ms of server CPU (49 µs each) and about 255 ms of client CPU (170 µs per round trip, excluding network). One verification per user every 2 minutes is about 0.06% of a core per user. ℓ can be reduced, but that raises FRR.
- **Storage:** about 1500 lockers × (nonce + ciphertext); with 32-byte lockers plus a 16-byte nonce that is about 72 KB per user (inferred, not measured).
- **ISO 24745:** renewable by rotating k. Irreversible while k is secret.
- **Go:** circl `oprf` (ristretto255; the package warns that the P-256 server ops are not constant-time); `crypto/hkdf`.
- **Verdict:** sound cryptography, but **accuracy is worse than O7** and the cost is higher. It only beats O1 against A2-passive and A3. Keep it as an option if a server-side "the server never sees behavioural data" claim is mandatory *and* no device keys are available.

### O4 Homomorphic-encryption matching (CKKS / BGV / BFV, lattigo)

- **Model:**
  - Templates are stored as `Enc_pk(μ, √w)`. The probe arrives encrypted.
  - The server computes `Enc(Σ w(x−μ)²)` (CKKS), or Hamming distance on bits (BGV); see boddeti2018, kolberg2019, bassit2021, safa2014, sedenka2015.
  - Someone must hold sk:
    - **client holds sk:** the client learns the score and decides. The server must then trust the client, which makes this equivalent to O7 with extra cost.
    - **separate decryptor (HSM or threshold, mouchet2021) returns only the decision:** this is the meaningful variant.
- **Measured (lattigo v6.2.0, N=2^13, 128-bit per hestd2018):**

  | Operation or object | Cost |
  |---|---|
  | Client encrypt | 3.3 ms |
  | Server distance | 9.8 ms |
  | Decrypt | 0.3 ms |
  | Probe ciphertext | 393 KB |
  | Stored template (unpacked) | 787 KB per user |
  | Evaluation keys per key-holder | 12.6 MB |
  | BGV Hamming distance over 256 bits | 13.2 ms |

  Packing 64 users per ciphertext should bring templates to about 12 KB per user (inferred, not measured). For continuous use, one probe per minute is about 6.5 KB/s of upload per user.
- **Protection by attacker:**
  - A1: protected.
  - A3 without decryptor access: protected.
  - A2 that owns the evaluator only: protected. A2 that owns the decryptor: everything.
  - A4 is **not** solved by HE:
    - If the score is ever revealed, centre search recovers the template in O(n) queries (pagnin2014, A).
    - Revealing CKKS decryptions allows key recovery (li2021ckks, A: IND-CPA^D).
    - Required mitigations: return only a thresholded bit computed under encryption (BGV comparison or a polynomial sign approximation, which costs more depth), add noise or flooding, and rate-limit. Malicious-client security adds ZK proofs; bassit2021 reports 0.95–2.50 s.
- **ISO 24745:** confidentiality, irreversibility (computational) and renewability (re-encrypt under new keys) all hold while sk is protected. HE as a protection method for ISO 24745 is UNVERIFIED: the standard text is paywalled and was not read.
- **GDPR:** the data is still biometric personal data, but encrypted. This is a strong Art. 25/32 argument.
- **Go:** lattigo (Apache-2.0, pure Go, includes multiparty).
- **Verdict:** feasible in Go at these sizes. It is the right tool **if the business requires server-side matching** (for example, roaming users without a trusted device). It is not the MVP, because it adds a decryptor service, bandwidth, and the oracle problem without improving accuracy.

### O5 Two-party computation / garbled circuits (Yao, GMW, ABY)

- **Model:** client and server jointly compute `[dist < τ]`. Neither sees the other's input (yao1986, erkin2009, sadeghi2009, osadchy2010, blanton2011, chun2014, bringer2013spm).
- **Protection:** like O4, with no long-term decryptor. Both A1 and A2 see only the server's share or the template, depending on design.
- **Cost:** several rounds and MB-scale communication per comparison (literature, not measured here). The best toolkits are C++ (ABY, demmler2015aby). In Go there is markkurossi/mpc (MIT, research grade).
- **Verdict:** not for the MVP. No production-grade Go stack exists, and the oracle problem remains.

### O6 Learned embedding + protected template

- **Model:** a population-trained encoder maps windows to a d-dimensional embedding (TypeNet, TypeFormer, KVC: stragapede2024kvc). The embedding is protected with O2, O4 or O7.
- **Measured proxy:** a population-trained LDA-16 is the cheapest possible embedding. It lowers EER from 8.6% to 6.4% (Aalto n200), and FRR@FAR1% from 40.5% to 20.9%. It did *not* help on Tappy with Aalto priors, because of domain shift (`experiments-v2.md` §4).
- **Entropy:** the embedding does not raise the guessing bound: 4.0 bits for LDA-LSSC (§0).
- **Verdict:** an accuracy lever, not a security lever. Plan for it from M3 onwards, with priors and encoder trained **in-domain**.

### O7 On-device verification, device-bound key, server sees only attested assertions. **Recommended core.**

- **Model:**
  - The template is sealed with a non-exportable device key: a TPM 2.0 key sealed to the agent's measured state where available, or the OS keystore otherwise.
  - Scoring and adaptation run locally.
  - The server receives short signed assertions (risk band, window count, model version, monotonic counter, nonce), signed by a device key whose provenance is established once with WebAuthn/TPM attestation (webauthn3, rfc9334, coker2011).
  - This is NIST's preferred local comparison (nist80063b4: "comparison SHOULD be performed locally").
- **Protection by attacker:**
  - A1, A2, A3: **no behavioural data on the server**. They can forge decisions for their own server, which gives them nothing.
  - A4: the oracle is local. Mitigate with in-agent rate limits, accept/reject-only output, and no score API.
  - A5: **not protected** in general. Malware can inject synthetic input or read the unsealed template.
    - Partial mitigations: TPM PCR-bound sealing, signed agent, hardware input-source checks where the OS exposes them.
    - Honest claim: ZTBE does not defend against a compromised endpoint.
  - A6: online FAR at the chosen threshold, fused over several windows.
  - A7: the adaptation policy in §4.
- **Cost:** 1.7 KB sealed template, sub-microsecond scoring, one signature per assertion. Assertions are about 200 B per window (inferred).
- **ISO 24745:**
  - Confidentiality: yes (sealed).
  - Integrity: yes (AEAD plus counter).
  - Renewability and unlinkability: yes, with an O2 transform keyed per relying party inside the sealed blob.
  - Irreversibility: **no**, the plaintext template exists inside the device.
- **GDPR:** data minimisation and no central biometric store. Still Art. 9 processing on the device, with a DPIA needed (gdpr2016, wp193).
- **Go:** go-tpm, go-tpm-tools, go-attestation (Apache-2.0); go-webauthn (BSD-3); go-keyring / go-keychain (MIT); memguard (Apache-2.0); gohook (MIT, cgo).

### O8 Threshold / multi-party variants

- **Model:** split the HE decryption key (lattigo multiparty, mouchet2021) or the OPRF key across two operators. A2 must then compromise both.
- **Verdict:** a hardening step for O3/O4 if those are ever needed. It does not change the entropy bound or the oracle problem.

## 3. Comparison matrix

Columns A1–A7 are the attackers from §1. ✓ = protected, ◐ = partial or conditional, ✗ = not protected. Latency is measured on this box (Go 1.27.2, 1 goroutine) unless marked "inf." (inferred).

| | A1 dump | A2 server | A3 insider | A4 oracle | A5 endpoint | A7 poison | Storage/user | Verify latency | ISO 24745 C/I/Irr/Ren/Unl | GDPR | Go libs | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O0 keyless FE | ✗ (≤4 bits) | ✗ | ✗ | ✗ | ✗ | – | ~72 KB (inf.) | µs–ms | weak (no real Irr) | central biometric | stdlib | **reject** |
| O1 encrypted at rest | ✓ (KMS separate) | ✗ | ◐ | ◐ rate limit | ✗ | policy | 1.7 KB | 2 µs | C,I only | central biometric | stdlib, tink-go | escrow only |
| O2 keyed transform | ◐ (token secret) | ◐ (HSM) | ◐ | ◐ | ✗ | policy | ~1–2 KB | µs | Ren/Unl; Irr only with secret token | central or device | stdlib, go-tpm | use inside O7 |
| O3 OPRF + lockers | ✓ | ◐ (HSM oracle) | ✓ | ◐ (FAR 7.6% @k=24) | ✗ | re-Gen | ~72 KB (inf.) | ~74 ms server + ~255 ms client per verification, plus network | C,I,Irr(keyed),Ren | server never sees bits | circl | fallback if no device keys |
| O4 HE (CKKS/BGV) | ✓ | ◐ (if decryptor separate) | ✓ | ◐ (bit-only output needed) | ✗ | policy (encrypted update is costly) | 787 KB (12 KB packed, inf.) | 3.3 + 9.8 + 0.3 ms, 393 KB up | C,I,Irr(comp.),Ren | encrypted central | lattigo | when server-side matching is required |
| O5 2PC/GC | ✓ | ◐ | ✓ | ◐ | ✗ | policy | template on one side | multi-round, MB (lit.) | C,I,Irr | | markkurossi/mpc (research) | no |
| O6 embedding | n/a: accuracy lever | | | | | | | | | | | from M3 |
| **O7 on-device + attest** | **✓ (nothing stored)** | **✓** | **✓** | ◐ local rate limit | ✗ | §4 policy | 1.7 KB device, ~0 server | <10 µs + sign | C,I,Ren,Unl; **no Irr** | minimised | go-tpm, go-attestation, go-webauthn, memguard | **recommend** |
| O8 threshold | hardening for O3/O4 | | | | | | | | | | lattigo multiparty | later |

## 4. Drift adaptation and anti-poisoning (re-evaluated for O7)

**Setup.** Measured on Tappy: 75 users with ≥ 28 days of data; 200-keystroke windows; enrolment in week 1; global threshold at the week-2 EER (`results/adapt_n200.txt`).

**Policies:**
- **naive:** update on every accepted window.
- **gated:** update only if score ≤ median genuine score (the spec's §6.1 dual threshold; self-update thresholds are analysed in didaci2014).
- **anchor:** reject an update that moves μ more than r_anchor from enrolment (uludag2004 multi-template idea, reduced to one anchor).
- **velocity:** at most r_anchor/14 of movement per day.
- **sanitize:** if the last 10 updates are consistently aligned (mean cosine to their sum > 0.5), roll back to the checkpoint and freeze updates for 200 windows (biggio2015spm's sanitization, with a freeze added).
- The attack is a perfect-knowledge boundary walk (biggio2012/2015): 50 windows per day, each just inside the update gate, aimed at the attacker's mean.

| Policy | FRR wk8, pooled [per-user mean] | Takeover after 1 / 7 / 28 days of attack | Victim FRR after a 28-day attack (per-user mean) |
|---|---|---|---|
| static | 10.9% [30.2%] | 8.0 / 8.0 / 8.0% (= no-attack baseline of 8.0%) | 24.1% |
| naive | **7.4% [21.7%]** | **65 / 83 / 83%** | 91% |
| gated | 10.9% [29.5%] | 65 / 83 / 83% | 91% |
| gated+anchor | 10.9% [29.5%] | 33 / 33 / 33% | 58% |
| gated+anchor+velocity | 11.3% [29.2%] | 9 / 15 / 33% | 58% |
| gated+anchor+velocity+sanitize | 11.0% [29.1%] | **9 / 14 / 9%** | 24% |

**Findings:**
1. **Gating alone does not stop poisoning.** The boundary walk stays inside any gate. The spec's dual threshold (§6.1) gives the same 83% takeover as naive updating. This is the biggio2012/2015 result, now reproduced on keystroke data.
2. An anchor bounds the damage but leaves 33% takeover and turns the attack into a denial-of-service on the victim (58% FRR).
3. A velocity limit only delays the attack. Sanitization with rollback to a checkpoint plus a freeze is what brings takeover back to the no-attack baseline (9%) and victim FRR back to baseline (24%).
4. The benefit of unsupervised self-update in this data is **small**:
   - In pooled terms, the week-8 FRR goes from 10.9% to 7.4% with naive updating, and the gated policies give almost nothing.
   - The macro FRR (per-user mean) is far higher than the pooled FRR: Gini of per-user FRR is 0.8–0.9 in every run. A minority of users dominate errors, which matches eberz2017.

**Recommendation for O7:**
- Make **supervised** updates the default: update only from windows in sessions that passed a strong step-up (WebAuthn) within the last *T* minutes. Supervised updates get naive-like gains (the naive genuine replay is their upper bound) without A7 exposure.
- Keep gated+anchor+velocity+sanitize as defence in depth for unsupervised updates, if they are enabled at all.
- On rollback, raise an alert, because the event is evidence of A6/A7.
- Enforce NIST's "limit on the allowable time for adaptation" (nist80063b4): re-enrol after N days without a strong-auth checkpoint.
- Per-user thresholds are needed for the high-FRR minority. Fixing them is a policy choice; see PROPOSAL §9.

## 5. Regulatory fit (summary, not legal advice)

- **GDPR:** keystroke/mouse templates are biometric data under Art. 4(14). Art. 9 applies when the processing is "for the purpose of uniquely identifying". The ICO reads 1:1 verification as included (phase-1 B.9). O7 minimises: no central store, local processing, and erasure of raw events after feature extraction.
- **NIST SP 800-63B-4** (F):
  - ZTBE's score can only be a fraud indicator or a session-continuity signal. It is never an AAL factor.
  - If it ever gates a step-up decision, alternative non-biometric options must exist.
  - Adaptation must be time-limited.
- **EU AI Act** (euaiact2024, A):
  - Pure 1:1 verification is excluded from Annex III(1)(a).
  - **Annex III(4)(b)** lists AI used "to monitor and evaluate the performance and behaviour of persons" in employment. A workforce deployment of continuous behavioural monitoring could fall there. Hossein needs a legal opinion on intended use.
  - The engine's outputs must not be repurposed for productivity monitoring.
- **ISO/IEC 24745:2022** (A1, paywalled; requirements known from the abstract and summaries only): O7 meets confidentiality, integrity and renewability. It does **not** provide irreversibility on-device, and the documentation must say so.
