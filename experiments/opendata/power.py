"""Sample-size planning for ZTBE's own consented data collection (PLAN.md, phase 3).
Inputs: per-user error counts from userpolicy.py (Tappy, P0 global threshold, K=4 blocks), used to estimate
the intra-user correlation of errors (rho) and hence the design effect DEFF = 1 + (m-1)*rho (clustered binomial).
Outputs: users x blocks needed so that a 95% CI on pooled FRR / FAR has a given half-width; rule-of-3 / rule-of-30."""
import json, math, sys, glob, os
import numpy as np
R = os.path.join(os.path.dirname(__file__), "results")
z = 1.96
def rho_hat(pairs):
    # ANOVA estimator of intra-cluster correlation for binary outcomes (Fleiss)
    n = np.array([p[0] for p in pairs], float); x = np.array([p[1] for p in pairs], float)
    k = len(n); N = n.sum(); pbar = x.sum() / N
    msb = ((x - n * pbar) ** 2 / n).sum() / (k - 1)
    msw = (x - x ** 2 / n).sum() / (N - k)
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    return pbar, max(0.0, (msb - msw) / (msb + (n0 - 1) * msw))
print("# power analysis (power.py)\n")
print("## intra-user error correlation, Tappy, P0 global threshold, K=4 blocks")
print("cfg | users | pooled FRR | rho_FRR | pooled FAR | rho_FAR (per target)")
rhos_g, rhos_i = [], []
for f in sorted(glob.glob(f"{R}/userpolicy_*_K4_counts.json")):
    d = json.load(open(f)); pg, rg = rho_hat(d["genuine"]); pi, ri = rho_hat(d["impostor"])
    rhos_g.append(rg); rhos_i.append(ri)
    print(f"{d['cfg']} | {len(d['genuine'])} | {pg*100:.1f}% | {rg:.2f} | {pi*100:.1f}% | {ri:.2f}")
rg, ri = max(rhos_g), max(rhos_i)
print(f"\nPlanning values (max over configs): rho_FRR = {rg:.2f}, rho_FAR = {ri:.2f}")
def users_needed(p, h, m, rho):
    n_eff = z * z * p * (1 - p) / (h * h); deff = 1 + (m - 1) * rho
    return math.ceil(n_eff * deff / m), n_eff, deff
print("\n## users needed for a 95% CI half-width h on pooled error rate p, with m blocks per user (normal approx., clustered)")
print("target | p | h | m blocks/user | DEFF | effective n | users needed")
for name, p, h, rho in (("FRR", 0.05, 0.02, rg), ("FRR", 0.05, 0.01, rg), ("FAR (block)", 0.10, 0.03, ri), ("FAR (block)", 0.10, 0.02, ri)):
    for m in (20, 50, 100, 200):
        u, ne, de = users_needed(p, h, m, rho)
        print(f"{name} | {p:.2f} | ±{h:.2f} | {m} | {de:.1f} | {ne:.0f} | {u}")
print("\nNote: with rho > 0, adding blocks per user saturates; the minimum number of users is n_eff*rho for m→∞.")
for name, p, h, rho in (("FRR", 0.05, 0.02, rg), ("FAR (block)", 0.10, 0.03, ri)):
    ne = z * z * p * (1 - p) / (h * h); print(f"{name} p={p} h=±{h}: users ≥ {math.ceil(ne*rho)} even with unlimited blocks per user")
print("\n## rule of 3 / rule of 30 (independent trials)")
for far in (1e-2, 1e-3, 1e-4):
    print(f"claim FAR ≤ {far:g} at 95% with zero errors: ≥ {math.ceil(3/far)} independent impostor attempts (rule of 3); "
          f"to observe 30 errors at FAR={far:g} (rule of 30: ±30% relative at 90% confidence; attribution to Doddington et al. UNVERIFIED, not in bib): ≥ {math.ceil(30/far)} attempts")
print("With N users, cross-user impostor pairs = N(N-1); attempts from the same attacker are correlated, so pairs are not independent trials.")
