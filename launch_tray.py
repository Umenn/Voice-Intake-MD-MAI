"""
launch_tray.py  —  starts tray.py in a detached background process with log capture.
Called by start_background.bat and update_to_v004.bat instead of PowerShell Start-Process.

Usage:  python launch_tray.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TRAY = ROOT / "_app" / "tray.py"

# Log directory — try config first, fall back to logs/tray
try:
    sys.path.insert(0, str(ROOT / "_app"))
    import config
    log_dir = Path(config.LOGS_TRAY_DIR)
except Exception:
    log_dir = ROOT / "logs" / "tray"

log_dir.mkdir(parents=True, exist_ok=True)

ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_out = log_dir / f"tray_{ts}.log"
log_err = log_dir / f"tray_{ts}_err.log"

with open(log_out, "w", encoding="utf-8") as fo, \
     open(log_err, "w", encoding="utf-8") as fe:
    proc = subprocess.Popen(
        [sys.executable, str(TRAY)],
        cwd=str(ROOT),
        stdout=fo,
        stderr=fe,
        creationflags=(
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        ) if sys.platform == "win32" else 0,
    )

print(f"[launch] tray.py started — PID {proc.pid}")
print(f"[launch] stdout: {log_out}")
print(f"[launch] stderr: {log_err}")
