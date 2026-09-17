"""Offline educational hybrid handshake with custom, bounded framing.

Uses real ephemeral X25519 and ML-KEM-768 and an RFC 8446-like SHA-256
schedule, but is NOT TLS, authenticated key exchange, or an encryption layer.
No networking, external private keys, security or FIPS certification claims.
Dropping Python references is not a secure-memory zeroization guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import secrets
from time import perf_counter_ns

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import mlkem, x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

_DOMAIN = b"PQC-Bench offline handshake v1\x00"
MAX_MESSAGE_BYTES = 1510
MAX_TRANSCRIPT_BYTES = 4096
_ZERO = bytes(32)


class ProtocolError(ValueError):
    """Malformed, unconfirmed or out-of-order simulation operation."""


def _bytes(value, name, *, size=None, maximum=4096):
    if type(value) is not bytes or len(value) > maximum or (size is not None and len(value) != size):
        raise ValueError(f"invalid {name}")
    return value


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """RFC 5869 HKDF-Extract with SHA-256; bounded byte inputs only."""
    return hmac.digest(_bytes(salt, "salt"), _bytes(ikm, "ikm"), "sha256")


def hkdf_expand_label(secret: bytes, label: bytes, context: bytes, length: int = 32) -> bytes:
    """RFC 8446 HkdfLabel serialization and SHA-256 expansion."""
    _bytes(secret, "secret", size=32)
    _bytes(label, "label", maximum=249)
    _bytes(context, "context", maximum=255)
    if not label or type(length) is not int or not 1 <= length <= 8160:
        raise ValueError("invalid label or length")
    label = b"tls13 " + label
    info = length.to_bytes(2, "big") + bytes([len(label)]) + label + bytes([len(context)]) + context
    return HKDFExpand(algorithm=hashes.SHA256(), length=length, info=info).derive(secret)


def derive_secret(secret: bytes, label: bytes, transcript: bytes) -> bytes:
    return hkdf_expand_label(secret, label, hashlib.sha256(_bytes(transcript, "transcript")).digest())


@dataclass(frozen=True)
class _Schedule:
    client_handshake: bytes = field(repr=False)
    server_handshake: bytes = field(repr=False)
    master: bytes = field(repr=False)


def _key_schedule(x: bytes, kem: bytes, transcript: bytes) -> _Schedule:
    """No-PSK schedule; fixed-width X25519 || ML-KEM combiner."""
    _bytes(x, "X25519 shared secret", size=32)
    _bytes(kem, "ML-KEM shared secret", size=32)
    _bytes(transcript, "transcript")
    if x == _ZERO:
        raise ValueError("null X25519 shared secret")
    early = hkdf_extract(_ZERO, _ZERO)
    handshake = hkdf_extract(derive_secret(early, b"derived", b""), x + kem)
    return _Schedule(derive_secret(handshake, b"c hs traffic", transcript),
                     derive_secret(handshake, b"s hs traffic", transcript),
                     hkdf_extract(derive_secret(handshake, b"derived", b""), _ZERO))


def _frame(kind, body):
    return bytes([kind]) + len(body).to_bytes(3, "big") + body


@dataclass(frozen=True)
class ClientHello:
    random: bytes
    x25519_public: bytes
    mlkem_public: bytes
    context: bytes = b""

    def __post_init__(self):
        _bytes(self.random, "random", size=32)
        _bytes(self.x25519_public, "X25519 public", size=32)
        _bytes(self.mlkem_public, "ML-KEM public", size=1184)
        _bytes(self.context, "context", maximum=256)

    def encode(self):
        return _frame(1, self.random + self.x25519_public + self.mlkem_public
                      + len(self.context).to_bytes(2, "big") + self.context)


@dataclass(frozen=True)
class ServerHello:
    random: bytes
    x25519_public: bytes
    mlkem_ciphertext: bytes
    context: bytes = b""

    def __post_init__(self):
        _bytes(self.random, "random", size=32)
        _bytes(self.x25519_public, "X25519 public", size=32)
        _bytes(self.mlkem_ciphertext, "ML-KEM ciphertext", size=1088)
        _bytes(self.context, "context", maximum=256)

    def encode(self):
        return _frame(2, self.random + self.x25519_public + self.mlkem_ciphertext
                      + len(self.context).to_bytes(2, "big") + self.context)


@dataclass(frozen=True)
class Finished:
    sender: str
    verify_data: bytes = field(repr=False)

    def __post_init__(self):
        if type(self.sender) is not str or self.sender not in ("client", "server"):
            raise ValueError("invalid sender")
        _bytes(self.verify_data, "verify data", size=32)

    def encode(self):
        return _frame(20, (b"c" if self.sender == "client" else b"s") + self.verify_data)


def decode_message(wire: bytes):
    """Decode exactly one custom frame; reject unknown types and trailing data."""
    try:
        _bytes(wire, "message", maximum=MAX_MESSAGE_BYTES)
        if len(wire) < 4 or int.from_bytes(wire[1:4], "big") != len(wire) - 4:
            raise ValueError("invalid frame length")
        body = wire[4:]
        if wire[0] in (1, 2):
            size = 1184 if wire[0] == 1 else 1088
            pos = 64 + size
            if len(body) < pos + 2 or int.from_bytes(body[pos:pos+2], "big") != len(body) - pos - 2:
                raise ValueError("invalid context length")
            cls = ClientHello if wire[0] == 1 else ServerHello
            return cls(body[:32], body[32:64], body[64:pos], body[pos+2:])
        if wire[0] == 20 and len(body) == 33 and body[:1] in (b"c", b"s"):
            return Finished("client" if body[:1] == b"c" else "server", body[1:])
        raise ValueError("unknown message")
    except ValueError as exc:
        raise ProtocolError(str(exc)) from exc


@dataclass(frozen=True)
class TrafficSecrets:
    """Ephemeral test values only; repr redacted, no zeroization guarantee."""
    client_application: bytes = field(repr=False)
    server_application: bytes = field(repr=False)

    def __post_init__(self):
        _bytes(self.client_application, "client application", size=32)
        _bytes(self.server_application, "server application", size=32)


class _Peer:
    def __init__(self, context=b""):
        self._context = _bytes(context, "context", maximum=256)
        self.state = "new"
        self._transcript = _DOMAIN
        self._schedule = self._traffic = None
        self._x = self._kem = None

    def __repr__(self):
        return f"{type(self).__name__}(state={self.state!r})"

    def _fail(self, message):
        self.state = "failed"
        self._schedule = self._traffic = self._x = self._kem = None
        raise ProtocolError(message)

    def _expect(self, state):
        if self.state != state:
            self._fail("out-of-order operation")

    def _message(self, wire, cls, sender=None):
        try:
            msg = decode_message(wire)
        except ValueError:
            self._fail("malformed message")
        if type(msg) is not cls or (sender is not None and msg.sender != sender):
            self._fail("unexpected message type or sender")
        return msg

    def _append(self, wire):
        if len(self._transcript) + len(wire) > MAX_TRANSCRIPT_BYTES:
            self._fail("transcript too large")
        self._transcript += wire

    def _finished(self, sender):
        secret = (self._schedule.client_handshake if sender == "client"
                  else self._schedule.server_handshake)
        key = hkdf_expand_label(secret, b"finished", b"")
        return Finished(sender, hmac.digest(key, hashlib.sha256(self._transcript).digest(), "sha256"))

    def _verify(self, wire, sender):
        msg = self._message(wire, Finished, sender)
        if not hmac.compare_digest(msg.verify_data, self._finished(sender).verify_data):
            self._fail("Finished mismatch")
        self._append(wire)

    def _applications(self):
        # Called only with transcript through server Finished, not client Finished.
        self._traffic = TrafficSecrets(
            derive_secret(self._schedule.master, b"c ap traffic", self._transcript),
            derive_secret(self._schedule.master, b"s ap traffic", self._transcript))

    @property
    def traffic_secrets(self):
        if self.state != "complete":
            raise ProtocolError("handshake not complete")
        return self._traffic

    @property
    def transcript_hash(self):
        return hashlib.sha256(self._transcript).hexdigest()


class ClientPeer(_Peer):
    """Independent client owning only locally generated ephemeral private keys."""

    def client_hello(self):
        self._expect("new")
        self._x = x25519.X25519PrivateKey.generate()
        self._kem = mlkem.MLKEM768PrivateKey.generate()
        wire = ClientHello(secrets.token_bytes(32), self._x.public_key().public_bytes_raw(),
                           self._kem.public_key().public_bytes_raw(), self._context).encode()
        self._append(wire)
        self.state = "await_server_hello"
        return wire

    def receive_server_hello(self, wire):
        self._expect("await_server_hello")
        msg = self._message(wire, ServerHello)
        try:
            x = self._x.exchange(x25519.X25519PublicKey.from_public_bytes(msg.x25519_public))
            kem = self._kem.decapsulate(msg.mlkem_ciphertext)
            self._append(wire)
            self._schedule = _key_schedule(x, kem, self._transcript)
        except ValueError:
            self._fail("invalid hybrid key share")
        self._x = self._kem = None
        self.state = "await_server_finished"

    def receive_server_finished(self, wire):
        self._expect("await_server_finished")
        self._verify(wire, "server")
        self._applications()
        self.state = "ready_client_finished"

    def client_finished(self):
        self._expect("ready_client_finished")
        wire = self._finished("client").encode()
        self._append(wire)
        self._schedule = None
        self.state = "complete"
        return wire


class ServerPeer(_Peer):
    """Independent server; received public shares are never private-key inputs."""

    def receive_client_hello(self, wire):
        self._expect("new")
        msg = self._message(wire, ClientHello)
        try:
            self._x = x25519.X25519PrivateKey.generate()
            x = self._x.exchange(x25519.X25519PublicKey.from_public_bytes(msg.x25519_public))
            # cryptography 50: encapsulate returns (shared_secret, ciphertext).
            kem, ciphertext = mlkem.MLKEM768PublicKey.from_public_bytes(msg.mlkem_public).encapsulate()
            reply = ServerHello(secrets.token_bytes(32), self._x.public_key().public_bytes_raw(),
                                ciphertext, self._context).encode()
            self._append(wire)
            self._append(reply)
            self._schedule = _key_schedule(x, kem, self._transcript)
        except ValueError:
            self._fail("invalid hybrid key share")
        self._x = None
        self.state = "ready_server_finished"
        return reply

    def server_finished(self):
        self._expect("ready_server_finished")
        wire = self._finished("server").encode()
        self._append(wire)
        self._applications()
        self.state = "await_client_finished"
        return wire

    def receive_client_finished(self, wire):
        self._expect("await_client_finished")
        self._verify(wire, "client")
        self._schedule = None
        self.state = "complete"


@dataclass(frozen=True)
class SimulationResult:
    local_duration_ns: int
    transcript_hash: str
    client_application_match: bool
    server_application_match: bool

    def to_report(self):
        return {"local_duration_ns": self.local_duration_ns, "transcript_hash": self.transcript_hash,
                "client_application_match": self.client_application_match,
                "server_application_match": self.server_application_match,
                "measurement": "local_simulation_duration_not_network_rtt",
                "production_tls": False, "peer_authentication": False,
                "confidentiality_claim": False, "fips_certification_claim": False}


def simulate_handshake(client_context=b"", server_context=b"") -> SimulationResult:
    """Generate fresh ephemeral peers; return only equality and local timing metadata."""
    _bytes(client_context, "client context", maximum=256)
    _bytes(server_context, "server context", maximum=256)
    start = perf_counter_ns()
    client, server = ClientPeer(client_context), ServerPeer(server_context)
    client.receive_server_hello(server.receive_client_hello(client.client_hello()))
    client.receive_server_finished(server.server_finished())
    server.receive_client_finished(client.client_finished())
    c, s = client.traffic_secrets, server.traffic_secrets
    cm = hmac.compare_digest(c.client_application, s.client_application)
    sm = hmac.compare_digest(c.server_application, s.server_application)
    elapsed = perf_counter_ns() - start
    if not cm or not sm or client.transcript_hash != server.transcript_hash:
        raise ProtocolError("peer agreement failed")
    return SimulationResult(elapsed, client.transcript_hash, cm, sm)
