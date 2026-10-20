#!/usr/bin/env python3
"""Sanity baselines for analyze.py: (a) unprotected real-valued distance EER with the same
enrollment/probe protocol; (b) same-session vs cross-session genuine BER (drift effect)."""
import os, sys, numpy as np
os.environ.setdefault("NW", "10"); os.environ.setdefault("FEAT", "mu")
sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else "DSL-StrongPasswordData.csv"]
src = open(os.path.join(os.path.dirname(__file__), "analyze.py")).read().split("print(f\"subjects")[0]
exec(src)
def eer(gen, imp):
    ths = np.quantile(np.concatenate([gen, imp]), np.linspace(0, 1, 2001))
    frr = np.array([(gen > t).mean() for t in ths]); far = np.array([(imp <= t).mean() for t in ths])
    k = np.argmin(np.abs(frr - far)); return (frr[k] + far[k]) / 2
gen, imp = [], []
for u in eval_users:
    enr = (windows(u, [1]) - mu_pop) / sd_pop; c = enr.mean(0); s = enr.std(0) + 1e-6
    for w in windows(u, range(2, 9)): gen.append(np.abs(((w - mu_pop) / sd_pop - c) / s).sum())
    for v in eval_users:
        if v != u:
            for w in windows(v, range(2, 9))[::4]: imp.append(np.abs(((w - mu_pop) / sd_pop - c) / s).sum())
print(f"(a) unprotected scaled-Manhattan on window means, enroll=session1, probe=sessions2-8: EER {eer(np.array(gen), np.array(imp))*100:.1f}%")
popz = (pop - mu_pop) / sd_pop
for m in (1, 2):
    edges = [np.quantile(popz[:, j], [q / 2**m for q in range(1, 2**m)]) for j in range(D)]
    same, cross = [], []
    for u in eval_users:
        W1 = windows(u, [1]); half = len(W1) // 2
        t = quantize((W1[:half].mean(0) - mu_pop) / sd_pop, m, edges)
        for w in W1[half:]: same.append(np.count_nonzero(quantize((w - mu_pop) / sd_pop, m, edges) ^ t) / (D * m))
        for w in windows(u, [8]): cross.append(np.count_nonzero(quantize((w - mu_pop) / sd_pop, m, edges) ^ t) / (D * m))
    print(f"(b) m={m}: genuine BER same-session mean {np.mean(same):.3f} (p90 {np.quantile(same,.9):.3f}); session-8 vs session-1 mean {np.mean(cross):.3f}")
