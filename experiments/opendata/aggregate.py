"""Collect results/*.json into markdown tables (printed to stdout; pasted into notes/experiments-v2.md)."""
import glob, json, os, re
R = os.path.join(os.path.dirname(__file__), "results")
ORDER = ["aalto_n50", "aalto_n100", "aalto_n200", "aalto_t30", "aalto_t60",
         "laser_n50", "laser_n100", "laser_n200", "laser_t30", "laser_t60", "laser_t120", "laser_n100_intra", "laser_t60_intra",
         "tappy_n100", "tappy_n200", "tappy_n400", "tappy_t60", "tappy_t120", "tappy_t300",
         "tappy_n100_selfprior", "tappy_n200_selfprior", "tappy_n400_selfprior", "tappy_t60_selfprior", "tappy_t120_selfprior", "tappy_t300_selfprior",
         "sapimouse_t15", "sapimouse_t30", "sapimouse_t60", "balabit_t30", "balabit_t60", "balabit_t120"]
tags = [t for t in ORDER if os.path.exists(f"{R}/{t}.json")]
D = {t: json.load(open(f"{R}/{t}.json")) for t in tags}
H = {}
for t in tags:
    txt = open(f"{R}/{t}.txt").read().splitlines()
    m = re.search(r"eval users (\d+); enrol windows (\d+) test windows (\d+)", txt[1]); m2 = re.search(r"median (\d+)", txt[2])
    H[t] = (m.groups() if m else ("?", "?", "?")) + ((m2.group(1),) if m2 else ("?",))
pct = lambda x: "-" if x is None else f"{100*x:.1f}"
def row(t, lab):
    for r in D[t]["matching"]:
        if r["label"].startswith(lab): return r
KEY = ["unprotected scaled-Manhattan", "unprotected LDA-16", "Gray m=1", "Gray m=2", "LSSC S=8, all", "pop-mask top16 LSSC", "LDA-16 LSSC", "DROBA L=64", "1-bit DROBA"]
SHORT = ["SM", "LDA", "Gray1", "Gray2", "LSSC8", "pm-LSSC8", "LDA-LSSC8", "DROBA64", "DROBA1"]
print("### EER % by variant (global threshold)\n")
print("| run | eval users | enrol/test windows | med. enrol win/user | " + " | ".join(SHORT) + " |")
print("|" + "---|" * (4 + len(SHORT)))
for t in tags:
    cells = []
    for k in KEY:
        r = row(t, k); cells.append(pct(r["eer"]) if r else "-")
    print(f"| {t} | {H[t][0]} | {H[t][1]}/{H[t][2]} | {H[t][3]} | " + " | ".join(cells) + " |")
print("\n### FRR@FAR1% and FAR@FRR10% (%), Gini of per-user FRR and per-attacker FAR\n")
print("| run | SM FRR@FAR1 | SM FAR@FRR10 | SM Gini FRR/FAR | LDA FRR@FAR1 | LDA FAR@FRR10 | best binary (EER) | its FRR@FAR1 |")
print("|---|---|---|---|---|---|---|---|")
for t in tags:
    sm, ld = row(t, KEY[0]), row(t, KEY[1])
    bins = [r for r in D[t]["matching"] if not r["label"].startswith("unprotected")]
    b = min(bins, key=lambda r: r["eer"])
    print(f"| {t} | {pct(sm['frr_far1'])} | {pct(sm['far_frr10'])} | {sm['gini_frr']:.2f}/{sm['gini_far']:.2f} | {pct(ld['frr_far1'])} | {pct(ld['far_frr10'])} | {b['label'].split(' [')[0]} ({pct(b['eer'])}) | {pct(b['frr_far1'])} |")
print("\n### Genuine / impostor BER (mean) and Daugman DoF for binary variants\n")
print("| run | " + " | ".join(SHORT[2:]) + " |")
print("|" + "---|" * (1 + len(SHORT) - 2))
for t in tags:
    cells = []
    for k in KEY[2:]:
        r = row(t, k); ln = next((l for l in open(f"{R}/{t}.txt") if l.startswith(r["label"] + " |")), None) if r else None
        if ln:
            f = [x.strip() for x in ln.split("|")]
            cells.append(f"{f[4].split('/')[0]}/{f[5].split('/')[0]} ({r['dof']:.0f})")
        else:
            cells.append("-")
    print(f"| {t} | " + " | ".join(cells) + " |")
print("\n### Guessing (population dictionary, greedy) — P1 / P10 / P100, guesses for 50%, -log2 P1\n")
print("| run | variant | thr | P1 | P10 | P100 | g50 | -log2 P1 |")
print("|---|---|---|---|---|---|---|---|")
for t in tags:
    for g in D[t].get("guess", []):
        print(f"| {t} | {g['variant']} | {g['thr']} | {g['p1']:.3f} | {g['p10']:.3f} | {g['p100']:.3f} | {g['g50'] if g['g50'] else '>'+str(g.get('n_guesses','?'))} | {g['h1']:.1f} |")
print("\n### Sample-then-lock, best binary variant per run (ell=1500)\n")
print("| run | variant | k | FRR | FAR | P(1 pop guess opens locker) med/max |")
print("|---|---|---|---|---|---|")
for t in tags:
    for s in D[t].get("stl", []):
        if s["variant"].startswith("LDA-16 LSSC") and s["k"] in (16, 24, 32):
            print(f"| {t} | {s['variant']} | {s['k']} | {pct(s['frr'])} | {pct(s['far'])} | {s['p_lock_med']:.3f}/{s['p_lock_max']:.3f} |")

print("\n### Per-feature variation: test-window within-user sd / between-user sd of templates (z-units), and population ICC\n")
FV = [t for t in ("aalto_n200", "laser_n200", "tappy_n200_selfprior", "tappy_n200") if t in D]
fn = list(D[FV[0]]["feature_var"].keys())
fn.sort(key=lambda f: -D[FV[0]]["feature_var"][f]["icc"])
print("| feature | " + " | ".join(f"{t} ICC / ratio" for t in FV) + " |")
print("|---|" + "---|" * len(FV))
for f in fn:
    cells = []
    for t in FV:
        v = D[t]["feature_var"].get(f)
        cells.append(f"{v['icc']:.2f} / {v['within']/max(v['between'],1e-6):.2f}" if v else "-")
    print(f"| {f} | " + " | ".join(cells) + " |")

print("\n### Decision fusion over k consecutive windows (fuse.py)\n")
for f in sorted(glob.glob(f"{R}/fuse_*.txt")):
    L = open(f).read().strip().splitlines()
    print(f"**{os.path.basename(f)[:-4]}**: {L[0].lstrip('# ')}\n")
    print("| " + L[1] + " |"); print("|" + "---|" * len(L[1].split("|")))
    for l in L[2:]: print("| " + l + " |")
    print()
print("### Adaptation and poisoning (adapt.py, Tappy n200)\n")
print("```"); print(open(f"{R}/adapt_n200.txt").read().strip()); print("```")
