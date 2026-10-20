"""Round 2: Tappy windows built with the *spec v2* window rules (spec §4), plus a per-user timer-quantum label.

Spec rules: idle gaps > 5 s are removed from active time; a window closes at 200 keystrokes OR 60 s of active
typing, whichever comes first ("hyb"); windows with < 40 keystrokes are not scored. Also writes a time-only
variant ("s60": 60 s active, >5 s gaps removed, >= 40 keys) for comparison with the experiment-default t60
(1.5 s gap cap, >= 20 keys). Digraph features still ignore press-press gaps >= 1.5 s (features.PAUSE_MS).
Quantum: coarsest q in {15.625, 7.8125, 3.90625, 1} ms with >= 95% of hold times within 0.06 ms of a multiple
of q, over ALL of the user's hold times (tappy_timer.py uses the first two monthly files only). 0 = finer or
irregular, -1 = fewer than 500 keystrokes.
Output: $DATA/derived/tappy_{hyb,s60}.npz with X, uid, day, q (quantum of the window's user), names."""
import os, collections, numpy as np
from multiprocessing import Pool
import features as F
import extract_tappy as ET

IDLE_MS, MIN_KEYS = 5000.0, 40


def quantum(hold):
    for q in (15.625, 7.8125, 3.90625, 1.0):
        if np.mean(np.abs(hold / q - np.round(hold / q)) * q < 0.06) >= 0.95:
            return q
    return 0.0


def windows(press, release, cls, seg, n_keys, active_s):
    gap = np.diff(press, prepend=press[0]); gap[0] = 0
    newseg = np.r_[True, seg[1:] != seg[:-1]]
    gap = np.where(newseg | (gap > IDLE_MS), 0, gap)
    out, s, act = [], 0, 0.0
    for i in range(1, press.size):
        act += gap[i] / 1000.0
        if (n_keys and i - s + 1 >= n_keys) or (active_s and act >= active_s):
            e = i + 1
            if e - s >= MIN_KEYS:
                out.append((s, e))
            s, act = e, 0.0
    X = [F.key_window(press[a:b], release[a:b], cls[a:b], seg[a:b], extra=False) for a, b in out]
    st = [press[a] for a, _ in out]
    return (np.vstack(X) if X else np.zeros((0, F.N_KEY), np.float32)), np.asarray(st)


def load(args):
    uid, names = args
    import io, zipfile, pandas as pd
    frames = []
    with zipfile.ZipFile(ET.Z) as z:
        for n in names:
            raw = z.read(n).decode("latin-1", "replace")
            frames.append(pd.read_csv(io.StringIO(raw), sep="\t", header=None, usecols=range(8), on_bad_lines="skip",
                                      names=["u", "date", "ts", "hand", "hold", "dir", "lat", "flight"], dtype=str))
    df = pd.concat(frames); df = df[df.u == uid]
    dt = pd.to_datetime(df.date.str.strip() + " " + df.ts.str.strip(), format="%y%m%d %H:%M:%S.%f", errors="coerce")
    hold = pd.to_numeric(df.hold, errors="coerce")
    ok = dt.notna() & hold.notna() & df.hand.isin(list(ET.HAND))
    df, dt, hold = df[ok], dt[ok], hold[ok]
    if len(df) < MIN_KEYS:
        return uid, None
    o = np.argsort(dt.values, kind="stable")
    t = (dt.values[o] - dt.values[o][0]).astype("timedelta64[us]").astype(np.int64) / 1000.0
    h = hold.to_numpy(float)[o]
    cls = np.array([ET.HAND[x] for x in df.hand.to_numpy()[o]], np.int8)
    seg = np.cumsum(np.r_[0, np.diff(t) > 60000])
    hv = h[(h > 0) & (h < 2000)]
    q = quantum(hv) if len(hv) >= 500 else -1.0
    res = {}
    for c, nk, a in (("hyb", 200, 60), ("s60", None, 60)):
        X, st = windows(t, t + h, cls, seg, nk, a)
        res[c] = (X, np.floor(st / 86400000.0).astype(int) if len(st) else np.zeros(0, int))
    return uid, (res, q)


if __name__ == "__main__":
    import zipfile
    with zipfile.ZipFile(ET.Z) as z:
        names = [n for n in z.namelist() if n.endswith(".txt")]
    by = {}
    for n in names:
        by.setdefault(os.path.basename(n).split("_")[0], []).append(n)
    acc = {c: [[], [], [], []] for c in ("hyb", "s60")}
    qs = {}
    with Pool(7) as p:
        for uid, r in p.imap_unordered(load, sorted(by.items())):
            if r is None: continue
            res, q = r; qs[uid] = q
            for c in acc:
                X, d = res[c]
                if len(X):
                    acc[c][0].append(X); acc[c][1].extend([uid] * len(X)); acc[c][2].append(d); acc[c][3].extend([q] * len(X))
    for c, (Xs, U, D, Q) in acc.items():
        np.savez_compressed(f"{ET.DATA}/derived/tappy_{c}.npz", X=np.vstack(Xs), uid=np.array(U), day=np.concatenate(D),
                            q=np.array(Q), names=np.array(F.KEY_FEATURES))
        print(c, np.vstack(Xs).shape, "users", len(set(U)))
    print("quantum over all hold times (users):", sorted(collections.Counter(qs.values()).items()))
