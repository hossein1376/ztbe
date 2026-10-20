"""Mouse window features for Balabit Mouse Dynamics Challenge and SapiMouse.
Balabit: enrol = training sessions, test = labelled test sessions (is_illegal 0 = genuine, 1 = foreign user).
SapiMouse: enrol = 3-min session, test = 1-min session (same day)."""
import os, glob, numpy as np, pandas as pd
import features as F

DATA = os.environ.get("DATA", "/workspace/data")
WINS = [15, 30, 60, 120]


def windows(df, tcol, W):
    t = df[tcol].to_numpy(float); x = df.x.to_numpy(float); y = df.y.to_numpy(float)
    st = df.state.astype(str).to_numpy(); bt = df.button.astype(str).to_numpy()
    mv = (st == "Move") | (st == "Drag")
    ok = (x < 10000) & (y < 10000)            # balabit has 65535 sentinel coords
    out = []
    for w0 in np.arange(t.min(), t.max() - W + 1e-9, W):
        s = (t >= w0) & (t < w0 + W) & ok
        if (s & mv).sum() < 30:
            continue
        pr = t[s & (st == "Pressed") & (bt != "Scroll")]; rl = t[s & (st == "Released") & (bt != "Scroll")]
        n = min(len(pr), len(rl)); dn, up = [], []
        j = 0
        for p in pr:                       # pair each press with next release
            while j < len(rl) and rl[j] < p: j += 1
            if j < len(rl): dn.append(p); up.append(rl[j]); j += 1
        out.append(F.mouse_window(t[s], x[s], y[s], mv[s], np.array(dn), np.array(up)))
    return out


def balabit():
    root = f"{DATA}/balabit"
    lab = pd.read_csv(f"{root}/public_labels.csv").set_index("filename").is_illegal.to_dict()
    for W in WINS:
        X, U, ROLE, GEN, SES = [], [], [], [], []
        for role, d in (("enrol", "training_files"), ("test", "test_files")):
            for f in sorted(glob.glob(f"{root}/{d}/user*/session_*")):
                u = f.split("/")[-2]; s = os.path.basename(f)
                if role == "test" and s not in lab:
                    continue
                df = pd.read_csv(f).rename(columns={"client timestamp": "ct"})
                ws = windows(df, "ct", W)
                X += ws; U += [u] * len(ws); ROLE += [role] * len(ws); SES += [s] * len(ws)
                GEN += [1 if role == "enrol" else 1 - lab[s]] * len(ws)
        np.savez_compressed(f"{DATA}/derived/balabit_t{W}.npz", X=np.vstack(X), uid=np.array(U), role=np.array(ROLE),
                            genuine=np.array(GEN), sess=np.array(SES), names=np.array(F.MOUSE_FEATURES))
        print("balabit", W, len(X), "test sessions with >=1 window:", len(set(s for s, r in zip(SES, ROLE) if r == "test")))


def sapimouse():
    root = f"{DATA}/sapimouse/sapimouse"
    for W in WINS:
        X, U, ROLE = [], [], []
        for f in sorted(glob.glob(f"{root}/user*/session_*.csv")):
            u = f.split("/")[-2]; role = "enrol" if "3min" in f else "test"
            df = pd.read_csv(f)
            df.columns = [c.strip().lower() for c in df.columns]
            df = df.rename(columns={"client timestamp": "ct", "timestamp": "ct"})
            df["ct"] = df.ct / 1000.0                       # ms -> s
            ws = windows(df, "ct", W)
            X += ws; U += [u] * len(ws); ROLE += [role] * len(ws)
        if X:
            np.savez_compressed(f"{DATA}/derived/sapimouse_t{W}.npz", X=np.vstack(X), uid=np.array(U), role=np.array(ROLE),
                                names=np.array(F.MOUSE_FEATURES))
        print("sapimouse", W, len(X))


if __name__ == "__main__":
    os.makedirs(f"{DATA}/derived", exist_ok=True)
    sapimouse(); balabit()
