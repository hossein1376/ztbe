# go-he: cost of the cryptographic matching options in Go

Micro-benchmarks behind `notes/design-options.md` and `PROPOSAL.md`. Go 1.27.2, linux/amd64, 8-vCPU Intel Xeon (box), single goroutine.

| File | What |
|---|---|
| `he_test.go` | CKKS (lattigo v6.2.0): encrypted weighted squared-Euclidean distance, D=64 (Enc(x)·Enc(√w) − Enc(μ√w), square, InnerSum). BGV: encrypted Hamming distance over 256 bits (t+p−2tp). Correctness tests check against plaintext. OPRF (circl v1.6.5, RFC 9497, ristretto255) server evaluation and full client round-trip without network. |
| `sign_test.go` | Signing/verifying a 200-byte risk assertion with software Ed25519 and ECDSA P-256 keys. TPM or Secure Enclave signing latency is **not measured**: there is no TPM on this box. |
| `plain_test.go` | Plaintext reference for the recommended on-device path: LDA-16 projection + scaled-Manhattan over 36 features; AES-256-GCM seal+open of a 1.7 KB template blob. |
| `results.txt` | Raw `go test` output (sizes, correctness, 3 runs of each benchmark). |

Run: `go test -v -run 'TestSizes|Correct' . && go test -run '^$' -bench . -benchtime=30x -count=3 .`

## Parameters
- CKKS: LogN=13, LogQ={50,40,40}, LogP={50}, scale 2^40 (LogQP=180, i.e. ≤ 218 for 128-bit security at N=2^13 per the HE-standard tables lattigo follows). 4096 slots.
- BGV: LogN=13, LogQ={54,54}, LogP={55}, t=65537.

## Results (medians of 3 runs, this box)
| Operation | Time | Size |
|---|---|---|
| CKKS client: encode+encrypt probe | 3.3 ms | 393,566 B ciphertext |
| CKKS server: distance (mul, relin, rotate-sum) | 9.8 ms | result ct 131,390 B |
| CKKS decrypt result | 0.29 ms | |
| CKKS keygen (sk, pk, relin, 7 Galois) | 55 ms | eval keys 12.6 MB |
| CKKS stored template (2 ct) | | 787,132 B per user unpacked |
| BGV server: Hamming over 256 bits | 13.2 ms | ct 262,478 B |
| OPRF server evaluate (ristretto255) | 49 µs | 32 B element |
| OPRF client round trip (blind, eval, finalize) | 170 µs | |
| Plain LDA-16 + scaled-Manhattan score | 0.30 µs | |
| AES-256-GCM seal+open template | 1.5 µs | 1,756 B sealed |
| Ed25519 sign / verify 200-B assertion (software key) | 19.6 µs / 44.3 µs | 64 B sig |
| ECDSA P-256 sign / verify (software key) | 31.3 µs / 68.3 µs | ~72 B sig |

Not measured: network latency; packing many users per ciphertext (4096 slots / 64 features = 64 users per ct would bring the template to ~12 KB/user — inference, not measured); malicious-security add-ons (ZK proofs, Bassit et al. 2021 report 0.95–2.50 s); threshold decryption.

Caveats: CKKS decryptions leak key information if decrypted results are shared with an adversary (Li & Micciancio, EUROCRYPT 2021, IND-CPA^D). Any scheme that returns a distance/score to a party that can submit probes enables centre-search (Pagnin et al., INDOCRYPT 2014). Return only a thresholded bit, rate-limit, and keep the decryptor separate from the evaluator.
