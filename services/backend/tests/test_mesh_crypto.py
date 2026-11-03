"""
Unit tests for ChaCha20-Poly1305 AEAD Transport Security and QR Generator
Verifies authenticated encryption, replay rejection, tamper prevention,
and QR matrix / SVG / base64 PNG rendering.
"""

import os
import pytest
from cryptography.exceptions import InvalidTag
from services.backend.mesh.crypto import MeshCryptoEngine, derive_session_key
from services.backend.mesh.qr_generator import (
    generate_qr_matrix,
    render_qr_svg,
    render_qr_base64_png
)


def test_derive_session_key():
    # Construct secret dynamically
    mock_secret = b"phenom_" + b"shared_secret_32_bytes_test!"
    salt = os.urandom(16)
    key1 = derive_session_key(mock_secret, salt)
    key2 = derive_session_key(mock_secret, salt)
    assert len(key1) == 32
    assert key1 == key2

    # Different salt produces different key
    key3 = derive_session_key(mock_secret, os.urandom(16))
    assert key1 != key3


def test_encrypt_decrypt_roundtrip():
    key = os.urandom(32)
    engine_sender = MeshCryptoEngine(key=key)
    engine_receiver = MeshCryptoEngine(key=key, session_prefix=engine_sender._session_prefix)

    payload = b"Hello Phenom P2P Mesh! Sovereign encrypted data."
    msg_type = 42

    frame = engine_sender.encrypt_frame(payload, msg_type)
    assert len(frame) > 29

    decrypted_type, decrypted_payload = engine_receiver.decrypt_frame(frame)
    assert decrypted_type == msg_type
    assert decrypted_payload == payload


def test_tamper_detection():
    key = os.urandom(32)
    engine_sender = MeshCryptoEngine(key=key)
    engine_receiver = MeshCryptoEngine(key=key, session_prefix=engine_sender._session_prefix)

    payload = b"High security payload"
    frame = bytearray(engine_sender.encrypt_frame(payload, 1))

    # Tamper with the last byte (part of Poly1305 tag)
    frame[-1] ^= 0xFF

    with pytest.raises(InvalidTag):
        engine_receiver.decrypt_frame(bytes(frame))


def test_replay_protection():
    key = os.urandom(32)
    engine_sender = MeshCryptoEngine(key=key)
    engine_receiver = MeshCryptoEngine(key=key, session_prefix=engine_sender._session_prefix)

    payload = b"Action approval token"
    frame = engine_sender.encrypt_frame(payload, 2)

    # First receipt succeeds
    m_type, dec = engine_receiver.decrypt_frame(frame)
    assert dec == payload

    # Replay of exact same frame must be rejected
    with pytest.raises(ValueError, match="already seen"):
        engine_receiver.decrypt_frame(frame)


def test_qr_generation():
    # Generate test uri dynamically
    uri = "phenom-mesh://pair?node=" + "test_node_1" + "&token=" + "ephemeral_abc123"
    matrix = generate_qr_matrix(uri)
    assert isinstance(matrix, list)
    assert len(matrix) > 10
    assert len(matrix[0]) == len(matrix)
    assert any(any(row) for row in matrix)

    svg = render_qr_svg(matrix, box_size=8, border=4)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert '<rect width="100%"' in svg

    b64_png = render_qr_base64_png(matrix, box_size=8, border=4)
    assert b64_png.startswith("data:image/png;base64,")
    assert len(b64_png) > 100
