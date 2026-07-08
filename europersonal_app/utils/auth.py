"""Autentificare cu utilizatori locali (SQLite).

Baza de date: users.db (în folderul aplicației). Parolele sunt stocate
ca hash SHA-256 cu salt individual — niciodată în clar.

Cont implicit pentru faza de testare:  admin / 1337
"""
import hashlib
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "users.db"

DEFAULT_ADMIN = ("admin", "1337")


def _hash(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf8")).hexdigest()


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db(seed_user: str = DEFAULT_ADMIN[0], seed_pass: str = DEFAULT_ADMIN[1]) -> None:
    """Creează tabela și contul admin inițial (doar dacă baza e goală).

    Pe Streamlit Cloud, seed_user/seed_pass vin din Secrets — astfel contul
    admin supraviețuiește repornirilor (users.db e efemer în cloud).
    """
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            salt TEXT NOT NULL,
            pw_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )""")
        n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n == 0:
            add_user(seed_user, seed_pass, role="admin")


def add_user(username: str, password: str, role: str = "user") -> None:
    """Adaugă un utilizator nou. Ridică ValueError dacă există deja."""
    username = username.strip().lower()
    if not username or not password:
        raise ValueError("Utilizatorul și parola nu pot fi goale.")
    salt = secrets.token_hex(16)
    try:
        with _conn() as c:
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                      (username, salt, _hash(password, salt), role,
                       datetime.now().strftime("%d.%m.%Y %H:%M")))
    except sqlite3.IntegrityError:
        raise ValueError(f"Utilizatorul „{username}” există deja.")


def verify_user(username: str, password: str) -> dict | None:
    """Returnează {username, role} dacă datele sunt corecte, altfel None."""
    username = username.strip().lower()
    with _conn() as c:
        row = c.execute("SELECT salt, pw_hash, role FROM users WHERE username=?",
                        (username,)).fetchone()
    if row and secrets.compare_digest(row[1], _hash(password, row[0])):
        return {"username": username, "role": row[2]}
    return None


def change_password(username: str, new_password: str) -> None:
    salt = secrets.token_hex(16)
    with _conn() as c:
        c.execute("UPDATE users SET salt=?, pw_hash=? WHERE username=?",
                  (salt, _hash(new_password, salt), username.strip().lower()))


def list_users() -> list[tuple]:
    with _conn() as c:
        return c.execute("SELECT username, role, created_at FROM users ORDER BY username").fetchall()
