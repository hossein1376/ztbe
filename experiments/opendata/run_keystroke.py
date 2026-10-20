"""Eberz-style evaluation of unprotected vs protected keystroke templates.

usage: python3 run_keystroke.py <aalto|laser|tappy> <cfg> [--guess]
Results: results/<dataset>_<cfg>.txt and results/<dataset>_<cfg>.json
"""
import os, sys, json
import numpy as np
import evallib as E

DATA = os.environ.get("DATA", "/workspace/data")
OUT = os.path.join(os.path.dirname(__file__), "results")
N_POP = int(os.environ.get("N_POP", "20000"))
N_EVAL = int(os.environ.get("N_EVAL", "3000"))
COMMON = 34          # features shared by all datasets (no backspace / modifier hold)
lines = []


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lines.append(s)


def load_aalto(cfg, n_pop=N_POP):
    d = np.load(f"{DATA}/derived/aalto_{cfg}.npz")
    return d["X"], d["uid"], d["widx"]


def aalto_population(cfg, n_pop, exclude=()):
    X, uid, w = load_aalto(cfg)
    users = np.unique(uid)
    users = np.setdiff1d(users, np.asarray(exclude))
    rng = np.random.default_rng(7)
    pop = rng.choice(users, size=min(n_pop, len(users)), replace=False)
    m = np.isin(uid, pop)
    return X[m], uid[m], w[m], users


def templates_from(Z, uid):
    u, inv = np.unique(uid, return_inverse=True)
    s = np.zeros((len(u), Z.shape[1])); np.add.at(s, inv, Z)
    return u, (s / np.bincount(inv)[:, None]).astype(np.float32)


def setup(dataset, cfg):
    """Returns dict with Zpop/uidpop (population, priors+dictionary), Z/uid/enroll/test (evaluation)."""
    if dataset == "aalto":
        X, uid, w = load_aalto(cfg)
        users = np.unique(uid[w >= 1])                        # >= 2 windows
        rng = np.random.default_rng(7)
        perm = rng.permutation(users)
        pop, ev = perm[:N_POP], perm[N_POP:N_POP + N_EVAL]
        mp, me = np.isin(uid, pop), np.isin(uid, ev)
        Xp, up = X[mp], uid[mp]
        Xe, ue, we = X[me], uid[me], w[me]
        enroll, test = E.split_chrono(ue, we, 0.5, min_win=2)
        note = "intra-session (single Aalto session; first half enrol, second half test)"
    elif dataset == "laser":
        d = np.load(f"{DATA}/derived/laser_{cfg}.npz")
        Xe, ue, se, we = d["X"], d["uid"], d["sess"], d["widx"]
        Xp, up, _, _ = aalto_population(cfg, N_POP)
        mode = os.environ.get("LASER_MODE", "cross")
        if mode == "cross":
            enroll, test = se == 1, se >= 2
            note = "cross-session (enrol session 1, test sessions 2-4); priors+dictionary from Aalto"
        else:
            enroll = np.zeros(len(ue), bool); test = np.zeros(len(ue), bool)
            for u in np.unique(ue):
                ix = np.flatnonzero((ue == u) & (se == 1)); k = len(ix) // 2
                enroll[ix[:k]] = True; test[ix[k:]] = True
            note = "intra-session (session 1 halves); priors+dictionary from Aalto"
    elif dataset == "tappy":
        d = np.load(f"{DATA}/derived/tappy_{cfg}.npz")
        Xe, ue, de = d["X"], d["uid"], d["day"]
        if os.environ.get("PRIOR", "aalto") == "self":
            users = np.unique(ue); rng = np.random.default_rng(11)
            pop = rng.choice(users, len(users) // 2, replace=False)
            mp = np.isin(ue, pop)
            Xp, up = Xe[mp], ue[mp]
            Xe, ue, de = Xe[~mp], ue[~mp], de[~mp]
            src = "half of Tappy users (in-domain)"
        else:
            acfg = {"n400": "n200", "t300": "t120"}.get(cfg, cfg)   # Aalto sessions are too short for these windows
            Xp, up, _, _ = aalto_population(acfg, N_POP)
            Xp = Xp[:, :COMMON]
            src = f"Aalto {acfg} windows (34 common features)"
        enroll = np.zeros(len(ue), bool); test = np.zeros(len(ue), bool)
        gap = int(os.environ.get("TAPPY_GAP_DAYS", "7"))
        for u in np.unique(ue):
            ix = np.flatnonzero(ue == u); d0 = de[ix].min()
            enroll[ix[de[ix] < d0 + 7]] = True          # first week enrol
            test[ix[de[ix] >= d0 + 7 + gap]] = True       # test from week (1+gap/7) on
        note = f"cross-day (enrol first 7 days, test >= {7+gap} days after first day); priors+dictionary from {src}"
    elif dataset in ("sapimouse", "balabit"):
        d = np.load(f"{DATA}/derived/{dataset}_{cfg}.npz")
        Xe, ue, role = d["X"], d["uid"], d["role"]
        enroll, test = role == "enrol", role == "test"
        if dataset == "sapimouse":
            users = np.unique(ue); rng = np.random.default_rng(7); pop = rng.choice(users, len(users) // 2, replace=False)
            mp = np.isin(ue, pop)
            Xp, up = Xe[mp], ue[mp]
            Xe, ue, enroll, test = Xe[~mp], ue[~mp], enroll[~mp], test[~mp]
            note = "same-day cross-session (enrol 3-min session, test 1-min session); priors+dictionary from 60 disjoint SapiMouse users"
        else:
            gen = d["genuine"]
            mp = enroll
            Xp, up = Xe[mp], ue[mp]
            illegal = test & (gen == 0)
            ill_uid = ue.copy()
            note = "cross-session (enrol training sessions, test labelled test sessions; impostors = sessions labelled is_illegal=1 plus zero-effort others); priors from Balabit training sessions of the same 10 users (optimistic)"
            ok = [u for u in np.unique(ue)]
            Xe = np.nan_to_num(Xe, nan=np.nan)
            return dict(Xp=Xp, up=up, Xe=Xe, ue=ue, enroll=enroll, test=test & (gen == 1), illegal=illegal,
                        note=note, names=d["names"])
        return dict(Xp=Xp, up=up, Xe=Xe, ue=ue, enroll=enroll, test=test, note=note, names=d["names"])
    Xe = Xe[:, :Xp.shape[1]]
    # keep users with >=1 enrol and >=1 test window
    ok = [u for u in np.unique(ue) if enroll[ue == u].any() and test[ue == u].any()]
    keep = np.isin(ue, ok)
    names = np.load(f"{DATA}/derived/aalto_n100.npz")["names"]
    return dict(Xp=Xp, up=up, Xe=Xe[keep], ue=ue[keep], enroll=enroll[keep], test=test[keep], note=note, names=names)


def main(dataset, cfg, do_guess):
    S = setup(dataset, cfg)
    prior = E.Prior(S["Xp"], S["up"])
    Zp = prior.z(S["Xp"]); Ze = prior.z(S["Xe"])
    lda = E.LDA(Zp, S["up"], k=16)
    users = list(np.unique(S["ue"]))
    nU = len(users); D = Ze.shape[1]
    uidx = {u: i for i, u in enumerate(users)}
    en, te = S["enroll"], S["test"]
    ue = np.array([uidx[u] for u in S["ue"]])
    Zt = Ze[te]; ut = ue[te]
    log(f"# {dataset} {cfg}: {S['note']}")
    log(f"population users {len(np.unique(S['up']))} windows {len(Zp)}; eval users {nU}; enrol windows {en.sum()} test windows {te.sum()}; D={D}")
    # templates
    Tm = np.zeros((nU, D), np.float32); Tsd = np.zeros((nU, D), np.float32); ne = np.zeros(nU)
    for k in range(nU):
        z = Ze[en & (ue == k)]; ne[k] = len(z)
        Tm[k] = z.mean(0)
        mad = np.abs(z - z.mean(0)).mean(0) if len(z) > 1 else np.zeros(D)
        w = np.sqrt(prior.within) * 0.8                   # population within-user spread (MAD ~ 0.8 sd)
        Tsd[k] = np.sqrt((len(z) * mad ** 2 + 2 * w ** 2) / (len(z) + 2)) + 1e-3
    log(f"enrol windows per user: median {np.median(ne):.0f} min {ne.min():.0f}")
    if "illegal" in S:
        il = S["illegal"]
        Zt = np.vstack([Ze[te], Ze[il]]); ut = np.r_[ue[te], ue[il]]
        G, I = E.pairs(ue[te], list(range(nU)), n_imp=min(30, nU - 1))
        off = te.sum()
        extra = np.array([(ue[il][j], off + j, nU) for j in range(il.sum())])
        I = np.vstack([I, extra]) if len(extra) else I
        log(f"balabit: {il.sum()} windows from sessions labelled illegal added as impostor probes")
    else:
        G, I = E.pairs(ut, list(range(nU)), n_imp=min(30, nU - 1))
    R = {}

    # ---- per-feature variation
    order = np.argsort(-prior.fisher)
    names = list(S["names"])[:D]
    # within-user (test windows around own enrol template) vs between-user spread on eval set
    wsd = np.sqrt(np.mean((Zt - Tm[ut]) ** 2, 0)); bsd = Tm.std(0)
    log("\n## per-feature variation (z-units; pop = population within/between; eval = test windows vs own enrol template)")
    log("feature | pop ICC | pop Fisher | eval within-sd | eval between-sd | ratio within/between")
    for j in order:
        log(f"{names[j]} | {prior.icc[j]:.2f} | {prior.fisher[j]:.2f} | {wsd[j]:.2f} | {bsd[j]:.2f} | {wsd[j]/max(bsd[j],1e-6):.2f}")
    R["feature_var"] = {names[j]: dict(icc=float(prior.icc[j]), fisher=float(prior.fisher[j]), within=float(wsd[j]), between=float(bsd[j])) for j in range(D)}

    # ---- unprotected matchers
    def sm(tk, pi):
        return (np.abs(Zt[pi] - Tm[tk]) / Tsd[tk]).mean(1)
    Le = lda(Ze); Lt = lda(Zt)
    TL = np.vstack([Le[en & (ue == k)].mean(0) for k in range(nU)])
    def ldad(tk, pi):
        return np.sqrt(((Lt[pi] - TL[tk]) ** 2).mean(1))
    res = []
    for name, fn in [("unprotected scaled-Manhattan", sm), ("unprotected LDA-16 Euclidean", ldad)]:
        res.append(E.evaluate(fn, nU, G, I, name))

    # ---- binary (protected-template candidates)
    fsel = order[:16]
    binspecs = [
        ("Gray m=1 (sign), all", lambda Z: E.encode(Z, prior, "gray", 2)),
        ("Gray m=2, all", lambda Z: E.encode(Z, prior, "gray", 4)),
        ("Gray m=3, all", lambda Z: E.encode(Z, prior, "gray", 8)),
        ("LSSC S=4, all", lambda Z: E.encode(Z, prior, "lssc", 4)),
        ("LSSC S=8, all", lambda Z: E.encode(Z, prior, "lssc", 8)),
        ("pop-mask top16 Gray m=2", lambda Z: E.encode(Z, prior, "gray", 4, fsel)),
        ("pop-mask top16 LSSC S=8", lambda Z: E.encode(Z, prior, "lssc", 8, fsel)),
    ]
    # LDA-binarized: priors for LDA dims from population
    Lp = lda(Zp)
    class P2: pass
    pl = P2(); pl.q = {S_: np.quantile(Lp, np.arange(1, S_) / S_, axis=0) for S_ in (2, 4, 8)}
    binspecs += [
        ("LDA-16 sign (16 bit)", lambda Z: E.encode(lda(Z), pl, "gray", 2)),
        ("LDA-16 LSSC S=8 (112 bit)", lambda Z: E.encode(lda(Z), pl, "lssc", 8)),
    ]
    bin_out = {}
    for name, enc in binspecs:
        Bt = enc(Zt); Tb = enc(Tm)
        n = Bt.shape[1]
        def hd(tk, pi, Bt=Bt, Tb=Tb, n=n):
            return (Bt[pi] != Tb[tk]).sum(1) / n
        m = E.evaluate(hd, nU, G, I, f"{name} [n={n}]")
        m["n"] = n; m["dof"] = E.daugman_dof(m["imp"])
        res.append(m); bin_out[name] = (enc, Bt, Tb, m)
    # DROBA per user (user-specific helper data)
    for L, bmax, nm in [(64, 3, "DROBA L=64 (user-specific alloc)"), (16, 1, "1-bit DROBA-style top16 (user-specific mask)")]:
        allocs = [E.droba_alloc(Tm[k], np.maximum(Tsd[k] / 0.8, 0.05), prior, L, bmax) for k in range(nU)]
        Tb = [E.droba_encode(Tm[k:k + 1], prior, allocs[k])[0] for k in range(nU)]
        def hd(tk, pi, allocs=allocs, Tb=Tb):
            out = np.empty(len(tk))
            for k in np.unique(tk):
                s = tk == k
                out[s] = (E.droba_encode(Zt[pi[s]], prior, allocs[k]) != Tb[k]).mean(1)
            return out
        m = E.evaluate(hd, nU, G, I, f"{nm} [n={L}]"); m["n"] = L; m["dof"] = E.daugman_dof(m["imp"])
        res.append(m)

    log("\n## matching performance (global threshold; zero-effort impostors never used in training)")
    log("variant | EER | FRR@FAR1% | FAR@FRR10% | gen BER mean/p90 | imp BER mean/p5 | DoF | Gini(FRR users) | Gini(FAR attackers)")
    for m in res:
        g, i = m["gen"], m["imp"]
        ber = f"{g.mean():.3f}/{np.quantile(g,0.9):.3f} | {i.mean():.3f}/{np.quantile(i,0.05):.3f}" if "n" in m else "- | -"
        dof = f"{m['dof']:.1f}" if "dof" in m else "-"
        log(f"{m['label']} | {m['eer']*100:.1f}% | {m['frr_far1']*100:.1f}% | {m['far_frr10']*100:.1f}% | {ber} | {dof} | {m['gini_frr']:.2f} | {m['gini_far']:.2f}")
    R["matching"] = [{k: (float(v) if isinstance(v, (float, np.floating, int, np.integer)) else v) for k, v in m.items() if k not in ("gen", "imp")} for m in res]

    # ---- sample-then-lock on the best binary variants
    log("\n## sample-then-lock (hypergeometric, per probe) on binary variants: FRR / FAR, and population-prior attack on ONE locker")
    log("variant | k_sub | ell | FRR | FAR | P(1 guess opens a given locker) median / max | P(>=1 of ell lockers opened by pop-mode guesses)")
    stl = []
    Tpop_cache = {}
    up_u, Tp = templates_from(Zp, S["up"])
    for name in ["Gray m=1 (sign), all", "LSSC S=8, all", "pop-mask top16 LSSC S=8", "LDA-16 LSSC S=8 (112 bit)"]:
        enc, Bt, Tb, m = bin_out[name]
        n = Bt.shape[1]
        hg = (Bt[G[:, 1]] != Tb[G[:, 0]]).sum(1); hi = (Bt[I[:, 1]] != Tb[I[:, 0]]).sum(1)
        Bp = enc(Tp)
        for k, ell in [(8, 1500), (16, 1500), (24, 1500), (32, 1500)]:
            if k > n:
                continue
            frr = 1 - E.stl_rates(hg, n, k, ell).mean(); far = E.stl_rates(hi, n, k, ell).mean()
            ps = E.stl_locker_attack(Bp, Tb, k, 300)
            any_open = 1 - np.prod(1 - np.sort(ps)[::-1][:min(ell, len(ps))]) if len(ps) else 0
            log(f"{name} [n={n}] | {k} | {ell} | {frr*100:.1f}% | {far*100:.2f}% | {np.median(ps):.3f} / {ps.max():.3f} | {any_open:.3f} (over 300 sampled lockers)")
            stl.append(dict(variant=name, n=n, k=k, ell=ell, frr=frr, far=far, p_lock_med=float(np.median(ps)), p_lock_max=float(ps.max())))
    R["stl"] = stl

    # ---- guessing curves (population dictionary attack)
    if do_guess:
        log("\n## population-dictionary guessing (attacker: templates of disjoint population users, greedy max-coverage)")
        log("Acceptance = target's verifier accepts the guessed feature vector at the stated threshold.")
        log("variant | threshold | P(success) 1 / 10 / 100 / 1000 guesses | guesses for 50% | -log2 P1 (fuzzy min-entropy upper estimate)")
        rng = np.random.default_rng(3)
        nd = min(4000, len(Tp) // 2)
        perm = rng.permutation(len(Tp)); Dg, Aa = Tp[perm[:nd]], Tp[perm[nd:2 * nd]]
        # attacker-side scales: population within spread
        wpop = np.sqrt(prior.within) * 0.8 + 1e-3
        gres = []
        for thrname, thr_sm in [("EER", res[0]["thr_eer"]), ("FAR=1%", res[0]["thr_far1"])]:
            dA = np.vstack([(np.abs(Dg[i:i + 200, None] - Aa[None]) / wpop).mean(2) for i in range(0, nd, 200)])
            dT = np.vstack([(np.abs(Dg[i:i + 200, None] - Tm[None]) / Tsd[None]).mean(2) for i in range(0, nd, 200)])
            c = E.greedy_guessing(dA <= thr_sm, dT <= thr_sm, 2000)
            s = E.summarize_curve(c); s.update(variant="unprotected scaled-Manhattan", thr=thrname); gres.append(s)
        for name in ["Gray m=1 (sign), all", "LSSC S=8, all", "LDA-16 LSSC S=8 (112 bit)"]:
            enc, Bt, Tb, m = bin_out[name]
            BD, BA = enc(Dg), enc(Aa)
            for thrname, t in [("EER", m["thr_eer"]), ("FAR=1%", m["thr_far1"])]:
                n = Bt.shape[1]
                c = E.greedy_guessing(E.popcount_dist(BD, BA) <= t * n, E.popcount_dist(BD, Tb) <= t * n, 2000)
                s = E.summarize_curve(c); s.update(variant=name, thr=thrname); gres.append(s)
        for s in gres:
            log(f"{s['variant']} | {s['thr']} | {s['p1']:.3f} / {s['p10']:.3f} / {s['p100']:.3f} / {s['p1000']:.3f} | {s['g50']} | {s['h1']:.1f} bits")
        R["guess"] = gres

    os.makedirs(OUT, exist_ok=True)
    tag = f"{dataset}_{cfg}" + ("_intra" if dataset == "laser" and os.environ.get("LASER_MODE") == "intra" else "") \
        + ("_selfprior" if dataset == "tappy" and os.environ.get("PRIOR") == "self" else "")
    open(f"{OUT}/{tag}.txt", "w").write("\n".join(lines) + "\n")
    json.dump(R, open(f"{OUT}/{tag}.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--guess" in sys.argv)
