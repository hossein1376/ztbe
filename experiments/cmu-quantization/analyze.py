#!/usr/bin/env python3
"""ZTBE sanity experiment on the CMU Killourhy-Maxion (DSN 2009) keystroke benchmark.

Purpose: get *measured* (not assumed) numbers for the spec's Stage-1 pipeline
(population z-scoring -> equiprobable quantization -> Gray code) on a real
behavioral dataset: intra-user bit error rate (BER), impostor fractional
Hamming distance, Daugman-style degrees of freedom, and what a
sample-then-lock locker configuration would yield.

Data is NOT redistributed here. Download it yourself (no explicit license on the
page; the authors request citation):
  curl -O https://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv
  (md5 470235f96568f28f9ea0da62234ec857, as listed on the dataset page)

Caveats: fixed-text password (".tie5Roanl"), 51 subjects, lab setting.
Free-text continuous data will be noisier. Results are therefore OPTIMISTIC.
Only numpy + stdlib needed.
"""
import csv, math, sys, random
from statistics import NormalDist
from math import comb, log2
import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else "DSL-StrongPasswordData.csv"
rows = list(csv.reader(open(path)))
hdr, rows = rows[0], rows[1:]
subj = np.array([r[0] for r in rows]); sess = np.array([int(r[1]) for r in rows])
X = np.log(np.maximum(np.array([[float(v) for v in r[3:]] for r in rows]), 1e-3) + 0.0)  # log timings
# UD (release-to-press) can be negative (rollover); log of clipped value is a crude choice
# so we use signed log1p for UD columns instead:
raw = np.array([[float(v) for v in r[3:]] for r in rows])
for j, name in enumerate(hdr[3:]):
    if name.startswith("UD."):
        X[:, j] = np.sign(raw[:, j]) * np.log1p(np.abs(raw[:, j]) * 1000)  # ms scale
    else:
        X[:, j] = np.log(raw[:, j] * 1000)

users = sorted(set(subj)); rng = random.Random(1); rng.shuffle(users)
pop_users, eval_users = users[:25], users[25:]
import os
NW = int(os.environ.get("NW", 10))  # repetitions per "window"
FEAT = os.environ.get("FEAT", "musigma")  # "musigma" (spec 3.2: z=[mu||sigma]) or "mu"
MASK = int(os.environ.get("MASK", 0))  # if >0 keep only the MASK highest-FDR features per user (spec 4.2 step 4)

def windows(u, sessions):
    idx = np.where((subj == u) & np.isin(sess, sessions))[0]
    W = []
    for s in range(0, len(idx) - NW + 1, NW):
        blk = X[idx[s:s+NW]]
        W.append(np.concatenate([blk.mean(0), blk.std(0)]) if FEAT == 'musigma' else blk.mean(0))
    return np.array(W)

pop = np.vstack([windows(u, range(1, 9)) for u in pop_users])
mu_pop, sd_pop = pop.mean(0), pop.std(0)
D = pop.shape[1]

def gray(q): return q ^ (q >> 1)

def quantize(z, m, edges):
    out = []
    for j in range(D):
        q = int(np.searchsorted(edges[j], z[j]))
        g = gray(q)
        out.extend([(g >> (m-1-b)) & 1 for b in range(m)])
    return np.array(out, dtype=np.uint8)

def run(m, edge_mode):
    if edge_mode == "gauss":   # spec 4.2: assume N(0,1) after population z-scoring
        nd = NormalDist()
        e = [nd.inv_cdf(q / 2**m) for q in range(1, 2**m)]
        edges = [np.array(e) for _ in range(D)]
        popz = (pop - mu_pop) / sd_pop
        occ = np.array([np.histogram(popz[:, j], bins=[-np.inf]+e+[np.inf])[0] / len(popz) for j in range(D)])
        imbalance = float(np.abs(occ - 1/2**m).max())
    else:                      # empirical equiprobable quantiles on the population set
        popz = (pop - mu_pop) / sd_pop
        edges = [np.quantile(popz[:, j], [q / 2**m for q in range(1, 2**m)]) for j in range(D)]
        imbalance = 0.0
    n = D * m if not MASK else MASK * m
    gen, imp, templates, masks = [], [], {}, {}
    for u in eval_users:
        enr = windows(u, [1])                 # session 1 = enrollment
        zt = (enr.mean(0) - mu_pop) / sd_pop
        templates[u] = quantize(zt, m, edges)
        if MASK:
            ez = (enr - mu_pop) / sd_pop
            fdr = (ez.mean(0)) ** 2 / np.maximum(ez.var(0), 1e-9)   # spec 4.2 FDR (population mean = 0 after z-scoring)
            keep = np.argsort(-fdr)[:MASK]
            masks[u] = np.repeat(np.isin(np.arange(D), keep), m)
        else:
            masks[u] = np.ones(D * m, bool)
    probes = {u: [quantize((w - mu_pop) / sd_pop, m, edges) for w in windows(u, range(2, 9))] for u in eval_users}
    for u in eval_users:
        for p in probes[u]:
            gen.append(np.count_nonzero((p ^ templates[u])[masks[u]]) / masks[u].sum())
        for v in eval_users:
            if v != u:
                for p in probes[v][::4]:
                    imp.append(np.count_nonzero((p ^ templates[u])[masks[u]]) / masks[u].sum())
    gen, imp = np.array(gen), np.array(imp)
    # EER on fractional HD
    ths = np.linspace(0, 1, 2001)
    frr = np.array([(gen > t).mean() for t in ths]); far = np.array([(imp <= t).mean() for t in ths])
    k = np.argmin(np.abs(frr - far)); eer = (frr[k] + far[k]) / 2
    dof = imp.mean() * (1 - imp.mean()) / imp.var()   # Daugman binomial-equivalent DoF
    # per-bit population entropy (Shannon, upper bound on what bits can carry)
    T = np.array(list(templates.values()))
    return dict(m=m, edges=edge_mode, n=n, imbalance=imbalance,
                gen_mean=gen.mean(), gen_p50=np.median(gen), gen_p90=np.quantile(gen, .9), gen_p95=np.quantile(gen, .95),
                imp_mean=imp.mean(), imp_p01=np.quantile(imp, .01), imp_p05=np.quantile(imp, .05),
                eer=eer, eer_th=ths[k], dof=dof,
                far_018=(imp <= .18).mean(), far_0243=(imp <= .243).mean(), far_0423=(imp <= .423).mean(),
                frr_018=(gen > .18).mean(), gen=gen, imp=imp)

def stl_frr(gen, n, k, ell):
    # exact per-probe hypergeometric p_clean, averaged over the empirical genuine BER distribution
    out = []
    for f in gen:
        e = int(round(f * n))
        p = comb(n - e, k) / comb(n, k) if n - e >= k else 0.0
        out.append((1 - p) ** ell)
    return float(np.mean(out))

print(f"subjects: pop={len(pop_users)} eval={len(eval_users)}; window={NW} reps; FEAT={FEAT} D={D}; MASK={MASK}")
for m in (1, 2, 3):
    for mode in ("gauss", "empirical"):
        r = run(m, mode)
        print(f"\n== m={m} bits/feature, edges={mode}, n={r['n']} bits; max |bin occupancy - 2^-m| = {r['imbalance']:.3f}")
        print(f"genuine frac-HD: mean {r['gen_mean']:.3f}  p50 {r['gen_p50']:.3f}  p90 {r['gen_p90']:.3f}  p95 {r['gen_p95']:.3f}")
        print(f"impostor frac-HD: mean {r['imp_mean']:.3f}  p1 {r['imp_p01']:.3f}  p5 {r['imp_p05']:.3f}   Daugman DoF ~ {r['dof']:.1f}")
        print(f"EER {r['eer']*100:.1f}% at HD {r['eer_th']:.3f};  @t=0.18n: FRR {r['frr_018']*100:.1f}% FAR {r['far_018']*100:.2f}%;  "
              f"FAR@0.243n {r['far_0243']*100:.1f}%  FAR@0.423n {r['far_0423']*100:.1f}%")
        if m == 2 and mode == "empirical":
            for k, ell in ((32, 1500), (16, 1500), (8, 1500)):
                print(f"   sample-then-lock k_sub={k}, l={ell}: genuine FRR ~ {stl_frr(r['gen'], r['n'], k, ell)*100:.2f}%  "
                      f"impostor FAR ~ {(1-stl_frr(r['imp'], r['n'], k, ell))*100:.2f}%  (per-locker brute force <= 2^{k})")
