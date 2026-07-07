"""
tray.py — System tray manager for Voice Intake v0.0.4

Starts the FastAPI server as a subprocess, shows a system tray icon,
and optionally starts a Cloudflare tunnel for external (mobile) access.

Run:
    pythonw.exe _app/tray.py          # background, no console
    python     _app/tray.py          # foreground (debug)
"""

import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add _app/ to path so we can import config
sys.path.insert(0, str(Path(__file__).parent))
import config

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("[tray] pystray/Pillow not installed. Run: pip install pystray Pillow")
    sys.exit(1)

try:
    import tkinter as tk
    _HAS_TK = True
except ImportError:
    _HAS_TK = False

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
MAIN_PY     = ROOT / "_app" / "main.py"
NGROK_EXE   = ROOT / "_tools" / "ngrok.exe"
NGROK_ZIP   = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"

# ── State ─────────────────────────────────────────────────────────────────────
_server_proc   = None
_tunnel_proc   = None
_tunnel_url    = ""
_tray_icon     = None
_popup_thread  = None
_popup_win     = None   # reference so we can close it externally


# ── Helpers ───────────────────────────────────────────────────────────────────

def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _make_icon(color: str = "#238636") -> Image.Image:
    """Generate a 64x64 tray icon programmatically."""
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color)
    pts = [32, 14, 48, 20, 48, 36, 32, 52, 16, 36, 16, 20]
    draw.polygon(pts, fill="white")
    return img


def _copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.encode("utf-8"), check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


# ── Status popup (double-click on icon) ───────────────────────────────────────

def _show_popup():
    """Show a small dark status window near the system tray."""
    global _popup_thread, _popup_win

    # If already open, close it (toggle)
    if _popup_win is not None:
        try:
            _popup_win.destroy()
        except Exception:
            pass
        _popup_win = None
        return

    if not _HAS_TK:
        return

    # Don't stack multiple threads
    if _popup_thread and _popup_thread.is_alive():
        return

    def _run():
        global _popup_win

        ip   = _local_ip()
        port = config.PORT
        code = config.MACHINE_CODE

        root = tk.Tk()
        _popup_win = root

        root.overrideredirect(True)          # no title bar / borders
        root.attributes("-topmost", True)    # always on top
        root.configure(bg="#0d1117")

        # ── Outer border frame ────────────────────────────────────────────────
        border = tk.Frame(root, bg="#30363d", padx=1, pady=1)
        border.pack(fill="both", expand=True)

        inner = tk.Frame(border, bg="#0d1117", padx=0, pady=0)
        inner.pack(fill="both", expand=True)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(inner, bg="#161b22")
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="  Voice Intake", bg="#161b22", fg="#58a6ff",
            font=("Segoe UI", 11, "bold"), anchor="w"
        ).pack(side="left", pady=10, padx=4)

        tk.Label(
            hdr, text="v0.0.2.5  ", bg="#161b22", fg="#484f58",
            font=("Segoe UI", 8), anchor="e"
        ).pack(side="right", pady=10)

        # Divider
        tk.Frame(inner, bg="#30363d", height=1).pack(fill="x")

        # ── Info rows ─────────────────────────────────────────────────────────
        info = tk.Frame(inner, bg="#0d1117", padx=16, pady=10)
        info.pack(fill="x")

        def _info_row(parent, label, value, value_font=("Segoe UI", 9)):
            row = tk.Frame(parent, bg="#0d1117")
            row.pack(fill="x", pady=2)
            tk.Label(
                row, text=label, bg="#0d1117", fg="#8b949e",
                font=("Segoe UI", 8), width=5, anchor="w"
            ).pack(side="left")
            tk.Label(
                row, text=value, bg="#0d1117", fg="#e6edf3",
                font=value_font, anchor="w"
            ).pack(side="left", padx=(4, 0))

        _info_row(info, "IP", f"{ip}:{port}")

        # Code row with copy hint
        code_row = tk.Frame(info, bg="#0d1117")
        code_row.pack(fill="x", pady=2)
        tk.Label(
            code_row, text="Cod", bg="#0d1117", fg="#8b949e",
            font=("Segoe UI", 8), width=5, anchor="w"
        ).pack(side="left")
        code_lbl = tk.Label(
            code_row, text=code, bg="#0d1117", fg="#f0f6fc",
            font=("Consolas", 13, "bold"), cursor="hand2"
        )
        code_lbl.pack(side="left", padx=(4, 0))
        code_lbl.bind("<Button-1>", lambda e: _copy_to_clipboard(code))
        tk.Label(
            code_row, text=" click=copiere", bg="#0d1117", fg="#484f58",
            font=("Segoe UI", 7)
        ).pack(side="left")

        # Tunnel status row
        if _tunnel_url:
            _info_row(info, "URL", _tunnel_url[:40] + ("…" if len(_tunnel_url) > 40 else ""),
                      ("Consolas", 7))

        # Divider
        tk.Frame(inner, bg="#30363d", height=1).pack(fill="x")

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(inner, bg="#0d1117", padx=12, pady=10)
        btn_row.pack(fill="x")

        def _btn(parent, text, bg, fg, cmd):
            b = tk.Button(
                parent, text=text, bg=bg, fg=fg,
                activebackground=bg, activeforeground=fg,
                font=("Segoe UI", 9), bd=0, padx=10, pady=5,
                cursor="hand2", relief="flat", command=cmd
            )
            b.pack(side="left", padx=3)
            return b

        def _open():
            webbrowser.open(f"http://{ip}:{port}")
            root.destroy()

        def _stop():
            root.destroy()
            if _tray_icon:
                _shutdown(_tray_icon)

        _btn(btn_row, "Deschide", "#238636", "white", _open)
        _btn(btn_row, "Opreste tot", "#da3633", "white", _stop)

        # Close button (top-right X)
        tk.Button(
            hdr, text=" ✕ ", bg="#161b22", fg="#8b949e",
            activebackground="#161b22", activeforeground="#f85149",
            font=("Segoe UI", 9), bd=0, cursor="hand2",
            command=root.destroy
        ).pack(side="right", padx=4)

        # ── Position: bottom-right above taskbar ──────────────────────────────
        root.update_idletasks()
        w  = root.winfo_reqwidth()
        h  = root.winfo_reqheight()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - w - 16
        y  = sh - h - 56        # 56 ≈ taskbar height + small gap
        root.geometry(f"{w}x{h}+{x}+{y}")

        # Close when focus leaves the window
        root.bind("<FocusOut>", lambda e: root.destroy() if root.winfo_exists() else None)
        root.focus_force()

        root.mainloop()
        _popup_win = None   # cleared when window closes

    _popup_thread = threading.Thread(target=_run, daemon=True)
    _popup_thread.start()


# ── Server management ─────────────────────────────────────────────────────────

def start_server():
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        return
    _server_proc = subprocess.Popen(
        [sys.executable, str(MAIN_PY)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    print(f"[tray] Server started (PID {_server_proc.pid})")


def stop_server():
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
        print("[tray] Server stopped.")
    _server_proc = None


def server_running() -> bool:
    return _server_proc is not None and _server_proc.poll() is None


# ── ngrok tunnel ──────────────────────────────────────────────────────────────

def _ensure_ngrok() -> bool:
    if NGROK_EXE.exists():
        return True
    NGROK_EXE.parent.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request, zipfile
        from io import BytesIO
        print("[tray] Downloading ngrok...")
        with urllib.request.urlopen(NGROK_ZIP, timeout=60) as r:
            data = r.read()
        with zipfile.ZipFile(BytesIO(data)) as z:
            for name in z.namelist():
                if name.endswith("ngrok.exe") or name == "ngrok.exe":
                    with z.open(name) as src, open(NGROK_EXE, "wb") as dst:
                        dst.write(src.read())
                    break
        print("[tray] ngrok downloaded.")
        return NGROK_EXE.exists()
    except Exception as e:
        print(f"[tray] Failed to download ngrok: {e}")
        return False


def _read_ngrok_url() -> str:
    """Poll ngrok local API for the public URL."""
    import urllib.request, json
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=2) as r:
                data = json.loads(r.read())
            for t in data.get("tunnels", []):
                if t.get("proto") == "https":
                    return t["public_url"]
        except Exception:
            pass
        time.sleep(1)
    return ""


def start_tunnel(icon=None):
    global _tunnel_proc, _tunnel_url
    if _tunnel_proc and _tunnel_proc.poll() is None:
        _copy_to_clipboard(_tunnel_url)
        return

    if not _ensure_ngrok():
        if icon:
            icon.notify("Nu s-a putut descarca ngrok.", "Voice Intake")
        return

    domain = getattr(config, "NGROK_DOMAIN", "")
    token  = getattr(config, "NGROK_TOKEN",  "")
    cmd = [str(NGROK_EXE), "http", str(config.PORT)]
    if token:
        cmd += ["--authtoken", token]
    if domain:
        cmd += ["--url", domain]
        _tunnel_url = f"https://{domain}"
        print(f"[tray] Starting permanent ngrok tunnel: {_tunnel_url}")
    else:
        print("[tray] Starting ngrok (no domain — run setup_tunnel.bat for permanent URL)...")

    _session_ts  = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    _ngrok_dir   = ROOT / "logs" / "ngrok"
    _ngrok_dir.mkdir(parents=True, exist_ok=True)
    ngrok_log    = _ngrok_dir / f"ngrok_{_session_ts}.log"
    # Prune old ngrok logs — keep last 10
    _old_logs = sorted(_ngrok_dir.glob("ngrok_*.log"), key=lambda p: p.stat().st_mtime)
    for _old in _old_logs[:-10]:
        try: _old.unlink()
        except OSError: pass
    _ngrok_log_f = open(ngrok_log, "w", encoding="utf-8")
    _tunnel_proc = subprocess.Popen(
        cmd,
        stdout=_ngrok_log_f,
        stderr=_ngrok_log_f,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    def _notify():
        global _tunnel_url
        time.sleep(3)
        if not (_tunnel_proc and _tunnel_proc.poll() is None):
            if icon:
                icon.notify("Tunelul nu a putut porni.\nVerificati logs\\ngrok\\", "Voice Intake")
            return
        url = _tunnel_url or _read_ngrok_url()
        if url:
            _tunnel_url = url
            _copy_to_clipboard(url)
            if icon:
                icon.notify(f"Tunel activ!\n{url}\n(copiat in clipboard)", "Voice Intake")
                _update_menu(icon)

    threading.Thread(target=_notify, daemon=True).start()


def stop_tunnel():
    global _tunnel_proc, _tunnel_url
    if _tunnel_proc and _tunnel_proc.poll() is None:
        _tunnel_proc.terminate()
        try:
            _tunnel_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _tunnel_proc.kill()
    _tunnel_proc = None
    _tunnel_url  = ""
    print("[tray] Tunnel stopped.")


def tunnel_running() -> bool:
    return _tunnel_proc is not None and _tunnel_proc.poll() is None


# ── Tray menu ─────────────────────────────────────────────────────────────────

def _update_menu(icon):
    icon.menu = _build_menu(icon)


def _build_menu(icon):
    ip   = _local_ip()
    url  = f"http://{ip}:{config.PORT}"
    code = config.MACHINE_CODE

    items = [
        # Default action on double-click — opens the popup
        pystray.MenuItem(
            "Status", lambda icon, item: _show_popup(),
            default=True, visible=False
        ),
        pystray.MenuItem(
            f"Voice Intake v0.0.2.5  |  {ip}:{config.PORT}",
            None, enabled=False
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Deschide in browser", lambda: webbrowser.open(url)),
        pystray.MenuItem(
            f"Cod acces: {code}  (click = copiere)",
            lambda: _copy_to_clipboard(code)
        ),
        pystray.Menu.SEPARATOR,
    ]

    if tunnel_running() and _tunnel_url:
        tunnel_kind = "permanent" if getattr(config, "NGROK_DOMAIN", "") else "temporar"
        items += [
            pystray.MenuItem(
                f"Tunel {tunnel_kind}: {_tunnel_url}",
                lambda: _copy_to_clipboard(_tunnel_url)
            ),
            pystray.MenuItem(
                "Opreste tunel",
                lambda icon=icon: (stop_tunnel(), _update_menu(icon))
            ),
        ]
    else:
        if getattr(config, "NGROK_DOMAIN", ""):
            tunnel_btn = f"Porneste tunel permanent (ngrok)"
        else:
            tunnel_btn = "Porneste tunel (ngrok - rulati setup_tunnel.bat pentru URL permanent)"
        items.append(pystray.MenuItem(
            tunnel_btn,
            lambda icon=icon: threading.Thread(
                target=start_tunnel, args=(icon,), daemon=True
            ).start()
        ))

    items += [
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Reporneste server",
            lambda: (stop_server(), time.sleep(1), start_server())
        ),
        pystray.MenuItem(
            "Opreste tot si inchide",
            lambda icon=icon: _shutdown(icon)
        ),
    ]

    return pystray.Menu(*items)


def _shutdown(icon):
    stop_tunnel()
    stop_server()
    icon.stop()


# ── Watchdog ──────────────────────────────────────────────────────────────────

def _watchdog():
    while True:
        time.sleep(10)
        if _tray_icon and not server_running():
            print("[tray] Server died — restarting...")
            start_server()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global _tray_icon

    ip   = _local_ip()
    code = config.MACHINE_CODE

    print(f"[tray] Voice Intake v0.0.2.5 starting...")
    print(f"[tray] Machine code: {code}")
    print(f"[tray] Local URL:    http://{ip}:{config.PORT}")

    start_server()
    time.sleep(1)

    icon_img = _make_icon("#238636")

    _tray_icon = pystray.Icon(
        name  = "VoiceIntake",
        icon  = icon_img,
        # Hover tooltip — shows on mouse-over in system tray
        title = f"Voice Intake  |  {ip}:{config.PORT}  |  Cod: {code}",
    )
    _tray_icon.menu = _build_menu(_tray_icon)

    threading.Thread(target=_watchdog, daemon=True).start()

    print("[tray] Tray icon running.")
    print("[tray]   Hover = tooltip with IP + code")
    print("[tray]   Double-click = status popup")
    print("[tray]   Right-click = full menu")
    _tray_icon.run()

    stop_tunnel()
    stop_server()


if __name__ == "__main__":
    main()
