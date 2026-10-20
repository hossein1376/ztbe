"""Operating characteristics of candidate pilot rules (D18 redesign of D15/D16; review round 2 H9).

Assumptions (NOT data): per-victim alarm-within-10 rate ~ Beta(mean p, ICC rho); crossed impostor effect on the
logit scale with sd sd_imp; segments independent given victim and impostor. Design: N victims, round robin with
3 impostors per victim, S ten-window segments per impostor session.
Interval ("conservative CI"): the union of (a) the 95% percentile cluster bootstrap over victims (B resamples) and
(b) the Wilson 95% interval on n_eff = n / (1 + (m-1) rho_hat), where rho_hat is the one-way ANOVA ICC estimate
floored at 0.1. The lower bound is the min of the two, the upper bound the max.
Usage: python3 pilot_oc2.py [R] -> results/pilot_oc2.txt
"""
import os, sys
import numpy as np
rng = np.random.default_rng(20261021)
R = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
B = 1000
Z = 1.96

def sim(N, p, rho, sd_imp, S):
    a = p * (1 - rho) / rho; b = (1 - p) * (1 - rho) / rho
    pv = np.clip(rng.beta(a, b, N), 1e-6, 1 - 1e-6)
    imp = rng.normal(0, sd_imp, N)
    att = (np.arange(N)[:, None] + np.array([1, 2, 3])[None, :]) % N          # N x 3
    lg = np.log(pv / (1 - pv))[:, None] + imp[att]
    q = 1 / (1 + np.exp(-lg))                                               # N x 3
    return (rng.random((N, 3, S)) < q[:, :, None]).reshape(N, 3 * S).astype(float)

def wilson(phat, n):
    c = (phat + Z * Z / (2 * n)) / (1 + Z * Z / n)
    h = Z * np.sqrt(phat * (1 - phat) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return c - h, c + h

def cons_ci(y):
    N, m = y.shape
    mv = y.mean(1); phat = mv.mean()
    bs = mv[rng.integers(0, N, (B, N))].mean(1)
    blo, bhi = np.percentile(bs, [2.5, 97.5])
    msb = m * ((mv - phat) ** 2).sum() / (N - 1)
    msw = ((y - mv[:, None]) ** 2).sum() / (N * (m - 1))
    den = msb + (m - 1) * msw
    rho_hat = max(0.1, (msb - msw) / den if den > 0 else 0.1)
    neff = N * m / (1 + (m - 1) * rho_hat)
    wlo, whi = wilson(phat, neff)
    return phat, min(blo, wlo), max(bhi, whi)

def rule_single(N, S):
    def f(p, rho, sdi):
        y = sim(N, p, rho, sdi, S); ph, lo, hi = cons_ci(y)
        cov = lo <= p <= hi
        if lo >= 0.70: return "go", cov
        if ph < 0.60: return "stop", cov
        return "inc", cov
    return f

def rule_two_stage(N1, N2, S):
    def f(p, rho, sdi):
        y1 = sim(N1, p, rho, sdi, S); ph, lo, hi = cons_ci(y1)
        if lo >= 0.70: return "go1", lo <= p <= hi
        if ph < 0.60: return "stop1", lo <= p <= hi
        y = np.vstack([y1, sim(N2, p, rho, sdi, S)])     # second cohort, own round robin
        ph, lo, hi = cons_ci(y)
        if lo >= 0.70: return "go", lo <= p <= hi
        if ph < 0.70: return "stop", lo <= p <= hi
        return "inc", lo <= p <= hi
    return f

designs = [
    ("A single N=20, S=2, stop if p_hat<0.60", rule_single(20, 2)),
    ("B two-stage 16+16, S=2; stage 1: go lo>=0.70 / stop p_hat<0.60; stage 2 (N=32): go lo>=0.70 / stop p_hat<0.70", rule_two_stage(16, 16, 2)),
    ("C two-stage 20+20, S=2; same boundaries as B (stage 2 N=40)", rule_two_stage(20, 20, 2)),
]
out = ["# Pilot rule operating characteristics (simulated; rho and impostor sd are ASSUMPTIONS)",
       f"# {R} simulated pilots per row; conservative CI = union of victim-cluster bootstrap (B={B}) and Wilson on n_eff (rho_hat floored at 0.1)",
       "# burden condition assumed met (it is evaluated separately on a point estimate)"]
for name, f in designs:
    out.append(f"\n## {name}")
    out.append("true p | rho | impostor sd | P(go) | P(stop) | P(inconclusive) | CI coverage | P(decided at stage 1)")
    for p in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.88):
        for rho, sdi in ((0.1, 0.0), (0.2, 0.8), (0.3, 0.8)):
            res = [f(p, rho, sdi) for _ in range(R)]
            g = sum(r.startswith("go") for r, _ in res) / R; s = sum(r.startswith("stop") for r, _ in res) / R
            e1 = sum(r in ("go1", "stop1") for r, _ in res) / R
            c = sum(cv for _, cv in res) / R
            out.append(f"{p:.2f} | {rho} | {sdi} | {g:.2f} | {s:.2f} | {1-g-s:.2f} | {c:.2f} | {e1:.2f}")
    print("\n".join(out[-28:]), flush=True)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "pilot_oc2.txt"), "w").write("\n".join(out) + "\n")
