"""Decision fusion over k consecutive windows (continuous-authentication operating points).
Score = mean scaled-Manhattan distance of k consecutive (non-overlapping) test windows.
Genuine: the user's own consecutive test windows. Impostor: k consecutive windows of another user (zero-effort),
up to 30 attackers per target. Usage: fuse.py <laser|tappy|aalto> <cfg>   (env as run_keystroke.py)."""
import sys, os
import numpy as np
import evallib as E
import run_keystroke as RK

ds, cfg = sys.argv[1], sys.argv[2]
S = RK.setup(ds, cfg)
prior = E.Prior(S["Xp"], S["up"]); Ze = prior.z(S["Xe"])
users = list(np.unique(S["ue"])); uidx = {u: i for i, u in enumerate(users)}
ue = np.array([uidx[u] for u in S["ue"]]); en, te = S["enroll"], S["test"]
nU, D = len(users), Ze.shape[1]
Tm = np.zeros((nU, D)); Tsd = np.zeros((nU, D)); w = np.sqrt(prior.within) * 0.8
for k in range(nU):
    z = Ze[en & (ue == k)]; Tm[k] = z.mean(0)
    mad = np.abs(z - z.mean(0)).mean(0) if len(z) > 1 else np.zeros(D)
    Tsd[k] = np.sqrt((len(z) * mad ** 2 + 2 * w ** 2) / (len(z) + 2)) + 1e-3
rng = np.random.default_rng(20261021)
tests = {k: np.flatnonzero(te & (ue == k)) for k in range(nU)}
lines = [f"# fusion over k consecutive windows: {ds} {cfg} ({S['note']}); eval users {nU}",
         "k | users with >= k test windows | genuine blocks | impostor blocks | EER | FRR@FAR1% | FRR@FAR0.1% | FAR@FRR5% | Gini FRR"]
for K in (1, 2, 4, 8, 16):
    gen, imp, gu = [], [], []
    ok = [k for k in range(nU) if len(tests[k]) >= K]
    if len(ok) < 5: break
    for t in ok:
        def blocks(ix):
            nb = len(ix) // K
            return [ix[b * K:(b + 1) * K] for b in range(nb)]
        for b in blocks(tests[t]):
            gen.append((np.abs(Ze[b] - Tm[t]) / Tsd[t]).mean()); gu.append(t)
        att = [a for a in ok if a != t]
        for a in rng.choice(att, min(30, len(att)), replace=False):
            bl = blocks(tests[a])
            for b in [bl[i] for i in rng.choice(len(bl), min(3, len(bl)), replace=False)]:
                imp.append((np.abs(Ze[b] - Tm[t]) / Tsd[t]).mean())
    m = E.roc_metrics(gen, imp)
    gen, gu = np.array(gen), np.array(gu)
    rej = gen > m["thr_eer"]
    per = [rej[gu == u].mean() for u in np.unique(gu)]
    lines.append(f"{K} | {len(ok)} | {len(gen)} | {len(imp)} | {m['eer']*100:.1f}% | {m['frr_far1']*100:.1f}% | {m['frr_far01']*100:.1f}% | {m['far_frr5']*100:.1f}% | {E.gini(per):.2f}")
tag = f"fuse_{ds}_{cfg}" + ("_selfprior" if os.environ.get("PRIOR") == "self" and ds == "tappy" else "")
open(os.path.join(RK.OUT, tag + ".txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
