# ZTBE spec v1.0.0-draft: critical review

Pass 1, 2026-10-21. Reviewed against `spec/ZTBE-spec-v1.0.0-draft.md`. Citation keys refer to `references/bibliography.md`.

Every number below comes from code in `experiments/`, cited as [S§k] (`sanity/output.txt` section k), [CMU] (`cmu-quantization/results.txt`, `baseline-results.txt`) and [GO] (`go-bench/results.txt`).

Severity: **S1** breaks a stated guarantee or requirement. **S2** is a wrong claim or formula, fixable. **S3** is a minor or editorial issue.

---

## 0. Summary of findings

| # | Sev | Spec § | Finding |
|---|---|---|---|
| R1 | S1 | NFR-04, §5.4, §5.3, §7.1 | Storage target of ≤2 KB per user is contradicted by every recommended backend. |
| R2 | S1 | §4.3-B, §7.1 | Sample-then-lock with k_sub=32 caps offline security at ≤2^32 work per locker, about 2 core-hours. "H∞(W\|T) ≥ 80 bits" does not hold. |
| R3 | S1 | §4.3-A, §8.2 | Under the spec's own entropy estimate (20–45 bits), the Architecture A bound β−(n−k) is negative. The "information-theoretically impossible to reverse" conclusion does not follow. |
| R4 | S1 | §5.1 (Arch A), §5.2 | Both the in-place syndrome update and re-Gen with code-offset leak the exact drift vector Δw. The "re-blind" term is a no-op. |
| R5 | S1 | §4.3-C, §5.3, FR-04, FR-07 | Architecture C is not irreversible or unlinkable as claimed. It uses the sign-LSH that §4.1 rejects, it has a trivial accepting pre-image, and published attacks apply. |
| R6 | S1 | §4.2, §4.3-B, §6 | On real keystroke data, cross-session BER is 0.30–0.40, not 15–25%. With t_verify=0.18n, FRR is 41–100%. |
| R7 | S2 | §4.3-B | The FRR "bound" runs the wrong direction. It is ~4× optimistic at the spec's own example. |
| R8 | S2 | §4.2 | The Gray code wraps around, so "only 1 bit flips for adjacent bins" does not bound the error. Distant bins can also be 1 bit apart. |
| R9 | S2 | §6.1–6.3 | Anchor tolerance 0.243n is infeasible for sample-then-lock, needing ~68k lockers. Anchor plus working-template tolerance admits probes up to 0.423n from the anchor, where 8–38% of impostors fall. |
| R10 | S2 | FR-05, §4.3-A | Publishing S_trust (or wt(ê)) creates a hill-climbing oracle. |
| R11 | S2 | §4.2 | The "FDR" is not Fisher's ratio. The reliability mask is user-specific helper data that leaks. |
| R12 | S2 | §9, §4.3-B, §8.2 | Citation errors (see `references/bibliography.md` Part A). |
| R13 | S2 | §7.2 | Four FOSS licences are wrong, one project is not open source, and one repo is archived. |
| R14 | S3 | NFR-01..03 | Latency and CPU are feasible in Go. Session RAM ≤4 KB is borderline. A 15 MB daemon is unlikely with Python/River. |

Correct as written (verified): the EW-Welford recursion (§3.2) [S§6]; burstiness B=(σ−μ)/(σ+μ) (goh2008; the spec should cite it); the navigation entropy-rate formula (§3.1-3); the Bloom pre-image formula, which is the number of surjections N_b→|BF| [S§4]; the Bloom dissimilarity D_BF, which matches the Rathgeb-style score; and the spec's arithmetic 0.85^32 = 0.00551, e^−8.28 = 2.5·10^−4 [S§1].

---

## R1. Storage contradiction (S1)

NFR-04 requires ≤2 KB per user profile.

- **Architecture B.** Each locker stores I_i (32 indices × 9 bits = 36 B, or 0 B if derived from a seed), a nonce, and c_i (λ+γ bits). Measured sizes [GO, TestStorage]:
  - ℓ=1000: 117 KiB with explicit indices, 54.7 KiB nonce-only, 39.1 KiB minimal.
  - ℓ=1500: 58.6 KiB minimal.
  - The spec's own §5.4 gives 24–48 KB.
- **Architecture C.** The CBF is 32×256×4 bit = 4096 B [S§5]. The spec's §5.4 says "2–4 KB".
- **Hybrid (§5.4 recommendation, §7.1).** CBF + lockers + anchor FE comes to ≥ 28 KiB, and ≥ 60 KiB at the spec's ℓ=1500.
- **Architecture A, "128-byte syndrome" (§5.4).** 1024 bits is more than n=512. For n=511 the syndrome has at most 511 bits (64 B). At 15% BER, BCH(511,76) has a 435-bit (54 B) syndrome [S§2].

**Fix.** Either relax NFR-04 to about 64 KiB, or derive I_i and nonce_i from a per-user seed with a PRF and use a short tag (γ≈32 bits). Lockers then shrink to (λ+γ)/8 B each, which is still ≥ 39 KiB at ℓ=1000.

## R2. Architecture B security is capped by k_sub (S1)

Each locker is an independent offline target. An attacker who brute-forces the k_sub=32 bits of v_i for a single locker recovers R. The cost is ≤ 2^32 × 1.56 µs ≈ 6.7·10³ core-seconds, about 1.9 core-hours (1.56 µs/locker from an earlier bench run; the committed run gives 1.78 µs, i.e. ~2.1 core-hours), and much less if v_i is predictable from a population prior [S§1b].

So the scheme's strength is at most the **minimum over lockers of H∞(W_I)**, which is ≤ k_sub = 32 bits. This is exactly the correction Shukla et al. make to Canetti et al.'s analysis (shukla2025, A-level). It does not reach 80 bits, so the §7.1 claim "H∞(W\|T) ≥ 80 bits" is unsupported for Architecture B. On iris, Shukla et al. need careful subset selection and a large ℓ to reach 105 bits, and iris has far more degrees of freedom than keystrokes (Daugman DoF 9–89 on CMU [CMU]; the iris figure in daugman2006 is in the hundreds, exact value not re-checked: UNVERIFIED).

The spec's §8.2 Argon2id idea cannot close the gap. A 20 ms Rep budget over ℓ=1500 lockers leaves 13.3 µs per locker [S§1b], which is not memory-hard. A per-locker cost c raises attack cost and genuine cost equally.

**Options**
- Raise k_sub and use reliability-selected bits (Shukla et al.). This is impossible at the measured BER (R6).
- Use a second factor, or a device-held secret mixed into the locker key (this is no longer a pure fuzzy extractor).
- Rate-limit by keeping lockers server-side and online-only. The threat model then changes from "DB dump" to "online".

## R3. Architecture A bound is vacuous (S1)

The leftover-entropy bound is H̃∞(W\|P) ≥ β − (n−k). For BCH codes at n=511, the minimum β for 80-bit residual security [S§2]:

| BER | t | code | β needed |
|---|---|---|---|
| 5% | 26 | BCH(511,295) | ≥ 296 |
| 15% | 77 | BCH(511,76) | ≥ 515 |
| 18% | 92 | BCH(511,49) | ≥ 542 |

The spec itself estimates β ≈ 20–45 bits (§8.2). Then β−(n−k) < 0 and the bound says nothing.

"2^k pre-images exist" is not irreversibility either. The pre-images are not equiprobable under W, and the attacker needs only the likely one (ignatenko2010; fuller2020when). The correct measure is fuzzy min-entropy (fuller2020when). For efficient information-theoretic schemes there are negative results (fuller2024impossible).

Smaller points:
- "Gilbert-Varshamov and Plotkin bounds degrade k/n" (§4.3-B): GV is an existence (lower) bound. The relevant limits are Hamming/MRRW upper bounds and decoder capability. The practical point stands: at 25% BER, BCH(511,·) has k=1.
- "Polar code" is listed, but a bounded-distance syndrome decoder with a guaranteed t is not standard for polar codes. Drop it or justify it.

## R4. Update leakage in §5.1 (Arch A) and §5.2 (S1)

- **§5.2.** P^(t+1) ⊕ P^(t) = H·Δw^T. The "re-blind" term H·c^T is zero by definition, so the "fix" does nothing. With wt(Δw) ≤ t, decoding the difference gives Δw exactly. The spec concedes this in its caveat.
- **§5.1 with code-offset.** Re-Gen with a *fresh* codeword also leaks: (w⊕c₁)⊕(w'⊕c₂) = (w⊕w')⊕(c₁⊕c₂), which decodes to w⊕w' when d_H(w,w') ≤ t. This is the decodability attack (kelkboom2011). Demo on BCH(31,16,t=3): drift vector recovered 1000/1000 for the syndrome form and 1000/1000 for code-offset with fresh c [S§7].
- **"Keyed permutation" mitigation.** The key must be secret from the DB attacker, which turns the scheme into a keyed (cancelable) system and adds a key-custody problem (§8.2 Q2). Kelkboom 2011 analyses bit permutation as a countermeasure, and blanton2013 analyses reusability of sketches in general. Cite them, and state that the security model is no longer information-theoretic.
- **§5.4** says Approach 2 is "Information-Theoretic (Single Enrollment)". By definition, it has more than one enrolment.

## R5. Architecture C (S1)

1. **It is LSH.** b_i = 𝟙((Q_K z̃)_i ≥ 0) is exactly the sign-random-projection that §4.1 forbids as a terminal template. Its security therefore rests entirely on K_app staying secret. Known-token pre-image attacks exist (lacharme2013), and accuracy collapses in the stolen-token case (kong2006).
2. **The math does not fit.** An orthonormal Q ∈ ℝ^{n×D} with n > D cannot exist, since at most D orthonormal rows exist in ℝ^D. With n ≫ D (e.g., 2048 bits from D≈60), the bits are highly correlated, and so is the effective entropy.
3. **Irreversibility argument.**
   - The pre-image count is correct but irrelevant. Verification is order-invariant, so *any* column sequence that covers the set bits of BF_r yields an exactly matching template. An attacker who holds BF builds an accepting binary template in O(N_b) per block, with no search [S§4].
   - Recovering z̃ is then a sign-LSH inversion given K_app (§4.1's own argument).
   - Published attacks:
     - hermans2014: unlinkability broken with ≥96% success in the worst case, plus key recovery.
     - bringer2015 / bringer2017: irreversibility attacks that exploit non-uniform data.
     - gomezbarrero2018tifs: the original XOR-based "unlinkability" is linkable through linearity.
4. **The counting BF leaks more.** Four-bit counters reveal visit frequencies per slot, not just set membership. Over successive DB snapshots, the deltas expose which slots the user hit in each verified window, which is a per-window leak. The §5.3 argument ("collisions from N_b columns") does not account for this.
5. **Citation.** "Rathgeb et al. (2014)" is ICB 2013 (rathgeb2013icb), and it does not use BioHashing (§R12).

## R6. Measured error rates on CMU keystroke data (S1)

**Setup** (`experiments/cmu-quantization`): the spec's Stage-1 pipeline (population z-score, equiprobable Gaussian bins, Gray code, optional FDR mask) on killourhy2009.
- 51 subjects: 25 for population priors, 26 for evaluation.
- Enrol on session 1, probe on sessions 2–8.
- Windows of NW reps averaged.

| config | n | genuine BER (mean) | impostor BER | EER | FRR @ t=0.18n | FAR @ 0.423n |
|---|---|---|---|---|---|---|
| NW=10, μ+σ, m=1 | 62 | 0.322 | 0.491 | 22.4% | 90.8% | 28.2% |
| NW=10, μ, m=2 | 62 | 0.298 | 0.496 | 21.5% | 78.8% | 25.9% |
| NW=10, μ+σ, m=3 | 186 | 0.372 | 0.477 | 21.7% | 99.7% | 16.8% |
| NW=50, μ, FDR mask 16, m=1 | 16 | 0.152 | — | 17.2% | 41.2% | 34.4% |

- Unprotected scaled-Manhattan on the same split: **EER 21.4%** [CMU baseline]. So cross-session drift dominates, not the quantizer.
- Same-session BER: 0.159 (m=1) and 0.209 (m=2). Session 8 against session 1: **0.359 and 0.401** [CMU baseline]. The spec's "15–25%" holds only within a session.
- Gaussian bin edges give occupancy imbalance up to 0.52 (m=2). The "maximizes Shannon entropy" claim needs empirical (quantile) edges. Behavioural features are non-Gaussian, consistent with the BB-MAS report (belman2019).
- Sample-then-lock simulated on the bits (m=2, empirical edges, ℓ=1500):
  - k_sub=32: FRR 84–98%.
  - k_sub=8: FRR 1–4%, but FAR 64–90%.

  No operating point is both usable and secure.
- Daugman DoF of the impostor HD distribution is 9–89, depending on configuration. This is a rough upper bound on the entropy available to any binary template.

**Caveats.** CMU is fixed-text (one password), so free text will be noisier. Windows are averages of 10 or 50 repetitions, and there are 26 evaluation subjects. These numbers are indicative, not a ZTBE evaluation. Next steps: Clarkson II and Aalto, plus the Eberz et al. protocol (eberz2017).

## R7. FRR bound direction (S2)

The spec writes δ = (1−p)^ℓ ≤ exp(−ℓ(1−t/n)^k). This uses p ≈ (1−t/n)^k, but (1−t/n)^k > C(n−t,k)/C(n,k) (sampling without replacement), so the stated inequality runs the wrong way.

| t/n | ℓ | exact FRR | spec "bound" | lockers for FRR ≤ 1e-3 |
|---|---|---|---|---|
| 0.15 | 1500 | **1.09·10⁻³** | 2.56·10⁻⁴ | 1519 |
| 0.18 (= t_verify) | 1500 | **0.12** | 0.073 | 4879 |
| 0.243 (= t_anchor) | 1500 | **0.86** | 0.82 | 68,322 |

Values from [S§1]. A correct bound is δ ≤ exp(−ℓ·p) with the exact hypergeometric p.

Note also that the worked example uses t/n=0.15, while §6.1 sets t_verify=0.18n. At 0.18n the spec's ℓ gives a 12% FRR. The "<1.5 ms" figure is plausible: Go measured a worst-case Rep (all ℓ lockers tried) of 1.75 ms at ℓ=1000 and 2.66 ms at ℓ=1500 with HKDF-SHA256, and 1.81 ms at ℓ=1500 with HMAC-SHA256, on SHA-NI [GO].

## R8. Gray code wrap-around (S2)

The reflected Gray code is cyclic. For m=3, bins 0 and 7 (opposite tails) are at Hamming distance 1, and bins 0 and 3 are also at distance 1 [S§3].

- **Adjacent bins:** the "1 bit flips" claim is true.
- **Larger drift:** the error stays bounded by m bits per feature, but the Hamming distance stops being monotone in bin distance. An impostor several bins away can look close.

**Fix.** Use LSSC (lim2013lssc) or a thermometer/unary code, which costs more bits. Alternatively, use m=1 with DROBA-style bit allocation (chen2009droba).

## R9. Anti-poisoning envelope (S2)

From §6.1–6.3 [S§8]:
- t_adapt = 0.45–0.65 × 0.18n = 0.081–0.117n.
- t_anchor = 1.35 × 0.18n = 0.243n.
- The working template may sit anywhere within 0.243n of the anchor and accepts probes within 0.18n of itself. So a probe up to **0.423n** from the anchor can eventually be accepted. On CMU, 8–38% of impostor windows fall within 0.423n [CMU].
- V_max = 0.02n/day reaches 0.243n in about 13 days. A slow attacker (biggio2012; biggio2015spm move the centroid along the update boundary) is not stopped by clamping alone.
- **Feasibility.** As an Architecture B anchor, 0.243n needs about 68k lockers (R7), roughly 2.6 MiB minimal at 40 B each.
- The dual-threshold idea is already in biggio2012's model: the attacker is assumed to know the self-update threshold. The literature's countermeasure is **template sanitization**, which detects consistently biased drift and rolls back (biggio2015spm, F-level).
- **Recommendation:** add multi-template anchors (uludag2004), sanitization, and per-update provenance (session from a trusted device or MFA event).

## R10. Score oracle (S2)

FR-05 outputs S_trust ∈ [0,1], and §4.3-A defines it as 1 − wt(ê)/t. Any exposed graded score enables hill-climbing toward the template (galbally2010), and §4.1 already cites this risk.

**Recommendation:** expose only d ∈ {0,1} outside the TCB, and rate-limit attempts. If a continuous score is needed for UX, coarsen it to 2–3 levels and keep it server-side.

## R11. Reliability mask and "FDR" (S2)

(μ_u − μ_pop)²/σ_u² is a per-user signal-to-noise ratio, not Fisher's discriminant ratio (which uses between-class over within-class variance across classes).

M_rel is user-specific helper data stored in the clear. It leaks which features are distinctive for this user, and so it is linkable across databases (FR-07). Simoens et al. (simoens2009) and the masked-bit literature analyse this kind of leak.

**Recommendation:** use population-level bit allocation, or account for the mask in the entropy analysis (chen2009droba; kelkboom2010).

## R12. Citation errors (S2)

Full details are in `references/bibliography.md` Part A.

1. §8.2 "Monroe et al." → **Monrose** et al. (monrose2002).
2. §4.3-B "Canetti, Fuller, Paneth, **Varia**" → Canetti, Fuller, Paneth, **Reyzin, Smith**. Varia is a co-author of canetti2010locker.
3. Canetti J. Cryptology 34(1) "1–46": JoC uses article no. 2, and the page range is UNVERIFIED (other papers cite 1–33). Published online 2020, issue 2021. The EUROCRYPT version is LNCS 9665, pp. 117–146.
4. Rathgeb, Breitinger, Busch "2014, ICB / IET Biometrics" → **ICB 2013**, DOI 10.1109/ICB.2013.6612976. The IET Biometrics 3(4) 2014 paper is a different article, with Baier as co-author. The scheme uses XOR, not BioHashing.
5. Gomez-Barrero et al. "2017" → **2018** (TIFS 13(6)).
6. Ballard, Lopresti, Monrose 2007: the venue is IEEE TSMC **Part B (Cybernetics)**. The paper is about handwriting forgery, not entropy limits. The intended entropy source is likely ballard2008usenix.
7. Biggio et al. 2012: metadata correct. The implied "dual-threshold defence" is not in the paper (R9).
8. §8.2 "20–45 bits": no cited source supports this. Monrose 2002 reports *guessing entropy* 10.5 (an expected number of guesses, over 20 users). Ballard 2008 shows that such estimates overstate strength.
9. ISO/IEC 30136:2018 title: no "Biometrics —". A DIS revision is in progress.
10. "Rathgeb et al. 2014" in §4.3-C is the same issue as item 4.

## R13. FOSS stack (S2)

Licences that are wrong in §7.2:
- pynput is **LGPL-3.0**.
- python-fuzzy-extractor is **GPL-3.0**.
- bchlib is **GPL-2.0**.
- reedsolo is Unlicense / MIT-0.
- ezpwd is GPL-3.0.
- zeroize is Apache-2.0 OR MIT, and it **does not mlock**.

Other issues:
- dasec/face-bf-btp is not OSI open source (h_da licence agreement), face-only, and has had no push since 2017.
- The UserALE.js repo is archived; the code is now in the apache/flagon monorepo.
- feap is iris-specific.

The Go equivalents table is in bibliography.md A.2. GPL dependencies are a concern if ZTBE ships as a library.

## R14. Resource NFRs (S3)

- **NFR-03.** Rep is 1.8–2.7 ms in Go [GO], and the 32×256 Bloom distance is 170 ns [GO]. The ≤ 8 ms target is met. Note that Rep allocates about 1.5–2.2 MB per call in the naive implementation, so it should reuse buffers.
- **NFR-02.** 20 events/s × O(d) EW-Welford updates is negligible.
- **NFR-01.**
  - Session state ≤ 4 KB: estimate 1.9–4.3 KB depending on C zones and K states. Digraph statistics are C²×2×(μ,σ)×4 B, and the bit counters for §5.1-2 are 512 B [S§9]. It exceeds 4 KB at C ≥ 10.
  - 15 MB daemon: unlikely with CPython + River + numpy (not measured). A Go or Rust daemon is realistic.
- **NFR-05.** The Go GC may copy secrets. mlock does not cover the Go heap. Use memguard or fixed arrays with `runtime/secret` (experimental). See bibliography.md Go table. Note that Gen re-runs on every update (§5.1), so w lives in RAM regularly.

## Other observations (S3)

- FR-02 zone mapping removes key identity, which lowers discriminability compared with per-digraph features (gunetti2005). Quantify this on Aalto.
- §3.1 time-of-day sin/cos is not a behavioural *habit* feature in the same sense. Combined with Gray-coded bins, it encodes when the user works, which is a privacy concern under GDPR minimisation (edpb2020dpbd).
- §1.2 / FR-04: protected templates remain personal data, and biometric data under GDPR Art. 4(14) (gdpr2016; wp193 explicitly lists keystroke analysis).
- Evaluate FR-05 with continuous-authentication metrics: actions until detection (bours2012), and the pitfalls catalogued in eberz2017 and sugrim2019. EER alone is not enough.
