# Spike E: SQLCipher Encryption & Windows Credential Manager

## Purpose
Verify that:
1. Python can generate and manage encrypted SQLite databases using SQLCipher.
2. The database encryption key can be safely stored in and retrieved from Windows Credential Manager.
3. The database file is demonstrably unreadable and indecipherable without the key.

## Implementation Details
- **Library**: `sqlcipher3-wheels` 0.5.7 (SQLCipher v4 engine)
- **Credential Storage**: Windows Credential Manager via native `win32cred` (`pywin32` 312)
- **Key Generation**: 256-bit cryptographically secure hex key via Python `secrets.token_hex(32)`

## How to Run
```bash
python spikes/e-encryption/test_encryption.py
```

## Results
- **Key Roundtrip**: PASS. Stored in Windows Credential Manager as `CRED_TYPE_GENERIC` and read back with exact match.
- **File Unreadability**: PASS.
  - Raw 8192 bytes contain no standard `SQLite format 3` header.
  - Plaintext search for secret data returns 0 matches.
  - Standard unencrypted `sqlite3` driver throws `DatabaseError: file is not a database`.
  - Opening with incorrect key throws `DatabaseError: file is not a database` (HMAC check failed).
- **Authorized Decryption**: PASS. Opened with key retrieved from Windows Credential Manager, decrypting stored row cleanly.
- **Status**: Works.
