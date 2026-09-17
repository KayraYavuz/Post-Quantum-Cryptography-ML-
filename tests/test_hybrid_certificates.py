"""Offline CPU profile tests, fresh library-generated keys; no deployed certificates."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import mldsa, rsa
from cryptography.x509.oid import ExtensionOID, NameOID

from pqc_bench.pki import HybridCertificate, HybridValidationError, generate_chain, verify_chain
from pqc_bench.pki.hybrid_certs import DOMAIN, PQ_OID, PQ_PREFIX, _message, _usage

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def chain():
    return generate_chain(not_before=NOW)


def verify(chain, at=NOW, pin=None):
    return verify_chain(chain, trusted_root_der=chain[0].der if pin is None else pin, at=at)


def test_generated_schema_and_repeatable_verification(chain):
    root, leaf = chain
    for _ in range(3):
        assert verify(chain) is None
    for index, item in enumerate(chain):
        cert = item.certificate
        assert cert.public_key().key_size == 4096
        assert len(item.pq_signature) == 3309
        pq = cert.extensions.get_extension_for_oid(PQ_OID)
        assert not pq.critical and pq.value.value.startswith(PQ_PREFIX)
        assert len(pq.value.value) == len(PQ_PREFIX) + 1952
        assert cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca == (index == 0)
        assert x509.load_der_x509_certificate(item.der) == cert
        assert _message(cert) == DOMAIN + len(item.der).to_bytes(4, 'big') + item.der
    assert root.certificate.serial_number != leaf.certificate.serial_number
    assert root.certificate.public_key() != leaf.certificate.public_key()
    assert not hasattr(root, 'private_key')


@pytest.mark.parametrize('offset', [0, 30 * 86400])
def test_validity_boundaries_inclusive(chain, offset):
    verify(chain, at=NOW + timedelta(seconds=offset))


@pytest.mark.parametrize('offset', [-1, 30 * 86400 + 1])
def test_reject_outside_validity(chain, offset):
    with pytest.raises(HybridValidationError):
        verify(chain, at=NOW + timedelta(seconds=offset))


@pytest.mark.parametrize('index', [0, 1])
def test_reject_tampered_pq_signature(chain, index):
    altered = list(chain)
    sig = altered[index].pq_signature
    altered[index] = replace(altered[index], pq_signature=bytes([sig[0] ^ 1]) + sig[1:])
    with pytest.raises(HybridValidationError):
        verify(tuple(altered))


@pytest.mark.parametrize('index', [0, 1])
def test_reject_tampered_classical_signature(chain, index):
    altered = list(chain)
    der = altered[index].der
    cert = x509.load_der_x509_certificate(der[:-1] + bytes([der[-1] ^ 1]))
    altered[index] = replace(altered[index], certificate=cert)
    with pytest.raises(HybridValidationError):
        verify(tuple(altered), pin=chain[0].der)


def test_pq_signature_bound_to_cert(chain):
    with pytest.raises(HybridValidationError):
        verify((chain[0], replace(chain[1], pq_signature=chain[0].pq_signature)))


@pytest.mark.parametrize('pin', [b'', b'not a root', b'x' * 16385, None, 'DER', bytearray(b'a')])
def test_explicit_pin_required(chain, pin):
    with pytest.raises(HybridValidationError):
        verify_chain(chain, trusted_root_der=pin, at=NOW)


def test_pin_cannot_be_omitted(chain):
    with pytest.raises(TypeError):
        verify_chain(chain, at=NOW)


@pytest.mark.parametrize('value', [None, [], (), (None, None), (1,), 'chain'])
def test_bad_chain(value, chain):
    with pytest.raises(HybridValidationError):
        verify_chain(value, trusted_root_der=chain[0].der, at=NOW)


def test_wrong_order_and_extra_chain(chain):
    for wrong in [(chain[1], chain[0]), (chain[0], chain[0]), (*chain, chain[0]), list(chain)]:
        with pytest.raises(HybridValidationError):
            verify_chain(wrong, trusted_root_der=chain[0].der, at=NOW)


@pytest.mark.parametrize('value', [None, 'now', 42, datetime(2026, 1, 1),
                                  NOW.replace(microsecond=1), NOW.replace(year=1949)])
def test_bad_time_input(chain, value):
    with pytest.raises(HybridValidationError):
        generate_chain(not_before=value)
    with pytest.raises(HybridValidationError):
        verify(chain, at=value)


@pytest.mark.parametrize('value', [None, '', ' ', 'x' * 65, 'a\nb', ' a', 'a ',
                                  'ü', 1, True, 'name@host'])
@pytest.mark.parametrize('field', ['root_cn', 'leaf_cn'])
def test_bad_common_names(value, field):
    with pytest.raises(HybridValidationError):
        generate_chain(not_before=NOW, **{field: value})


@pytest.mark.parametrize('value', [True, False, 0, -1, 366, 1.0, '30', None])
def test_bad_lifetime(value):
    with pytest.raises(HybridValidationError):
        generate_chain(not_before=NOW, validity_days=value)


def test_equal_names_rejected():
    with pytest.raises(HybridValidationError):
        generate_chain(root_cn='same', leaf_cn='same', not_before=NOW)


@pytest.mark.parametrize('value', [b'', b'a' * 3308, b'a' * 3310, None, 'a' * 3309])
def test_envelope_signature_validation(chain, value):
    with pytest.raises(HybridValidationError):
        HybridCertificate(chain[0].certificate, value)


def test_envelope_certificate_validation():
    with pytest.raises(HybridValidationError):
        HybridCertificate(b'not a certificate', b'a' * 3309)


@pytest.fixture(scope='module')
def issuer():
    # Independent, locally generated test issuer; used to sign invalid profiles
    # correctly in BOTH layers, ensuring policy rejects rather than just signatures.
    return (rsa.generate_private_key(public_exponent=65537, key_size=4096),
            mldsa.MLDSA65PrivateKey.generate())


def signed_variant(chain, issuer, *, role='leaf', variant=None):
    rsa_key, pq_key = issuer
    root_name = chain[0].certificate.subject
    root_pq = PQ_PREFIX + pq_key.public_key().public_bytes_raw()

    def build(ca):
        old = chain[0 if ca else 1].certificate
        modify = ca == (role == 'root')
        name = old.subject
        issuer_name = root_name
        start, end = NOW, NOW + timedelta(days=30)
        serial = old.serial_number
        pub = rsa_key.public_key() if ca else old.public_key()
        bc = x509.BasicConstraints(ca, 0 if ca else None)
        usage = _usage(ca)
        pq = root_pq if ca else old.extensions.get_extension_for_oid(PQ_OID).value.value
        pq_critical, bc_critical, ku_critical = False, True, True
        algorithm = hashes.SHA256()
        if modify:
            if variant == 'issuer':
                issuer_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Other')])
            elif variant == 'subject':
                name = x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Other')])
            elif variant == 'same_name':
                name = root_name
            elif variant == 'same_serial':
                serial = chain[0].certificate.serial_number
            elif variant == 'same_rsa_key':
                pub = rsa_key.public_key()
            elif variant == 'same_pq_key':
                pq = root_pq
            elif variant == 'weak_rsa':
                pub = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
            elif variant == 'wrong_key_type':
                pub = pq_key.public_key()
            elif variant == 'sha384':
                algorithm = hashes.SHA384()
            elif variant == 'wrong_bc':
                bc = x509.BasicConstraints(not ca, 0 if not ca else None)
            elif variant == 'path_length':
                bc = x509.BasicConstraints(True, 1)
            elif variant == 'bc_noncritical':
                bc_critical = False
            elif variant == 'wrong_usage':
                usage = _usage(not ca)
            elif variant == 'ku_noncritical':
                ku_critical = False
            elif variant == 'pq_critical':
                pq_critical = True
            elif variant == 'pq_wrong_version':
                pq = b'PQC2' + pq[4:]
            elif variant == 'pq_short':
                pq = pq[:-1]
            elif variant == 'pq_wrong_key':
                pq = PQ_PREFIX + mldsa.MLDSA44PrivateKey.generate().public_key().public_bytes_raw()
            elif variant == 'too_long':
                end = NOW + timedelta(days=366)
            elif variant == 'outside_root':
                start = NOW - timedelta(days=1)
        builder = (x509.CertificateBuilder().subject_name(name).issuer_name(issuer_name)
                   .public_key(pub).serial_number(serial).not_valid_before(start).not_valid_after(end)
                   .add_extension(bc, bc_critical).add_extension(usage, ku_critical))
        if not (modify and variant == 'pq_missing'):
            builder = builder.add_extension(x509.UnrecognizedExtension(PQ_OID, pq), pq_critical)
        if modify and variant in ('unknown_critical', 'unknown_noncritical'):
            builder = builder.add_extension(x509.UnrecognizedExtension(
                x509.ObjectIdentifier('1.2.3.4.5'), b'test'), variant == 'unknown_critical')
        cert = builder.sign(rsa_key, algorithm)
        sig = pq_key.sign(_message(cert))
        if modify and variant == 'wrong_pq_signer':
            sig = mldsa.MLDSA65PrivateKey.generate().sign(_message(cert))
        if modify and variant == 'rsa_tamper_pq_valid':
            der = cert.public_bytes(serialization.Encoding.DER)
            cert = x509.load_der_x509_certificate(der[:-1] + bytes([der[-1] ^ 1]))
            sig = pq_key.sign(_message(cert))
        return HybridCertificate(cert, sig)

    return build(True), build(False)


def test_independent_correct_issuer_and_pin(chain, issuer):
    other = signed_variant(chain, issuer)
    verify(other)
    with pytest.raises(HybridValidationError):
        verify(other, pin=chain[0].der)
    with pytest.raises(HybridValidationError):
        verify((other[0], chain[1]))


@pytest.mark.parametrize('role', ['root', 'leaf'])
@pytest.mark.parametrize('variant', [
    'issuer', 'subject', 'weak_rsa', 'wrong_key_type', 'sha384', 'wrong_bc',
    'path_length', 'bc_noncritical', 'wrong_usage', 'ku_noncritical',
    'pq_critical', 'pq_wrong_version', 'pq_short', 'pq_wrong_key', 'pq_missing',
    'too_long', 'unknown_critical', 'unknown_noncritical', 'wrong_pq_signer',
    'rsa_tamper_pq_valid',
])
def test_reject_signed_bad_profile(chain, issuer, role, variant):
    bad = signed_variant(chain, issuer, role=role, variant=variant)
    with pytest.raises(HybridValidationError):
        verify(bad)


@pytest.mark.parametrize('variant', ['same_name', 'same_serial', 'same_rsa_key',
                                     'same_pq_key', 'outside_root'])
def test_reject_leaf_relationship(chain, issuer, variant):
    with pytest.raises(HybridValidationError):
        verify(signed_variant(chain, issuer, variant=variant))


def test_timezone_normalization(chain):
    verify(chain, at=NOW.astimezone(timezone(timedelta(hours=3))))
