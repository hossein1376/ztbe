# ZTBE interfaces (v2.2 draft)

Status: draft v2.2, 2026-10-21 (review round 2 fixes H1–H3, H5, H8; D18–D20). Normative behaviour is in `spec/ZTBE-spec-v2-draft.md` §9. This document gives the wire formats and APIs.
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
  unprotected: {},                       ; empty; everything is protected (non-empty MUST be rejected)
  payload:     bstr .cbor (ZTBE-Assertion / ZTBE-Proof),
  signature:   bstr .size 64             ; raw r||s for ESP256, or Ed25519
])

ztbe-protected = {
  1 => -9 / -19,                         ; alg: ESP256 | Ed25519 (RFC 9864). -7/-8 MUST be rejected
  4 => bstr .size 16,                    ; kid: assertions = dev (verifier-only); proofs = pdid (pairwise, D18)
  3 => "application/ztbe-assertion+cbor" / "application/ztbe-proof+cbor"   ; content type
}

status = &( active: 0, enrolling: 1, disabled: 2, paused: 3, locked: 4, capture-lost: 5, unscored: 6 )
band   = &( ok: 0, uncertain: 1, high: 2 )
key-protection = &( hw-attested: 0, hw-unattested: 1, software: 2 )
flags = uint .bits flag-bits
flag-bits = &( synthetic-suspect: 0, latched: 1, rollover-disabled: 2,
               unscored-change: 3, reserved4: 4, device-change: 5, idle: 6, unlocked-since-last: 7 )
; "unscored" covers assistive profile and remote session; the reason is never transmitted (spec §3.1, D18)

; ---------- device -> verifier only (push over mTLS, every <= 60 s while unlocked) ----------
ZTBE-Assertion = {
  1 => 2,                                ; v: schema version
  2 => bstr .size 16,                    ; dev = SHA-256(device SPKI)[:16]; never sent to RPs
  3 => uint,                             ; seq = max(last_seq + 1, unix_ms * 2^10), persisted before send (spec §9.4)
  4 => bstr .size 16,                    ; nonce: current verifier epoch nonce
  5 => uint,                             ; t0 (Unix s)
  6 => uint,                             ; t1 (Unix s), t1 <= now + 30
  7 => uint,                             ; nwin: scored windows in this period (0 = heartbeat)
  8 => status,
  ? 9 => band,                           ; effective band (spec §9.9); present iff status == active
  10 => flags,
  11 => key-protection,
  12 => tstr,                            ; model_ver
  13 => tstr,                            ; policy_ver
  ? 14 => bstr .size 32,                 ; pgrant: SHA-256(pause grant); required iff status == paused
  ? 18 => uint,                          ; lsw: end of last scored window (Unix s); absent if none since unlock
}

; ---------- device -> linked RP only (pull, per RP challenge); signed by the per-RP proof key ----------
ZTBE-Proof = {
  1 => 2,                                ; v
  11 => key-protection,                  ; of the per-RP proof key
  15 => tstr,                            ; aud: linked RP origin (set by the extension from the sender origin) or client_id
  16 => bstr .size (16..64),             ; chal: RP challenge, echoed
  17 => uint,                            ; iat (Unix s)
  19 => sig,                             ; effective state (spec §9.9)
  20 => age,                             ; time since last scored window, coarse
}
; deliberately absent from proofs: dev, seq, flags, status detail, model_ver, policy_ver (linkable or sensitive)
sig = &( low: 0, medium: 1, high: 2, no-signal: 3 )
age = &( le2min: 0, le5min: 1, le10min: 2, gt10min-or-none: 3 )

; ---------- verifier -> device: pause grant (COSE_Sign1 by verifier key) ----------
ZTBE-PauseGrant = {
  1 => bstr .size 16,                    ; dev
  2 => uint,                             ; nbf
  3 => uint,                             ; exp, exp - nbf <= 3600
  4 => bstr .size 16,                    ; webauthn_ref: hash of the WebAuthn assertion that authorised it
}

; ---------- verifier -> device: latch clear receipt after verified WebAuthn (spec §9.9 exit a) ----------
ZTBE-Clear = {
  1 => bstr .size 16,                    ; dev
  2 => uint,                             ; iat
  3 => bstr .size 16,                    ; webauthn_ref
}

; ---------- verifier -> RP: link record (returned by /rp/v1/links) ----------
ZTBE-Link = {
  1 => tstr,                             ; rp_id
  2 => tstr,                             ; rp_sub: the RP's own subject for the user
  3 => bstr .size 16,                    ; pdid = HMAC-SHA-256(k_verifier, rp_id || dev)[:16]
  4 => bstr,                             ; proof public key (COSE_Key)
  5 => key-protection,
}
```

Size: an assertion is ≈ 120–200 B encoded, plus a 64 B signature (spec §9.1). A proof is smaller (≈ 60–110 B + 64 B).

The COSE implementation checklist (DER → raw `r‖s`, verify over received bytes, alg/key-type check, strict decoding, negative fuzzing, key-use separation) is normative in spec §9.1.

**Sig_structure.** Sign `["Signature1", protected, h'', payload]` (RFC 9052 §4.4). Deterministic CBOR encoding (RFC 8949 §4.2) is used for the protected header and the payload, so that test vectors are byte-stable.

## 2. Verifier HTTP API (OpenAPI 3.1 sketch)

Authentication by caller:
- `/device/*`: **mTLS with the device key**. The client certificate is issued at enrolment (spec §9.4).
- `/rp/*`: OAuth 2.0 client credentials; DPoP- or mTLS-bound per RFC 9449 / RFC 8705. Every `/rp/*` response is **scoped to the calling `rp_id`**: an RP can only see links, `pdid`s and proof keys of its own subjects (D18).
- `/user/*`: a user session at the IdP, plus WebAuthn where marked.

```yaml
openapi: 3.1.0
info: { title: ZTBE verifier, version: 2.2.0-draft }
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
        '409': { description: "dropped; problem body includes server_time and current epoch so the device resyncs (spec §9.4)", $ref: '#/components/responses/Problem' }
  /device/v1/links:
    post:
      summary: User-initiated link to an RP (agent/extension UI, after the user approves the origin). Registers a fresh per-RP proof key
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [rp_origin, proof_key, key_attestation]
      responses: { '201': { description: "one-time link code (≤ 10 min) to show/hand to the RP; pdid is NOT returned to the page" } }
    delete:
      summary: User unlinks an RP; proof key and pdid are deleted
      responses: { '204': { description: done } }
  /user/v1/pause:
    post:
      summary: Issue a pause grant after WebAuthn (<= 60 min) (spec §9.3)
      responses: { '201': { description: "ZTBE-PauseGrant (COSE_Sign1 by verifier)" } }
  /user/v1/stepup:
    post:
      summary: IdP or agent UI reports a WebAuthn assertion verified for this user; clears the HIGH latch (spec §9.9 exit a); emits risk-level-change LOW with reason STEP_UP_OK to linked RPs
      responses: { '204': { description: "latch cleared; ZTBE-Clear delivered to the device with the next assertion response" } }
  /user/v1/ztbe:
    delete:
      summary: Withdraw consent / disable ZTBE for all of the user's devices; deletes device records. Requires a fresh WebAuthn assertion, like consent (spec §9.3)
      responses:
        '204': { description: done }
        '401': { description: "no or stale WebAuthn assertion", $ref: '#/components/responses/Problem' }
  /rp/v1/links:
    post:
      summary: Redeem a one-time link code. The verifier checks rp_sub belongs to the device's user (pairwise sub it issued to this RP, or an IdP ID token for the user)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [link_code, rp_sub]
              properties:
                link_code: { type: string }
                rp_sub: { type: string }
                id_token: { type: string, description: "required if the verifier is not the IdP" }
      responses: { '201': { description: "ZTBE-Link (pdid, proof key, key_protection)" } }
  /rp/v1/subjects/{rp_sub}/devices:
    get:
      summary: Proof keys linked to the calling RP for its own subject. No lookup by global user or device ID exists
      parameters: [ { name: rp_sub, in: path, required: true, schema: { type: string } } ]
      responses:
        '200': { description: "JWKS of per-RP proof keys: kid (= pdid), kty, crv, x, y, key_protection" }
        '404': { description: "no link for this rp_sub at this RP (indistinguishable from unknown subject)" }
  /rp/v1/proof/verify:
    post:
      summary: Optional convenience — verifier checks a ZTBE-Proof for the calling RP
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [proof, expected_aud, expected_chal, rp_sub]
      responses: { '200': { description: "{ valid: bool, sig, age, reason }" } }
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
| `bad-signature` | 409 | Signature or `kid` mismatch with mTLS identity; malformed COSE | None. **Integrity**: counted |
| `stale-seq` | 409 | `seq` ≤ last seen (replay or restore) | None. **Hygiene**: logged, not counted toward `integrity-suspect` |
| `bad-nonce` | 409 | Not the current or previous epoch | None. **Hygiene**. The device MUST refetch `/epoch` and drop stale queued assertions |
| `future-time` | 409 | `t1 > now + 30 s` | None. **Hygiene**. The device corrects its clock offset from `server_time` |
| `bad-alg` | 400 | −7 / −8 or other alg, or alg ≠ registered key type | None. **Integrity**: counted |
| `no-grant` | 409 | `status=paused` without a valid grant | Treated as `capture_lost` → SIGNAL_LOST |
| `rate-limited` | 429 | More than 10 assertions per minute per device | None |
| `integrity-suspect` | — (event) | More than 10 **integrity** failures per device per hour | CAEP MEDIUM, `ASSERTION_INVALID`; operator alert |

Persistent failures of either kind mean no valid assertion arrives; after 150 s the effective outcome is `SIGNAL_LOST` → HIGH (latched). See spec §9.4.

## 3. SSF / CAEP mapping

The verifier is the SSF Transmitter. Each RP or IdP is a Receiver. Events are SETs (RFC 8417):
- header `typ: secevent+jwt`, as SSF requires;
- no `sub` claim;
- the subject goes in `sub_id`.

Events go **only to linked RPs**, and each RP gets its own pairwise identifiers (D18). The levels follow the state machine in spec §9.9:

| ZTBE state change | CAEP `current_level` | `principal` | `risk_reason` |
|---|---|---|---|
| → LOW (block `ok`) | LOW | DEVICE | `BEHAVIOUR_OK` |
| → MEDIUM (block `uncertain`) | MEDIUM | DEVICE | `BEHAVIOUR_DEVIATION` |
| → MEDIUM (`synthetic_suspect`) | MEDIUM | DEVICE | `SYNTHETIC_INPUT_SUSPECT` |
| → MEDIUM (`unscored_change`: allowlisted input without an assistive profile, outside a supervised period) | MEDIUM | DEVICE | `UNSCORED_CHANGE` |
| → MEDIUM (stale: > 10 min unlocked without a scored window) | MEDIUM | DEVICE | `NO_RECENT_SCORE` |
| → MEDIUM (`integrity_suspect`) | MEDIUM | DEVICE | `ASSERTION_INVALID` |
| → HIGH (trust alarm), **latched** | HIGH | DEVICE | `BEHAVIOUR_DEVIATION` |
| → HIGH (silence ≥ 150 s, `capture_lost`, `paused` without grant), **latched** | HIGH | DEVICE | `SIGNAL_LOST` |
| HIGH → LOW after verified WebAuthn | LOW | DEVICE | `STEP_UP_OK` |
| HIGH → LOW after OS lock → unlock | LOW | DEVICE | `UNLOCK` |
| enrolling / disabled / unscored / paused with a grant / locked | No event (LOW and no-signal are equivalent for RPs; proofs carry `no_signal`) | — | — |

While latched, the verifier sends **no** LOW or MEDIUM event for the device; the next event after HIGH is always `STEP_UP_OK` or `UNLOCK`.

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
    "user":   { "format": "iss_sub", "iss": "https://idp.example.com/", "sub": "rp-pairwise-9c1e" },
    "device": { "format": "opaque", "id": "pdid-for-this-rp-3b7d0e1a9f42c6d8" }
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

The identifiers and timestamps are illustrative (2026-10-21). `sub` is the RP's own (pairwise) subject and `id` is this RP's `pdid`; another RP receives unrelated values for the same user and device.

## 4. RP integration guide

1. **Register as an SSF Receiver.** Use push (RFC 8935) or poll (RFC 8936), and subscribe to `risk-level-change`.
2. **Linking (D18).** The user starts the link in the ZTBE agent or extension UI and approves your origin. You receive a one-time link code (shown to the user or posted by the extension to your linked page) and redeem it at `/rp/v1/links` with your `rp_sub` (plus an IdP ID token if the verifier is not your IdP). Store the returned `pdid` and proof key. Later, fetch keys only via `/rp/v1/subjects/{rp_sub}/devices`. Pages that are not linked get no response from the extension.
3. **Pull proofs** (A3, spec §9.5):
   1. Generate `chal` (≥ 16 random bytes) per sensitive operation, and every 5 min per session. Store it server-side with the session.
   2. Browser: call the ZTBE extension through the page API (`window.postMessage` to the content script; the extension adds the origin). Native: use the local IPC socket.
   3. Verify the proof:
      - COSE signature with the per-RP proof key whose `kid` (= `pdid`) is linked to the session's `rp_sub`;
      - `aud` equals your origin or `client_id`;
      - `chal` matches;
      - `iat` is no more than 60 s old;
      - for sensitive operations, `age ≤ 1` (score at most 5 min old), otherwise step up;
      - map `sig`: `high` → step-up, `medium` → optional step-up for sensitive operations, `low` / `no_signal` → nothing.
      (Proofs carry no `seq`; replay is prevented by your single-use `chal` and the 60 s `iat` window.)
   4. Remember (session → `pdid`) so that DEVICE-principal events map to sessions.
   5. No valid proof → step-up.
4. **Sender-constrain sessions**: DBSC for browser sessions; DPoP (RFC 9449) or mTLS (RFC 8705) for API tokens. This is **required** for any claim that A3 (session hijack) is mitigated. Periodic proofs alone do not bind ordinary requests (spec §9.5).
5. **Policy.**
   - HIGH → step-up (RFC 9470 `insufficient_user_authentication`, WebAuthn with UV). **Latched:** do not clear a pending step-up on a later LOW/MEDIUM; clear it only after your successful step-up or on `STEP_UP_OK` / `UNLOCK`. Run the step-up at the IdP that reports it to the verifier, otherwise the device stays latched.
   - MEDIUM → optional step-up for sensitive operations only.
   - LOW → nothing. LOW never raises assurance.
   - No signal (`sig = no_signal`, incl. paused) → your normal non-ZTBE policy. Never treat it as suspect.
   - Rate-limit ZTBE step-ups to ≤ 2 per hour per user.
6. **Retention.** Keep events ≤ 30 days. No per-person reports (D6). Do not combine bands with HR or performance data.
7. **Test vectors.** Generated by `cmd/ztbe-eval` once M2 lands; not yet available.
