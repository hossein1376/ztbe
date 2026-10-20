#!/bin/sh
# Round-2 harness runs (see eval2.py). ~1-3 min each.
set -e
cd "$(dirname "$0")"
for c in t60 t120 n100 n200 hyb s60; do python3 eval2.py $c all all 4 1000 > /dev/null & done; wait
for c in hyb t60; do python3 eval2.py $c v21 all 4 1000 > /dev/null & python3 eval2.py $c all q3.9 4 1000 > /dev/null & done; wait
python3 eval2.py hyb v21 q3.9 4 1000 > /dev/null
