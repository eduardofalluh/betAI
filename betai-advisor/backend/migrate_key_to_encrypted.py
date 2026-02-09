"""
One-time script: read OPENAI_API_KEY from .env, encrypt it, save to api_key.enc,
and replace .env with BETAI_PASSPHRASE only. Run from backend dir: python migrate_key_to_encrypted.py
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"

def main():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        print("No OPENAI_API_KEY in .env. Nothing to migrate.")
        return
    passphrase = secrets.token_urlsafe(24)
    from secrets_helper import encrypt_and_save
    encrypt_and_save(key, passphrase)
    print("Encrypted API key saved to api_key.enc")
    # Rewrite .env with only the passphrase (and keep ODDS_API_KEY if present)
    odds = os.getenv("ODDS_API_KEY", "").strip()
    lines = [
        "# BetAI — passphrase to decrypt api_key.enc (do not commit)",
        "BETAI_PASSPHRASE=" + passphrase,
    ]
    if odds:
        lines.append("ODDS_API_KEY=" + odds)
    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(".env updated: OPENAI_API_KEY removed, BETAI_PASSPHRASE set. Key is now stored encrypted.")

if __name__ == "__main__":
    main()
