#!/usr/bin/env bash
# Runs every evaluation; results land in results/. Expects $DATA/derived/*.npz (see README).
set -e
cd "$(dirname "$0")"
for c in n50 n100 n200 t30 t60; do python3 run_keystroke.py aalto $c --guess; done
for c in n50 n100 n200 t30 t60 t120; do python3 run_keystroke.py laser $c --guess; done
for c in n100 t60; do LASER_MODE=intra python3 run_keystroke.py laser $c; done
for c in t15 t30 t60; do python3 run_keystroke.py sapimouse $c --guess; done
for c in t30 t60 t120; do python3 run_keystroke.py balabit $c --guess; done
for c in n100 n200 n400 t60 t120 t300; do python3 run_keystroke.py tappy $c --guess; PRIOR=self python3 run_keystroke.py tappy $c --guess; done
