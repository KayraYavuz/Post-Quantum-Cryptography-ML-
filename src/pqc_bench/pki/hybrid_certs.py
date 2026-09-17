"""Local experimental dual-signature envelope, NOT a composite X.509 standard."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import mldsa, padding, rsa
from cryptography.x509.oid import ExtensionOID, NameOID, SignatureAlgorithmOID

PQ_OID = x509.ObjectIdentifier('2.25.' + str(UUID('db7a4f5e-9c1d-4e8a-b2f3-0a1b2c3d4e5f').int))
DOMAIN = b'pqc-bench/hybrid-cert/v1\x00'
PQ_PREFIX = b'PQC1\x00ML-DSA-65\x00'
MAX_DAYS = 365


class HybridValidationError(ValueError):
    """Invalid input, untrusted chain, or invalid signature/profile."""


@dataclass(frozen=True)
class HybridCertificate:
    certificate: x509.Certificate
    pq_signature: bytes

    def __post_init__(self):
        if not isinstance(self.certificate, x509.Certificate):
            raise HybridValidationError('certificate must be an X.509 certificate')
        if type(self.pq_signature) is not bytes or len(self.pq_signature) != 3309:
            raise HybridValidationError('ML-DSA-65 signature must be 3309 bytes')

    @property
    def der(self):
        return self.certificate.public_bytes(serialization.Encoding.DER)


def _time(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise HybridValidationError('time must be timezone-aware datetime')
    value = value.astimezone(timezone.utc)
    if value.microsecond or not 1950 <= value.year <= 9998:
        raise HybridValidationError('time must have whole seconds and year 1950..9998')
    return value


def _name(value):
    if (type(value) is not str or not 1 <= len(value) <= 64
            or not value.isascii() or value.strip() != value
            or any(not (c.isalnum() or c in ' ._-') for c in value)):
        raise HybridValidationError('CN must be 1..64 ASCII letters/digits, space, dot, _ or -')
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, value)])


def _message(cert):
    der = cert.public_bytes(serialization.Encoding.DER)
    return DOMAIN + len(der).to_bytes(4, 'big') + der


def _usage(ca):
    return x509.KeyUsage(True, False, False, False, False, ca, ca, False, False)


def generate_chain(*, root_cn='PQC Bench Test Root', leaf_cn='PQC Bench Test Leaf',
                   not_before, validity_days=30):
    """Return (root, leaf); only public certificates survive, private test keys discarded.

    No network, storage, imported keys, hostname claims, or trust-store changes.
    The caller must provision the root DER separately to a verifier.
    """
    root_name, leaf_name = _name(root_cn), _name(leaf_cn)
    if root_name == leaf_name:
        raise HybridValidationError('root and leaf names must differ')
    start = _time(not_before)
    if type(validity_days) is not int or not 1 <= validity_days <= MAX_DAYS:
        raise HybridValidationError('validity_days must be integer 1..365')
    try:
        end = start + timedelta(days=validity_days)
    except OverflowError as exc:
        raise HybridValidationError('validity overflow') from exc
    _time(end)
    rsa_keys = [rsa.generate_private_key(public_exponent=65537, key_size=4096) for _ in range(2)]
    pq_keys = [mldsa.MLDSA65PrivateKey.generate() for _ in range(2)]
    serials = [x509.random_serial_number(), x509.random_serial_number()]
    while serials[0] == serials[1]:
        serials[1] = x509.random_serial_number()
    result = []
    for i, name in enumerate((root_name, leaf_name)):
        ca = i == 0
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(root_name)
                .public_key(rsa_keys[i].public_key()).serial_number(serials[i])
                .not_valid_before(start).not_valid_after(end)
                .add_extension(x509.BasicConstraints(ca, 0 if ca else None), critical=True)
                .add_extension(_usage(ca), critical=True)
                .add_extension(x509.UnrecognizedExtension(
                    PQ_OID, PQ_PREFIX + pq_keys[i].public_key().public_bytes_raw()), critical=False)
                .sign(rsa_keys[0], hashes.SHA256()))
        result.append(HybridCertificate(cert, pq_keys[0].sign(_message(cert))))
    return tuple(result)


def _profile(cert, ca, at):
    if cert.version != x509.Version.v3:
        raise HybridValidationError('only X.509 v3 accepted')
    key = cert.public_key()
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 4096:
        raise HybridValidationError('RSA-4096 public key required')
    if key.public_numbers().e != 65537:
        raise HybridValidationError('RSA exponent must be 65537')
    if cert.signature_algorithm_oid != SignatureAlgorithmOID.RSA_WITH_SHA256:
        raise HybridValidationError('RSA PKCS1v15 SHA256 required')
    if len(cert.subject) != 1 or len(cert.subject.rdns) != 1:
        raise HybridValidationError('subject must contain only a CN')
    attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if len(attrs) != 1 or cert.subject != _name(attrs[0].value):
        raise HybridValidationError('invalid subject CN')
    start, end = cert.not_valid_before_utc, cert.not_valid_after_utc
    if not start <= at <= end:
        raise HybridValidationError('certificate expired or not yet valid')
    if not timedelta(0) < end - start <= timedelta(days=MAX_DAYS):
        raise HybridValidationError('invalid validity interval')
    if not 0 < cert.serial_number < 2**159:
        raise HybridValidationError('invalid serial')
    expected = {ExtensionOID.BASIC_CONSTRAINTS, ExtensionOID.KEY_USAGE, PQ_OID}
    if {ext.oid for ext in cert.extensions} != expected or len(cert.extensions) != 3:
        raise HybridValidationError('exact three-extension profile required')
    bc = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
    ku = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
    pq = cert.extensions.get_extension_for_oid(PQ_OID)
    if not bc.critical or bc.value != x509.BasicConstraints(ca, 0 if ca else None):
        raise HybridValidationError('invalid basic constraints')
    if not ku.critical or ku.value != _usage(ca):
        raise HybridValidationError('invalid key usage')
    if pq.critical or not isinstance(pq.value, x509.UnrecognizedExtension):
        raise HybridValidationError('invalid PQ extension')
    payload = pq.value.value
    if len(payload) != len(PQ_PREFIX) + 1952 or not payload.startswith(PQ_PREFIX):
        raise HybridValidationError('invalid PQ key schema')
    return mldsa.MLDSA65PublicKey.from_public_bytes(payload[len(PQ_PREFIX):])


def verify_chain(chain, *, trusted_root_der, at):
    """Validate this exact two-certificate profile at explicit time; return None.

    Pin is explicit and mandatory. This is NOT general RFC 5280 path building,
    identity/hostname verification, revocation checking, or TLS authentication.
    """
    at = _time(at)
    if type(chain) is not tuple or len(chain) != 2:
        raise HybridValidationError('chain must be a (root, leaf) tuple')
    if any(type(item) is not HybridCertificate for item in chain):
        raise HybridValidationError('invalid envelope type')
    if type(trusted_root_der) is not bytes or not 1 <= len(trusted_root_der) <= 16384:
        raise HybridValidationError('explicit bounded root DER pin required')
    root, leaf = chain
    if root.der != trusted_root_der:
        raise HybridValidationError('untrusted root')
    try:
        root_pq = _profile(root.certificate, True, at)
        _profile(leaf.certificate, False, at)
        rc, lc = root.certificate, leaf.certificate
        if rc.issuer != rc.subject or lc.issuer != rc.subject or lc.subject == rc.subject:
            raise HybridValidationError('invalid issuer/subject relationship')
        if rc.serial_number == lc.serial_number or rc.public_key() == lc.public_key():
            raise HybridValidationError('root and leaf must have distinct serials and keys')
        rp = rc.extensions.get_extension_for_oid(PQ_OID).value.value
        lp = lc.extensions.get_extension_for_oid(PQ_OID).value.value
        if rp == lp:
            raise HybridValidationError('root and leaf must have distinct PQ keys')
        if not (rc.not_valid_before_utc <= lc.not_valid_before_utc
                and lc.not_valid_after_utc <= rc.not_valid_after_utc):
            raise HybridValidationError('leaf validity outside root validity')
        for item in chain:
            item.__post_init__()
            cert = item.certificate
            rc.public_key().verify(cert.signature, cert.tbs_certificate_bytes,
                                   padding.PKCS1v15(), hashes.SHA256())
            root_pq.verify(item.pq_signature, _message(cert))
    except HybridValidationError:
        raise
    except (InvalidSignature, ValueError, TypeError, UnsupportedAlgorithm,
            x509.DuplicateExtension, x509.ExtensionNotFound) as exc:
        raise HybridValidationError('invalid hybrid certificate chain') from exc
