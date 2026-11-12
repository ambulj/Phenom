"""
ChaCha20-Poly1305 AEAD Transport Security for Phenom P2P Mesh
Provides authenticated symmetric encryption, HKDF-SHA256 session key derivation,
96-bit nonce rotation, and sliding-window / monotonic replay protection.
"""

import os
import struct
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

HEADER_MAGIC = b"PHN1"
# Header format: 4s (magic) + B (msg_type) + Q (sequence, 8 bytes big-endian) + 12s (nonce) + I (ciphertext length, 4 bytes big-endian)
HEADER_FORMAT = ">4sBQ12sI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 29 bytes


def derive_session_key(shared_secret: bytes, salt: bytes, info: bytes = b"phenom-p2p-session-v1") -> bytes:
    """Derive a 256-bit symmetric key from shared secret using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    )
    return hkdf.derive(shared_secret)


class MeshCryptoEngine:
    """
    Encrypts and decrypts P2P mesh message frames using ChaCha20-Poly1305 AEAD.
    Enforces 96-bit nonces (4B session prefix + 8B sequence) and anti-replay protection.
    """

    def __init__(self, key: bytes, session_prefix: Optional[bytes] = None):
        if len(key) != 32:
            raise ValueError(f"ChaCha20-Poly1305 key must be exactly 32 bytes, got {len(key)}")
        self._key = key
        self._aead = ChaCha20Poly1305(key)
        self._session_prefix = session_prefix if session_prefix is not None else os.urandom(4)
        if len(self._session_prefix) != 4:
            raise ValueError(f"Session prefix must be exactly 4 bytes, got {len(self._session_prefix)}")
        self._send_seq = 0
        self._recv_last_seq = -1
        # 64-bit replay sliding window bitmask
        self._replay_window = 0

    def _build_nonce(self, seq: int) -> bytes:
        """Construct a 12-byte (96-bit) nonce: 4 bytes session prefix + 8 bytes sequence (big-endian)."""
        return self._session_prefix + struct.pack(">Q", seq)

    def encrypt_frame(
        self,
        payload: bytes,
        msg_type: int,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Encrypt a payload into an EncryptedMeshFrame binary packet.
        Frame format:
        [HEADER: 29 bytes]
          - Magic: 4 bytes (PHN1)
          - msg_type: 1 byte
          - seq: 8 bytes
          - nonce: 12 bytes
          - ciphertext_len: 4 bytes
        [BODY: ciphertext_len bytes (ciphertext + 16B Poly1305 tag)]
        """
        seq = self._send_seq
        self._send_seq += 1
        nonce = self._build_nonce(seq)

        # Ciphertext computation with ChaCha20-Poly1305
        # The AAD incorporates associated_data or the sequence and msg_type
        aad = associated_data if associated_data is not None else struct.pack(">BQ", msg_type, seq)
        ciphertext = self._aead.encrypt(nonce, payload, aad)

        header = struct.pack(
            HEADER_FORMAT,
            HEADER_MAGIC,
            msg_type,
            seq,
            nonce,
            len(ciphertext)
        )
        return header + ciphertext

    def decrypt_frame(
        self,
        frame_bytes: bytes,
        associated_data: Optional[bytes] = None
    ) -> Tuple[int, bytes]:
        """
        Decrypt and verify an EncryptedMeshFrame binary packet.
        Returns: (msg_type, decrypted_payload)
        Raises:
            ValueError: on corrupt header, invalid magic, replay, or truncated frame
            cryptography.exceptions.InvalidTag: on ciphertext or tag tampering
        """
        if len(frame_bytes) < HEADER_SIZE:
            raise ValueError(f"Frame length {len(frame_bytes)} is shorter than header size {HEADER_SIZE}")

        magic, msg_type, seq, nonce, ct_len = struct.unpack(
            HEADER_FORMAT,
            frame_bytes[:HEADER_SIZE]
        )

        if magic != HEADER_MAGIC:
            raise ValueError(f"Invalid frame magic: {magic!r}, expected {HEADER_MAGIC!r}")

        expected_total = HEADER_SIZE + ct_len
        if len(frame_bytes) != expected_total:
            raise ValueError(f"Frame size mismatch: got {len(frame_bytes)}, expected {expected_total}")

        ciphertext = frame_bytes[HEADER_SIZE:expected_total]

        # Replay protection check
        self._validate_and_update_replay(seq)

        # AAD verification
        aad = associated_data if associated_data is not None else struct.pack(">BQ", msg_type, seq)
        plaintext = self._aead.decrypt(nonce, ciphertext, aad)

        return msg_type, plaintext

    def _validate_and_update_replay(self, seq: int) -> None:
        """
        Enforce anti-replay check using a 64-sequence sliding window.
        Rejects sequences already seen or older than window threshold.
        """
        if self._recv_last_seq == -1:
            # First frame received
            self._recv_last_seq = seq
            self._replay_window = 1
            return

        diff = seq - self._recv_last_seq
        if diff > 0:
            # New sequence ahead of window
            if diff < 64:
                self._replay_window = (self._replay_window << diff) | 1
            else:
                self._replay_window = 1
            self._recv_last_seq = seq
        else:
            # Sequence behind or equal to current highest
            offset = -diff
            if offset >= 64:
                raise ValueError(f"Replay rejected: sequence {seq} is too old (highest {self._recv_last_seq})")
            bit = 1 << offset
            if self._replay_window & bit:
                raise ValueError(f"Replay rejected: sequence {seq} already seen")
            self._replay_window |= bit
