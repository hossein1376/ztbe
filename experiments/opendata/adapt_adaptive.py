"""Review round 1: does the sanitiser in adapt.py survive an attacker who knows about it?

Reuses the definitions in adapt.py (Tappy n200, Aalto priors, same thresholds and Policy class) and replaces the
straight-line boundary walk with a jittered walk: each injected window moves toward the attacker's mean plus a random
component orthogonal to that direction, of norm lambda * |direction|, then is clipped to just inside the adapt gate
(as in adapt.py). lambda = 0 is the original attack. Larger lambda lowers the mean cosine that the sanitiser tests
(> 0.5 over 10 updates triggers rollback + freeze) at the cost of slower progress.
Usage: python3 adapt_adaptive.py  -> results/adapt_adaptive_n200.txt  (about 1 min)
"""
import os, sys
import numpy as np
sys.argv = ["adapt.py", "n200"]
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "adapt.py")).read()
exec(compile(src[:src.index('log("\\n## genuine replay')], "adapt_defs", "exec"))   # data, thresholds, Policy

rng2 = np.random.default_rng(99)
pairs = [(u, v) for u in users for v in rng.choice([x for x in users if x != u], 3, replace=False)]
out = []
def say(s):
    print(s, flush=True); out.append(s)
base = np.mean([np.mean(dist(Z[np.flatnonzero(U == v)], tmpl[u][0], tmpl[u][1]) <= thr_v) >= 0.5 for u, v in pairs])
say(f"# adaptive poisoning vs full guard stack, Tappy n200, {len(users)} users, {len(pairs)} victim-attacker pairs")
say(f"thr_v {thr_v:.3f}, thr_a {thr_a:.3f}, r_anchor {r_anchor:.3f}; no-attack takeover on these pairs {base*100:.1f}%")
say("policy | lambda | attack days | takeover (attacker windows accepted >= 50%) | median attacker acceptance")
kw = dict(gate=True, anchor=True, velocity=True, sanitize=True)
for lam in (0.0, 2.0, 3.0):
    for days in (1, 7, 14, 28, 56):
        succ, accs = [], []
        for u, v in pairs:
            mu0, s, later, d0 = tmpl[u]
            iv = np.flatnonzero(U == v); mu_a = Z[iv].mean(0)
            P = Policy("full", mu0, s, **kw)
            for dday in range(days):
                for _ in range(50):
                    d = mu_a - P.mu
                    if lam > 0:
                        n = rng2.standard_normal(d.shape); n -= (n @ d) / (d @ d + 1e-12) * d
                        d = d + n * (np.linalg.norm(d) / (np.linalg.norm(n) + 1e-12) * lam)
                    dd = dist(P.mu + d, P.mu, s)
                    x = P.mu + d if dd <= 0.98 * thr_a else P.mu + d * (0.98 * thr_a / dd)
                    P.observe(x, 10000 + dday)
            acc = np.mean(dist(Z[iv], P.mu, s) <= thr_v); accs.append(acc); succ.append(acc >= 0.5)
        say(f"gated+anchor+velocity+sanitize | {lam} | {days} | {np.mean(succ)*100:.1f}% | {np.median(accs)*100:.1f}%")
open(os.path.join(HERE, "results", "adapt_adaptive_n200.txt"), "w").write("\n".join(out) + "\n")
