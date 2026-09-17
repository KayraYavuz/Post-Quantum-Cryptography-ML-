# WS-P7.2 — Offline hybrid handshake simulation

## Scope

`pqc_bench.tls_simulator` is a bounded, in-memory educational model. It reuses
`cryptography>=50.0.0,<51` (tested 50.0.1), including actual X25519 and
ML-KEM-768 primitives. No new dependency, socket, live endpoint, certificate
service or external key input is used by `simulate_handshake`.

This is **not wire-compatible TLS**, a standardized X25519MLKEM768 group,
X25519Kyber768 interoperability implementation, or authenticated PKI. There is
no record layer, encryption, certificate exchange, peer identity validation,
0-RTT, PSK, resumption, key update or deployable session-key API. No production
confidentiality, security, FIPS 140-3 certification or network-performance claim
is made. Finished checks establish agreement within this model, not identity.

## API

```python
from pqc_bench.tls_simulator import simulate_handshake

result = simulate_handshake(b"local client context", b"local server context")
report = result.to_report()  # equality flags, digest, local duration; no secrets
assert report["client_application_match"]
assert report["server_application_match"]
```

For local protocol tests, `ClientPeer` and `ServerPeer` generate their own
fresh ephemeral keys and exchange bytes in this order:

1. `client.client_hello()` → `server.receive_client_hello(ch)` returns `sh`.
2. `client.receive_server_hello(sh)` independently decapsulates and derives.
3. `server.server_finished()` → `client.receive_server_finished(sf)`.
4. `client.client_finished()` → `server.receive_client_finished(cf)`.

Only completed peers expose `traffic_secrets`, with separate
`client_application` and `server_application` test values. Each direction
matches across peers; client and server directions are **not** equal to each
other. These bytes are inspectable for tests, not for deployment. Secret fields
are excluded from repr and simulation reports. Private-key references are
released after hello processing; schedules are released at completion. Python
memory zeroization is not guaranteed. Peers are single-session, synchronous
objects, not thread-safe services. A client can complete after emitting its
Finished without knowing whether the server received it; the runner completes
both peers before reporting success.

## Model and limits

- Hybrid input is the fixed-size concatenation `X25519 shared || ML-KEM shared`
  (32 + 32 bytes), not a newly standardized hybrid combiner.
- SHA-256 HKDF follows RFC 8446 §7.1: no-PSK early secret, `derived` with
  Hash(empty), handshake Extract, directional handshake secrets, another
  `derived` and master Extract, then directional application secrets.
- HKDF labels encode uint16 output length, length-prefixed `tls13 ` + label,
  and length-prefixed context. Derive-Secret hashes its transcript argument.
- Custom transcript begins with `PQC-Bench offline handshake v1\0`, followed by
  type + uint24 body length + body for each message. Hello bodies contain
  32-byte random, 32-byte X25519 public key, 1184-byte ML-KEM public key (client)
  or 1088-byte ciphertext (server), and uint16-length-prefixed context.
- Contexts are bytes only, 0–256 bytes. Message cap is 1510 bytes; transcript
  cap is 4096 bytes. Finished bodies use a one-byte direction plus 32-byte
  verify data. No parser accepts trailing data or inconsistent lengths.
- Application secrets bind the transcript **through server Finished**, as in
  the TLS key-schedule boundary. Client Finished verifies that same transcript;
  the final reported digest additionally includes client Finished.
- Malformed frames, invalid public shares, wrong direction/type, reordering,
  replay and Finished mismatch terminally fail the receiving peer and disable
  access to its traffic values. This is not a third-party TLS testing utility.

## Timing and verification

`local_duration_ns` uses `perf_counter_ns` around fresh peer creation, generated
keys, all in-memory exchanges and agreement checks (excluding final report
construction). Argument validation happens before timing. This measures local
simulation duration only, **not network latency or RTT**. Repeating the same
procedure is supported; randomness, scheduling and execution times are not
deterministic. Tests replace the clock to verify an exact duration delta and
also exercise real timing without speed thresholds.

CPU test command: `python3 -m pytest tests/test_tls_simulator.py -q`.
The 74 cases cover RFC 5869 Extract known-answer data, independent HMAC label
and key-schedule references, both hybrid components, independent peer equality,
transcript/Finished boundaries, tampering, canonical framing, bounds, invalid
shares, replay/order rejection, redacted representations and socket-denied
simulation. Final full repository run: **1029 passed, 2 dependency warnings,
30.07 s** (includes all 74 simulator cases). No GitHub CI result is asserted.

References: [RFC 8446 §7](https://www.rfc-editor.org/rfc/rfc8446.html#section-7),
[RFC 5869](https://www.rfc-editor.org/rfc/rfc5869.html),
[cryptography ML-KEM API](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mlkem/).
