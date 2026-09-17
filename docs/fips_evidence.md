# WS-P7.3 — Local FIPS 140-3 evidence and gap matrix

## Purpose and authority

This component organizes **caller-supplied local document assertions**, not
cryptographic module certification. It does not contact CMVP, inspect deployed
modules, authenticate documents, test a module against FIPS 140-3, submit a
validation application, or establish that a product is compliant.

Official references reviewed on 2026-09-17:

1. [FIPS 140-3 — Security Requirements for Cryptographic Modules](https://csrc.nist.gov/pubs/fips/140-3/final)
   defines the module standard, distinct from algorithm specifications.
2. [CMVP — Validated Modules](https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules)
   explains certificate details, security policies, exact version/part/release
   and operational environments. Algorithm validation alone is insufficient.
   Revoked validations cannot demonstrate conformance; historical validations
   require separate consideration and should not be included in new federal
   systems. An application embedding a module is not automatically validated.
3. [CMVP FAQs](https://csrc.nist.gov/projects/cryptographic-module-validation-program/faqs)
   explain independent laboratory testing and CMVP validation, security-policy
   review, module-versus-product claims, and approved-use limitations.

The references are rule provenance, **not evidence that this repository or any
listed module has a certificate**. The engine never imports existing CBOM
policy labels as certificate evidence. Neither ML-KEM / ML-DSA algorithm names,
FIPS 203 / 204 implementation, nor use of the `cryptography` package establishes
FIPS 140-3 module validation.

## Review semantics

Keep the intended module identity, version, operational environment, mode and
services separate from what each document asserts. Keep certificate references,
standard, status, security-policy references and document locations explicit.
Absent evidence, contradictory assertions, scope mismatches and adverse
certificate statuses are review gaps, not automatic certification decisions.
Even a complete, internally consistent synthetic bundle remains `not_verified`:
its authenticity, current CMVP status and actual runtime mode are unverified.

Matching is deliberately conservative and exact: the component does not decide
whether another environment is equivalent, whether a port preserves validation,
whether a bound module is still acceptable, or whether certificate caveats have
been satisfied. Refer these questions to the module security policy, current
CMVP guidance and qualified reviewers. This bounded matrix is not an exhaustive
mapping of all FIPS 140-3 security requirement areas or a substitute for a lab.

## Dependencies and scope

The repository already provides Pydantic for structured validation and Python
for deterministic JSON/Markdown serialization; no new dependency is required.
The existing CBOM evaluator was inspected and is unsuitable as module evidence
because it derives policy labels from algorithm names. This step adds the
explicitly requested, isolated document-review contract instead of extending
those labels into certification claims.

Tests use only invented local document assertions. They do not retrieve real
certificates or assert that any fixture is a validated module. The implementation
has no service endpoint, transport, credential handling or laboratory integration.

## API and unknown scope

`build_matrix(request)` returns a plain report; `matrix_json(request)` and
`matrix_markdown(request)` serialize it deterministically. `load_request(text)`
validates bounded JSON without opening files or fetching document locators.
The implementation uses only Python's standard library; Pydantic is not required
by this component.

An omitted/null field or scalar literal `unknown` is unavailable evidence.
Unknown target scope generates `missing_target_scope`, not a comparison against
the literal string. Every evidence-bearing document must identify its own module,
version, environment and certificate reference; a null or `unknown` binding field
generates `unbound_document_scope`. Fragments are never silently joined into a
verified module. `services` is a set-valued scope, compared by subset; differing
document service sets conservatively flag a conflict even if both cover the target.

```python
from pqc_bench.fips_evidence import build_matrix, matrix_json

request = {"target": {"module_id": "SYNTHETIC MODULE"}, "documents": []}
assert build_matrix(request)["overall_status"] == "not_verified"
print(matrix_json(request))
```

The input has exactly `target` and `documents`. Target fields are `module_id`
(required), `version`, `environment`, `approved_mode`, and `services`. Each
document requires unique `document_id` and `locator`, and may provide the target
fields plus `certificate_reference`, `certificate_standard`, `certificate_status`
and `security_policy_reference`. Unknown keys are rejected. Strings are trimmed,
printable, 1–512 characters; at most 64 documents and 32 distinct services are
accepted. JSON text is limited to 262144 characters; duplicate keys and nonfinite
constants are rejected. Certificate standard assertions accept `FIPS 140-3`,
`FIPS 140-2`, `unknown`; status assertions accept `active`, `historical`, `revoked`,
`unknown`. All certificate values remain unauthenticated caller assertions.

Run `python3 -m pytest -q tests/test_fips_evidence.py` for the offline contract tests.
