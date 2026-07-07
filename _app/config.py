import os
import secrets
from pathlib import Path
from dotenv import load_dotenv, set_key

# Load .env from voice_intake/ (one level up from _app/), then fall back to robo_cop_bot/.env
_here   = Path(__file__).parent.parent          # voice_intake/
_parent = _here.parent / "robo_cop_bot" / ".env"
_env    = _here / ".env"

load_dotenv(_env)                      # voice_intake/.env  (if it exists)
load_dotenv(_parent, override=False)   # robo_cop_bot/.env  (fills any missing keys)

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
HOST            = os.getenv("HOST", "0.0.0.0")
PORT            = int(os.getenv("PORT", 8000))
AUTH_SECRET     = os.getenv("AUTH_SECRET", secrets.token_hex(32))
TUNNEL_ID             = os.getenv("TUNNEL_ID",  "")   # legacy cloudflare (unused)
TUNNEL_URL            = os.getenv("TUNNEL_URL", "")   # legacy cloudflare (unused)
CLOUDFLARE_API_TOKEN  = os.getenv("CLOUDFLARE_API_TOKEN", "")  # legacy
NGROK_TOKEN           = os.getenv("NGROK_TOKEN",  "")  # set by setup_tunnel.py
NGROK_DOMAIN          = os.getenv("NGROK_DOMAIN", "")  # e.g. your-name.ngrok-free.app

# ── Machine code — unique per installation ────────────────────────────────────
# Generated once and persisted to .env so it survives restarts.
# Officers enter this code on first visit to get a 30-day session cookie.
MACHINE_CODE = os.getenv("MACHINE_CODE", "")
if not MACHINE_CODE:
    MACHINE_CODE = secrets.token_hex(4).upper()   # e.g. "A3F8B2C1"
    if _env.exists():
        set_key(str(_env), "MACHINE_CODE", MACHINE_CODE)
    os.environ["MACHINE_CODE"] = MACHINE_CODE

# ── Folder layout ─────────────────────────────────────────────────────────────
#
# Defaults:  all folders live inside the install directory (BASE_DIR).
# Override:  set these env vars in .env to move any folder to a different drive.
#
#   DATA_DIR      — users.csv, audit.csv           (env: VI_DATA_DIR)
#   CASES_DIR     — generated .docx case files     (env: VI_CASES_DIR)
#   UPLOADS_DIR   — temp audio files               (env: VI_UPLOADS_DIR)
#   LOGS_DIR      — server logs                    (env: VI_LOGS_DIR)
#   TEMPLATES_DIR — .docx master templates         (env: VI_TEMPLATES_DIR)
#
BASE_DIR      = os.path.dirname(os.path.dirname(__file__))  # voice_intake/

DATA_DIR      = os.getenv("VI_DATA_DIR",      os.path.join(BASE_DIR, "data"))
TEMPLATES_DIR = os.getenv("VI_TEMPLATES_DIR", os.path.join(BASE_DIR, "templates"))
CASES_DIR     = os.getenv("VI_CASES_DIR",     os.path.join(BASE_DIR, "cases"))
UPLOADS_DIR   = os.getenv("VI_UPLOADS_DIR",   os.path.join(BASE_DIR, "uploads"))
LOGS_DIR      = os.getenv("VI_LOGS_DIR",      os.path.join(BASE_DIR, "logs"))

USERS_CSV     = os.path.join(DATA_DIR, "users.csv")
AUDIT_CSV     = os.path.join(DATA_DIR, "audit.csv")
RECORDINGS_DIR = os.getenv("VI_RECORDINGS_DIR", os.path.join(BASE_DIR, "recordings"))

# Log subdirectories
LOGS_APP_DIR    = os.path.join(LOGS_DIR, "app")
LOGS_TRAY_DIR   = os.path.join(LOGS_DIR, "tray")
LOGS_NGROK_DIR  = os.path.join(LOGS_DIR, "ngrok")
LOGS_ERROR_DIR  = os.path.join(LOGS_DIR, "errors")

# Create all directories on import
for _d in (DATA_DIR, TEMPLATES_DIR, CASES_DIR, UPLOADS_DIR, LOGS_DIR,
           RECORDINGS_DIR, LOGS_APP_DIR, LOGS_TRAY_DIR, LOGS_NGROK_DIR, LOGS_ERROR_DIR):
    os.makedirs(_d, exist_ok=True)
