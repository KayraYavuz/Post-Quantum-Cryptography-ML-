# PQC offline executive review &#8212; synthetic example

**Overall: not_verified**

- Offline management review only; no production security, attack resistance, certification or hardware claim.
- All supplied excerpts and file locators are caller-attested, not authenticated or read by this exporter.
- Missing fields are unmeasured, never zero, passed or compliant. No aggregate security/compliance score.
- Synthetic fixture values are examples, not observations. A recorded local TLS duration is not network RTT.
- Input files and full module outputs must be retained separately; excerpt hashes do not verify those files.

## Always unmeasured

production_security, attack_resistance, hardware_cycles, network_rtt, fips_module_validation

## Security estimate

Static lookup estimates, not a fresh lattice-estimator run or measured security.

- module: pqc&#95;bench&#46;security&#95;estimation&#46;lattice&#95;runner
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: 54b2d423d2d158e3e51e5ce69bf8fb1b67a3e6928fc90f70b0d99a6aebb05642

| Output excerpt field | Caller-supplied value |
|---|---|
| scheme | ml&#45;kem&#45;768 |
| classical&#95;security&#95;bits | 192 |
| quantum&#95;security&#95;bits | 192 |

## Quantum cost

Placeholder resource model, not an AQRE/Qualtran run or hardware measurement.

- module: pqc&#95;bench&#46;quantum&#95;cost
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: 97f652758680bf7bebf6fcf8f9fdc06a3089e60ca5684199aae1d6bab3ca9dd5

| Output excerpt field | Caller-supplied value |
|---|---|
| scheme | ml&#45;kem&#45;768 |
| logical&#95;qubits | 4215 |
| t&#95;gate&#95;count | 5474000 |
| t&#95;depth | 10948000 |
| physical&#95;qubits | 13459200 |
| runtime&#95;seconds | 14400 |

## CBOM policy labels

Legacy heuristic policy labels, not normative NIST/CNSA compliance or certification.

- module: pqc&#95;bench&#46;cbom&#46;policy
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: d1f707a2a71bd916c5f28dde3c31ae189d8dd7818f19d1ebc6312c972f9c5960

| Output excerpt field | Caller-supplied value |
|---|---|
| cNSA&#95;2&#95;0&#95;status | partial |
| nist&#95;sp&#95;800&#95;208&#95;status | partial |

## Static instruction review

Findings and their absence prove neither leakage nor constant-time behavior.

- module: pqc&#95;bench&#46;constant&#95;time&#46;binary&#95;auditor
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: a7db816304c5da09f62c5fc373a9c18975fb7a50da42301a237ee80672872204

| Output excerpt field | Caller-supplied value |
|---|---|
| status | incomplete |
| finding&#95;count | 1 |
| instruction&#95;count | 3 |
| scan&#95;complete | false |
| findings&#95;truncated | false |

## Offline hybrid test PKI

Caller-recorded local verify_chain outcome; experimental envelope, not production PKI.

- module: pqc&#95;bench&#46;pki&#46;hybrid&#95;certs
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: 268b0d747b1484a135a83c3831f0f5cab5b7f7cc2809c99d87899cb66b38621a

| Output excerpt field | Caller-supplied value |
|---|---|
| chain&#95;verified | true |

## Offline handshake model

Custom local model, not production TLS, peer authentication, confidentiality or network RTT.

- module: pqc&#95;bench&#46;tls&#95;simulator
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: e61b669a137910877baf6bd2de4c68e918566540f9419dc62c9298cd079b9d0d

| Output excerpt field | Caller-supplied value |
|---|---|
| local&#95;duration&#95;ns | 123456 |
| client&#95;application&#95;match | true |
| server&#95;application&#95;match | true |

## FIPS 140-3 document review

Document assertions only; authenticity, current CMVP status and runtime mode not verified.

- module: pqc&#95;bench&#46;fips&#95;evidence
- input_file: tests&#47;fixtures&#47;executive&#95;report&#47;inputs&#46;json
- output_file: tests&#47;fixtures&#47;executive&#95;report&#47;outputs&#46;json
- evidence_kind: synthetic&#95;fixture
- excerpt_sha256: 8f750fe3cb1fa1f3b1c1560adcbb941ecda71db09c5fe9ec28b5a67913882c24

| Output excerpt field | Caller-supplied value |
|---|---|
| overall&#95;status | not&#95;verified |
| gap&#58; approved&#95;mode | missing&#95;evidence |
| gap&#58; approved&#95;mode | missing&#95;target&#95;scope |
| gap&#58; certificate&#95;reference | missing&#95;evidence |
| gap&#58; certificate&#95;standard | missing&#95;evidence |
| gap&#58; certificate&#95;status | missing&#95;evidence |
| gap&#58; environment | missing&#95;evidence |
| gap&#58; environment | missing&#95;target&#95;scope |
| gap&#58; module&#95;id | missing&#95;evidence |
| gap&#58; review | authenticity&#95;not&#95;verified |
| gap&#58; review | current&#95;cmvp&#95;status&#95;not&#95;verified |
| gap&#58; review | runtime&#95;mode&#95;not&#95;verified |
| gap&#58; security&#95;policy&#95;reference | missing&#95;evidence |
| gap&#58; services | missing&#95;evidence |
| gap&#58; services | missing&#95;target&#95;scope |
| gap&#58; version | missing&#95;evidence |
| gap&#58; version | missing&#95;target&#95;scope |
