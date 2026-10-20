"""Round-2 evaluation harness (review round 1, M2/M4/M5/M6/M7/M9 and M1 bound).

- User-fold calibration: users are split into 2 folds (seed). For each fold, the population prior, tau_g (block)
  and tau_w (window, trust model) come ONLY from the other fold's users; metrics are computed on the held-out fold.
- Timeline per user (as userpolicy.py): enrol days 0-6, calibration days 7-13 (genuine), test day >= 14.
- 95% CIs: percentile bootstrap over evaluation users (B resamples; a target's impostor blocks move with it).
- Pooled AND macro (per-user mean) FRR/FAR; p90 user FRR; Gini.
- Policies at their nominal settings AND at matched pooled FAR (sweep of each policy's knob; FRR read at FAR=10%).
- Trust model: genuine trust resets at the start of each calendar day (session proxy) and after an alarm;
  impostor runs = 30 consecutive test windows of another held-out user, starting at trust 100 (right-censored at 30).
- Device-confound bound: impostor acceptance split by whether the attacker's timer quantum equals the target's.
- Cold start: template from the first m windows; tau_g fold-calibrated with m-window templates; all users with
  >= m pre-test windows (not only heavy typists).
Usage: eval2.py <cfg> [feats=all|v21] [subset=all|q3.9] [K=4] [B=1000]   -> results/eval2_<cfg>_<feats>_<subset>.txt
PD labels are not used (D7)."""
import sys, os
import numpy as np
import evallib as E

DATA = os.environ.get("DATA", "/workspace/data"); OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
cfg = sys.argv[1]; feats = sys.argv[2] if len(sys.argv) > 2 else "all"; subset = sys.argv[3] if len(sys.argv) > 3 else "all"
K = int(sys.argv[4]) if len(sys.argv) > 4 else 4; B = int(sys.argv[5]) if len(sys.argv) > 5 else 1000
SEED = 20261021
rng = np.random.default_rng(SEED)
d = np.load(f"{DATA}/derived/tappy_{cfg}.npz")
X, U, DAY, names = d["X"], d["uid"], d["day"], list(d["names"])
# timer quantum per user: from the v2 extraction (same users), else unknown
qmap = {}
for src in ("hyb", "s60"):
    p = f"{DATA}/derived/tappy_{src}.npz"
    if os.path.exists(p):
        e = np.load(p); qmap.update(dict(zip(e["uid"], e["q"])))
Q = np.array([qmap.get(u, -2.0) for u in U])
V21 = (["pp_median", "rollover_frac", "hold_mu_L", "hold_mu_R", "hold_mu_S", "hold_sd_L", "hold_sd_R"] +
       [f"pp_mu_{t}" for t in ("LL", "LR", "LS", "RL", "RR", "RS", "SL", "SR")] +
       [f"rp_mu_{t}" for t in ("LL", "LR", "LS", "RL", "RR", "SL")])
if feats == "v21":
    X = X[:, [names.index(n) for n in V21]]
if subset == "q3.9":
    keep = np.isclose(Q, 3.90625); X, U, DAY, Q = X[keep], U[keep], DAY[keep], Q[keep]
out = []
def log(s=""): print(s, flush=True); out.append(s)

def blocks(ix): return [ix[b * K:(b + 1) * K] for b in range(len(ix) // K)]
def split(u):
    ix = np.flatnonzero(U == u); dd = DAY[ix] - DAY[ix].min()
    return ix[dd < 7], ix[(dd >= 7) & (dd < 14)], ix[dd >= 14], ix[dd < 14]

users = np.unique(U)
fold = dict(zip(users, rng.permutation(np.arange(len(users)) % 2)))
info = {u: split(u) for u in users}
elig = [u for u in users if len(info[u][0]) >= 3 and len(blocks(info[u][1])) >= 2 and len(blocks(info[u][2])) >= 2]
log(f"# eval2: tappy {cfg}, features={feats} ({X.shape[1]}), subset={subset}, K={K}, user-fold calibration (2 folds, seed {SEED}), bootstrap B={B}")
log(f"users in file {len(users)}; eligible (enrol>=3 win, calib>=2 blocks, test>=2 blocks) {len(elig)}")

class Fold:
    def __init__(self, f):
        self.f = f
        pop_u = [u for u in users if fold[u] != f]
        m = np.isin(U, pop_u)
        self.prior = E.Prior(X[m], U[m]); self.Z = self.prior.z(X); self.w = 0.8 * np.sqrt(self.prior.within)
        self.pop = [u for u in elig if fold[u] != f]; self.ev = [u for u in elig if fold[u] == f]
    def tmpl(self, ix):
        z = self.Z[ix]; mu = z.mean(0); n = len(z)
        mad = np.abs(z - mu).mean(0) if n > 1 else np.zeros(z.shape[1])   # mean absolute deviation
        return mu, np.sqrt((n * mad ** 2 + 2 * self.w ** 2) / (n + 2)) + 1e-3
    def sc(self, ix, t): return (np.abs(self.Z[ix] - t[0]) / t[1]).mean(-1)

def evaluate(Fo):
    T = {u: Fo.tmpl(info[u][0]) for u in elig}
    C = {u: np.array([Fo.sc(b, T[u]).mean() for b in blocks(info[u][1])]) for u in elig}
    Cw = {u: Fo.sc(info[u][1], T[u]) for u in elig}
    tg = np.quantile(np.concatenate([C[u] for u in Fo.pop]), 0.95)
    tw = np.quantile(np.concatenate([Cw[u] for u in Fo.pop]), 0.90)
    R = {}
    for u in Fo.ev:
        G = np.array([Fo.sc(b, T[u]).mean() for b in blocks(info[u][2])])
        Ii, Iq = [], []
        att = [a for a in Fo.ev if a != u]
        for a in rng.choice(att, min(30, len(att)), replace=False):
            bl = blocks(info[a][2])
            for j in rng.choice(len(bl), min(3, len(bl)), replace=False):
                Ii.append(Fo.sc(bl[j], T[u]).mean()); Iq.append(Q[info[a][2][0]] == Q[info[u][2][0]] and Q[info[u][2][0]] > 0)
        # trust sequences
        te = info[u][2]; days = DAY[te]
        gseq = [Fo.sc(te[days == dd], T[u]) for dd in np.unique(days)]
        iseq = [Fo.sc(info[a][2][:30], T[u]) for a in rng.choice(att, min(10, len(att)), replace=False)]
        R[u] = dict(G=G, C=C[u], I=np.array(Ii), Iq=np.array(Iq, bool), gseq=gseq, iseq=iseq, nwin=len(te))
    return R, tg, tw, C

folds = [Fold(0), Fold(1)]
RES, TG, TW = {}, {}, {}
for Fo in folds:
    R, tg, tw, C = evaluate(Fo)
    for u in R: RES[u] = R[u]; TG[u] = tg; TW[u] = tw
ul = list(RES)
log(f"evaluated users {len(ul)}; tau_g per fold {sorted(set(np.round(list(TG.values()), 3)))}; tau_w per fold {sorted(set(np.round(list(TW.values()), 3)))}")

def boot(fn, n=B):
    """fn(list_of_users) -> scalar; returns (point, lo, hi)"""
    pt = fn(ul); bs = []
    for _ in range(n):
        bs.append(fn(list(rng.choice(ul, len(ul), replace=True))))
    lo, hi = np.nanpercentile(bs, [2.5, 97.5]); return pt, lo, hi
def f3(t, pct=True): return f"{t[0]*100:.1f}% [{t[1]*100:.1f}, {t[2]*100:.1f}]" if pct else f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"

# ---- policies: flags given knob
def thr_P0(u, q): return TG[u] if q is None else np.quantile(np.concatenate([RES[v]["C"] for v in ul if v != u] ), q)
def policy_thr(name, u, q):
    C = RES[u]["C"]
    if name == "P0": return TG[u] if q is None else q_pool[q]
    if name == "P1": return np.quantile(C, 0.95 if q is None else q)
    if name == "P5":
        qq = 0.95 if q is None else q; tg = TG[u] if q is None else q_pool[q]; n = len(C)
        return (n * np.quantile(C, qq) + 20 * tg) / (n + 20)
    if name == "P3":
        z = 1.645 if q is None else q
        return C.mean() + z * (C.std() + 1e-6)
# pooled calibration quantiles per fold are needed for sweeps: approximate with fold-specific pooled calib of the *other* fold
popC = {}
for Fo in folds:
    T = {u: Fo.tmpl(info[u][0]) for u in Fo.pop}
    popC[id(Fo)] = np.concatenate([[Fo.sc(b, T[u]).mean() for b in blocks(info[u][1])] for u in Fo.pop])
ufold = {u: folds[0] if u in folds[0].ev else folds[1] for u in ul}

def counts(name, knob):
    rows = {}
    for u in ul:
        r = RES[u]
        if name in ("P0", "P5") and knob is not None:
            global q_pool
            q_pool = {knob: np.quantile(popC[id(ufold[u])], knob)}
        t = policy_thr(name, u, knob)
        rows[u] = (len(r["G"]), int((r["G"] > t).sum()), len(r["I"]), int((r["I"] <= t).sum()))
    return rows
def metr(rows, us):
    a = np.array([rows[u] for u in us], float)
    frr_p = a[:, 1].sum() / a[:, 0].sum(); far_p = a[:, 3].sum() / a[:, 2].sum()
    frr_u = a[:, 1] / a[:, 0]; far_u = a[:, 3] / a[:, 2]
    return dict(frr_p=frr_p, far_p=far_p, frr_m=frr_u.mean(), far_m=far_u.mean(), frr_p90=np.percentile(frr_u, 90), gini=E.gini(frr_u))

log("\n## A. policies at nominal settings (user-fold calibrated tau_g); 95% bootstrap CI over users")
log("policy | FRR pooled | FRR macro | FRR p90 user | Gini FRR | FAR pooled | FAR macro")
for name, lab in (("P0", "P0 global tau_g (5% of other-fold calib. blocks)"), ("P1", "P1 per-user q95 own calib."),
                  ("P5", "P5 shrinkage (n0=20) to tau_g"), ("P3", "P3 z-norm, z=1.645")):
    rows = counts(name, None)
    cell = [f3(boot(lambda us, k=k: metr(rows, us)[k]), pct=(k != "gini")) for k in ("frr_p", "frr_m", "frr_p90", "gini", "far_p", "far_m")]
    log(f"{lab} | " + " | ".join(cell))

log("\n## B. policies at matched pooled FAR (each policy's knob swept; FRR interpolated where pooled FAR = target). Point estimate + bootstrap CI (knob re-matched per resample)")
grids = {"P0": np.linspace(0.50, 0.995, 60), "P1": np.linspace(0.50, 1.0, 60), "P5": np.linspace(0.50, 0.995, 60), "P3": np.linspace(-1.0, 4.0, 60)}
cache = {n: [counts(n, float(k)) for k in g] for n, g in grids.items()}
def frr_at(n, us, target, macro=False):
    pts = [metr(rw, us) for rw in cache[n]]
    far = np.array([p["far_p"] for p in pts]); frr = np.array([p["frr_m" if macro else "frr_p"] for p in pts])
    o = np.argsort(far)
    if target < far.min() or target > far.max(): return np.nan
    return float(np.interp(target, far[o], frr[o]))
log("policy | FRR pooled @FAR 10% | FRR macro @FAR 10% | FRR pooled @FAR 5% | FRR macro @FAR 5%")
for n in grids:
    cells = [f3(boot(lambda us, n=n, t=t, m=m: frr_at(n, us, t, m), n=min(B, 300))) for t, m in ((0.10, False), (0.10, True), (0.05, False), (0.05, True))]
    log(f"{n} | " + " | ".join(cells))

log("\n## C. trust model (tau_w = q90 of other-fold calib. windows; a=40, P=40, R=5; reset per day and after alarm)")
def run(seq, tau, a=40, P=40, R=5):
    t, al, first = 100.0, 0, None
    for i, s in enumerate(seq):
        t = min(100.0, t + float(np.clip(a * (tau - s), -P, R)))
        if t < 50:
            al += 1; t = 100.0
            if first is None: first = i + 1
    return al, first
TR = {}
for u in ul:
    al = sum(run(s, TW[u])[0] for s in RES[u]["gseq"]); fi = [run(s, TW[u])[1] or 99 for s in RES[u]["iseq"]]
    TR[u] = (al, RES[u]["nwin"], np.array(fi))
gen_rate = lambda us: 60 * sum(TR[u][0] for u in us) / sum(TR[u][1] for u in us)
gen_macro = lambda us: np.mean([60 * TR[u][0] / TR[u][1] for u in us])
gen_p90 = lambda us: np.percentile([60 * TR[u][0] / TR[u][1] for u in us], 90)
det = lambda k: (lambda us: np.mean(np.concatenate([TR[u][2] for u in us]) <= k))
log(f"genuine alarms per 60 windows: pooled {f3(boot(gen_rate), False)}; macro {f3(boot(gen_macro), False)}; p90 user {f3(boot(gen_p90), False)}")
log(f"impostor (different device, zero-effort) alarm within 5 windows {f3(boot(det(5)))}; within 10 {f3(boot(det(10)))}; within 30 {f3(boot(det(30)))}")

log("\n## D. device-confound bound: impostor blocks accepted (score <= tau_g) by whether attacker's timer quantum == target's")
same = lambda us: np.mean(np.concatenate([RES[u]["I"][RES[u]["Iq"]] <= TG[u] for u in us]))
diff = lambda us: np.mean(np.concatenate([RES[u]["I"][~RES[u]["Iq"]] <= TG[u] for u in us]))
ns = sum(RES[u]["Iq"].sum() for u in ul); nd = sum((~RES[u]["Iq"]).sum() for u in ul)
log(f"same-quantum impostor blocks {ns}: FAR {f3(boot(same))}; different/unknown-quantum blocks {nd}: FAR {f3(boot(diff))}")
log(f"ratio same/different FAR (point) = {same(ul)/max(diff(ul),1e-9):.2f}")

log("\n## E. cold start (template from first m windows; tau_g from other fold with m-window templates; users with >= m pre-test windows and >= 2 test blocks)")
log("m | users | block EER (a-posteriori) | FRR @ fold tau_g | FAR @ fold tau_g")
for m in (1, 2, 3, 5, 8, 12, 20):
    g_all, i_all, fr, fa, nu = [], [], [], [], 0
    for Fo in folds:
        el = [u for u in users if len(info[u][3]) >= m and len(blocks(info[u][2])) >= 2]
        T = {u: Fo.tmpl(info[u][3][:m]) for u in el}
        popu = [u for u in el if fold[u] != Fo.f and len(blocks(info[u][1])) >= 1]
        cal = [Fo.sc(b, T[u]).mean() for u in popu for b in blocks(info[u][1])]
        if not cal: continue
        tg = np.quantile(cal, 0.95)
        ev = [u for u in el if fold[u] == Fo.f]
        for u in ev:
            nu += 1
            g = [Fo.sc(b, T[u]).mean() for b in blocks(info[u][2])]
            att = [a for a in ev if a != u]
            im = []
            for a in rng.choice(att, min(20, len(att)), replace=False):
                bl = blocks(info[a][2]); im += [Fo.sc(bl[j], T[u]).mean() for j in rng.choice(len(bl), min(2, len(bl)), replace=False)]
            g_all += g; i_all += im; fr += [x > tg for x in g]; fa += [x <= tg for x in im]
    mm = E.roc_metrics(g_all, i_all)
    log(f"{m} | {nu} | {mm['eer']*100:.1f}% | {np.mean(fr)*100:.1f}% | {np.mean(fa)*100:.1f}%")
os.makedirs(OUT, exist_ok=True)
open(f"{OUT}/eval2_{cfg}_{feats}_{subset}.txt", "w").write("\n".join(out) + "\n")
