# Offline educational TLS 1.3-style simulator (WS-P7.2)

`pqc_bench.tls_simulator` is a bounded in-memory four-message protocol model.
It uses actual installed `cryptography` X25519 and ML-KEM-768 primitives, not
hash-based stand-ins. APIs were inspected locally using cryptography 50.0.1:
`X25519PrivateKey.generate()` / `exchange()`, `MLKEM768PrivateKey.generate()`,
`MLKEM768PublicKey.from_public_bytes()` / `encapsulate()`, and private-key
`decapsulate()`. Encapsulation returns **(shared_secret, ciphertext)**. Existing
`cryptography>=50.0.0,<51` suffices; this implementation adds no dependencies.

## Scope and non-goals

This is **not production TLS**, wire-compatible TLS 1.3, a standardized hybrid
TLS group, or historical X25519Kyber768. It has no sockets, external endpoints,
TLS stack, certificates, identity authentication, record encryption,
confidentiality claim, key export service, tickets, PSK/resumption, 0-RTT,
negotiation, HelloRetryRequest, or key updates. It makes **no FIPS certification
claim**. Finished demonstrates transcript/key confirmation within this model,
**not peer identity authentication**. No MITM-resistance or production security
claim is made. Both hybrid components are mandatory; no fallback exists.

Private keys are freshly generated inside peers, never imported or persisted.
Use only locally generated ephemeral test keys. Parsing supports local modeling
and tests, not remote service integration. No secrets are logged or included in
reports. `TrafficSecrets` and internal schedules redact repr, but explicit
attribute inspection exposes educational byte values. Do not serialize them with
`dataclasses.asdict`; repr redaction is not access control. Keys/schedules are
dereferenced after use/failure, **without guaranteed Python/backend memory erasure**.

## API

```python
from pqc_bench.tls_simulator import simulate_handshake

result = simulate_handshake(client_context=b"lesson-client", server_context=b"lesson-server")
assert result.client_application_match
assert result.server_application_match
report = result.to_report()  # local duration, public transcript digest, booleans; no secrets
```

For educational inspection, independent single-use peers expose these operations:

```python
from pqc_bench.tls_simulator import ClientPeer, ServerPeer

client, server = ClientPeer(), ServerPeer()
ch = client.client_hello()
sh = server.receive_client_hello(ch)
client.receive_server_hello(sh)
sf = server.server_finished()
client.receive_server_finished(sf)
cf = client.client_finished()
server.receive_client_finished(cf)
assert client.traffic_secrets == server.traffic_secrets
```

Each peer independently computes its X25519 shared value and full schedule.
The server encapsulates to the client's ML-KEM public key; the client independently
decapsulates. Only serialized messages cross between peers. Directional equality:

- Client-derived **client application** equals server-derived **client application**.
- Client-derived **server application** equals server-derived **server application**.
- Client application and server application directions are **not** equated to each other.

`traffic_secrets` is unavailable before local completion. Client completion means
it checked ServerFinished and emitted ClientFinished, not that it knows the server
received it. Server completion requires valid ClientFinished. Read-only properties
`state` and `transcript_hash` expose local status/public digest.

Protocol errors raise `ProtocolError` (a `ValueError`) and make that peer terminal,
releasing held schedule/application values. A replayed operation invalidates even
a completed peer's local access. Earlier references intentionally obtained by a
caller cannot be revoked. Use new peers for another exchange; peers are not
thread-safe. Reading unavailable `traffic_secrets` raises without changing state.

Frozen `ClientHello`, `ServerHello`, and `Finished` structures have `encode()`;
`decode_message(bytes)` returns exactly one validated structure. Helpers:
`hkdf_extract(salt, ikm)`, `hkdf_expand_label(secret, label, context, length=32)`,
and `derive_secret(secret, label, transcript)`.

## Custom framing, bounds and transcript

Each frame is `uint8 kind || uint24 body_length || body` (big-endian lengths):

1. ClientHello (1): random[32], X25519 public[32], ML-KEM public[1184],
   uint16 context_length, context.
2. ServerHello (2): random[32], X25519 public[32], ML-KEM ciphertext[1088],
   uint16 context_length, context.
3. ServerFinished (20): byte `s`, verify_data[32].
4. ClientFinished (20): byte `c`, verify_data[32].

The transcript starts with `b"PQC-BENCH-OFFLINE-TLS13-V1\x00"`, then exact canonical
frames in this order. Contexts need not equal each other; both are transcript-bound
public opaque lesson data, not credentials. Framing/domain prefix intentionally
differ from TLS.

- Exact immutable `bytes` inputs; strings, bytearray, memoryview, and others fail.
- Each hello context: 0–256 bytes; maximum message: 1510 bytes.
- Maximum ClientHello: 1510 bytes; ServerHello: 1414; each Finished: 37.
- Transcript maximum: 4096 bytes; only four ordered messages are accepted.
- X25519 and ML-KEM shared values: exactly 32 bytes each, fixed order
  `X25519_shared || MLKEM_shared`; all-zero X25519 exchange is rejected.
- Public key/ciphertext sizes are exact; backend validation rejects invalid
  X25519 exchanges and noncanonical ML-KEM public keys. ML-KEM implicit rejection
  means a modified correctly-sized ciphertext can yield a different secret
  instead of an exception; Finished detects the resulting disagreement.
- Extract salt/IKM: 0–4096 bytes each. Expand secret: exactly 32 bytes;
  label: 1–249 bytes; context: 0–255 bytes; output length: integer 1–8160
  (bool and float rejected). Derive-Secret transcript: 0–4096 bytes.

Unknown kinds, wrong direction, wrong lengths, truncation, trailing/concatenated
bytes, order errors and replayed operations are rejected. These are local contracts,
not a hardened network-parser guarantee or global cross-session replay database.
Fresh randomness and Finished bind the exchange; no identity trust is established.

## SHA-256 key schedule

Let `Z` be 32 zero bytes, `H` be SHA-256, `Extract` be RFC 5869 HMAC-SHA256
Extract, and `DS` be RFC 8446-style Derive-Secret. Expansion uses cryptography's
`HKDFExpand`; it does not perform another Extract.

```
HkdfLabel = uint16 output_length
          || uint8 len(b"tls13 " + label) || b"tls13 " + label
          || uint8 len(context) || context
DS(secret, label, transcript) = ExpandLabel(secret, label, H(transcript), 32)

early     = Extract(Z, Z)                       # no PSK
handshake = Extract(DS(early, "derived", empty), X25519_shared || MLKEM_shared)
c_hs      = DS(handshake, "c hs traffic", domain || CH || SH)
s_hs      = DS(handshake, "s hs traffic", domain || CH || SH)
master    = Extract(DS(handshake, "derived", empty), Z)

finished_key = ExpandLabel(direction_hs, "finished", empty, 32)
verify_data  = HMAC(finished_key, H(transcript_before_this_Finished))

c_app = DS(master, "c ap traffic", domain || CH || SH || ServerFinished)
s_app = DS(master, "s ap traffic", domain || CH || SH || ServerFinished)
```

An empty Derive-Secret transcript is hashed; the Finished expansion context itself
is empty, not the hash of empty. ServerFinished covers both hellos; ClientFinished
also covers ServerFinished. Like TLS 1.3's application-secret boundary, application
derivation includes ServerFinished but not ClientFinished. The final reported
digest includes all four messages. Master itself is not transcript-bound; traffic
expansions are. Confirmations/final comparisons use `hmac.compare_digest`.

## Local timing and verification

`simulate_handshake()` runs one exchange. Monotonic `perf_counter_ns()` measures
from before peer/key creation through final directional equality and transcript
checks. Initial context validation and result/report construction are outside the
interval. The report names this `local_simulation_duration_not_network_rtt` and
stores `local_duration_ns`. Python/crypto/scheduling overhead is included. It is
neither network RTT, pure CPU time, a latency guarantee, nor constant-time evidence.
Randomness, digests and actual elapsed values vary; deterministic patched-clock
tests reproduce the timing contract, not the measured performance.

```sh
python3 -m pytest tests/test_tls_simulator.py -q
```

Focused verification: **74 passed (0.44 s)** on the local CPU with cryptography
50.0.1. Tests cover RFC 5869 known-answer Extract/Expand, independent HMAC reference
for TLS label encoding/full schedule, independent peers/directional equality,
both hybrid components, Finished transcript boundaries, altered hellos/ciphertext,
low-order X25519 and noncanonical ML-KEM keys, malformed/order/replay failures,
bounds, secret-free repr/report, real local duration and deterministic clock
contract. Socket creation is disabled during the convenience-simulation test.
Final parent verification on the committed source: **1029 passed, 2 dependency
warnings (26.23 s)**, including all 74 simulator tests. Source SHA-256 before and
after that run: `d824cf104a4f3b32fa37885aa95e7ba07ab59c1b23f722c472ff34d67ff619bc`.
No external TLS interoperability or GitHub CI success is claimed.
