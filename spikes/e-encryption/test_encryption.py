"""
Spike E: Encryption and Key Management Feasibility Spike
Tests:
1. Generates cryptographic key and stores it in Windows Credential Manager (win32cred)
2. Reads key back from Windows Credential Manager
3. Creates a SQLCipher encrypted database with that key
4. Writes confidential records to the database
5. Demonstrates that the database file is completely unreadable without the key
   - Raw binary scan reveals zero plaintext and missing SQLite header
   - Standard sqlite3 reader fails with DatabaseError
   - Wrong key fails with DatabaseError
6. Demonstrates successful data retrieval using the key from Credential Manager
"""

import os
import sys
import secrets
import sqlite3
import json
import sqlcipher3
import win32cred

CRED_TARGET_NAME = "Phenom_DB_MasterKey_Test"
DB_PATH = os.path.abspath("spikes/e-encryption/test_encrypted.db")

def store_key_in_cred_manager(target: str, key_str: str):
    cred = {
        "Type": win32cred.CRED_TYPE_GENERIC,
        "TargetName": target,
        "CredentialBlob": key_str,
        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        "Comment": "Phenom Database Master Key (Spike E)"
    }
    win32cred.CredWrite(cred, 0)

def read_key_from_cred_manager(target: str) -> str:
    cred = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC)
    blob = cred["CredentialBlob"]
    # CredentialBlob in pywin32 comes back as UTF-16LE bytes
    if isinstance(blob, bytes):
        return blob.decode("utf-16le")
    return str(blob)

def delete_key_from_cred_manager(target: str):
    try:
        win32cred.CredDelete(target, win32cred.CRED_TYPE_GENERIC)
    except Exception:
        pass

def run_spike_e():
    print("=== SPIKE E: SQLCIPHER & WINDOWS CREDENTIAL MANAGER ===")
    results = {}
    
    # Clean previous run
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    # Step 1: Generate key & store in Windows Credential Manager
    generated_key = secrets.token_hex(32)
    print(f"[1] Generated 256-bit key: {generated_key[:8]}...{generated_key[-8:]}")
    store_key_in_cred_manager(CRED_TARGET_NAME, generated_key)
    print("    Stored key in Windows Credential Manager.")
    
    # Step 2: Read key back
    retrieved_key = read_key_from_cred_manager(CRED_TARGET_NAME)
    print(f"[2] Retrieved key from Credential Manager: {retrieved_key[:8]}...{retrieved_key[-8:]}")
    assert generated_key == retrieved_key, "Retrieved key does not match generated key!"
    print("    Key roundtrip verification: PASS")
    results["key_roundtrip"] = "PASS"
    
    # Step 3: Create SQLCipher database and write secret data
    print(f"[3] Creating encrypted database at {DB_PATH}")
    conn = sqlcipher3.connect(DB_PATH)
    conn.execute(f"PRAGMA key = '{retrieved_key}';")
    conn.execute("PRAGMA cipher_compatibility = 4;")
    conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, content TEXT, timestamp DATETIME);")
    sample_secret = "TOP_SECRET_USER_FACT_Jarvis_phenom_quantum_token_98765"
    conn.execute("INSERT INTO memories (content, timestamp) VALUES (?, datetime('now'));", (sample_secret,))
    conn.commit()
    conn.close()
    print("    Encrypted table created and secret written.")
    
    # Step 4: Show that file is unreadable without the key
    print("[4] Testing unreadability without key:")
    
    # 4a: Check raw file bytes
    with open(DB_PATH, "rb") as f:
        raw_bytes = f.read()
    
    # Standard SQLite header is 'SQLite format 3\x00'
    has_sqlite_header = raw_bytes.startswith(b"SQLite format 3\x00")
    secret_in_raw = sample_secret.encode("utf-8") in raw_bytes
    print(f"    Raw bytes length: {len(raw_bytes)} bytes")
    print(f"    Contains standard SQLite header: {has_sqlite_header} (expected False)")
    print(f"    Contains plaintext secret in raw file: {secret_in_raw} (expected False)")
    assert not has_sqlite_header, "Database has unencrypted SQLite header!"
    assert not secret_in_raw, "Secret appeared in plaintext in file!"
    
    # 4b: Attempt open with standard sqlite3 (unencrypted)
    std_sqlite_failed = False
    try:
        std_conn = sqlite3.connect(DB_PATH)
        cur = std_conn.cursor()
        cur.execute("SELECT * FROM memories;")
        cur.fetchall()
        std_conn.close()
    except sqlite3.DatabaseError as e:
        print(f"    Standard sqlite3 read attempt failed as expected: {e}")
        std_sqlite_failed = True
    assert std_sqlite_failed, "Standard sqlite3 was able to read encrypted database!"
    
    # 4c: Attempt open with wrong key
    wrong_key_failed = False
    try:
        bad_conn = sqlcipher3.connect(DB_PATH)
        bad_conn.execute("PRAGMA key = 'wrong_password_12345';")
        bad_conn.execute("PRAGMA cipher_compatibility = 4;")
        bad_cur = bad_conn.cursor()
        bad_cur.execute("SELECT * FROM memories;")
        bad_cur.fetchall()
        bad_conn.close()
    except sqlcipher3.DatabaseError as e:
        print(f"    Wrong key attempt failed as expected: {e}")
        wrong_key_failed = True
    assert wrong_key_failed, "SQLCipher read succeeded with wrong key!"
    
    results["unreadable_without_key"] = "PASS"
    
    # Step 5: Read back with key from Credential Manager
    print("[5] Reading back with retrieved Credential Manager key...")
    auth_conn = sqlcipher3.connect(DB_PATH)
    auth_conn.execute(f"PRAGMA key = '{retrieved_key}';")
    auth_conn.execute("PRAGMA cipher_compatibility = 4;")
    auth_cur = auth_conn.cursor()
    auth_cur.execute("SELECT content FROM memories;")
    rows = auth_cur.fetchall()
    auth_conn.close()
    
    assert len(rows) == 1 and rows[0][0] == sample_secret
    print(f"    Successfully decrypted secret: '{rows[0][0]}'")
    results["decrypt_with_key"] = "PASS"
    results["status"] = "works"
    
    # Cleanup Credential Manager entry used for spike
    delete_key_from_cred_manager(CRED_TARGET_NAME)
    print("    Cleaned up test key from Credential Manager.")
    
    print("\n>>> ALL SPIKE E ASSERTIONS PASSED! <<<")
    return results

if __name__ == "__main__":
    res = run_spike_e()
    with open("spikes/e-encryption/results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
