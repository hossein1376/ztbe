# ZTBE interfaces (v2.1 draft)

Status: draft, 2026-10-21. Normative behaviour is in `spec/ZTBE-spec-v2-draft.md` §9. This document gives the wire formats and APIs.
- Formats are written in CDDL (RFC 8610).
- The HTTP API is an OpenAPI 3.1 sketch.
- Events follow OpenID SSF 1.0 / CAEP 1.0 (Final).
- Errors use `application/problem+json` (RFC 9457).

Nothing here is implemented yet. All of it is MVP milestone M2–M4 work (PLAN).

## 1. CDDL

```cddl
; ---------- COSE envelope (RFC 9052 COSE_Sign1, tag 18) ----------
ZTBE-Signed = #6.18([
  protected:   bstr .cbor ztbe-protected,
  unprotected: {},                       ; empty; everything is protected
  payload:     bstr .cbor (ZTBE-Assertion / ZTBE-Proof),
  signature:   bstr                      ; 64 B for both algorithms
])

ztbe-protected = {
  1 => -9 / -19,                         ; alg: ESP256 | Ed25519 (RFC 9864). -7/-8 MUST be rejected
  4 => bstr .size 16,                    ; kid = SHA-256(device SubjectPublicKeyInfo)[:16]
  3 => "application/ztbe-assertion+cbor" / "application/ztbe-proof+cbor"   ; content type
}

; ---------- common body ----------
ztbe-common = (
  1 => 2,                                ; v: schema version
  2 => bstr .size 16,                    ; dev
  3 => uint,                             ; seq, strictly increasing per device (shared by assertions and proofs)
  8 => status,
  ? 9 => band,                           ; present iff status == active and >= 1 scored window in period
  10 => flags,
  11 => key-protection,
  12 => tstr,                            ; model_ver
  13 => tstr,                            ; policy_ver
)

status = &( active: 0, enrolling: 1, disabled: 2, paused: 3, locked: 4, capture-lost: 5 )
band   = &( ok: 0, uncertain: 1, high: 2 )
key-protection = &( hw-attested: 0, hw-unattested: 1, software: 2 )
flags = uint .bits flag-bits
flag-bits = &( synthetic-suspect: 0, reserved1: 1, rollover-disabled: 2,
               unscored-assistive: 3, remote-session: 4, device-change: 5, idle: 6 )

; ---------- device -> verifier (push, every <= 60 s while unlocked) ----------
ZTBE-Assertion = {
  ztbe-common,
  4 => bstr .size 16,                    ; nonce: current verifier epoch nonce
  5 => uint,                             ; t0 (Unix s)
  6 => uint,                             ; t1 (Unix s), t1 <= now + 30
  7 => uint,                             ; nwin: scored windows in this period (0 = heartbeat)
  ? 14 => bstr .size 32,                 ; pgrant: SHA-256(pause grant); required iff status == paused
}

; ---------- device -> RP (pull, per RP challenge) ----------
ZTBE-Proof = {
  ztbe-common,
  15 => tstr,                            ; aud: RP origin (browser, set by the extension from the sender origin) or OAuth client_id
  16 => bstr .size (16..64),             ; chal: RP challenge, echoed
  17 => uint,                            ; iat (Unix s)
}

; ---------- verifier -> device: pause grant (JWS-free; COSE_Sign1 by verifier key) ----------
ZTBE-PauseGrant = {
  1 => bstr .size 16,                    ; dev
  2 => uint,                             ; nbf
  3 => uint,                             ; exp, exp - nbf <= 3600
  4 => bstr .size 16,                    ; webauthn_ref: hash of the WebAuthn assertion that authorised it
}
```

Size: an assertion is ≈ 120–200 B encoded, plus a 64 B signature (spec §9.1).

**Sig_structure.** Sign `["Signature1", protected, h'', payload]` (RFC 9052 §4.4). Deterministic CBOR encoding (RFC 8949 §4.2) is used for the protected header and the payload, so that test vectors are byte-stable.

## 2. Verifier HTTP API (OpenAPI 3.1 sketch)

Authentication by caller:
- `/device/*`: **mTLS with the device key**. The client certificate is issued at enrolment (spec §9.4).
- `/rp/*`: OAuth 2.0 client credentials; DPoP- or mTLS-bound per RFC 9449 / RFC 8705.
- `/user/*`: a user session at the IdP, plus WebAuthn where marked.

```yaml
openapi: 3.1.0
info: { title: ZTBE verifier, version: 2.1.0-draft }
paths:
  /device/v1/enrol:
    post:
      summary: Register device key, bound to a WebAuthn assertion (spec §9.2)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [csr, key_attestation, webauthn_assertion]
              properties:
                csr: { type: string, description: "PKCS#10, base64url; device key (P-256 or Ed25519)" }
                key_attestation: { type: string, description: "TPM2 certify blob + AK chain (base64url), or empty" }
                webauthn_assertion: { type: object, description: "challenge = SHA-256(pubkey || attestation)" }
      responses:
        '201': { description: "client certificate (PEM), dev id, key_protection as verified" }
        '400': { $ref: '#/components/responses/Problem' }
  /device/v1/epoch:
    get:
      summary: Current and previous epoch nonce (rotated every 10 min)
      responses: { '200': { description: "{ current: b64url16, previous: b64url16, rotates_at: int }" } }
  /device/v1/assertions:
    post:
      summary: Submit one ZTBE-Assertion (application/cose; cose-type="cose-sign1")
      requestBody: { content: { application/cose: {} } }
      responses:
        '202': { description: accepted }
        '409': { description: "dropped (seq/nonce/time); counted; band unchanged", $ref: '#/components/responses/Problem' }
  /user/v1/pause:
    post:
      summary: Issue a pause grant after WebAuthn (<= 60 min) (spec §9.3)
      responses: { '201': { description: "ZTBE-PauseGrant (COSE_Sign1 by verifier)" } }
  /user/v1/ztbe:
    delete:
      summary: Withdraw consent / disable ZTBE for all of the user's devices; deletes device records
      responses: { '204': { description: done } }
  /rp/v1/devices/{user}:
    get:
      summary: Device keys registered to a user (for ZTBE-Proof verification); JWK set
      parameters: [ { name: user, in: path, required: true, schema: { type: string } } ]
      responses: { '200': { description: "JWKS: kid, kty, crv, x, y, key_protection, status" } }
  /rp/v1/proof/verify:
    post:
      summary: Optional convenience — verifier checks a ZTBE-Proof for the RP
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [proof, expected_aud, expected_chal, user]
      responses: { '200': { description: "{ valid: bool, status, band, flags, reason }" } }
components:
  responses:
    Problem:
      description: RFC 9457 problem details
      content: { application/problem+json: { schema: { $ref: '#/components/schemas/Problem' } } }
  schemas:
    Problem:
      type: object
      properties:
        type:   { type: string, format: uri }
        title:  { type: string }
        status: { type: integer }
        detail: { type: string }
```

SSF stream management (`/ssf/...`) follows OpenID SSF §7–§8 (Transmitter Configuration Metadata at `/.well-known/ssf-configuration`). It is not repeated here.

### 2.1 Error codes (`type` URIs, suffix shown)

| Suffix | HTTP | Meaning | Effect on band |
|---|---|---|---|
| `bad-signature` | 409 | Signature or `kid` mismatch with mTLS identity | None. Counted |
| `stale-seq` | 409 | `seq` ≤ last seen (replay) | None. Counted |
| `bad-nonce` | 409 | Not the current or previous epoch | None. The device should refetch `/epoch` |
| `future-time` | 409 | `t1 > now + 30 s` | None. Counted |
| `bad-alg` | 400 | −7 / −8 or other alg | None. Counted |
| `no-grant` | 409 | `status=paused` without a valid grant | Treated as `capture_lost` → SIGNAL_LOST |
| `rate-limited` | 429 | More than 10 assertions per minute per device | None |
| `integrity-suspect` | — (event) | More than 10 invalid assertions per device per hour | CAEP MEDIUM, `ASSERTION_INVALID`; operator alert |

## 3. SSF / CAEP mapping

The verifier is the SSF Transmitter. Each RP or IdP is a Receiver. Events are SETs (RFC 8417):
- header `typ: secevent+jwt`, as SSF requires;
- no `sub` claim;
- the subject goes in `sub_id`.

| ZTBE state change | CAEP `current_level` | `principal` | `risk_reason` |
|---|---|---|---|
| band → ok | LOW | DEVICE | `BEHAVIOUR_OK` |
| band → uncertain | MEDIUM | DEVICE | `BEHAVIOUR_DEVIATION` |
| band → high (trust alarm) | HIGH | DEVICE | `BEHAVIOUR_DEVIATION` |
| silence ≥ 150 s while active, or `capture_lost`, or `paused` without a grant | HIGH | DEVICE | `SIGNAL_LOST` |
| `synthetic_suspect` | MEDIUM | DEVICE | `SYNTHETIC_INPUT_SUSPECT` |
| `integrity_suspect` | MEDIUM | DEVICE | `ASSERTION_INVALID` |
| enrolling / disabled / unscored / remote / locked / paused with a grant | No risk event. A ZTBE-specific `signal-status` event MAY be sent (not standard CAEP) | — | — |

Notes:
- CAEP 1.0 §3.8.1 requires `principal` and `current_level`. `risk_reason` is RECOMMENDED and free-form; the values above are ZTBE's.
- The verifier does not know RP session IDs, so the principal is the **device**. The RP maps the device to its sessions through the proofs it has verified (§4).
- "No signal" states are deliberately **not** risk events: absence of a ZTBE signal must not read as risk (spec §9.8).

Example SET (payload; signed by the verifier's JWKS key):

```json
{
  "iss": "https://ztbe.example.com/",
  "jti": "0f8e3c3b6c9b4f6e9d1a",
  "iat": 1792570000,
  "aud": "https://rp.example.com/ssf",
  "txn": "dev-7f2a-seq-48121",
  "sub_id": {
    "format": "complex",
    "user":   { "format": "iss_sub", "iss": "https://idp.example.com/", "sub": "u-4711" },
    "device": { "format": "opaque", "id": "7f2a9c0e5b1d4a3f8e6c2b9a1d0f3e4c" }
  },
  "events": {
    "https://schemas.openid.net/secevent/caep/event-type/risk-level-change": {
      "current_level": "HIGH",
      "previous_level": "LOW",
      "principal": "DEVICE",
      "risk_reason": "SIGNAL_LOST",
      "event_timestamp": 1792569990
    }
  }
}
```

The timestamps are illustrative (2026-10-21).

## 4. RP integration guide

1. **Register as an SSF Receiver.** Use push (RFC 8935) or poll (RFC 8936), and subscribe to `risk-level-change`.
2. **Enrolment linkage.** At the user's first WebAuthn login with ZTBE enabled, the IdP (or the RP) records the user's ZTBE device `kid` list from `/rp/v1/devices/{user}`.
3. **Pull proofs** (A3, spec §9.5):
   1. Generate `chal` (≥ 16 random bytes) per sensitive operation, and every 5 min per session. Store it server-side with the session.
   2. Browser: call the ZTBE extension through the page API (`window.postMessage` to the content script; the extension adds the origin). Native: use the local IPC socket.
   3. Verify the proof:
      - COSE signature with the `kid` from the registry;
      - `aud` equals your origin or `client_id`;
      - `chal` matches;
      - `iat` is no more than 60 s old;
      - the device belongs to the session user;
      - `seq` is greater than the last `seq` seen for this device by you.
   4. Remember (session → `kid`) so that DEVICE-principal events map to sessions.
   5. No valid proof → step-up.
4. **Sender-constrain sessions** where possible: DBSC for browser sessions; DPoP (RFC 9449) or mTLS (RFC 8705) for API tokens.
5. **Policy.**
   - HIGH → step-up (RFC 9470 `insufficient_user_authentication`, WebAuthn with UV).
   - MEDIUM → optional step-up for sensitive operations only.
   - LOW → nothing. LOW never raises assurance.
   - No signal → your normal non-ZTBE policy.
   - Rate-limit ZTBE step-ups to ≤ 2 per hour per user.
6. **Retention.** Keep events ≤ 30 days. No per-person reports (D6). Do not combine bands with HR or performance data.
7. **Test vectors.** Generated by `cmd/ztbe-eval` once M2 lands; not yet available.
