"""CMU LASER-2012 free vs transcribed (Killourhy & Maxion): 20 subjects x 4 sessions.
Reconstructs press/release times from per-screen keydown-keydown and hold times."""
import os, numpy as np, pandas as pd
import features as F

DATA = os.environ.get("DATA", "/workspace/data")
D = f"{DATA}/laser/data"
NAMES = {"space": " ", "period": ".", "comma": ",", "apostrophe": "'", "minus": "-", "semicolon": ";",
         "slash": "/", "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
         "six": "6", "seven": "7", "eight": "8", "nine": "9", "equal": "=", "quotedbl": '"'}
CFGS = [("n50", dict(n_keys=50)), ("n100", dict(n_keys=100)), ("n200", dict(n_keys=200)),
        ("t30", dict(active_s=30)), ("t60", dict(active_s=60)), ("t120", dict(active_s=120))]


def kcls(k):
    if k in ("Delete", "BackSpace"):
        return F.B
    if k in ("Shift", "Shift_L", "Shift_R", "Control", "Alt", "Caps_Lock"):
        return F.M
    if k.startswith("Shift."):
        k = k[6:]
    k = NAMES.get(k, k)
    return F.cls_from_char(k) if len(k) == 1 else F.O


def load():
    rd = lambda f: pd.read_csv(f"{D}/{f}", sep=r"\s+")
    h, dd, sm = rd("TimingFeatures-Hold.txt"), rd("TimingFeatures-DD.txt"), rd("SessionMap.txt")
    task = {(r.user, r.sessionIndex): ("free" if "Free" in r.value else "trans") for r in sm.itertuples()}
    rows = []
    for (sub, ses), g in h.groupby(["subject", "sessionIndex"]):
        P, Rl, C, S = [], [], [], []
        t0 = 0.0
        for scr, gh in g.groupby("screenIndex"):
            gh = gh.sort_values("index")
            gd = dd[(dd.subject == sub) & (dd.sessionIndex == ses) & (dd.screenIndex == scr)].sort_values("index")
            n = len(gh)
            pp = np.zeros(n)
            m = min(n - 1, len(gd))
            pp[1:m + 1] = gd.time.to_numpy()[:m] * 1000
            press = t0 + np.cumsum(pp)
            P.append(press); Rl.append(press + gh.time.to_numpy() * 1000)
            C.append(np.array([kcls(k) for k in gh.key], np.int8)); S.append(np.full(n, scr))
            t0 = press[-1] + 60000
        rows.append((sub, ses, task[(sub, ses)], np.concatenate(P), np.concatenate(Rl), np.concatenate(C), np.concatenate(S)))
    return rows


if __name__ == "__main__":
    rows = load()
    os.makedirs(f"{DATA}/derived", exist_ok=True)
    for cname, kw in CFGS:
        Xs, U, Ss, T, W = [], [], [], [], []
        for sub, ses, task, p, r, c, s in rows:
            X, _ = F.key_windows(p, r, c, s, extra=True, **kw)
            Xs.append(X); U += [sub] * len(X); Ss += [ses] * len(X); T += [task] * len(X); W += list(range(len(X)))
        X = np.vstack(Xs)
        np.savez_compressed(f"{DATA}/derived/laser_{cname}.npz", X=X, uid=np.array(U), sess=np.array(Ss),
                            task=np.array(T), widx=np.array(W), names=np.array(F.KEY_FEATURES + F.KEY_EXTRA))
        print(cname, X.shape, "per-session windows median", np.median(np.bincount(pd.factorize(pd.Series(U).astype(str) + pd.Series(Ss).astype(str))[0])))
