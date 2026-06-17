"""
encryption_service.py
──────────────────────
Paper: "All candidate data is encrypted in transit and at rest,
        with access controls limiting exposure."

Encryption Strategy:
    At Rest   → Fernet symmetric encryption (AES-128-CBC)
    In Transit → HTTPS/TLS (ProductionConfig enforces this)
    Passwords  → werkzeug bcrypt hash (User model)
    Files      → UUID filename + deleted after parse
"""

import os
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise EnvironmentError(
            "ENCRYPTION_KEY not set in environment. "
            "Generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode())
    except Exception:
        raise ValueError("Invalid ENCRYPTION_KEY — must be a valid Fernet key.")


def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    try:
        fernet    = _get_fernet()
        encrypted = fernet.encrypt(plain_text.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Encryption failed: {e}")


def decrypt(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    try:
        fernet    = _get_fernet()
        decrypted = fernet.decrypt(encrypted_text.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        raise ValueError("Decryption failed — data may be tampered or key is incorrect.")
    except Exception as e:
        raise RuntimeError(f"Decryption failed: {e}")


def encrypt_if_not_empty(value: str) -> str:
    if not value or not value.strip():
        return value
    return encrypt(value)


def decrypt_if_not_empty(value: str) -> str:
    if not value or not value.strip():
        return value
    try:
        return decrypt(value)
    except Exception:
        return value


def generate_new_key() -> str:
    return Fernet.generate_key().decode("utf-8")