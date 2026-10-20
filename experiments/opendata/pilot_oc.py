"""Review round 2: operating characteristic of the D15 go/stop rule as analysed in docs/pilot-protocol.md §7.

Simulation (assumptions, not data): N victims x 3 impostors x 3 ten-window segments. Each segment is an alarm (1)
or not. Victim-level clustering: the per-victim rate ~ Beta with mean p and intra-class correlation rho
(beta-binomial). Optional crossed impostor effect: each participant also has an impostor "wolfishness" offset on the
logit scale (sd_imp). Analysis as in the protocol: 95% percentile cluster bootstrap over victims (B resamples).
Go needs lower bound >= 70% (the burden condition is assumed met); Stop needs upper bound < 60%.
Also reports the coverage of that bootstrap CI for the true p.
Usage: python3 pilot_oc.py -> results/pilot_oc.txt
"""
import os
import numpy as np
rng = np.random.default_rng(20261021)
R, B = 2000, 1000

def sim(N, p, rho, sd_imp):
    a = p * (1 - rho) / rho; b = (1 - p) * (1 - rho) / rho
    pv = rng.beta(a, b, N)                         # per-victim rate
    imp = rng.normal(0, sd_imp, N)                 # impostor offset (participant i as impostor)
    y = np.zeros((N, 9))
    for v in range(N):
        attackers = [(v + k) % N for k in (1, 2, 3)]  # round robin, 3 impostors per victim
        for j, att in enumerate(attackers):
            lg = np.log(pv[v] / (1 - pv[v])) + imp[att] if 0 < pv[v] < 1 else (50 if pv[v] >= 1 else -50)
            q = 1 / (1 + np.exp(-np.clip(lg, -50, 50)))
            y[v, 3 * j:3 * j + 3] = rng.random(3) < q
    return y

def ci(y):
    N = len(y); m = y.mean(1)
    idx = rng.integers(0, N, (B, N))
    bs = m[idx].mean(1)
    return np.percentile(bs, 2.5), np.percentile(bs, 97.5)

out = ["# D15 rule operating characteristic (simulated; rho and impostor sd are ASSUMPTIONS)",
       f"# {R} simulated pilots per row; cluster bootstrap over victims with B={B}",
       "N | true p | rho | impostor sd (logit) | P(go) | P(stop) | P(inconclusive) | CI coverage of true p"]
for N in (10, 16, 20):
    for p in (0.55, 0.65, 0.75, 0.80, 0.88):
        for rho, sdi in ((0.2, 0.0), (0.2, 0.8)):
            go = st = cov = 0
            for _ in range(R):
                y = sim(N, p, rho, sdi); lo, hi = ci(y)
                go += lo >= 0.70; st += hi < 0.60; cov += lo <= p <= hi
            out.append(f"{N} | {p:.2f} | {rho} | {sdi} | {go/R:.2f} | {st/R:.2f} | {1-(go+st)/R:.2f} | {cov/R:.2f}")
print("\n".join(out))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "pilot_oc.txt"), "w").write("\n".join(out) + "\n")
