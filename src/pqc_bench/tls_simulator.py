"""Offline educational TLS 1.3-style model, NOT TLS or an authenticated channel.

Only internally generated ephemeral keys; no network, records, confidentiality
or FIPS certification claim. Reprs omit secrets; no memory erasure guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import os
from time import perf_counter_ns

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey, MLKEM768PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

HASH_SIZE = 32
MAX_CONTEXT_BYTES = 256
MAX_MESSAGE_BYTES = 1510
MAX_TRANSCRIPT_BYTES = 4096
MAX_HKDF_INPUT_BYTES = 4096
_DOMAIN = b"PQC-BENCH-OFFLINE-TLS13-V1\x00"
_ZEROS = bytes(32)


class ProtocolError(ValueError):
    """Invalid message, confirmation failure, or incorrect/terminal state."""


def _bytes(name: str, value: bytes, minimum: int, maximum: int) -> None:
    if type(value) is not bytes or not minimum <= len(value) <= maximum:
        raise ValueError(f"{name} must be bytes of length {minimum}..{maximum}")


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """RFC 5869 Extract(SHA-256), bounded bytes-only inputs."""
    _bytes("salt", salt, 0, MAX_HKDF_INPUT_BYTES)
    _bytes("ikm", ikm, 0, MAX_HKDF_INPUT_BYTES)
    return hmac.digest(salt, ikm, "sha256")


def hkdf_expand_label(secret: bytes, label: bytes, context: bytes, length: int = 32) -> bytes:
    """RFC 8446 HkdfLabel encoding and HKDF-Expand, not a second Extract."""
    _bytes("secret", secret, 32, 32)
    _bytes("label", label, 1, 249)
    _bytes("context", context, 0, 255)
    if type(length) is not int or not 1 <= length <= 8160:
        raise ValueError("length must be an integer in 1..8160")
    full_label = b"tls13 " + label
    info = (length.to_bytes(2, "big") + bytes([len(full_label)]) + full_label
            + bytes([len(context)]) + context)
    return HKDFExpand(algorithm=hashes.SHA256(), length=length, info=info).derive(secret)


def derive_secret(secret: bytes, label: bytes, transcript: bytes) -> bytes:
    """Derive-Secret hashes the transcript, even when the transcript is empty."""
    _bytes("transcript", transcript, 0, MAX_TRANSCRIPT_BYTES)
    return hkdf_expand_label(secret, label, hashlib.sha256(transcript).digest())


def _context(value: bytes) -> None:
    _bytes("context", value, 0, MAX_CONTEXT_BYTES)


def _frame(kind: int, body: bytes) -> bytes:
    return bytes([kind]) + len(body).to_bytes(3, "big") + body


@dataclass(frozen=True)
class ClientHello:
    random: bytes = field(repr=False)
    x25519_public: bytes = field(repr=False)
    mlkem_public: bytes = field(repr=False)
    context: bytes = field(default=b"", repr=False)

    def __post_init__(self) -> None:
        _bytes("random", self.random, 32, 32)
        _bytes("X25519 public", self.x25519_public, 32, 32)
        _bytes("ML-KEM public", self.mlkem_public, 1184, 1184)
        _context(self.context)

    def encode(self) -> bytes:
        self.__post_init__()
        return _frame(1, self.random + self.x25519_public + self.mlkem_public
                      + len(self.context).to_bytes(2, "big") + self.context)


@dataclass(frozen=True)
class ServerHello:
    random: bytes = field(repr=False)
    x25519_public: bytes = field(repr=False)
    mlkem_ciphertext: bytes = field(repr=False)
    context: bytes = field(default=b"", repr=False)

    def __post_init__(self) -> None:
        _bytes("random", self.random, 32, 32)
        _bytes("X25519 public", self.x25519_public, 32, 32)
        _bytes("ML-KEM ciphertext", self.mlkem_ciphertext, 1088, 1088)
        _context(self.context)

    def encode(self) -> bytes:
        self.__post_init__()
        return _frame(2, self.random + self.x25519_public + self.mlkem_ciphertext
                      + len(self.context).to_bytes(2, "big") + self.context)


@dataclass(frozen=True)
class Finished:
    sender: str
    verify_data: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.sender) is not str or self.sender not in ("client", "server"):
            raise ValueError("Finished sender must be client or server")
        _bytes("verify_data", self.verify_data, 32, 32)

    def encode(self) -> bytes:
        self.__post_init__()
        return _frame(20, (b"c" if self.sender == "client" else b"s") + self.verify_data)


def decode_message(wire: bytes) -> ClientHello | ServerHello | Finished:
    """Parse one canonical custom frame; reject trailing or concatenated data."""
    try:
        _bytes("message", wire, 4, MAX_MESSAGE_BYTES)
        kind, body = wire[0], wire[4:]
        if int.from_bytes(wire[1:4], "big") != len(body):
            raise ValueError("message length mismatch")
        if kind == 20:
            if len(body) != 33 or body[:1] not in (b"c", b"s"):
                raise ValueError("invalid Finished")
            return Finished("client" if body[:1] == b"c" else "server", body[1:])
        if kind not in (1, 2):
            raise ValueError("unknown message type")
        end = 64 + (1184 if kind == 1 else 1088)
        if len(body) < end + 2 or int.from_bytes(body[end:end + 2], "big") != len(body) - end - 2:
            raise ValueError("hello context length mismatch")
        cls = ClientHello if kind == 1 else ServerHello
        return cls(body[:32], body[32:64], body[64:end], body[end + 2:])
    except ValueError as exc:
        raise ProtocolError("invalid encoded message") from exc


@dataclass(frozen=True)
class TrafficSecrets:
    """Educational byte inspection only, not deployable channel keys."""
    client_application: bytes = field(repr=False)
    server_application: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _bytes("client application", self.client_application, 32, 32)
        _bytes("server application", self.server_application, 32, 32)


@dataclass(frozen=True)
class _Schedule:
    client_handshake: bytes = field(repr=False)
    server_handshake: bytes = field(repr=False)
    master: bytes = field(repr=False)


def _key_schedule(x25519_shared: bytes, mlkem_shared: bytes, transcript: bytes) -> _Schedule:
    _bytes("X25519 shared", x25519_shared, 32, 32)
    _bytes("ML-KEM shared", mlkem_shared, 32, 32)
    if hmac.compare_digest(x25519_shared, _ZEROS):
        raise ValueError("all-zero X25519 shared value")
    early = hkdf_extract(_ZEROS, _ZEROS)  # No PSK: Hash.length zero bytes.
    handshake = hkdf_extract(derive_secret(early, b"derived", b""),
                             x25519_shared + mlkem_shared)
    return _Schedule(
        derive_secret(handshake, b"c hs traffic", transcript),
        derive_secret(handshake, b"s hs traffic", transcript),
        hkdf_extract(derive_secret(handshake, b"derived", b""), _ZEROS),
    )


def _finished(secret: bytes, transcript: bytes) -> bytes:
    key = hkdf_expand_label(secret, b"finished", b"")
    return hmac.digest(key, hashlib.sha256(transcript).digest(), "sha256")


class _Peer:
    def __init__(self, context: bytes = b"") -> None:
        _context(context)
        self._context = context
        self._state = "new"
        self._transcript = _DOMAIN
        self._schedule: _Schedule | None = None
        self._traffic: TrafficSecrets | None = None
        self._x: X25519PrivateKey | None = X25519PrivateKey.generate()
        self._kem: MLKEM768PrivateKey | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(state={self._state!r})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def transcript_hash(self) -> str:
        return hashlib.sha256(self._transcript).hexdigest()

    @property
    def traffic_secrets(self) -> TrafficSecrets:
        if self._state != "complete" or self._traffic is None:
            raise ProtocolError("application secrets are available only after local completion")
        return self._traffic

    def _fail(self, message: str) -> None:
        self._state = "failed"
        self._schedule = self._traffic = self._x = self._kem = None
        raise ProtocolError(message)

    def _expect(self, state: str) -> None:
        if self._state != state:
            self._fail("out-of-order or replayed operation; peer is now terminal")

    def _read(self, wire: bytes, cls: type, sender: str | None = None):
        try:
            message = decode_message(wire)
        except ValueError:
            self._fail("invalid message; peer is now terminal")
        if type(message) is not cls or (sender is not None and message.sender != sender):
            self._fail("unexpected message type or sender; peer is now terminal")
        return message

    def _append(self, wire: bytes) -> None:
        if len(self._transcript) + len(wire) > MAX_TRANSCRIPT_BYTES:
            self._fail("transcript limit exceeded")
        self._transcript += wire

    def _derive_application(self) -> None:
        self._traffic = TrafficSecrets(
            derive_secret(self._schedule.master, b"c ap traffic", self._transcript),
            derive_secret(self._schedule.master, b"s ap traffic", self._transcript),
        )

    def _complete(self) -> None:
        self._schedule = self._x = self._kem = None
        self._state = "complete"


class ClientPeer(_Peer):
    """Single-use client; private keys are generated internally, never imported."""

    def __init__(self, context: bytes = b"") -> None:
        super().__init__(context)
        self._kem = MLKEM768PrivateKey.generate()

    def client_hello(self) -> bytes:
        self._expect("new")
        wire = ClientHello(os.urandom(32), self._x.public_key().public_bytes_raw(),
                           self._kem.public_key().public_bytes_raw(), self._context).encode()
        self._append(wire)
        self._state = "await_server_hello"
        return wire

    def receive_server_hello(self, wire: bytes) -> None:
        self._expect("await_server_hello")
        hello = self._read(wire, ServerHello)
        try:
            x_shared = self._x.exchange(X25519PublicKey.from_public_bytes(hello.x25519_public))
            kem_shared = self._kem.decapsulate(hello.mlkem_ciphertext)
            self._append(wire)
            self._schedule = _key_schedule(x_shared, kem_shared, self._transcript)
        except ValueError:
            self._fail("invalid hybrid key share; peer is now terminal")
        self._x = self._kem = None
        self._state = "await_server_finished"

    def receive_server_finished(self, wire: bytes) -> None:
        self._expect("await_server_finished")
        message = self._read(wire, Finished, "server")
        expected = _finished(self._schedule.server_handshake, self._transcript)
        if not hmac.compare_digest(message.verify_data, expected):
            self._fail("server Finished mismatch; peer is now terminal")
        self._append(wire)
        self._derive_application()
        self._state = "ready_client_finished"

    def client_finished(self) -> bytes:
        self._expect("ready_client_finished")
        wire = Finished("client", _finished(self._schedule.client_handshake,
                                             self._transcript)).encode()
        self._append(wire)
        self._complete()
        return wire


class ServerPeer(_Peer):
    """Single-use server; independently computes shares and its full schedule."""

    def receive_client_hello(self, wire: bytes) -> bytes:
        """Accept ClientHello and emit ServerHello as one local transition."""
        self._expect("new")
        hello = self._read(wire, ClientHello)
        try:
            x_shared = self._x.exchange(X25519PublicKey.from_public_bytes(hello.x25519_public))
            public = MLKEM768PublicKey.from_public_bytes(hello.mlkem_public)
            # cryptography 50 returns (shared_secret, ciphertext), in that order.
            kem_shared, ciphertext = public.encapsulate()
            reply = ServerHello(os.urandom(32), self._x.public_key().public_bytes_raw(),
                                ciphertext, self._context).encode()
            self._append(wire)
            self._append(reply)
            self._schedule = _key_schedule(x_shared, kem_shared, self._transcript)
        except ValueError:
            self._fail("invalid hybrid key share; peer is now terminal")
        self._x = None
        self._state = "ready_server_finished"
        return reply

    def server_finished(self) -> bytes:
        self._expect("ready_server_finished")
        wire = Finished("server", _finished(self._schedule.server_handshake,
                                             self._transcript)).encode()
        self._append(wire)
        self._derive_application()
        self._state = "await_client_finished"
        return wire

    def receive_client_finished(self, wire: bytes) -> None:
        self._expect("await_client_finished")
        message = self._read(wire, Finished, "client")
        expected = _finished(self._schedule.client_handshake, self._transcript)
        if not hmac.compare_digest(message.verify_data, expected):
            self._fail("client Finished mismatch; peer is now terminal")
        self._append(wire)
        self._complete()


@dataclass(frozen=True)
class SimulationResult:
    """Secret-free local measurement and equality report; not security evidence."""
    local_duration_ns: int
    client_application_match: bool
    server_application_match: bool
    transcript_hash: str

    def to_report(self) -> dict:
        return {
            "profile": "offline-educational-tls13-style-v1",
            "hybrid_components": ["X25519", "ML-KEM-768"],
            "hash": "SHA-256",
            "measurement": "local_simulation_duration_not_network_rtt",
            "local_duration_ns": self.local_duration_ns,
            "client_application_match": self.client_application_match,
            "server_application_match": self.server_application_match,
            "transcript_hash": self.transcript_hash,
            "production_tls": False,
            "peer_authentication": False,
            "confidentiality_claim": False,
            "fips_certification_claim": False,
        }


def simulate_handshake(client_context: bytes = b"", server_context: bytes = b"") -> SimulationResult:
    """Time one local exchange, including key creation and final agreement checks.

    Monotonic perf_counter_ns elapsed time includes Python/scheduling overhead,
    not network RTT or pure CPU time. Initial validation/report creation are not
    timed. Fresh randomness, transcript digests and durations vary each run.
    """
    _context(client_context)
    _context(server_context)
    start = perf_counter_ns()
    client, server = ClientPeer(client_context), ServerPeer(server_context)
    client.receive_server_hello(server.receive_client_hello(client.client_hello()))
    client.receive_server_finished(server.server_finished())
    server.receive_client_finished(client.client_finished())
    c, s = client.traffic_secrets, server.traffic_secrets
    c_match = hmac.compare_digest(c.client_application, s.client_application)
    s_match = hmac.compare_digest(c.server_application, s.server_application)
    transcript_hash = client.transcript_hash
    if not c_match or not s_match or transcript_hash != server.transcript_hash:
        raise ProtocolError("independent peer derivations did not agree")
    duration = perf_counter_ns() - start
    return SimulationResult(duration, c_match, s_match, transcript_hash)
