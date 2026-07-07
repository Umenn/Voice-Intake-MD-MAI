"""
Voice Intake System v0.0.4 — FastAPI backend
Moldova Police — OSINT / Document Generation Tool

Run:  python main.py
  or  uvicorn main:app --host 0.0.0.0 --port 8000

v0.0.4 additions:
  - 8 new document templates (PV reținere, percheziție, audiere, etc.)
  - Contextual log folders: logs/app/, logs/tray/, logs/ngrok/, logs/errors/
  - Rotating session logs — last 10 sessions kept per folder
  - Full UI redesign with light/dark theme
"""

import json
import logging
import logging.handlers
import os
import shutil
import socket
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import config
import auth

# ── Session logger ────────────────────────────────────────────────────────────
def _setup_logger() -> logging.Logger:
    """One log file per app session, keep last 10."""
    session_ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file    = os.path.join(config.LOGS_APP_DIR, f"app_{session_ts}.log")
    err_file    = os.path.join(config.LOGS_ERROR_DIR, f"errors_{session_ts}.log")

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger("voice_intake")
    logger.setLevel(logging.DEBUG)

    # Session file handler (all levels)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Error-only file handler
    eh = logging.FileHandler(err_file, encoding="utf-8")
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt)
    logger.addHandler(eh)

    # Prune old sessions — keep last 10
    for log_dir in (config.LOGS_APP_DIR, config.LOGS_ERROR_DIR):
        files = sorted(Path(log_dir).glob("*.log"), key=lambda p: p.stat().st_mtime)
        for old in files[:-10]:
            try: old.unlink()
            except OSError: pass

    return logger

log = _setup_logger()
from transcribe import transcribe
from extractor import extract
from developer import develop
from separator import separate
from doc_generator import generate, list_templates
from file_extractor import extract_text as extract_file_text

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Voice Intake - Moldova Police",
    version="0.0.4",
    description="Sistem de preluare declaratii vocal + generare documente oficiale",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Auth middleware ────────────────────────────────────────────────────────────

_PUBLIC_PATHS = {"/login", "/api/login", "/health", "/static"}

class AccessCodeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in {"/login", "/api/login", "/health"} or path.startswith("/static"):
            return await call_next(request)
        token = request.cookies.get(auth._SESSION_COOKIE, "")
        session = auth.get_session(token)
        if not session:
            if path.startswith("/api/"):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return RedirectResponse("/login")
        request.state.user = session
        return await call_next(request)

app.add_middleware(AccessCodeMiddleware)

log.info("Voice Intake v0.0.4 — server starting on %s:%s", config.HOST, config.PORT)

# ── Helper ────────────────────────────────────────────────────────────────────

def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index(request: Request):
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return FileResponse(str(STATIC_DIR / "login.html"))


@app.post("/api/login")
async def api_login(request: Request, code: str = Form(...)):
    emp = auth.find_employee_by_code(code)
    if not emp:
        return JSONResponse({"ok": False, "error": "Cod incorect."}, status_code=401)
    token = auth.create_session(emp["username"])
    resp  = JSONResponse({"ok": True, "name": emp["name"], "role": emp["role"]})
    resp.set_cookie(
        key      = auth._SESSION_COOKIE,
        value    = token,
        max_age  = auth._SESSION_DAYS * 86400,
        httponly = True,
        samesite = "lax",
    )
    return resp


@app.get("/api/status")
def api_status(request: Request):
    session = getattr(request.state, "user", {}) or {}
    ip = _local_ip()
    return {
        "version":      "0.0.4",
        "machine_code": config.MACHINE_CODE,
        "local_url":    f"http://{ip}:{config.PORT}",
        "local_ip":     ip,
        "port":         config.PORT,
        "uptime":       str(datetime.now().strftime("%Y-%m-%d %H:%M")),
        "user":         session.get("name", ""),
        "username":     session.get("username", ""),
        "role":         session.get("role", ""),
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.0.4"}


@app.get("/api/templates")
def api_templates():
    return list_templates()


@app.post("/api/transcribe")
async def api_transcribe(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("ro"),
):
    allowed = {".webm", ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"}
    suffix = Path(audio.filename or "audio.webm").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Format audio nesupportat: {suffix}")

    tmp = os.path.join(config.UPLOADS_DIR, f"{uuid.uuid4()}{suffix}")
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        if os.path.getsize(tmp) < 100:
            raise HTTPException(400, "Fisierul audio este gol.")
        result = transcribe(tmp, language)

        # ── Save recording permanently ────────────────────────────────────────
        rec_id  = f"REC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        rec_dir = Path(config.RECORDINGS_DIR) / rec_id
        rec_dir.mkdir(parents=True, exist_ok=True)

        audio_dest = rec_dir / f"audio{suffix}"
        shutil.copy2(tmp, str(audio_dest))

        transcript_text = result.get("transcript", "")
        (rec_dir / "transcript.txt").write_text(transcript_text, encoding="utf-8")

        # Try to get audio duration
        audio_duration = None
        try:
            from mutagen import File as _MFile
            _info = _MFile(str(audio_dest))
            if _info and hasattr(_info.info, "length"):
                audio_duration = round(_info.info.length, 1)
        except Exception:
            pass

        _sess = getattr(request.state, "user", {}) or {}
        metadata = {
            "rec_id":         rec_id,
            "timestamp":      datetime.now().isoformat(),
            "username":       _sess.get("username", ""),
            "officer_name":   _sess.get("name", ""),
            "audio_file":     f"audio{suffix}",
            "audio_size":     os.path.getsize(str(audio_dest)),
            "audio_duration": audio_duration,
            "transcript":     transcript_text,
            "language":       language,
            "doc_types":      [],
            "documents":      [],
        }
        (rec_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        result["rec_id"] = rec_id
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error("Transcribe error: %s", e, exc_info=True)
        raise HTTPException(500, str(e))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@app.post("/api/separate")
async def api_separate(transcript: str = Form(...)):
    if not transcript.strip():
        raise HTTPException(400, "Transcrierea este goala")
    return separate(transcript)


@app.post("/api/extract")
async def api_extract(
    transcript: str = Form(...),
    doc_type:   str = Form("declaratie"),
):
    if not transcript.strip():
        raise HTTPException(400, "Transcrierea este goala")
    return extract(transcript, doc_type)


@app.post("/api/develop")
async def api_develop(
    transcript: str = Form(...),
    extracted:  str = Form(...),
    doc_type:   str = Form("declaratie"),
):
    if not transcript.strip():
        raise HTTPException(400, "Transcrierea este goala")
    try:
        extracted_dict = json.loads(extracted)
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON invalid in campul extracted")

    result = develop(transcript, extracted_dict, doc_type)
    if result.get("error"):
        raise HTTPException(500, f"Eroare GPT: {result['error']}")
    return result


@app.post("/api/generate")
async def api_generate(
    template:          str = Form(...),
    data:              str = Form(...),
    text_razvtat_ro:   str = Form(""),
    text_razvtat_ru:   str = Form(""),
    text_dezvoltat_ro: str = Form(""),
    text_dezvoltat_ru: str = Form(""),
    rec_id:            str = Form(""),
):
    try:
        case_data = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON invalid in campul data")

    body_ro = text_razvtat_ro or text_dezvoltat_ro or case_data.get("text_razvtat_ro", "")
    body_ru = text_razvtat_ru or text_dezvoltat_ru or case_data.get("text_razvtat_ru", "")
    case_data["text_razvtat_ro"] = body_ro
    case_data["text_razvtat_ru"] = body_ru

    case_number = f"CAZ-{uuid.uuid4().hex[:8].upper()}"
    try:
        out_path = generate(template, case_data, case_number)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    # ── Save document to recording archive ────────────────────────────────────
    if rec_id:
        rec_dir = Path(config.RECORDINGS_DIR) / rec_id
        if rec_dir.exists():
            docs_dir = rec_dir / "docs"
            docs_dir.mkdir(exist_ok=True)
            doc_filename = os.path.basename(out_path)
            shutil.copy2(out_path, str(docs_dir / doc_filename))
            meta_file = rec_dir / "metadata.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                if template not in meta.get("doc_types", []):
                    meta.setdefault("doc_types", []).append(template)
                if doc_filename not in meta.get("documents", []):
                    meta.setdefault("documents", []).append(doc_filename)
                meta_file.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )

    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(out_path),
    )


@app.post("/api/analyze-files")
async def api_analyze_files(
    request:  Request,
    files:    list[UploadFile] = File(...),
    doc_type: str = Form("declaratie"),
    language: str = Form("ro"),
    mode:     str = Form("document"),   # "document" | "handwriting"
):
    """
    Upload one or more files.
    mode="document"    — PDF/DOCX/TXT/scanned images via Tesseract
    mode="handwriting" — images via GPT-4o Vision
    Returns {rec_id, extracted, full_text, file_results}
    """
    IMAGE_EXTS    = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
    DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv"}
    allowed = IMAGE_EXTS | DOCUMENT_EXTS
    full_texts = []
    file_results = []

    for ufile in files:
        suffix = Path(ufile.filename or "file.txt").suffix.lower()
        if suffix not in allowed:
            file_results.append({"filename": ufile.filename, "error": f"Format nesupport: {suffix}", "text": ""})
            continue
        tmp = os.path.join(config.UPLOADS_DIR, f"{uuid.uuid4()}{suffix}")
        try:
            with open(tmp, "wb") as f:
                shutil.copyfileobj(ufile.file, f)
            res = extract_file_text(tmp, mode=mode)
            file_results.append(res)
            if res.get("text"):
                full_texts.append(f"=== {res['filename']} ===\n{res['text']}")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    combined_text = "\n\n".join(full_texts).strip()
    if not combined_text:
        raise HTTPException(400, "Niciun text extras din fisierele incarcate.")

    # Run GPT extraction on combined text
    extracted = {}
    try:
        extracted = extract(combined_text, doc_type)
    except Exception:
        pass  # Return empty extracted — user can fill form manually

    # Archive as a recording entry
    rec_id  = f"REC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    rec_dir = Path(config.RECORDINGS_DIR) / rec_id
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / "transcript.txt").write_text(combined_text, encoding="utf-8")
    _s2 = getattr(request.state, "user", {}) or {}
    metadata = {
        "rec_id":         rec_id,
        "timestamp":      datetime.now().isoformat(),
        "username":       _s2.get("username", ""),
        "officer_name":   _s2.get("name", ""),
        "audio_file":     None,
        "audio_size":     None,
        "audio_duration": None,
        "transcript":     combined_text,
        "language":       language,
        "doc_types":      [],
        "documents":      [],
        "source":         "handwriting" if mode == "handwriting" else "file-drop",
        "source_files":   [r["filename"] for r in file_results if not r.get("error")],
        "ocr_mode":       mode,
    }
    (rec_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "rec_id":       rec_id,
        "extracted":    extracted,
        "full_text":    combined_text,
        "file_results": file_results,
    }


@app.post("/api/archive-transcript")
async def api_archive_transcript(
    request:    Request,
    transcript: str = Form(""),
    language:   str = Form("ro"),
):
    """Create a recording archive entry for a manually-entered transcript (no audio)."""
    rec_id  = f"REC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    rec_dir = Path(config.RECORDINGS_DIR) / rec_id
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
    _s3 = getattr(request.state, "user", {}) or {}
    metadata = {
        "rec_id":         rec_id,
        "timestamp":      datetime.now().isoformat(),
        "username":       _s3.get("username", ""),
        "officer_name":   _s3.get("name", ""),
        "audio_file":     None,
        "audio_size":     None,
        "audio_duration": None,
        "transcript":     transcript,
        "language":       language,
        "doc_types":      [],
        "documents":      [],
        "source":         "manual",
    }
    (rec_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"rec_id": rec_id}


# ── History / Archive ─────────────────────────────────────────────────────────

@app.get("/history", response_class=HTMLResponse)
def history_page():
    return FileResponse(str(STATIC_DIR / "history.html"))


@app.get("/api/history")
def api_history(request: Request):
    session  = getattr(request.state, "user", {}) or {}
    username = session.get("username", "")
    rec_root = Path(config.RECORDINGS_DIR)
    result = []
    if rec_root.exists():
        for rec_dir in sorted(rec_root.iterdir(), reverse=True):
            meta_file = rec_dir / "metadata.json"
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                # Filter: show only this user's records (skip if other user owns it)
                rec_owner = meta.get("username", "")
                if username and rec_owner and rec_owner != username:
                    continue
                summary = {k: v for k, v in meta.items() if k != "transcript"}
                summary["transcript_preview"] = meta.get("transcript", "")[:300]
                result.append(summary)
            except Exception:
                pass
    return result


@app.get("/api/history/{rec_id}/audio")
def api_history_audio(rec_id: str):
    rec_dir = Path(config.RECORDINGS_DIR) / rec_id
    meta_file = rec_dir / "metadata.json"
    if not meta_file.exists():
        raise HTTPException(404, "Inregistrare negasita")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    audio_path = rec_dir / meta["audio_file"]
    if not audio_path.exists():
        raise HTTPException(404, "Fisierul audio lipseste")
    return FileResponse(str(audio_path), filename=f"{rec_id}{audio_path.suffix}")


@app.get("/api/history/{rec_id}/transcript")
def api_history_transcript(rec_id: str):
    transcript_path = Path(config.RECORDINGS_DIR) / rec_id / "transcript.txt"
    if not transcript_path.exists():
        raise HTTPException(404, "Transcrierea lipseste")
    return FileResponse(str(transcript_path), filename=f"{rec_id}_transcriere.txt",
                        media_type="text/plain; charset=utf-8")


@app.get("/api/history/{rec_id}/doc/{filename}")
def api_history_doc(rec_id: str, filename: str):
    # Sanitize filename — no path traversal
    filename = Path(filename).name
    doc_path = Path(config.RECORDINGS_DIR) / rec_id / "docs" / filename
    if not doc_path.exists():
        raise HTTPException(404, "Documentul lipseste")
    return FileResponse(str(doc_path), filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.post("/api/upload-template")
async def api_upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(400, "Numai fisiere .docx sunt acceptate")
    safe_name = name.lower().replace(" ", "_").replace("/", "_")
    dest = os.path.join(config.TEMPLATES_DIR, f"{safe_name}.docx")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": f"Sablon '{safe_name}' incarcat cu succes", "id": safe_name}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
