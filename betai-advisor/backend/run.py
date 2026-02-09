"""
Production entrypoint: run gunicorn bound to 0.0.0.0 and PORT (required for Render, etc.).
Usage: python run.py
"""
import os
import subprocess
import sys

if __name__ == "__main__":
    port = os.environ.get("PORT", "5000")
    bind = f"0.0.0.0:{port}"
    # Use same Python so gunicorn is found; bind to 0.0.0.0 so Render can detect the port
    sys.exit(
        subprocess.call([
            sys.executable,
            "-m", "gunicorn",
            "-w", "1",
            "-b", bind,
            "server:app",
        ])
    )
