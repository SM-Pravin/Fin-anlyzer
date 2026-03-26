"""
Setup manager: ensures Ollama is installed and the configured model is pulled
before the application starts accepting requests.
"""

import os
import shutil
import subprocess
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def ensure_ollama_ready() -> None:
    """
    1. Checks if the `ollama` binary is on PATH.
    2. If not, installs it via the official install script (Linux/macOS).
    3. Pulls the configured LLM model so it's ready at first request.
    """
    model = os.getenv("LLM_MODEL", "qwen2.5vl:7b")
    auto_install = os.getenv("AUTO_INSTALL_OLLAMA", "false").lower() == "true"

    # ── Step 1: Check / install Ollama ───────────────────────────────────────
    if shutil.which("ollama") is None:
        if not auto_install:
            print("⚠️  Ollama not found. Set AUTO_INSTALL_OLLAMA=true in .env to auto-install.")
            return

        print("📦  Ollama not found — installing via official script…")
        try:
            result = subprocess.run(
                "curl -fsSL https://ollama.com/install.sh | sh",
                shell=True,
                check=True,
                capture_output=False,
            )
            print("✅  Ollama installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌  Ollama installation failed: {e}")
            return
    else:
        print(f"✅  Ollama found at: {shutil.which('ollama')}")

    # ── Step 2: Pull the model (idempotent — skips if already present) ───────
    print(f"🔄  Pulling model '{model}' (skipped if already cached)…")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["ollama", "pull", model],
                check=True,
                capture_output=False,
            )
        )
        print(f"✅  Model '{model}' is ready.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not pull model '{model}': {e}. The app will still start.")
    except FileNotFoundError:
        print("⚠️  ollama binary not found after install attempt. Skipping model pull.")
