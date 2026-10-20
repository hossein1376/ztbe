"""Round 2: FRR benefit of SUPERVISED adaptation (spec v2 §8 U1-U4), Tappy, user-fold calibration.

Strong-auth proxy: Tappy has no login events and the derived windows carry only a day index, so the first S
windows of each calendar day (S in {2, 5, 10}) are treated as "within 30 min after a WebAuthn login".
Supervised windows update mu by EWMA (eta=0.05) if window score <= tau (U1/U2); the updated mu must stay within
r_anchor = 0.675*tau of the enrolment mu (U3, one anchor); sigma is re-estimated weekly from the last 50 accepted
supervised windows with the same shrinkage formula (U2). tau = q95 of genuine week-2 window scores of the OTHER
fold's users (user-fold calibration). Metric: window FRR by week since enrolment (pooled and macro), and the
paired difference supervised - static at weeks 6-8 with a 95% bootstrap CI over users.
Usage: adapt_supervised.py [cfg=t60] [B=1000] -> results/adapt_supervised_<cfg>.txt"""
import os, sys, numpy as np
import evallib as E
DATA = os.environ.get("DATA", "/workspace/data"); OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
cfg = sys.argv[1] if len(sys.argv) > 1 else "t60"; B = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
rng = np.random.default_rng(20261021)
d = np.load(f"{DATA}/derived/tappy_{cfg}.npz"); X, U, DAY = d["X"], d["uid"], d["day"]
users = [u for u in np.unique(U) if (lambda ix: DAY[ix].max() - DAY[ix].min() >= 28 and (DAY[ix] < DAY[ix].min() + 7).sum() >= 3)(np.flatnonzero(U == u))]
fold = dict(zip(users, rng.permutation(np.arange(len(users)) % 2)))
lines = []
def log(s=""): print(s, flush=True); lines.append(s)
log(f"# supervised adaptation, tappy {cfg}: {len(users)} users with >= 28 days span; 2 user folds")
res = {}
for f in (0, 1):
    m = np.isin(U, [u for u in np.unique(U) if fold.get(u, -1) != f])
    prior = E.Prior(X[m], U[m]); Z = prior.z(X); w = 0.8 * np.sqrt(prior.within)
    def tmpl(z):
        mu = z.mean(0); n = len(z); mad = np.abs(z - mu).mean(0)
        return mu, np.sqrt((n * mad ** 2 + 2 * w ** 2) / (n + 2)) + 1e-3
    def sc(z, t): return (np.abs(z - t[0]) / t[1]).mean(-1)
    def parts(u):
        ix = np.flatnonzero(U == u); d0 = DAY[ix].min(); return ix[DAY[ix] < d0 + 7], ix[DAY[ix] >= d0 + 7], d0
    cal = np.concatenate([sc(Z[p[1][DAY[p[1]] < p[2] + 14]], tmpl(Z[p[0]])) for p in map(parts, [u for u in users if fold[u] != f])])
    tau = np.quantile(cal, 0.95); r_anchor = 0.675 * tau
    for u in [u for u in users if fold[u] == f]:
        en, later, d0 = parts(u); t0 = tmpl(Z[en])
        for S in (0, 2, 5, 10):
            mu, s = t0[0].copy(), t0[1].copy(); buf = []; lastw = None; seen = {}; out = []
            for i in later:
                day = DAY[i]; wk = (day - d0) // 7
                if lastw is not None and wk != lastw and len(buf) >= 10:
                    zz = np.array(buf[-50:]); n = len(zz); mad = np.abs(zz - zz.mean(0)).mean(0)
                    s = np.sqrt((n * mad ** 2 + 2 * w ** 2) / (n + 2)) + 1e-3
                lastw = wk
                x = Z[i]; scv = sc(x, (mu, s)); out.append((wk, scv > tau))
                seen[day] = seen.get(day, 0) + 1
                if S and seen[day] <= S and scv <= tau:
                    new = (1 - 0.05) * mu + 0.05 * x
                    if sc(new, t0) <= r_anchor:
                        mu = new; buf.append(x)
            res.setdefault(S, {})[u] = out
log("window FRR by week since enrolment at user-fold tau (5% of other-fold week-2 windows): pooled [macro]")
log("S supervised windows/day | wk1 | wk2 | wk4 | wk6 | wk8")
ul = list(res[0])
def wkfrr(S, k, us, macro=False):
    v = [[f for wk, f in res[S][u] if wk == k] for u in us]; v = [x for x in v if x]
    if not v: return np.nan
    return np.mean([np.mean(x) for x in v]) if macro else np.mean(np.concatenate(v))
for S in (0, 2, 5, 10):
    lab = "0 (static)" if S == 0 else str(S)
    log(f"{lab} | " + " | ".join(f"{wkfrr(S,k,ul)*100:.1f}% [{wkfrr(S,k,ul,True)*100:.1f}%]" for k in (1, 2, 4, 6, 8)))
log("\npaired difference (supervised - static), weeks 6-8 pooled window FRR, 95% bootstrap CI over users")
def late(S, us):
    v = np.concatenate([[f for wk, f in res[S][u] if 6 <= wk <= 8] for u in us]); return v.mean() if v.size else np.nan
for S in (2, 5, 10):
    pt = late(S, ul) - late(0, ul); bs = []
    for _ in range(B):
        us = list(rng.choice(ul, len(ul))); bs.append(late(S, us) - late(0, us))
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    log(f"S={S}: {pt*100:+.1f} pp [{lo*100:+.1f}, {hi*100:+.1f}] (static wk6-8 pooled FRR {late(0, ul)*100:.1f}%)")
log("\nCaveats: strong-auth proxy = first S windows/day (no timestamps in derived data); one anchor; no attacker in this run")
log("(supervised updates are only reachable by an attacker who has passed WebAuthn, spec §8).")
open(f"{OUT}/adapt_supervised_{cfg}.txt", "w").write("\n".join(lines) + "\n")
