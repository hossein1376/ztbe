"""Tappy (PhysioNet, ODC-By 1.0): in-the-wild typing over weeks/months, already content-blind
(hand L/R/S only). Output windows with day index for cross-day evaluation and drift studies."""
import os, io, zipfile, re, numpy as np, pandas as pd
from multiprocessing import Pool
import features as F

DATA = os.environ.get("DATA", "/workspace/data")
Z = f"{DATA}/tappy/Archived-Data.zip"
CFGS = [("n100", dict(n_keys=100)), ("n200", dict(n_keys=200)), ("n400", dict(n_keys=400)),
        ("t30", dict(active_s=30)), ("t60", dict(active_s=60)), ("t120", dict(active_s=120)), ("t300", dict(active_s=300))]
HAND = {"L": F.L, "R": F.R, "S": F.S}


def users_meta():
    out = {}
    with zipfile.ZipFile(f"{DATA}/tappy/Archived-users.zip") as z:
        for n in z.namelist():
            m = re.search(r"User_(\w+)\.txt", n)
            if m:
                txt = z.read(n).decode("latin-1")
                out[m.group(1)] = "Parkinsons: True" in txt
    return out


def load_user(args):
    uid, names = args
    frames = []
    with zipfile.ZipFile(Z) as z:
        for n in names:
            raw = z.read(n).decode("latin-1", "replace")
            df = pd.read_csv(io.StringIO(raw), sep="\t", header=None, usecols=range(8), on_bad_lines="skip",
                             names=["u", "date", "ts", "hand", "hold", "dir", "lat", "flight"], dtype=str)
            frames.append(df)
    df = pd.concat(frames)
    df = df[df.u == uid]
    dt = pd.to_datetime(df.date.str.strip() + " " + df.ts.str.strip(), format="%y%m%d %H:%M:%S.%f", errors="coerce")
    hold = pd.to_numeric(df.hold, errors="coerce")
    ok = dt.notna() & hold.notna() & df.hand.isin(list(HAND))
    df, dt, hold = df[ok], dt[ok], hold[ok]
    o = np.argsort(dt.values, kind="stable")
    t = (dt.values[o] - dt.values[o][0]).astype("timedelta64[us]").astype(np.int64) / 1000.0   # ms
    hold = hold.to_numpy(float)[o]
    cls = np.array([HAND[h] for h in df.hand.to_numpy()[o]], np.int8)
    seg = np.cumsum(np.r_[0, np.diff(t) > 60000])              # new burst after > 60 s idle
    day = np.floor(t / 86400000.0).astype(int)
    res = {}
    for c, kw in CFGS:
        X, starts = F.key_windows(t, t + hold, cls, seg, extra=False, **kw)
        res[c] = (X, np.floor(starts / 86400000.0).astype(int) if len(starts) else np.zeros(0, int))
    return uid, res, len(t), int(day.max()) + 1 if len(day) else 0


if __name__ == "__main__":
    meta = users_meta()
    with zipfile.ZipFile(Z) as z:
        names = [n for n in z.namelist() if n.endswith(".txt")]
    by = {}
    for n in names:
        u = os.path.basename(n).split("_")[0]
        by.setdefault(u, []).append(n)
    acc = {c: [[], [], []] for c, _ in CFGS}
    stats = []
    with Pool(7) as p:
        for uid, res, nk, nd in p.imap_unordered(load_user, sorted(by.items())):
            stats.append((uid, nk, nd))
            for c in acc:
                X, d = res[c]
                if len(X):
                    acc[c][0].append(X); acc[c][1].extend([uid] * len(X)); acc[c][2].append(d)
    os.makedirs(f"{DATA}/derived", exist_ok=True)
    for c, (Xs, U, Ds) in acc.items():
        U = np.array(U)
        np.savez_compressed(f"{DATA}/derived/tappy_{c}.npz", X=np.vstack(Xs), uid=U, day=np.concatenate(Ds),
                            pd=np.array([meta.get(u, False) for u in U]), names=np.array(F.KEY_FEATURES))
        print(c, np.vstack(Xs).shape, "users", len(set(U)))
    s = np.array([(nk, nd) for _, nk, nd in stats])
    print("users", len(stats), "keystrokes median", np.median(s[:, 0]), "span days median", np.median(s[:, 1]),
          "users with >=14 days span", (s[:, 1] >= 14).sum())
