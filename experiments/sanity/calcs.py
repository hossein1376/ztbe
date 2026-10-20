#!/usr/bin/env python3
"""Sanity calculations for notes/spec-review.md. Pure stdlib. Run: python3 calcs.py"""
import math, random, itertools
from math import comb, log2, exp

def hdr(s): print("\n### " + s)

# ---------------------------------------------------------------- 1. sample-then-lock math (spec 4.3 B)
hdr("1. Sample-then-lock correctness (n=512, k_sub=32)")
n, k = 512, 32
for ber in (0.15, 0.18, 0.243):
    t = round(ber * n)
    p_hyp = comb(n - t, k) / comb(n, k)
    p_bin = (1 - ber) ** k
    for ell in (1000, 1500):
        print(f"t/n={ber:.3f} (t={t}): p_clean exact={p_hyp:.3e} approx={p_bin:.3e}; "
              f"l={ell}: FRR exact={(1-p_hyp)**ell:.3e}  spec-bound exp(-l(1-t/n)^k)={exp(-ell*p_bin):.3e}")
    for target in (1e-2, 1e-3):
        ell_need = math.ceil(math.log(target) / math.log(1 - p_hyp))
        print(f"   lockers needed for FRR<={target:g}: {ell_need}")
print("spec example check: 0.85^32 =", f"{0.85**32:.5f}", " 1500*0.85^32 =", f"{1500*0.85**32:.3f}", " e^-8.28 =", f"{exp(-8.28):.3e}")

hdr("1b. Offline brute force of ONE locker (security is capped by k_sub)")
hkdf_ns = 1560  # measured: ~2.34 ms / 1500 lockers in experiments/go-bench (1 core, Go, SHA-NI)
for kk in (16, 24, 32, 48, 64):
    s = 2**kk * hkdf_ns * 1e-9
    print(f"k_sub={kk}: <=2^{kk} guesses x {hkdf_ns} ns = {s:.3g} core-seconds ({s/3600:.3g} core-hours)")
print("Argon2id-per-locker budget for 20 ms Rep at l=1500:", f"{20e-3/1500*1e6:.1f} us/locker")

# ---------------------------------------------------------------- 2. BCH parameters (spec 4.3 A)
hdr("2. Binary BCH dimension k for n=511 (GF(2^9)), designed t")
def cyclotomic_cosets(m):
    N = 2**m - 1; seen = set(); cos = []
    for s in range(1, N):
        if s in seen: continue
        c = []; x = s
        while x not in c: c.append(x); x = (2 * x) % N
        seen.update(c); cos.append(c)
    return cos
def bch_k(m, t):
    N = 2**m - 1; roots = set()
    for c in cyclotomic_cosets(m):
        if any(1 <= r <= 2 * t for r in c): roots.update(c)
    return N - len(roots)
for ber in (0.05, 0.10, 0.15, 0.18, 0.25):
    t = round(ber * 511); kk = bch_k(9, t)
    print(f"BER {ber:.2f}: t={t:3d} -> BCH(511,{kk:3d}); syndrome n-k={511-kk} bits ({(511-kk)/8:.0f} B); "
          f"residual-entropy bound beta-(n-k) needs beta >= {511-kk+80} for 80-bit security")
print("Spec 5.4 '128-byte syndrome' = 1024 bits > n=512: inconsistent with n=512 (max n-k is 511 bits = 64 B).")

# ---------------------------------------------------------------- 3. Gray code wrap-around
hdr("3. Reflected Gray code: Hamming distance vs bin distance (m=3)")
g = lambda q: q ^ (q >> 1)
m = 3
for a in range(8):
    print("q=%d:" % a, " ".join(str(bin(g(a) ^ g(b)).count("1")) for b in range(8)))
print("e.g. bins 0 and 7 (opposite tails) differ in 1 bit; bins 0 and 3 differ in 1 bit.")

# ---------------------------------------------------------------- 4. Bloom-filter 'pre-image' formula
hdr("4. Bloom-filter pre-image count = surjections; and a trivial accepting pre-image")
def surj(N, s):  # spec formula: sum_k (-1)^k C(s,k) (s-k)^N
    return sum((-1)**j * comb(s, j) * (s - j)**N for j in range(s + 1))
for Nb, Wb in ((32, 8), (16, 8), (10, 4)):
    S = 2**Wb
    # expected number of set bits when Nb columns are uniform over 2^Wb values
    s = round(S * (1 - (1 - 1/S)**Nb))
    print(f"N_b={Nb}, W_b={Wb}: expected wt(BF)={s}; surjections = {surj(Nb, s):.3e} (~2^{log2(surj(Nb, s)):.1f}) per block")
# brute check of formula on tiny case
Nb, S = 5, 3
cnt = sum(1 for seq in itertools.product(range(S), repeat=Nb) if len(set(seq)) == S)
print(f"brute-force check N_b=5, |BF|=3: {cnt} == formula {surj(5,3)}")
print("Note: column ORDER does not matter for verification; ANY sequence covering the set bits reproduces BF exactly,")
print("so an attacker holding BF can build an accepting binary template in O(N_b) per block (no search).")

# ---------------------------------------------------------------- 5. Counting-BF storage
hdr("5. Storage")
print("CBF 32 blocks x 256 slots x 4 bit =", 32*256*4//8, "B;  binary BF =", 32*256//8, "B")
for ell, per in ((1000, 24), (1000, 40), (1500, 40), (1500, 92)):
    print(f"lockers l={ell} x {per} B = {ell*per/1024:.1f} KiB")
print("Hybrid L1(CBF 4 KiB)+L2(>=24 KiB)+anchor FE  vs NFR-04 <= 2 KiB")

# ---------------------------------------------------------------- 6. EW-Welford check
hdr("6. Exponentially weighted Welford (spec 3.2) vs direct weighted moments")
random.seed(0); alpha = 2 / (20 + 1)
xs = [random.gauss(100, 15) for _ in range(400)]
mu, var = xs[0], 0.0
for x in xs[1:]:
    d = x - mu; mu += alpha * d; var = (1 - alpha) * (var + alpha * d * d)
# direct: weights a(1-a)^(k-i) for i>=1, and (1-a)^(k) on x0 (initialisation)
K = len(xs) - 1
w = [(1 - alpha)**K] + [alpha * (1 - alpha)**(K - i) for i in range(1, K + 1)]
m_d = sum(wi * xi for wi, xi in zip(w, xs)); v_d = sum(wi * (xi - m_d)**2 for wi, xi in zip(w, xs))
print(f"recursive mu={mu:.6f} var={var:.6f} | direct mu={m_d:.6f} var={v_d:.6f}  (sum w = {sum(w):.6f})")

# ---------------------------------------------------------------- 7. Helper-data difference leakage (spec 5.1/5.2)
hdr("7. Update leakage demo with BCH(31,16,t=3): syndrome AND code-offset both leak the drift vector")
M = 5; N = 31; prim = 0b100101  # x^5+x^2+1
exp_t = [0]*62; x = 1
for i in range(31):
    exp_t[i] = x; x <<= 1
    if x & 32: x ^= prim
for i in range(31, 62): exp_t[i] = exp_t[i-31]
log_t = {exp_t[i]: i for i in range(31)}
def gmul(a, b): return 0 if a == 0 or b == 0 else exp_t[log_t[a] + log_t[b]]
def minpoly(e):  # minimal polynomial of alpha^e over GF(2), as int bitmask
    coset = []; c = e
    while c not in coset: coset.append(c); c = (2 * c) % N
    poly = [1]
    for r in coset:
        root = exp_t[r]; new = [0]*(len(poly)+1)
        for i, a in enumerate(poly):
            new[i+1] ^= a; new[i] ^= gmul(a, root)
        poly = new
    return sum((1 << i) for i, a in enumerate(poly) if a)
def pmul(a, b):
    r = 0
    while b:
        if b & 1: r ^= a
        a <<= 1; b >>= 1
    return r
def pmod(a, g):
    dg = g.bit_length() - 1
    while a.bit_length() - 1 >= dg: a ^= g << (a.bit_length() - 1 - dg)
    return a
gpoly = 1
for e in sorted({minpoly(e) for e in (1, 3, 5)}): gpoly = pmul(gpoly, e)
kdim = N - (gpoly.bit_length() - 1)
print(f"g(x) degree {gpoly.bit_length()-1} -> BCH({N},{kdim}), t=3")
syn = lambda v: pmod(v, gpoly)  # remainder = syndrome of cyclic code (linear, kernel = code)
table = {}
for wt in range(0, 4):
    for pos in itertools.combinations(range(N), wt):
        e = sum(1 << p for p in pos); table.setdefault(syn(e), e)
rnd = random.Random(7); hits_s = hits_o = 0; trials = 1000
for _ in range(trials):
    w = rnd.getrandbits(N); dw = sum(1 << p for p in rnd.sample(range(N), 3)); w2 = w ^ dw
    # syndrome sketch published before/after update
    if table.get(syn(w) ^ syn(w2)) == dw: hits_s += 1
    # code-offset sketch with FRESH random codewords each epoch
    c1 = pmul(rnd.getrandbits(kdim), gpoly); c2 = pmul(rnd.getrandbits(kdim), gpoly)
    if table.get(syn((w ^ c1) ^ (w2 ^ c2))) == dw: hits_o += 1
print(f"attacker recovers exact drift vector: syndrome {hits_s}/{trials}, code-offset(fresh c) {hits_o}/{trials}")

# ---------------------------------------------------------------- 8. Anti-poisoning envelope (spec 6)
hdr("8. Drift envelope implied by spec 6.1-6.3 (fractions of n)")
tv = 0.18; ta = 1.35 * tv
for g_ in (0.45, 0.65):
    print(f"gamma_gate={g_}: t_adapt={g_*tv:.3f}n")
print(f"t_anchor = 1.35*t_verify = {ta:.3f}n; working template may sit up to {ta:.3f}n from anchor, and accepts probes up to {tv:.3f}n from itself")
print(f"=> an impostor within {ta+tv:.3f}n of the anchor can eventually be accepted; V_max=0.02n/day reaches {ta:.3f}n in {math.ceil(ta/0.02)} days")

# ---------------------------------------------------------------- 9. Per-session RAM (NFR-01, 4 KiB)
hdr("9. Ephemeral per-session state estimate")
for C in (6, 8, 10):
    dig = C * C * 2 * 2 * 8   # PP and RP per zone pair, (mu, var) float64
    dwell = C * 2 * 8
    for K in (6, 10):
        markov = K * K * 4
        tot = dig + dwell + markov + 512
        print(f"C={C} zones, K={K} states: digraph {dig} + dwell {dwell} + Markov {markov} + bit counters 512 = {tot} B")
