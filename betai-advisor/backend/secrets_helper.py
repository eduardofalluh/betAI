"""
Encrypt/decrypt the OpenAI API key so it is not stored in plain text.
Uses Fernet (AES) with a key derived from a passphrase (PBKDF2).
"""
import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BACKEND_DIR = Path(__file__).resolve().parent
SECRETS_FILE = BACKEND_DIR / "api_key.enc"
PBKDF2_ITERATIONS = 120_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt_and_save(api_key: str, passphrase: str) -> None:
    """Encrypt the API key with the passphrase and save to api_key.enc."""
    if not api_key or not passphrase:
        raise ValueError("API key and passphrase are required")
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    f = Fernet(key)
    ciphertext = f.encrypt(api_key.encode("utf-8"))
    SECRETS_FILE.write_bytes(salt + ciphertext)


def load_and_decrypt(passphrase: str) -> str:
    """Load api_key.enc and decrypt with the passphrase. Returns the API key or empty string on failure."""
    if not SECRETS_FILE.exists() or not passphrase:
        return ""
    try:
        data = SECRETS_FILE.read_bytes()
        if len(data) < 17:
            return ""
        salt, ciphertext = data[:16], data[16:]
        key = _derive_key(passphrase, salt)
        f = Fernet(key)
        return f.decrypt(ciphertext).decode("utf-8")
    except Exception:
        return ""
