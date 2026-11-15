"""
Phenom Telegram Remote Bridge Daemon
Maintains continuous real-time long-polling connection with @Phenom_menalbot
Processes remote commands, /status, /snapshot, /lock, /do, and interactive approvals.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Set up paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "desktop" / "release" / "win-unpacked" / "resources"))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from services.backend.remote.credentials import get_telegram_owner_id, get_telegram_token
from services.backend.remote.telegram_bot import telegram_controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("telegram_bridge")

async def main():
    token = get_telegram_token()
    owner_id = get_telegram_owner_id()

    if not token or not owner_id:
        logger.error(f"Telegram credentials incomplete (Token: {bool(token)}, Owner: {owner_id}). Exiting.")
        return

    logger.info(f"Starting Phenom Telegram Remote Bridge for Owner ID {owner_id}...")
    telegram_controller.set_credentials(token, owner_id)
    telegram_controller._running = True

    try:
        await telegram_controller._poll_loop()
    except asyncio.CancelledError:
        logger.info("Telegram bridge shutting down cleanly.")
    except Exception as e:
        logger.error(f"Unexpected bridge error: {e}", exc_info=True)
    finally:
        telegram_controller.stop()

if __name__ == "__main__":
    asyncio.run(main())
