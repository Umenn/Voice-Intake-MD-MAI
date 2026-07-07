"""
auth.py  -  Per-employee authentication for Voice Intake v0.0.4

Each officer has a unique personal access code (SANDU01 etc.).
Sessions: in-memory dict (token -> employee info).
Cookie expires in 30 days.
"""

import secrets
import threading

# ---- Employee registry -------------------------------------------------------
EMPLOYEES = [
    {
        "username": "sandu.alexandru",
        "name":     "Sandu Alexandru",
        "role":     "Ofiter Superior de Investigatii Anti-Drog",
        "code":     "SANDU01",
    },
    {
        "username": "nikita.mocan",
        "name":     "Nikita Mocan",
        "role":     "Sub-Ofiter Superior de Investigatii Sectorul 4",
        "code":     "MOCAN02",
    },
    {
        "username": "dorin.ceban",
        "name":     "Dorin Ceban",
        "role":     "Ofiter de Investigatii Anti-Drog",
        "code":     "CEBAN03",
    },
    {
        "username": "daniel.rosca",
        "name":     "Daniel Rosca",
        "role":     "Sef pe practicanti",
        "code":     "ROSCA04",
    },
    {
        "username": "lucian.martea",
        "name":     "Lucian Martea",
        "role":     "Ofiter de Investigatii - Inspectoratul Riscani",
        "code":     "MARTEA05",
    },
]

_SESSION_COOKIE = "vi_session"
_SESSION_DAYS   = 30

_lock     = threading.Lock()
_sessions: dict = {}    # token -> {username, name, role}


def find_employee_by_code(code: str) -> dict | None:
    """Return matching employee dict or None."""
    c = code.strip().upper()
    for emp in EMPLOYEES:
        if emp["code"] == c:
            return emp
    return None


def create_session(username: str) -> str:
    """Create a random session token for the employee and store it."""
    token = secrets.token_hex(32)
    emp = next((e for e in EMPLOYEES if e["username"] == username), None)
    if emp:
        with _lock:
            _sessions[token] = {
                "username": emp["username"],
                "name":     emp["name"],
                "role":     emp["role"],
            }
    return token


def get_session(token: str) -> dict | None:
    """Return session dict or None if invalid/expired."""
    if not token:
        return None
    with _lock:
        return _sessions.get(token)


def get_user(token: str) -> str | None:
    s = get_session(token)
    return s["username"] if s else None


def logout(token: str):
    with _lock:
        _sessions.pop(token, None)


# ---- Backward compat shims (used by older code paths) -----------------------
def check_access_code(code: str) -> bool:
    return find_employee_by_code(code) is not None

def verify_session_token(token: str) -> bool:
    return get_session(token) is not None
