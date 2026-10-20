# ZTBE: design rationale (non-normative)

Status: rationale note, v2.1 round 2, 2026-10-21 (Asia/Tehran). **The normative text is [`spec/ZTBE-spec-v2-draft.md`](spec/ZTBE-spec-v2-draft.md).** This file explains *why* the design looks the way it does and points to the spec for every rule. Earlier PROPOSAL versions (v2.0 architecture with its own parameters) are in git history. Review round 1 §1.2 listed their contradictions with the spec; this rewrite resolves them by removing every normative statement from this file (decision D14).

## 1. The problem in one paragraph

A login proves who started a session, not who is typing an hour later. Keystroke dynamics can say something about the second question continuously and without user effort. But they are too weak to be an authentication factor:
- per-window FRR@FAR1% is 20–60%, and guessing entropy is about 1–4 bits (`notes/experiments-v2.md`);
- NIST SP 800-63B-4 requires FMR ≤ 1/10000 for all demographic groups.

So ZTBE is a **risk signal that can only ever trigger a WebAuthn step-up** (D1, spec §1).

## 2. Why on-device scoring, not server-side or cryptographic matching

| Option | Why rejected or kept | Evidence | Spec |
|---|---|---|---|
| Fuzzy extractors / fuzzy commitment / BTP (v1) | One population-dictionary guess opens 3.5–22% of lockers at FAR 1%. At usable FRR, sample-then-lock is opened 52% of the time | experiments-v2 §6 | §3 (dropped) |
| Server-side HE (CKKS) or OPRF lockers | 10³–10⁵× the cost (9.8 ms server, 393 KB upload per probe; or ≈ 74 ms + 255 ms) with no accuracy gain, and it does not remove the oracle | `experiments/go-he` | §1 non-goals, D5 |
| **On-device template, sealed by TPM or Secure Enclave, signed 3-level bands** | Nothing behavioural at the server. Signing costs microseconds | go-he plain benchmarks | §7, §9 |

## 3. Why these parameters

Everything was re-measured in round 2 with disjoint-user calibration and bootstrap CIs (`eval2.py`; experiments-v2 §9).
- **Global threshold, not per-user.** At matched FAR 10%, P0 FRR is 6.6% [4.4, 9.6] vs 11.1% [6.9, 18.2] for per-user q95 (spec §6.1).
- **21 features.** Non-inferior to 34 (spec §3; D11).
- **Hybrid window, K = 4, trust model.** Spec §4, §6.4–§6.5.
- **Long enrolment.** A 1-window template accepts 44% of impostor blocks, 20 windows 20%, and a full week 11–12% (spec §5).
- **No adaptation.** The unsupervised guard stack is broken by an adaptive attacker (31.6% takeover), and supervised updates give no FRR benefit (spec §8; D8).

## 4. Why the agent and protocol are shaped this way

- **Native agent split into a service and a capture helper.** Global capture, OS injection flags and keyboard identity are only available natively. The service cannot be stopped by a standard user (spec §9.3; D12; `notes/collector-tradeoffs.md`).
- **Heartbeat; silence → HIGH; pause only with WebAuthn.** Otherwise the walk-up attacker, the main A4 adversary, can simply turn ZTBE off (spec §9.3, §9.6; D10).
- **RP-challenge-bound proofs plus DBSC/DPoP/mTLS.** Push events alone do not stop a stolen cookie (spec §9.5).
- **COSE ESP256 / Ed25519, implemented in-house.** Per RFC 9864; go-cose lacks both (spec §9.1; D9).
- **CAEP risk-level-change.** It is the standard event for exactly this signal (spec §9.7; `docs/interfaces.md`).

## 5. What is still unknown (and decides go/no-go)

1. **Same-device impostors.** Every detection number so far comes from impostors on *different* hardware (spec §11 L1). The pilot in `docs/pilot-protocol.md` measures this, with pre-registered go/no-go thresholds (D15).
2. **Capture feasibility per OS:** injection flags for assistive tools, timestamp precision, permissions (PLAN M1-T5).
3. **Real step-up burden and `SIGNAL_LOST` rate** on real hardware.
4. **Legal basis for any workforce use** (D6; `docs/dpia-outline.md`).

## 6. Where things moved

| Former PROPOSAL section | Now |
|---|---|
| §1 summary, §8 claims | spec §1, §11 |
| §2 threat model (old A3–A7 numbering) | spec §2 (A1–A10) |
| §3 components and data flow, §4 storage budget, §7 latency budget | spec §13 |
| §5 parameters | spec §3–§6, App. A |
| §6 adaptation | spec §8 |
| §9 Go layout | spec §14; milestones in PLAN.md |
| §10 decisions | `notes/decisions.md` |
