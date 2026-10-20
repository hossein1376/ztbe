"""Template adaptation and poisoning on Tappy (cross-day, weeks).

Matcher: scaled Manhattan in population z-space (Aalto priors), template = (mu, s);
only mu is adapted (s frozen at enrolment). Policies:
  static        - never update
  naive         - EW update on every verified window (score <= thr_verify)
  gated         - EW update only if score <= thr_adapt (< thr_verify)        [spec 6.1]
  gated+anchor  - gated, and the updated mu must stay within r_anchor of the enrolment
                  template (multiple-anchor bound), else update rejected       [spec 6.3, Uludag]
  gated+anchor+sanitize - additionally roll back the last K updates when they drift
                  consistently in one direction (Biggio et al. 2015 sanitization)
Attack (Biggio-style boundary walk, perfect knowledge of current mu and s): each injected
window sits at distance just below thr_adapt from the current mu, on the line toward the
attacker's own mean. Success = attacker's own genuine windows accepted >= 50%.
Usage: python3 adapt.py [cfg]  -> results/adapt_<cfg>.txt
"""
import os, sys, numpy as np
import evallib as E
from run_keystroke import aalto_population, COMMON

DATA = os.environ.get("DATA", "/workspace/data")
OUT = os.path.join(os.path.dirname(__file__), "results")
cfg = sys.argv[1] if len(sys.argv) > 1 else "n200"
ETA = 0.05
lines = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lines.append(s)

d = np.load(f"{DATA}/derived/tappy_{cfg}.npz")
X, U, DAY = d["X"], d["uid"], d["day"]
Xp, up, _, _ = aalto_population(cfg, 20000)
prior = E.Prior(Xp[:, :COMMON], up)
Z = prior.z(X)
w = np.sqrt(prior.within) * 0.8 + 1e-3

users = []
for u in np.unique(U):
    ix = np.flatnonzero(U == u); d0 = DAY[ix].min()
    if DAY[ix].max() - d0 >= 28 and (DAY[ix] < d0 + 7).sum() >= 3:
        users.append(u)
log(f"# adaptation on Tappy {cfg}: users with >= 28 days span and >= 3 enrol windows: {len(users)}")

def dist(x, mu, s):
    return (np.abs(x - mu) / s).mean(-1)

tmpl = {}
for u in users:
    ix = np.flatnonzero(U == u); d0 = DAY[ix].min()
    e = ix[DAY[ix] < d0 + 7]
    z = Z[e]; mad = np.abs(z - z.mean(0)).mean(0)
    s = np.sqrt((len(z) * mad ** 2 + 2 * w ** 2) / (len(z) + 2)) + 1e-3
    tmpl[u] = (z.mean(0), s, ix[DAY[ix] >= d0 + 7], d0)

# global thresholds from static scores on week-2 data (genuine) vs other users (impostor)
rng = np.random.default_rng(5)
gs, is_ = [], []
for u in users:
    mu, s, later, d0 = tmpl[u]
    wk2 = later[DAY[later] < d0 + 14]
    gs += list(dist(Z[wk2], mu, s))
    others = rng.choice([v for v in users if v != u], 20, replace=False)
    for v in others:
        iv = np.flatnonzero(U == v); is_.append(dist(Z[rng.choice(iv)], mu, s))
m = E.roc_metrics(gs, is_)
thr_v = m["thr_eer"]
thr_a = float(np.quantile(gs, 0.5))             # adapt only on the better half of genuine windows
r_anchor = 1.35 * thr_v * 0.5                   # max drift of mu from anchor, in the same metric
log(f"thr_verify (EER on week 2) = {thr_v:.3f} (EER {m['eer']*100:.1f}%), thr_adapt = {thr_a:.3f}, r_anchor = {r_anchor:.3f}")

class Policy:
    """Template-update policy. flags: gate (dual threshold), anchor (bound to enrolment template),
    velocity (max drift per day), sanitize (roll back to checkpoint + freeze on consistent drift)."""
    def __init__(self, name, mu0, s, update=True, gate=False, anchor=False, velocity=False, sanitize=False):
        self.name, self.mu0, self.s = name, mu0, s
        self.mu = mu0.copy(); self.update, self.gate, self.anchor, self.velocity, self.sanitize = update, gate, anchor, velocity, sanitize
        self.day = None; self.mu_day = mu0.copy(); self.hist = []; self.ckpt = mu0.copy(); self.frozen = 0; self.n_upd = 0
    def observe(self, x, day):
        sc = dist(x, self.mu, self.s)
        ok = sc <= thr_v
        if day != self.day:
            self.day, self.mu_day = day, self.mu.copy()
        if not (ok and self.update):
            return ok
        if self.frozen > 0:
            self.frozen -= 1; return ok
        if self.gate and sc > thr_a:
            return ok
        new = (1 - ETA) * self.mu + ETA * x
        if self.anchor and dist(new, self.mu0, self.s) > r_anchor:
            return ok
        if self.velocity and dist(new, self.mu_day, self.s) > v_max:
            return ok
        if self.sanitize:
            if not self.hist:
                self.ckpt = self.mu.copy()
            self.hist.append(new - self.mu)
            if len(self.hist) >= 10:
                h = np.array(self.hist)
                tot = h.sum(0)
                cos = (h @ tot) / (np.linalg.norm(h, axis=1) * np.linalg.norm(tot) + 1e-9)
                self.hist = []
                if np.mean(cos) > 0.5:                 # consistently biased drift: roll back + freeze
                    self.mu = self.ckpt.copy(); self.frozen = 200
                    return ok
        self.mu = new; self.n_upd += 1
        return ok


POL = [("static", dict(update=False)), ("naive", dict()), ("gated", dict(gate=True)),
       ("gated+anchor", dict(gate=True, anchor=True)), ("gated+anchor+velocity", dict(gate=True, anchor=True, velocity=True)),
       ("gated+anchor+velocity+sanitize", dict(gate=True, anchor=True, velocity=True, sanitize=True))]
v_max = r_anchor / 14

log("\n## genuine replay: FRR by week since enrolment (global thr_verify) - pooled over windows [macro mean over users]")
log("policy | " + " | ".join(f"wk{k}" for k in (1, 2, 4, 6, 8)) + " | updates/user | impostor FAR after replay")
for name, kw in POL:
    per = {}; far = []; nupd = []
    for u in users:
        mu0, s, later, d0 = tmpl[u]
        P = Policy(name, mu0, s, **kw)
        for i in later:
            acc = P.observe(Z[i], DAY[i])
            per.setdefault((DAY[i] - d0) // 7, {}).setdefault(u, []).append(not acc)
        nupd.append(P.n_upd)
        for v in rng.choice([x for x in users if x != u], 10, replace=False):
            iv = np.flatnonzero(U == v); far.append(dist(Z[rng.choice(iv)], P.mu, s) <= thr_v)
    def cell(k):
        if k not in per: return "-"
        allv = np.concatenate([np.array(v) for v in per[k].values()])
        mac = np.mean([np.mean(v) for v in per[k].values()])
        return f"{allv.mean()*100:.1f}% [{mac*100:.1f}%]"
    log(f"{name} | " + " | ".join(cell(k) for k in (1, 2, 4, 6, 8)) + f" | {np.median(nupd):.0f} | {np.mean(far)*100:.1f}%")

log("\n## poisoning: perfect-knowledge boundary walk (Biggio et al.), 50 injected windows per day")
log("each injected window sits just inside the adapt gate on the line from current mu to the attacker's mean")
log("policy | attack days | takeover rate (attacker's own windows accepted >= 50%) | median attacker acceptance | victim FRR after attack")
pairs = [(u, v) for u in users for v in rng.choice([x for x in users if x != u], 3, replace=False)]
for name, kw in POL:
    for days in (1, 7, 28):
        succ, accs, vfrr = [], [], []
        for u, v in pairs:
            mu0, s, later, d0 = tmpl[u]
            iv = np.flatnonzero(U == v); mu_a = Z[iv].mean(0)
            P = Policy(name, mu0, s, **kw)
            for dday in range(days):
                for _ in range(50):
                    dd = dist(mu_a, P.mu, s)
                    x = mu_a.copy() if dd <= 0.98 * thr_a else P.mu + (mu_a - P.mu) * (0.98 * thr_a / dd)
                    P.observe(x, 10000 + dday)
            acc = np.mean(dist(Z[iv], P.mu, s) <= thr_v)
            accs.append(acc); succ.append(acc >= 0.5)
            vfrr.append(np.mean(dist(Z[later], P.mu, s) > thr_v))
        log(f"{name} | {days} | {np.mean(succ)*100:.1f}% | {np.median(accs)*100:.1f}% | {np.mean(vfrr)*100:.1f}%")
base = [np.mean(dist(Z[np.flatnonzero(U == v)], tmpl[u][0], tmpl[u][1]) <= thr_v) >= 0.5 for u, v in pairs]
log(f"(no attack, static template: attacker's own windows accepted >= 50% for {np.mean(base)*100:.1f}% of pairs)")
os.makedirs(OUT, exist_ok=True)
open(f"{OUT}/adapt_{cfg}.txt", "w").write("\n".join(lines) + "\n")
