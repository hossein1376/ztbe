# experiments/

Reproducible checks backing `notes/spec-review.md` (phase 1) and `notes/experiments-v2.md`, `notes/design-options.md`, `PROPOSAL.md` (phase 2). None of these are ZTBE product code.

| dir | what | how to run |
| --- | --- | --- |
| `sanity/` | closed-form checks of spec formulas (sample-then-lock FRR, BCH dimensions, Gray-code distances, Bloom pre-image count, EW-Welford, helper-data update leakage demo on BCH(31,16), anti-poisoning envelope, per-session RAM) | `python3 sanity/calcs.py` (stdlib only); output in `sanity/output.txt` |
| `go-bench/` | Go micro-benchmarks: worst-case sample-then-lock `Rep` with HKDF-SHA256 / HMAC lockers (l=1000/1500), Bloom-filter distance (32x256 bit), locker storage sizes | `cd go-bench && go test -run TestStorage -v -bench . -benchmem` (Go >= 1.24 for `crypto/hkdf`) |
| `opendata/` | **Phase 2.** Eberz-style evaluation on Aalto 136M, CMU LASER-2012, Tappy (PhysioNet), SapiMouse, Balabit: feature variation, quantizer BER, HD distributions, EER/FRR/FAR, window-length sweep, guessing-curve entropy, sample-then-lock, decision fusion, adaptation and poisoning | see `opendata/README.md` (`fetch.sh` → `extract_*.py` → `run_all.sh`, `adapt.py`, `fuse.py`, `aggregate.py`) |
| `go-he/` | **Phase 2.** Go costs of the design options: CKKS/BGV encrypted matching (lattigo v6), OPRF (circl, RFC 9497), plaintext score + AES-GCM template sealing | `cd go-he && go test -v -run 'TestSizes\|Correct' . && go test -run '^$' -bench . -count=3 .` |
| `cmu-quantization/` | spec Stage-1 pipeline (pop. z-score -> equiprobable bins -> Gray code -> optional FDR mask) on the CMU Killourhy-Maxion keystroke benchmark: measured genuine/impostor bit-error rates, EER, Daugman DoF, sample-then-lock FRR/FAR | download the CSV (see header of `analyze.py`), then `python3 analyze.py DSL-StrongPasswordData.csv` with env `NW`, `FEAT`, `MASK`; `baseline.py` gives unprotected EER and same- vs cross-session BER. Output in `results.txt` |

Machine used for the numbers in the notes: 8 vCPU "Intel(R) Xeon(R) Processor" with SHA-NI, Go 1.27.2, Python 3.13, numpy.
Dataset is not redistributed (the page has no explicit license; authors request citation).
