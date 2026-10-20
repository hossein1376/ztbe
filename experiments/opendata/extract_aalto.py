"""Stream the Aalto 136M zip (no unzip to disk) and write window features.

Filter: KEYBOARD_TYPE in {full, laptop}, LAYOUT == qwerty (keycode->hand map is QWERTY).
Output: $DATA/derived/aalto_<cfg>.npz with X[n_win,F], uid[n_win], widx[n_win].
"""
import os, sys, io, zipfile, csv
import numpy as np, pandas as pd
from multiprocessing import Pool
import features as F

DATA = os.environ.get("DATA", "/workspace/data")
ZIP = f"{DATA}/aalto/Keystrokes.zip"
OUT = f"{DATA}/derived"
CFGS = [("n50", dict(n_keys=50)), ("n100", dict(n_keys=100)), ("n200", dict(n_keys=200)),
        ("t30", dict(active_s=30)), ("t60", dict(active_s=60)), ("t120", dict(active_s=120))]
LIMIT = int(os.environ.get("LIMIT", "0"))


def meta():
    with zipfile.ZipFile(ZIP) as z:
        m = pd.read_csv(z.open("Keystrokes/files/metadata_participants.txt"), sep="\t",
                        quoting=csv.QUOTE_NONE, on_bad_lines="skip", low_memory=False)
    m = m[m.KEYBOARD_TYPE.isin(["full", "laptop"]) & (m.LAYOUT == "qwerty")]
    return m


def work(names):
    out = {c: [] for c, _ in CFGS}
    with zipfile.ZipFile(ZIP) as z:
        for nm in names:
            try:
                df = pd.read_csv(z.open(nm), sep="\t", quoting=csv.QUOTE_NONE, on_bad_lines="skip",
                                 usecols=["PARTICIPANT_ID", "TEST_SECTION_ID", "PRESS_TIME", "RELEASE_TIME", "KEYCODE"],
                                 encoding="latin-1")
                df = df.apply(pd.to_numeric, errors="coerce").dropna()
            except Exception:
                continue
            if len(df) < 200:
                continue
            df = df.sort_values("PRESS_TIME")
            uid = int(df.PARTICIPANT_ID.iloc[0])
            p = df.PRESS_TIME.to_numpy(float); r = df.RELEASE_TIME.to_numpy(float)
            c = F.cls_from_jskeycode(df.KEYCODE.to_numpy(int)); s = df.TEST_SECTION_ID.to_numpy(np.int64)
            for cname, kw in CFGS:
                X, _ = F.key_windows(p, r, c, s, extra=True, **kw)
                if len(X):
                    out[cname].append((uid, X))
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = meta()
    keep = set(m.PARTICIPANT_ID.astype(int))
    with zipfile.ZipFile(ZIP) as z:
        names = [n for n in z.namelist() if n.endswith("_keystrokes.txt")
                 and int(os.path.basename(n).split("_")[0]) in keep]
    names.sort()
    if LIMIT:
        names = names[:LIMIT]
    print("users after filter:", len(names), flush=True)
    chunks = [names[i:i + 500] for i in range(0, len(names), 500)]
    acc = {c: [] for c, _ in CFGS}
    with Pool(int(os.environ.get("NPROC", "7"))) as pool:
        for i, res in enumerate(pool.imap_unordered(work, chunks)):
            for c in acc:
                acc[c].extend(res[c])
            if i % 20 == 0:
                print(f"chunk {i}/{len(chunks)}", flush=True)
    for c, lst in acc.items():
        X = np.vstack([x for _, x in lst]).astype(np.float32)
        uid = np.concatenate([np.full(len(x), u, np.int64) for u, x in lst])
        widx = np.concatenate([np.arange(len(x)) for _, x in lst])
        np.savez_compressed(f"{OUT}/aalto_{c}.npz", X=X, uid=uid, widx=widx,
                            names=np.array(F.KEY_FEATURES + F.KEY_EXTRA))
        print(c, X.shape, "users", len(lst), flush=True)
