"""Review round 2: active typing time per spec hyb window on Tappy (200 keys or 60 s active, idle > 5 s removed,
>= 40 keys), to check how many windows make one active-typing hour. Same window rule as extract_tappy_v2.py.
Output: stdout (saved as results/window_duration.txt)."""
import sys, os, io, zipfile, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_tappy as ET
from multiprocessing import Pool
IDLE_MS, MIN_KEYS = 5000.0, 40
def win(press, seg):
    gap = np.diff(press, prepend=press[0]); gap[0] = 0
    newseg = np.r_[True, seg[1:] != seg[:-1]]
    gap = np.where(newseg | (gap > IDLE_MS), 0, gap)
    out, s, act = [], 0, 0.0
    for i in range(1, press.size):
        act += gap[i] / 1000.0
        if (i - s + 1 >= 200) or (act >= 60):
            e = i + 1
            if e - s >= MIN_KEYS: out.append((e - s, act, press[e-1]-press[s]))
            s, act = e, 0.0
    return out
def load(args):
    uid, names = args
    frames = []
    with zipfile.ZipFile(ET.Z) as z:
        for n in names:
            raw = z.read(n).decode("latin-1", "replace")
            frames.append(pd.read_csv(io.StringIO(raw), sep="\t", header=None, usecols=range(8), on_bad_lines="skip",
                names=["u","date","ts","hand","hold","dir","lat","flight"], dtype=str))
    df = pd.concat(frames); df = df[df.u == uid]
    dt = pd.to_datetime(df.date.str.strip() + " " + df.ts.str.strip(), format="%y%m%d %H:%M:%S.%f", errors="coerce")
    hold = pd.to_numeric(df.hold, errors="coerce")
    ok = dt.notna() & hold.notna() & df.hand.isin(list(ET.HAND))
    dt = dt[ok]
    if len(dt) < MIN_KEYS: return uid, []
    t = np.sort((dt.values - dt.values.min()).astype("timedelta64[us]").astype(np.int64) / 1000.0)
    seg = np.cumsum(np.r_[0, np.diff(t) > 60000])
    return uid, win(t, seg)
if __name__ == "__main__":
    with zipfile.ZipFile(ET.Z) as z:
        names = [n for n in z.namelist() if n.endswith(".txt")]
    by = {}
    for n in names: by.setdefault(os.path.basename(n).split("_")[0], []).append(n)
    W = []; per = {}
    with Pool(7) as p:
        for uid, w in p.imap_unordered(load, sorted(by.items())):
            if w: W += w; per[uid] = np.array(w)
    W = np.array(W)
    print("windows", len(W), "users", len(per))
    print("keys per window: median %.0f, mean %.0f" % (np.median(W[:,0]), W[:,0].mean()))
    print("active seconds per window: median %.1f, mean %.1f, p10 %.1f, p90 %.1f" % (np.median(W[:,1]), W[:,1].mean(), *np.percentile(W[:,1],[10,90])))
    print("share closed by 200 keys (active<60): %.1f%%" % (100*np.mean(W[:,1]<60)))
    print("windows per active-typing hour (pooled) = 3600/mean active s = %.0f" % (3600/W[:,1].mean()))
    um = np.array([v[:,1].mean() for v in per.values()])
    print("per-user mean active s: median %.1f, p10 %.1f, p90 %.1f" % (np.median(um), *np.percentile(um,[10,90])))
    print("wall-clock span per window (incl. removed idle): median %.0f s, mean %.0f s" % (np.median(W[:,2])/1000, W[:,2].mean()/1000))
