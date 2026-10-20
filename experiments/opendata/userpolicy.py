"""Per-user threshold policies, biometric-menagerie analysis and cold-start curve on Tappy (cross-day).
Priors from a disjoint half of Tappy users (proxy for ZTBE's own consented population, decision D3).
Timeline per user: enrol = days 0-6, calibration = days 7-13 (genuine only, as if observed after
step-up-confirmed sessions), test = day >= 14. Decisions on blocks of K consecutive windows (mean score).
PD labels are NOT used (decision D7).  Usage: userpolicy.py [cfg=t60] [K=4]"""
import sys, os
import numpy as np
import evallib as E

DATA = os.environ.get("DATA", "/workspace/data")
OUT = os.path.join(os.path.dirname(__file__), "results")
cfg = sys.argv[1] if len(sys.argv) > 1 else "t60"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 4
rng = np.random.default_rng(20261021)
d = np.load(f"{DATA}/derived/tappy_{cfg}.npz")
X, U, DAY = d["X"], d["uid"], d["day"]
users = np.unique(U)
pop = rng.choice(users, len(users) // 2, replace=False)
mp = np.isin(U, pop)
prior = E.Prior(X[mp], U[mp])
Z = prior.z(X[~mp]); U = U[~mp]; DAY = DAY[~mp]
w = np.sqrt(prior.within) * 0.8
out = []
def log(s=""):
    print(s); out.append(s)

def template(z):
    mu = z.mean(0); mad = np.abs(z - mu).mean(0) if len(z) > 1 else np.zeros(z.shape[1])
    return mu, np.sqrt((len(z) * mad ** 2 + 2 * w ** 2) / (len(z) + 2)) + 1e-3

def score(z, t):
    return (np.abs(z - t[0]) / t[1]).mean(-1)

def blocks(ix):
    return [ix[b * K:(b + 1) * K] for b in range(len(ix) // K)]

# per-user split
S = {}
for u in np.unique(U):
    ix = np.flatnonzero(U == u); d0 = DAY[ix].min(); dd = DAY[ix] - d0
    en, ca, te = ix[dd < 7], ix[(dd >= 7) & (dd < 14)], ix[dd >= 14]
    if len(en) >= 3 and len(blocks(ca)) >= 2 and len(blocks(te)) >= 2:
        S[u] = dict(en=en, ca=ca, te=te, t=template(Z[en]))
ul = list(S)
log(f"# per-user policy study: tappy {cfg}, K={K} windows per decision block, {len(ul)} eval users (priors: {len(pop)} disjoint Tappy users)")
# genuine block scores (cal, test) and impostor block scores on test period (30 attackers x up to 3 blocks)
G = {u: np.array([score(Z[b], S[u]["t"]).mean() for b in blocks(S[u]["te"])]) for u in ul}
C = {u: np.array([score(Z[b], S[u]["t"]).mean() for b in blocks(S[u]["ca"])]) for u in ul}
I = {}
for u in ul:
    att = [a for a in ul if a != u]; sc = []
    for a in rng.choice(att, min(30, len(att)), replace=False):
        bl = blocks(S[a]["te"])
        for j in rng.choice(len(bl), min(3, len(bl)), replace=False):
            sc.append(score(Z[bl[j]], S[u]["t"]).mean())
    I[u] = np.array(sc)
allG = np.concatenate([G[u] for u in ul]); allI = np.concatenate([I[u] for u in ul]); allC = np.concatenate([C[u] for u in ul])

def report(name, flag_g, flag_i, unc_g=None, unc_i=None):
    frr = np.array([flag_g[u].mean() for u in ul]); far = np.array([1 - flag_i[u].mean() for u in ul])
    pooled_frr = np.concatenate([flag_g[u] for u in ul]).mean()
    pooled_far = 1 - np.concatenate([flag_i[u] for u in ul]).mean()
    s = (f"{name} | {pooled_frr*100:.1f}% | {frr.mean()*100:.1f}% | {np.percentile(frr,90)*100:.1f}% | {(frr>0.2).mean()*100:.0f}% | "
         f"{E.gini(frr):.2f} | {pooled_far*100:.1f}% | {np.percentile(far,90)*100:.1f}% | {(far>0.3).mean()*100:.0f}%")
    if unc_g is not None:
        s += f" | {np.concatenate([unc_g[u] for u in ul]).mean()*100:.1f}% | {np.concatenate([unc_i[u] for u in ul]).mean()*100:.1f}%"
    log(s)
    return frr, far

log("\n## threshold policies (flag = block score above threshold; FRR = genuine blocks flagged, FAR = impostor blocks NOT flagged)")
log("policy | FRR pooled | FRR mean/user | FRR p90 user | users FRR>20% | Gini FRR | FAR pooled | FAR p90 target | targets FAR>30% | uncertain gen | uncertain imp")
# P0 global, calibrated so 5% of pooled calibration blocks are flagged
tg = np.quantile(allC, 0.95)
report("P0 global (5% of calib. blocks)", {u: G[u] > tg for u in ul}, {u: I[u] > tg for u in ul})
# P1 per-user quantile threshold from calibration blocks (5% target), no cap
tu = {u: np.quantile(C[u], 0.95) for u in ul}
report("P1 per-user q95 of own calib.", {u: G[u] > tu[u] for u in ul}, {u: I[u] > tu[u] for u in ul})
# P2 per-user, capped: tau_u = min(max(q95_u, tg), tcap) where tcap = global thr at which pooled calibration-FAR... use impostor-free cap
for capq in (0.99, 0.995):
    tcap = np.quantile(allC, capq)
    tc = {u: min(max(tu[u], tg), tcap) for u in ul}
    report(f"P2 per-user, floor=P0, cap=q{capq*100:g} pooled calib.", {u: G[u] > tc[u] for u in ul}, {u: I[u] > tc[u] for u in ul})
# P3 z-norm: (s - mean_cal_u)/sd_cal_u, global threshold on normalised calibration scores
zn = lambda u, s: (s - C[u].mean()) / (C[u].std() + 1e-6)
zc = np.concatenate([zn(u, C[u]) for u in ul]); tz = np.quantile(zc, 0.95)
report("P3 z-norm on calib. scores", {u: zn(u, G[u]) > tz for u in ul}, {u: zn(u, I[u]) > tz for u in ul})
# P4 three bands on top of P2(cap 0.995): ok <= tau_u ; uncertain in (tau_u, tau_u + delta]; high > tau_u + delta
tcap = np.quantile(allC, 0.995); tc = {u: min(max(tu[u], tg), tcap) for u in ul}
for delta_q in (0.5,):
    dl = {u: delta_q * C[u].std() + 0.25 * (tc[u] - np.median(C[u])) for u in ul}
    hi_g = {u: G[u] > tc[u] + dl[u] for u in ul}; hi_i = {u: I[u] > tc[u] + dl[u] for u in ul}
    un_g = {u: (G[u] > tc[u]) & ~hi_g[u] for u in ul}; un_i = {u: (I[u] > tc[u]) & ~hi_i[u] for u in ul}
    report("P4 bands: high only (P2 cap .995 + margin)", hi_g, hi_i, un_g, un_i)

# P5 shrinkage per-user threshold: tau_u = (n_u*q95_u + n0*tg)/(n_u + n0), n_u = #calib blocks, n0 = 20 pseudo-blocks
for n0 in (10, 20):
    ts = {u: (len(C[u]) * tu[u] + n0 * tg) / (len(C[u]) + n0) for u in ul}
    report(f"P5 shrinkage q95 toward P0 (n0={n0})", {u: G[u] > ts[u] for u in ul}, {u: I[u] > ts[u] for u in ul})

# ---- trust model (Mondal & Bours style penalty/reward), window-level (K=1) sequences
log("\n## trust model over single windows: trust in [0,100], start 100; delta = clip(a*(tau - s), -P, +R); alarm when trust < 50 -> step-up, trust reset to 100")
log("tau (pooled calib. window quantile) | a | P | R | genuine alarms per 60 active windows (mean / p90 user) | impostor: P(alarm within 5 windows) / within 10 | mean windows to alarm")
cw = np.concatenate([score(Z[S[u]['ca']], S[u]['t']) for u in ul])
def run(seq, tau, a, P, R, cap=None):
    t, alarms, first = 100.0, 0, None
    for i, s in enumerate(seq):
        t = min(100.0, t + float(np.clip(a * (tau - s), -P, R)))
        if t < 50:
            alarms += 1; t = 100.0
            if first is None: first = i + 1
    return alarms, first
for q, a, P, R in ((0.8, 40, 40, 5), (0.8, 25, 30, 5), (0.9, 40, 40, 5), (0.9, 25, 30, 3), (0.95, 50, 50, 5)):
    tau = np.quantile(cw, q)
    gr = []
    for u in ul:
        seq = score(Z[S[u]['te']], S[u]['t']); al, _ = run(seq, tau, a, P, R); gr.append(60 * al / len(seq))
    fi = []
    for u in ul:
        for a_ in rng.choice([x for x in ul if x != u], min(10, len(ul) - 1), replace=False):
            seq = score(Z[S[a_]['te'][:30]], S[u]['t']); _, f = run(seq, tau, a, P, R); fi.append(f if f else 99)
    fi = np.array(fi)
    log(f"q{q*100:g} ({tau:.2f}) | {a} | {P} | {R} | {np.mean(gr):.2f} / {np.percentile(gr,90):.2f} | {(fi<=5).mean()*100:.0f}% / {(fi<=10).mean()*100:.0f}% | {np.mean(np.minimum(fi,30)):.1f}")

# ---- menagerie (Yager & Dunstone 2010 style): genuine mean vs impostor mean (as attacked target)
log("\n## biometric menagerie on test period (per user: mean genuine block score vs mean score when attacked)")
gm = np.array([G[u].mean() for u in ul]); im = np.array([I[u].mean() for u in ul])
gq, iq = np.quantile(gm, [0.25, 0.75]), np.quantile(im, [0.25, 0.75])
lab = dict(worms=((gm > gq[1]) & (im < iq[0])).sum(), chameleons=((gm < gq[0]) & (im < iq[0])).sum(),
           phantoms=((gm > gq[1]) & (im > iq[1])).sum(), doves=((gm < gq[0]) & (im > iq[1])).sum())
log(f"users {len(ul)}; expected per class if independent: {len(ul)/16:.1f}; observed: " + ", ".join(f"{k} {v}" for k, v in lab.items()))
log(f"Spearman(mean genuine, mean impostor) = {np.corrcoef(np.argsort(np.argsort(gm)), np.argsort(np.argsort(im)))[0,1]:.2f}")
# predictability: does calibration-week FRR (global thr) predict test FRR?
fc = np.array([(C[u] > tg).mean() for u in ul]); ft = np.array([(G[u] > tg).mean() for u in ul])
log(f"per-user FRR at P0: calibration week vs test period Spearman = {np.corrcoef(np.argsort(np.argsort(fc)), np.argsort(np.argsort(ft)))[0,1]:.2f}; "
    f"of users with calib FRR>20%, {((ft>0.2)&(fc>0.2)).sum()}/{(fc>0.2).sum()} still >20% in test")

# ---- cold start: enrol from first m windows (chronological), test = day >= 14
log("\n## cold start: template from the first m windows (any day < 14), test blocks from day >= 14, global threshold")
log("m windows | approx. active typing | users | EER (K=1) | FRR@FAR1% (K=1) | EER (K=4 blocks) | FAR@FRR5% (K=4)")
for m in (1, 2, 3, 5, 8, 12, 20, 30):
    g1, i1, gk, ik = [], [], [], []
    ok = []
    for u in np.unique(U):
        ix = np.flatnonzero(U == u); d0 = DAY[ix].min(); dd = DAY[ix] - d0
        pre, te = ix[dd < 14], ix[dd >= 14]
        if len(pre) >= 30 and len(blocks(te)) >= 2: ok.append((u, pre[:m], te))
    T = {u: template(Z[e]) for u, e, _ in ok}
    for u, e, te in ok:
        g1 += list(score(Z[te], T[u])); gk += [score(Z[b], T[u]).mean() for b in blocks(te)]
        for a, _, ta in [ok[j] for j in rng.choice(len(ok), min(30, len(ok)), replace=False) if ok[j][0] != u]:
            i1 += list(score(Z[ta[:6]], T[u]))
            bl = blocks(ta); ik += [score(Z[bl[j]], T[u]).mean() for j in rng.choice(len(bl), min(2, len(bl)), replace=False)]
    m1, mk = E.roc_metrics(g1, i1), E.roc_metrics(gk, ik)
    unit = int(cfg[1:]); act = f"{m*unit/60:.0f} min" if cfg[0] == "t" else f"{m*unit} keys"
    log(f"{m} | {act} | {len(ok)} | {m1['eer']*100:.1f}% | {m1['frr_far1']*100:.1f}% | {mk['eer']*100:.1f}% | {mk['far_frr5']*100:.1f}%")
open(f"{OUT}/userpolicy_{cfg}_K{K}.txt", "w").write("\n".join(out) + "\n")
import json
json.dump({"cfg": cfg, "K": K, "genuine": [[int(len(G[u])), int((G[u] > tg).sum())] for u in ul],
           "impostor": [[int(len(I[u])), int((I[u] <= tg).sum())] for u in ul]},
          open(f"{OUT}/userpolicy_{cfg}_K{K}_counts.json", "w"))
