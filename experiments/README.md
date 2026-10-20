# experiments/

Small, reproducible sanity checks backing `notes/spec-review.md`. None of these are ZTBE code.

| dir | what | how to run |
| --- | --- | --- |
| `sanity/` | closed-form checks of spec formulas (sample-then-lock FRR, BCH dimensions, Gray-code distances, Bloom pre-image count, EW-Welford, helper-data update leakage demo on BCH(31,16), anti-poisoning envelope, per-session RAM) | `python3 sanity/calcs.py` (stdlib only); output in `sanity/output.txt` |
| `go-bench/` | Go micro-benchmarks: worst-case sample-then-lock `Rep` with HKDF-SHA256 / HMAC lockers (l=1000/1500), Bloom-filter distance (32x256 bit), locker storage sizes | `cd go-bench && go test -run TestStorage -v -bench . -benchmem` (Go >= 1.24 for `crypto/hkdf`) |
| `cmu-quantization/` | spec Stage-1 pipeline (pop. z-score -> equiprobable bins -> Gray code -> optional FDR mask) on the CMU Killourhy-Maxion keystroke benchmark: measured genuine/impostor bit-error rates, EER, Daugman DoF, sample-then-lock FRR/FAR | download the CSV (see header of `analyze.py`), then `python3 analyze.py DSL-StrongPasswordData.csv` with env `NW`, `FEAT`, `MASK`; `baseline.py` gives unprotected EER and same- vs cross-session BER. Output in `results.txt` |

Machine used for the numbers in the notes: 8 vCPU "Intel(R) Xeon(R) Processor" with SHA-NI, Go 1.27.2, Python 3.13, numpy.
Dataset is not redistributed (the page has no explicit license; authors request citation).
