"""Evaluation library: Eberz-style protocol, unprotected matchers, quantizers,
metrics (EER, FRR@FAR, Gini), template-protection simulations and entropy estimates.

Conventions: all scores are *distances* (lower = more similar).
"""
import numpy as np
from math import comb, log2

RNG = np.random.default_rng(20261021)

# ------------------------------------------------------------------ priors / normalisation
class Prior:
    """Population priors computed on a disjoint population set (spec §4.2 step 1)."""
    def __init__(self, X, uid, max_bins=16):
        self.mu = np.nanmean(X, 0)
        self.sd = np.nanstd(X, 0) + 1e-9
        Z = self.z(X)
        self.q = {S: np.quantile(Z, np.arange(1, S) / S, axis=0) for S in (2, 4, 8, 16) if S <= max_bins}
        # population Fisher ratio: var of user means / mean within-user var
        u, inv = np.unique(uid, return_inverse=True)
        cnt = np.bincount(inv)
        keep = cnt[inv] >= 2
        Zk, invk = Z[keep], inv[keep]
        sums = np.zeros((len(u), Z.shape[1])); np.add.at(sums, invk, Zk)
        c = np.bincount(invk, minlength=len(u))[:, None]
        m = sums[c[:, 0] > 0] / c[c[:, 0] > 0]
        within = np.zeros(Z.shape[1]); dev = Zk - (sums / np.maximum(c, 1))[invk]
        within = (dev ** 2).mean(0)
        self.between = m.var(0)
        self.within = within
        self.fisher = self.between / (within + 1e-9)
        self.icc = self.between / (self.between + within + 1e-9)

    def z(self, X):
        Z = (X - self.mu) / self.sd
        return np.clip(np.nan_to_num(Z, nan=0.0), -5, 5).astype(np.float32)


class LDA:
    """Population-trained LDA projection (a cheap 'learned embedding', fitted on population users only)."""
    def __init__(self, Z, uid, k=16, reg=1e-2):
        u, inv = np.unique(uid, return_inverse=True)
        D = Z.shape[1]
        sums = np.zeros((len(u), D)); np.add.at(sums, inv, Z)
        c = np.bincount(inv)[:, None]
        M = sums / c
        dev = Z - M[inv]
        Sw = dev.T @ dev / len(Z) + reg * np.eye(D)
        Mc = M - Z.mean(0)
        Sb = (Mc * c).T @ Mc / len(Z)
        w, V = np.linalg.eig(np.linalg.solve(Sw, Sb))
        o = np.argsort(-w.real)[:k]
        self.W = V[:, o].real
        P = dev @ self.W
        self.scale = P.std(0) + 1e-9          # whiten by within-class spread
    def __call__(self, Z):
        return (Z @ self.W / self.scale).astype(np.float32)

# ------------------------------------------------------------------ quantizers
def gray_bits(m):
    q = np.arange(2 ** m); g = q ^ (q >> 1)
    return ((g[:, None] >> np.arange(m)[::-1]) & 1).astype(np.uint8)          # [2^m, m]


def lssc_bits(S):
    """LSSC (Lim & Teoh 2013): S codewords of S-1 bits, HD(c_i, c_j) = |i - j|."""
    return (np.arange(S)[:, None] > np.arange(S - 1)[None, :]).astype(np.uint8)


def bin_index(Z, edges):
    """edges [S-1, D] -> integer bin per feature."""
    return (Z[:, None, :] > edges[None, :, :]).sum(1)


def encode(Z, prior, code="gray", S=4, feats=None):
    """Quantize standardized windows with population equiprobable edges, then label with Gray or LSSC."""
    if feats is not None:
        Z = Z[:, feats]
        edges = prior.q[S][:, feats]
    else:
        edges = prior.q[S]
    idx = bin_index(Z, edges)
    tab = gray_bits(int(log2(S))) if code == "gray" else lssc_bits(S)
    return tab[idx].reshape(len(Z), -1)


def droba_alloc(mu_u, sd_u, prior, L, bmax=3):
    """DROBA (Chen et al. 2009): per-user bit allocation maximizing sum log detection rate,
    detection rate delta_j(b) = P(sample stays in the bin of the user's mean) under N(mu_u, sd_u^2),
    equiprobable population bins with 2^b intervals. Greedy marginal allocation (concave in practice)."""
    from math import erf, sqrt
    D = len(mu_u)
    Phi = lambda x: 0.5 * (1 + np.vectorize(erf)(x / sqrt(2)))
    logd = np.zeros((D, bmax + 1))
    for b in range(1, bmax + 1):
        S = 2 ** b
        e = np.vstack([np.full(D, -np.inf), prior.q[S], np.full(D, np.inf)])   # [S+1, D]
        k = (mu_u[None, :] > prior.q[S]).sum(0)
        lo, hi = e[k, np.arange(D)], e[k + 1, np.arange(D)]
        s = np.maximum(sd_u, 0.05)
        logd[:, b] = np.log(np.maximum(Phi((hi - mu_u) / s) - Phi((lo - mu_u) / s), 1e-12))
    alloc = np.zeros(D, int)
    for _ in range(L):
        gain = np.where(alloc < bmax, logd[np.arange(D), np.minimum(alloc + 1, bmax)] - logd[np.arange(D), alloc], -np.inf)
        j = int(np.argmax(gain)); alloc[j] += 1
    return alloc


def droba_encode(Z, prior, alloc):
    out = []
    for j, b in enumerate(alloc):
        if b == 0:
            continue
        S = 2 ** b
        idx = (Z[:, j:j + 1] > prior.q[S][:, j][None, :]).sum(1)
        out.append(gray_bits(b)[idx])
    return np.hstack(out)

# ------------------------------------------------------------------ metrics
def roc_metrics(gen, imp):
    gen, imp = np.asarray(gen, float), np.asarray(imp, float)
    thr = np.unique(np.quantile(np.r_[gen, imp], np.linspace(0, 1, 2001)))
    gs, is_ = np.sort(gen), np.sort(imp)
    frr = 1 - np.searchsorted(gs, thr, side="right") / len(gs)
    far = np.searchsorted(is_, thr, side="right") / len(is_)
    i = np.argmin(np.abs(frr - far))
    def frr_at_far(a):
        ok = far <= a
        return frr[ok].min() if ok.any() else 1.0
    def far_at_frr(a):
        ok = frr <= a
        return far[ok].min() if ok.any() else 1.0
    return dict(eer=(frr[i] + far[i]) / 2, thr_eer=thr[i], frr_far1=frr_at_far(0.01), frr_far01=frr_at_far(0.001),
                far_frr5=far_at_frr(0.05), far_frr10=far_at_frr(0.10),
                thr_frr10=thr[np.argmin(np.abs(frr - 0.10))],
                thr_far1=thr[far <= 0.01].max() if (far <= 0.01).any() else thr[0])


def gini(v):
    v = np.sort(np.asarray(v, float))
    if v.sum() == 0:
        return 0.0
    n = len(v); c = np.cumsum(v)
    return float((n + 1 - 2 * (c / c[-1]).sum()) / n)


def daugman_dof(imp_frac_hd):
    p = np.mean(imp_frac_hd); s = np.std(imp_frac_hd)
    return p * (1 - p) / (s ** 2) if s > 0 else np.inf

# ------------------------------------------------------------------ protocol
def split_chrono(uid, order, enroll_frac=0.5, min_win=4):
    """Eberz: training = first part of each user's data, testing = later part."""
    enroll = np.zeros(len(uid), bool); test = np.zeros(len(uid), bool)
    for u in np.unique(uid):
        ix = np.flatnonzero(uid == u)
        if len(ix) < min_win:
            continue
        ix = ix[np.argsort(order[ix], kind="stable")]
        k = max(1, int(round(len(ix) * enroll_frac)))
        enroll[ix[:k]] = True; test[ix[k:]] = True
    return enroll, test


def pairs(uid_t, users, n_imp=30):
    """Genuine: each test window vs own template. Impostor: test windows of n_imp other
    (non-population, never used for training) users vs the template - zero-effort attacker."""
    by = {u: np.flatnonzero(uid_t == u) for u in users}
    G, I = [], []
    ua = np.array(users)
    for k, u in enumerate(users):
        G += [(k, i) for i in by[u]]
        others = RNG.choice(np.delete(ua, k), size=min(n_imp, len(ua) - 1), replace=False)
        for o in others:
            if len(by[o]):
                I.append((k, RNG.choice(by[o]), int(np.flatnonzero(ua == o)[0])))
    return np.array(G), np.array(I)


def evaluate(score_fn, n_users, G, I, label):
    """score_fn(template_idx_array, probe_idx_array) -> distances."""
    gs = score_fn(G[:, 0], G[:, 1]); is_ = score_fn(I[:, 0], I[:, 1])
    m = roc_metrics(gs, is_)
    thr = m["thr_eer"]
    frr_u = np.array([np.mean(gs[G[:, 0] == k] > thr) for k in range(n_users) if (G[:, 0] == k).any()])
    far_a = np.bincount(I[:, 2], weights=(is_ <= thr), minlength=n_users) / np.maximum(np.bincount(I[:, 2], minlength=n_users), 1)
    m.update(label=label, gini_frr=gini(frr_u), gini_far=gini(far_a[np.bincount(I[:, 2], minlength=n_users) > 0]),
             gen=gs, imp=is_)
    return m

# ------------------------------------------------------------------ protection simulations
def stl_rates(hd_counts, n, k, ell):
    """Sample-then-lock: P(at least one of ell random k-subsets avoids all e errors)."""
    out = []
    tot = comb(n, k) if k <= n else 0
    cache = {}
    for e in hd_counts:
        e = int(e)
        if e not in cache:
            p = comb(n - e, k) / tot if (tot and n - e >= k) else 0.0
            cache[e] = 1 - (1 - p) ** ell
        out.append(cache[e])
    return np.array(out)                 # acceptance probability per probe


def stl_locker_attack(T_pop, T_eval, k, n_lockers=200):
    """Per-locker offline attack with population prior: for random k-subsets I, guess the most frequent
    population pattern on I; success = fraction of eval templates that match it exactly.
    Returns per-locker success probs (attacker opens that locker with ONE guess)."""
    n = T_pop.shape[1]
    if k > n:
        return np.array([])
    w = 1 << np.arange(min(k, 62))
    ps = []
    for _ in range(n_lockers):
        I = RNG.choice(n, size=k, replace=False)
        kp = (T_pop[:, I[:62]].astype(np.int64) * w).sum(1)
        ke = (T_eval[:, I[:62]].astype(np.int64) * w).sum(1)
        vals, cnt = np.unique(kp, return_counts=True)
        guess = vals[np.argmax(cnt)]
        ps.append(np.mean(ke == guess))
    return np.array(ps)

# ------------------------------------------------------------------ guessing curves
def greedy_guessing(acc_att, acc_tgt, max_guesses=4096):
    """acc_att[g, a]: guess g accepted by attacker-side (population) template a;
    acc_tgt[g, t]: same for real targets. Greedy max-coverage on the attacker side,
    evaluated on targets. Returns cumulative target success after 1..G guesses."""
    covered_a = np.zeros(acc_att.shape[1], bool)
    covered_t = np.zeros(acc_tgt.shape[1], bool)
    curve = []
    avail = np.ones(acc_att.shape[0], bool)
    for _ in range(min(max_guesses, acc_att.shape[0])):
        gain = (acc_att[:, ~covered_a]).sum(1)
        gain[~avail] = -1
        g = int(np.argmax(gain))
        if gain[g] <= 0:
            break
        avail[g] = False
        covered_a |= acc_att[g]; covered_t |= acc_tgt[g]
        curve.append(covered_t.mean())
    return np.array(curve)


def popcount_dist(A, B):
    """Hamming distances between rows of A [na, n] and B [nb, n] (uint8 0/1), chunked."""
    Ap = np.packbits(A, axis=1); Bp = np.packbits(B, axis=1)
    lut = np.array([bin(i).count("1") for i in range(256)], np.uint8)
    out = np.empty((len(A), len(B)), np.uint16)
    for s in range(0, len(A), 256):
        x = Ap[s:s + 256, None, :] ^ Bp[None, :, :]
        out[s:s + 256] = lut[x].sum(2)
    return out


def summarize_curve(c):
    if not len(c):
        return dict(p1=0, p10=0, p100=0, p1000=0, g50=None, h1=float("inf"))
    get = lambda g: float(c[min(g, len(c)) - 1])
    g50 = int(np.argmax(c >= 0.5)) + 1 if (c >= 0.5).any() else None
    return dict(p1=get(1), p10=get(10), p100=get(100), p1000=get(1000), g50=g50, maxcov=float(c[-1]),
                n_guesses=len(c), h1=-log2(c[0]) if c[0] > 0 else float("inf"))
