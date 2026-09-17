"""CPU-only protocol contracts; no sockets, external keys, services or TLS stack."""
from dataclasses import replace
import hashlib
import hmac
import json

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

from pqc_bench import tls_simulator as tls


def hello_pair(client_context=b"", server_context=b""):
    client, server = tls.ClientPeer(client_context), tls.ServerPeer(server_context)
    ch = client.client_hello()
    sh = server.receive_client_hello(ch)
    client.receive_server_hello(sh)
    return client, server, ch, sh


def completed_pair():
    client, server, ch, sh = hello_pair()
    sf = server.server_finished()
    client.receive_server_finished(sf)
    cf = client.client_finished()
    server.receive_client_finished(cf)
    return client, server, (ch, sh, sf, cf)


def reference_expand(secret, label, context, length=32):
    label = b"tls13 " + label
    info = length.to_bytes(2, "big") + bytes([len(label)]) + label + bytes([len(context)]) + context
    result, previous = b"", b""
    for index in range(1, (length + 31) // 32 + 1):
        previous = hmac.digest(secret, previous + info + bytes([index]), "sha256")
        result += previous
    return result[:length]


def reference_derive(secret, label, transcript):
    return reference_expand(secret, label, hashlib.sha256(transcript).digest())


def test_hkdf_rfc5869_case_one_extract_and_expand():
    # RFC 5869 Appendix A.1 (published non-secret test data).
    ikm = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    prk = tls.hkdf_extract(salt, ikm)
    assert prk.hex() == "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
    assert HKDFExpand(algorithm=hashes.SHA256(), length=42, info=info).derive(prk).hex() == (
        "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
        "34007208d5b887185865")


@pytest.mark.parametrize("label,context,length", [
    (b"derived", b"", 32), (b"finished", b"ctx", 42),
    (b"c ap traffic", bytes(32), 64), (b"x" * 249, b"y" * 255, 8160),
])
def test_expand_label_against_independent_hmac_reference(label, context, length):
    secret = bytes(range(32))
    assert tls.hkdf_expand_label(secret, label, context, length) == reference_expand(
        secret, label, context, length)
    assert tls.derive_secret(secret, label, b"transcript") == reference_derive(
        secret, label, b"transcript")


def test_schedule_against_independent_reference_and_both_components():
    x, kem, transcript = b"x" * 32, b"k" * 32, b"model transcript"
    early = hmac.digest(bytes(32), bytes(32), "sha256")
    derived = reference_derive(early, b"derived", b"")
    hs = hmac.digest(derived, x + kem, "sha256")
    actual = tls._key_schedule(x, kem, transcript)
    assert actual.client_handshake == reference_derive(hs, b"c hs traffic", transcript)
    assert actual.server_handshake == reference_derive(hs, b"s hs traffic", transcript)
    assert actual.master == hmac.digest(reference_derive(hs, b"derived", b""), bytes(32), "sha256")
    assert actual != tls._key_schedule(b"z" * 32, kem, transcript)
    assert actual != tls._key_schedule(x, b"z" * 32, transcript)
    assert actual != tls._key_schedule(kem, x, transcript)
    changed = tls._key_schedule(x, kem, transcript + b"!")
    assert changed.client_handshake != actual.client_handshake
    # TLS master is not transcript-bound until the traffic-secret expansion.
    assert changed.master == actual.master
    assert tls.derive_secret(actual.master, b"c ap traffic", transcript) != tls.derive_secret(
        actual.master, b"c ap traffic", transcript + b"!")


def test_independent_peers_exact_secrets_transcript_and_schedule_boundaries():
    client, server, ch, sh = hello_pair(b"client context", b"server context")
    assert client._schedule is not server._schedule
    assert client._schedule == server._schedule
    assert client._x is client._kem is server._x is None
    schedule = client._schedule
    sf = server.server_finished()
    client.receive_server_finished(sf)
    for peer in (client, server):
        with pytest.raises(tls.ProtocolError):
            _ = peer.traffic_secrets
    transcript_through_sf = tls._DOMAIN + ch + sh + sf
    cf = client.client_finished()
    server.receive_client_finished(cf)
    c, s = client.traffic_secrets, server.traffic_secrets
    assert c is not s and c == s
    assert c.client_application != c.server_application
    assert c.client_application == reference_derive(schedule.master, b"c ap traffic", transcript_through_sf)
    assert c.server_application == reference_derive(schedule.master, b"s ap traffic", transcript_through_sf)
    # Client Finished includes server Finished in its confirmation transcript.
    finished_key = reference_expand(schedule.client_handshake, b"finished", b"")
    assert tls.decode_message(cf).verify_data == hmac.digest(
        finished_key, hashlib.sha256(transcript_through_sf).digest(), "sha256")
    assert client.transcript_hash == server.transcript_hash == hashlib.sha256(
        transcript_through_sf + cf).hexdigest()
    assert client._schedule is server._schedule is None


@pytest.mark.parametrize("which,field", [
    ("client", "context"), ("client", "random"),
    ("server", "context"), ("server", "random"),
    ("server", "mlkem_ciphertext"),
])
def test_tampered_hello_transcript_or_kem_rejected_by_finished(which, field):
    client, server = tls.ClientPeer(), tls.ServerPeer()
    ch = client.client_hello()

    def alter(wire):
        message = tls.decode_message(wire)
        value = getattr(message, field)
        changed = b"changed" if field == "context" else bytes([value[0] ^ 1]) + value[1:]
        return replace(message, **{field: changed}).encode()

    sh = server.receive_client_hello(alter(ch) if which == "client" else ch)
    client.receive_server_hello(alter(sh) if which == "server" else sh)
    with pytest.raises(tls.ProtocolError, match="Finished mismatch"):
        client.receive_server_finished(server.server_finished())
    assert client.state == "failed" and client._schedule is None
    with pytest.raises(tls.ProtocolError):
        _ = client.traffic_secrets


@pytest.mark.parametrize("side", ["client", "server"])
def test_low_order_x25519_public_rejected(side):
    client, server = tls.ClientPeer(), tls.ServerPeer()
    ch = client.client_hello()
    if side == "server":
        wire = replace(tls.decode_message(ch), x25519_public=bytes(32)).encode()
        peer, receive = server, server.receive_client_hello
    else:
        sh = server.receive_client_hello(ch)
        wire = replace(tls.decode_message(sh), x25519_public=bytes(32)).encode()
        peer, receive = client, client.receive_server_hello
    with pytest.raises(tls.ProtocolError):
        receive(wire)
    assert peer.state == "failed"


def test_noncanonical_mlkem_public_rejected():
    client, server = tls.ClientPeer(), tls.ServerPeer()
    wire = replace(tls.decode_message(client.client_hello()), mlkem_public=b"\xff" * 1184).encode()
    with pytest.raises(tls.ProtocolError):
        server.receive_client_hello(wire)
    assert server.state == "failed"


@pytest.mark.parametrize("sender", ["client", "server"])
def test_corrupted_finished_rejected_and_secret_access_disabled(sender):
    client, server, _, _ = hello_pair()
    sf = server.server_finished()
    if sender == "server":
        peer, receive, wire = client, client.receive_server_finished, sf
    else:
        client.receive_server_finished(sf)
        peer, receive, wire = server, server.receive_client_finished, client.client_finished()
    bad = replace(tls.decode_message(wire), verify_data=bytes(32)).encode()
    with pytest.raises(tls.ProtocolError):
        receive(bad)
    assert peer.state == "failed" and peer._traffic is None
    with pytest.raises(tls.ProtocolError):
        _ = peer.traffic_secrets


@pytest.mark.parametrize("operation", [
    lambda c, s: c.client_finished(),
    lambda c, s: c.receive_server_hello(b""),
    lambda c, s: c.receive_server_finished(b""),
    lambda c, s: s.server_finished(),
    lambda c, s: s.receive_client_finished(b""),
])
def test_out_of_order_new_peer_operations(operation):
    with pytest.raises(tls.ProtocolError, match="out-of-order"):
        operation(tls.ClientPeer(), tls.ServerPeer())


@pytest.mark.parametrize("operation", [
    lambda c, s, m: c.client_hello(),
    lambda c, s, m: c.receive_server_hello(m[1]),
    lambda c, s, m: c.receive_server_finished(m[2]),
    lambda c, s, m: c.client_finished(),
    lambda c, s, m: s.receive_client_hello(m[0]),
    lambda c, s, m: s.server_finished(),
    lambda c, s, m: s.receive_client_finished(m[3]),
])
def test_completed_peer_replay_rejected(operation):
    c, s, messages = completed_pair()
    with pytest.raises(tls.ProtocolError, match="out-of-order"):
        operation(c, s, messages)


def test_mid_handshake_replays_and_wrong_message_type_are_terminal():
    client, server, ch, sh = hello_pair()
    with pytest.raises(tls.ProtocolError):
        server.receive_client_hello(ch)
    with pytest.raises(tls.ProtocolError):
        client.receive_server_hello(sh)
    for peer in (client, server):
        assert peer.state == "failed"
    client, server, ch, _ = hello_pair()
    with pytest.raises(tls.ProtocolError):
        client.receive_server_finished(ch)
    assert client.state == "failed"


def test_wrong_finished_sender_and_cross_session_finished_rejected():
    client, server, _, _ = hello_pair()
    sf = server.server_finished()
    with pytest.raises(tls.ProtocolError):
        client.receive_server_finished(replace(tls.decode_message(sf), sender="client").encode())
    c2, s2, _, _ = hello_pair()
    with pytest.raises(tls.ProtocolError):
        c2.receive_server_finished(sf)
    assert s2.state == "ready_server_finished"


@pytest.mark.parametrize("wire", [None, "", bytearray(4), b"", b"\x01\x00\x00", b"x" * 1511,
    b"\x01\x00\x00\x01", b"\xff\x00\x00\x00", b"\x14\x00\x00\x21x" + bytes(32),
    b"\x14\x00\x00\x20" + bytes(32), b"\x01\x00\x00\x00"])
def test_malformed_wire_rejected(wire):
    with pytest.raises(tls.ProtocolError):
        tls.decode_message(wire)
    server = tls.ServerPeer()
    with pytest.raises(tls.ProtocolError):
        server.receive_client_hello(wire)
    assert server.state == "failed"


def test_canonical_serialization_limits_trailing_bytes_and_context_length():
    c, s, ch, sh = hello_pair(b"c" * 256, b"s" * 256)
    sf = s.server_finished()
    c.receive_server_finished(sf)
    cf = c.client_finished()
    s.receive_client_finished(cf)
    assert len(ch) == tls.MAX_MESSAGE_BYTES == 1510
    assert len(sh) == 1414
    assert len(c._transcript) <= tls.MAX_TRANSCRIPT_BYTES
    for wire in (ch, sh, sf, cf):
        assert tls.decode_message(wire).encode() == wire
        for invalid in (wire[:-1], wire + b"x", wire[:1] + bytes(3) + wire[4:]):
            with pytest.raises(tls.ProtocolError):
                tls.decode_message(invalid)
    bad_body = ch[4:-258] + b"\x00\x00" + ch[-256:]  # declared context length now zero
    with pytest.raises(tls.ProtocolError):
        tls.decode_message(b"\x01" + len(bad_body).to_bytes(3, "big") + bad_body)


@pytest.mark.parametrize("context", [None, "text", bytearray(b"x"), memoryview(b"x"), b"x" * 257, 1, True])
def test_context_validation(context):
    for constructor in (tls.ClientPeer, tls.ServerPeer, tls.simulate_handshake):
        with pytest.raises(ValueError):
            constructor(context)


@pytest.mark.parametrize("call", [
    lambda: tls.hkdf_extract(None, b"x"),
    lambda: tls.hkdf_extract(b"x" * 4097, b"x"),
    lambda: tls.hkdf_extract(b"", b"x" * 4097),
    lambda: tls.hkdf_expand_label(bytes(31), b"label", b""),
    lambda: tls.hkdf_expand_label(bytes(32), b"", b""),
    lambda: tls.hkdf_expand_label(bytes(32), b"x" * 250, b""),
    lambda: tls.hkdf_expand_label(bytes(32), b"x", bytes(256)),
    lambda: tls.hkdf_expand_label(bytes(32), b"x", b"", True),
    lambda: tls.hkdf_expand_label(bytes(32), b"x", b"", 0),
    lambda: tls.hkdf_expand_label(bytes(32), b"x", b"", 8161),
    lambda: tls.hkdf_expand_label(bytes(32), b"x", b"", 1.0),
    lambda: tls.derive_secret(bytes(32), b"x", bytes(4097)),
    lambda: tls._key_schedule(bytes(32), b"k" * 32, b""),
    lambda: tls._key_schedule(b"x" * 32, b"", b""),
    lambda: tls._key_schedule(b"x", b"k" * 32, b""),
    lambda: tls.Finished("other", bytes(32)),
    lambda: tls.Finished("client", bytes(31)),
    lambda: tls.TrafficSecrets(bytes(31), bytes(32)),
    lambda: tls.ClientHello(bytes(31), bytes(32), bytes(1184)),
    lambda: tls.ServerHello(bytes(32), bytes(31), bytes(1088)),
    lambda: tls.ServerHello(bytes(32), bytes(32), bytes(1087)),
])
def test_helper_validation(call):
    with pytest.raises(ValueError):
        call()


def test_local_timer_contract_report_no_secrets_and_no_network(monkeypatch):
    import socket

    def deny_network(*args, **kwargs):
        raise AssertionError("offline simulator must not use sockets")

    monkeypatch.setattr(socket, "socket", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)
    observations = []

    def clock():
        observations.append("clock")
        return 1000 if len(observations) == 1 else 1250

    monkeypatch.setattr(tls, "perf_counter_ns", clock)
    result = tls.simulate_handshake()
    assert observations == ["clock", "clock"]
    assert result.local_duration_ns == 250
    report = result.to_report()
    assert report["measurement"] == "local_simulation_duration_not_network_rtt"
    assert report["client_application_match"] is report["server_application_match"] is True
    assert report["production_tls"] is report["peer_authentication"] is False
    assert report["confidentiality_claim"] is report["fips_certification_claim"] is False
    assert len(result.transcript_hash) == 64
    assert "secret" not in json.dumps(report)
    with pytest.raises(ValueError):
        tls.simulate_handshake(b"x" * 257)
    assert len(observations) == 2  # validation is outside the timed interval


def test_real_duration_and_fresh_transcript_without_determinism_claim():
    first, second = tls.simulate_handshake(), tls.simulate_handshake()
    assert type(first.local_duration_ns) is int and first.local_duration_ns >= 0
    assert first.transcript_hash != second.transcript_hash


def test_repr_redacts_secret_and_private_state():
    client, server, _ = completed_pair()
    secrets = client.traffic_secrets
    assert repr(secrets) == "TrafficSecrets()"
    assert repr(client) == "ClientPeer(state='complete')"
    assert repr(server) == "ServerPeer(state='complete')"
    for value in (secrets.client_application, secrets.server_application):
        assert repr(value) not in repr(secrets)
        assert value.hex() not in repr(secrets)
    assert repr(tls.Finished("client", b"s" * 32)) == "Finished(sender='client')"
