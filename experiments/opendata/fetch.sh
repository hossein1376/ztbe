#!/usr/bin/env bash
# Fetch the open datasets used by experiments/opendata. Raw data is NEVER committed.
# Usage: DATA=/path/to/data ./fetch.sh [aalto|laser|tappy|balabit|sapimouse|all]
# Read each dataset's licence before use (printed below). Several are research/non-commercial only.
set -euo pipefail
DATA=${DATA:-/workspace/data}
what=${1:-all}
mkdir -p "$DATA"

note() { printf '\n== %s\n%s\n' "$1" "$2"; }

aalto() {
  note "Aalto 136M Keystrokes (Dhakal et al., CHI 2018)" \
"Licence (dataset page): free to use for research and non-commercial purposes with attribution.
Page: https://userinterfaces.aalto.fi/136Mkeystrokes/  (~1.57 GB zip, ~18.8 GB unpacked; extractors stream the zip)"
  mkdir -p "$DATA/aalto"
  curl -fL -C - -o "$DATA/aalto/Keystrokes.zip" https://userinterfaces.aalto.fi/136Mkeystrokes/data/Keystrokes.zip
}

laser() {
  note "CMU Free vs. Transcribed text (Killourhy & Maxion, LASER 2012)" \
"No explicit licence on the page; distributed by the authors for research. Cite the paper. Do not redistribute.
Page: https://www.cs.cmu.edu/~keystroke/laser-2012/"
  mkdir -p "$DATA/laser"
  curl -fL -o "$DATA/laser/DSL-Free-vs-Transcribed.zip" https://www.cs.cmu.edu/~keystroke/laser-2012/DSL-Free-vs-Transcribed.zip
  (cd "$DATA/laser" && unzip -oq DSL-Free-vs-Transcribed.zip)
}

tappy() {
  note "Tappy Keystroke Data (Adams 2017, PhysioNet)" \
"Licence: Open Data Commons Attribution v1.0 (ODC-By). Contains Parkinson's-disease subjects (health-related data).
Page: https://physionet.org/content/tappy/1.0.0/"
  mkdir -p "$DATA/tappy"
  for f in Archived-Data.zip Archived-users.zip; do
    curl -fL -C - -o "$DATA/tappy/$f" "https://physionet.org/files/tappy/1.0.0/$f"
  done
  (cd "$DATA/tappy" && sha256sum Archived-Data.zip Archived-users.zip && unzip -oq Archived-Data.zip && unzip -oq Archived-users.zip)
  echo "expected sha256 prefixes: Archived-Data.zip d5fb5506..., Archived-users.zip a15f5eea..."
}

balabit() {
  note "Balabit Mouse Dynamics Challenge (2016)" \
"No licence file in the repository; public research challenge data. Do not redistribute.
Repo: https://github.com/balabit/Mouse-Dynamics-Challenge"
  [ -d "$DATA/balabit/.git" ] || git clone --depth 1 https://github.com/balabit/Mouse-Dynamics-Challenge "$DATA/balabit"
}

sapimouse() {
  note "SapiMouse (Antal et al., 2021)" \
"Dataset page states no licence; the accompanying code repository is Apache-2.0. Cite the paper. Do not redistribute.
Page: https://ms.sapientia.ro/~manyi/sapimouse/sapimouse.html"
  mkdir -p "$DATA/sapimouse"
  curl -fL -o "$DATA/sapimouse/sapimouse.zip" https://ms.sapientia.ro/~manyi/sapimouse/sapimouse.zip
  (cd "$DATA/sapimouse" && unzip -oq sapimouse.zip)
}

case "$what" in
  all) aalto; laser; tappy; balabit; sapimouse ;;
  aalto|laser|tappy|balabit|sapimouse) "$what" ;;
  *) echo "unknown dataset $what"; exit 2 ;;
esac
echo; echo "done. Next: see README.md (extract_*.py, then run_keystroke.py / adapt.py)."
