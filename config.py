import os
import sys
from dotenv import load_dotenv

# Load local .env if available
load_dotenv()

# --- Telegram Credentials ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Storage Vault Channel (must be an integer, usually starts with -100)
_raw_log = os.getenv("LOG_CHANNEL_ID", "0").strip()
if _raw_log and not _raw_log.startswith("-"):
    _raw_log = f"-{_raw_log}"
try:
    LOG_CHANNEL_ID = int(_raw_log)
except ValueError:
    LOG_CHANNEL_ID = 0

# --- Database Settings ---
MONGO_URI = os.getenv("MONGO_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "stream_vault")

# --- Security / Whitelist ---
# Comma-separated user IDs allowed to search, scrape, and leech
raw_allowed = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = set()
if raw_allowed:
    for uid in raw_allowed.split(","):
        uid = uid.strip()
        if uid.isdigit():
            ALLOWED_USERS.add(int(uid))

# --- Streaming Web Server Settings ---
PORT = int(os.getenv("PORT", "7860"))
HOST = os.getenv("HOST", "0.0.0.0")
STREAM_URL = os.getenv("STREAM_URL", f"http://localhost:{PORT}").rstrip("/")

# --- Channel Indexing List ---
raw_channels = os.getenv("CHANNELS_TO_INDEX", "")
CHANNELS_TO_INDEX = [c.strip() for c in raw_channels.split(",") if c.strip()]

# --- GitHub Actions Cloud Leech Settings ---
GH_TOKEN = os.getenv("GH_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Aswin-2266/stream-vault")

# Validation helper
def validate_config():
    missing = []
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not LOG_CHANNEL_ID:
        missing.append("LOG_CHANNEL_ID")
    if not MONGO_URI:
        missing.append("MONGO_URI")

    if missing:
        print(f"[!] Warning: Missing required configuration keys in environment: {', '.join(missing)}")
        return False
    return True
