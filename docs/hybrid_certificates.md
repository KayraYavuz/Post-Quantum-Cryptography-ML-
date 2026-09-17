# WS-P7.1 — Offline experimental hybrid test PKI

## Scope and dependency

`pqc_bench.pki` builds a project-local two-certificate test chain using maintained
`cryptography` primitives: RSA-4096, exponent 65537, PKCS#1 v1.5/SHA-256 X.509
signatures and ML-DSA-65 (FIPS 204) detached signatures. The dependency is
`cryptography>=50.0.0,<51`; 50.0.1 was exercised on CPU. Backend ML-DSA support
is required; unsupported generation fails instead of substituting an algorithm.

This is an **experimental dual-signature envelope**, NOT a standardized composite
X.509 certificate, general RFC 5280 validator, TLS implementation, or production
PKI. It does not provide hostname validation, revocation, path discovery, SAN,
ACME, live CA, HSM, trust-store modification, networking or service integration.
Using FIPS 204's algorithm does not establish FIPS 140-3 module certification or
regulatory compliance. No interoperability or deployability is claimed.

## Exact schema

`generate_chain` returns an ordered tuple `(root, leaf)` of frozen
`HybridCertificate(certificate, pq_signature)` values. `certificate` is a
`cryptography.x509.Certificate`; `pq_signature` is exactly 3309 bytes.
`der` exports only the public RSA certificate, **not the hybrid envelope**.
There is no envelope wire parser/export format in this step.

Each certificate has:

- X.509 v3, a random positive serial of at most 159 bits (different per role).
- A single CN subject: 1–64 ASCII letters/digits, spaces, `.`, `_`, `-`;
  leading/trailing whitespace is rejected. Root and leaf CNs must differ.
- Root issuer equal to root subject; leaf issuer equal to root subject.
- Distinct RSA-4096 and ML-DSA-65 public keys per role.
- Explicit timezone-aware validity with whole seconds, 1–365 days when generated.
  Input years are 1950–9998; both endpoints must remain within that range.
  Generation uses the same validity interval for both roles. Validation requires
  a positive interval of at most 365 days and leaf validity contained in the root.
  Validity endpoints are inclusive.
- Exactly three extensions. Unknown extensions, even noncritical ones, are
  rejected by this intentionally narrow profile:
  1. Critical `BasicConstraints`: root `ca=True, path_length=0`, leaf
     `ca=False, path_length=None`.
  2. Critical `KeyUsage`: digitalSignature for both; keyCertSign and cRLSign
     additionally for root. All other bits false. cRLSign is a profile bit only;
     this module does not implement CRL handling.
  3. Noncritical experimental UUID OID
     `2.25.<integer of UUID db7a4f5e-9c1d-4e8a-b2f3-0a1b2c3d4e5f>` (`PQ_OID`).
     The extension's `extnValue` contents are exactly
     `b'PQC1\x00ML-DSA-65\x00'` followed by the 1952-byte raw ML-DSA-65 public key.
     This is a private experimental payload, not a standardized ASN.1 PQ key
     extension. X.509 supplies the outer extension OCTET STRING.

The root RSA key signs both X.509 certificates. The root ML-DSA-65 key signs
both detached envelopes over the exact message:

```text
b'pqc-bench/hybrid-cert/v1\x00' || uint32_big_endian(len(cert_DER)) || cert_DER
```

ML-DSA uses its default empty context with the above message prefix as domain
separation. The complete DER includes the RSA signature and the subject PQ key
extension. Changing either invalidates the PQ signature. A classical-only
consumer can ignore the noncritical extension and **will not verify the PQ
layer**; only this explicit dual-layer verifier enforces both. The leaf PQ
private key is generated but not used to sign certificates in this two-level
profile; proof of leaf private-key possession is out of scope.

## Trust and key handling

`verify_chain(chain, trusted_root_der=..., at=...)` requires an explicit bounded
root DER pin (1–16384 bytes); it never discovers or trusts a root automatically.
The caller must provision that pin through its own trusted channel. Obtaining
both pin and chain from an untrusted source does not establish trust. After
matching the pin exactly, validation checks both root signatures, both leaf
signatures, key/algorithm policy, names, constraints, usage, validity and schema.
Success returns `None`; policy/signature failures raise `HybridValidationError`
(a `ValueError`). Missing required Python arguments raise `TypeError` normally.

All four private test keys and serials use the library's secure random source.
Private keys are not returned, exported, persisted or logged by this API; they
become unreachable after generation (this is **not guaranteed memory zeroization**).
The certificates are deliberately unusable for a later TLS/private-key workflow.
No imported or deployed keys are accepted by the generation API.

## Local example

```python
from datetime import datetime, timezone
from pqc_bench.pki import generate_chain, verify_chain

at = datetime(2026, 9, 17, tzinfo=timezone.utc)
chain = generate_chain(not_before=at, validity_days=30)
# Only valid here because we just generated this root locally ourselves.
local_test_pin = chain[0].der
verify_chain(chain, trusted_root_der=local_test_pin, at=at)
```

## CPU verification

```bash
python3 -m pytest -q tests/test_hybrid_certificates.py
```

Tests use fresh local keys and fixed public timestamps: repeatable decisions,
not reproducible private keys, serials or signature bytes. Module-scoped fixtures
avoid unnecessary RSA generation. Coverage includes valid root/leaf schema,
DER round-trip, repeated verification, inclusive validity boundaries, timezone
normalization, expired/not-yet-valid rejection, explicit pinning, swapped/mixed
chains, tampered RSA and PQ signatures, detached signature substitution, malformed
arguments and independently signed invalid profiles. The invalid-profile tests
sign with local test issuers in both layers so policy tests do not pass merely
because of an unrelated signature mismatch. No production certificates, network
connections, private-key artifacts, performance or deployment claims are involved.
