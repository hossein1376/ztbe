"""Review round 1: timer quantisation of Tappy hold times, per user.

Reads the raw PhysioNet archive ($DATA/tappy/Archived-Data.zip), takes the hold-time field of the first two monthly
files of each user (users with >= 500 keystrokes there), and reports the coarsest quantum q in
{15.625, 7.8125, 3.90625, 1} ms such that >= 95% of hold times are within 0.06 ms of a multiple of q
(values are stored with 0.1 ms precision). Usage: python3 tappy_timer.py -> results/tappy_timer.txt
"""
import os, zipfile, collections
import numpy as np
DATA = os.environ.get("DATA", "/workspace/data")
z = zipfile.ZipFile(f"{DATA}/tappy/Archived-Data.zip")
files = collections.defaultdict(list)
for nm in z.namelist():
    if nm.endswith(".txt"):
        files[os.path.basename(nm)[:10]].append(nm)
cnt = collections.Counter()
for u, fl in sorted(files.items()):
    v = []
    for nm in sorted(fl)[:2]:
        for line in z.read(nm).decode(errors="ignore").splitlines():
            p = line.split("\t")
            if len(p) >= 5:
                try: v.append(float(p[4]))
                except ValueError: pass
    if len(v) < 500:
        continue
    v = np.array(v)
    on = lambda q: np.mean(np.abs(v / q - np.round(v / q)) * q < 0.06) >= 0.95
    cnt[next((f"{q:g} ms" for q in (15.625, 7.8125, 3.90625, 1.0) if on(q)), "finer or irregular")] += 1
out = ["# Tappy hold-time quantisation per user (first two monthly files, users with >= 500 keystrokes)",
       "quantum | users"] + [f"{k} | {n}" for k, n in cnt.most_common()] + [f"total | {sum(cnt.values())}"]
print("\n".join(out))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "tappy_timer.txt"), "w").write("\n".join(out) + "\n")
