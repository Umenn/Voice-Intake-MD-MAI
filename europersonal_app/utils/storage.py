"""Persistența dosarelor pe disc.

Structura:
    dosare/
      NUME_PRENUME/
        dosar.json            (metadate: nume, țară, adresă, status, date)
        acte_incarcate/       (cele 4 acte obligatorii: CIM, COMODAT, PROCURA, PASAPORT)
        acte_generate/        (documentele generate + pachetul ZIP)
        decizii_invitatii/    (deciziile și invitațiile primite de la IGM)
"""
import json
import re
from datetime import datetime
from pathlib import Path

# rădăcina aplicației = folderul de deasupra lui utils/
APP_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = APP_ROOT / "dosare"

REQUIRED_UPLOADS = ("CIM", "CONTRACT_COMODAT", "PROCURA", "PASAPORT")
SUBDIRS = ("acte_incarcate", "acte_generate", "decizii_invitatii")


def ensure_folders() -> None:
    """Creează folderele lipsă la prima rulare (idempotent)."""
    for name in ("dosare", "exemple", "templates", "test_output"):
        (APP_ROOT / name).mkdir(exist_ok=True)


def _safe_name(full_name: str) -> str:
    s = re.sub(r"[^\w ]", "", full_name.strip().upper())
    return re.sub(r"\s+", "_", s)


def dosar_dir(full_name: str) -> Path:
    return BASE_DIR / _safe_name(full_name)


def create_dosar(full_name: str, country: str) -> Path:
    d = dosar_dir(full_name)
    for sub in SUBDIRS:
        (d / sub).mkdir(parents=True, exist_ok=True)
    meta_path = d / "dosar.json"
    if not meta_path.exists():
        save_meta(full_name, {
            "nume_complet": full_name.strip().upper(),
            "tara": country,
            "creat_la": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status": "în lucru",
            "adresa_cazare": "",
            "acte_incarcate": {},
            "acte_generate": [],
        })
    return d


def load_meta(full_name: str) -> dict:
    p = dosar_dir(full_name) / "dosar.json"
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else {}


def save_meta(full_name: str, meta: dict) -> None:
    p = dosar_dir(full_name) / "dosar.json"
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf8")


def update_meta(full_name: str, **kwargs) -> dict:
    meta = load_meta(full_name)
    meta.update(kwargs)
    save_meta(full_name, meta)
    return meta


def save_upload(full_name: str, doc_type: str, file_bytes: bytes, original_name: str) -> Path:
    ext = Path(original_name).suffix.lower() or ".bin"
    fname = f"{doc_type}_{_safe_name(full_name)}{ext}"
    path = dosar_dir(full_name) / "acte_incarcate" / fname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_bytes)
    meta = load_meta(full_name)
    meta.setdefault("acte_incarcate", {})[doc_type] = fname
    save_meta(full_name, meta)
    return path


def save_generated(full_name: str, filename: str, file_bytes: bytes) -> Path:
    path = dosar_dir(full_name) / "acte_generate" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_bytes)
    meta = load_meta(full_name)
    gen = meta.setdefault("acte_generate", [])
    if filename not in gen:
        gen.append(filename)
    save_meta(full_name, meta)
    return path


def save_decizie(full_name: str, file_bytes: bytes, original_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"{stamp}_{Path(original_name).name}"
    path = dosar_dir(full_name) / "decizii_invitatii" / fname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_bytes)
    return path


def list_dosare() -> list[dict]:
    if not BASE_DIR.exists():
        return []
    out = []
    for d in sorted(BASE_DIR.iterdir()):
        if d.is_dir() and (d / "dosar.json").exists():
            meta = json.loads((d / "dosar.json").read_text(encoding="utf8"))
            meta["_folder"] = d.name
            out.append(meta)
    return list(reversed(out))


def list_files(full_name: str, subdir: str) -> list[Path]:
    d = dosar_dir(full_name) / subdir
    return sorted(p for p in d.iterdir() if p.is_file()) if d.exists() else []


def missing_uploads(full_name: str) -> list[str]:
    have = load_meta(full_name).get("acte_incarcate", {})
    return [t for t in REQUIRED_UPLOADS if t not in have]
