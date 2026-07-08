"""EUROPERSONAL — controler din system tray (Windows).

Pornire:  python launcher.py
Apare o iconiță în tray (lângă ceas). Click dreapta -> meniu.

Notă: PRIMA pornire după instalare durează 1-3 minute (antivirusul scanează
bibliotecile noi + Python își construiește cache-ul). Pornirile următoare
durează câteva secunde.
"""
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
APP_FILE = APP_DIR / "app.py"

try:
    from config import PORT, VERSION
except ImportError:
    PORT, VERSION = 8501, "1.0.0"

URL = f"http://localhost:{PORT}"

_proc = None  # procesul Streamlit


# ------------------------------------------------------------- control proces

def is_running() -> bool:
    return _proc is not None and _proc.poll() is None


def is_responding() -> bool:
    """Serverul chiar răspunde pe port? (pornit ≠ gata de utilizare)"""
    try:
        with socket.create_connection(("localhost", PORT), timeout=1):
            return True
    except OSError:
        return False


def start_app(command=None) -> bool:
    """Pornește Streamlit în fundal. Returnează True dacă a pornit acum."""
    global _proc
    if is_running():
        return False
    if command is None:
        command = [sys.executable, "-m", "streamlit", "run", str(APP_FILE),
                   "--server.port", str(PORT),
                   "--server.headless", "true",
                   "--server.fileWatcherType", "none",     # pornire mai rapidă
                   "--browser.gatherUsageStats", "false"]  # fără telemetrie
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # fără consolă pe Windows
    _proc = subprocess.Popen(command, cwd=str(APP_DIR), creationflags=flags)
    return True


def wait_until_up(timeout: float = 180) -> bool:
    """Așteaptă până serverul răspunde (sau până moare procesul)."""
    end = time.time() + timeout
    while time.time() < end:
        if is_responding():
            return True
        if not is_running():
            return False
        time.sleep(0.5)
    return False


def stop_app() -> bool:
    """Oprește serverul. Returnează True dacă era pornit."""
    global _proc
    if not is_running():
        return False
    _proc.terminate()
    try:
        _proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _proc.kill()
        _proc.wait(timeout=5)
    _proc = None
    return True


def status_text() -> str:
    if not is_running():
        return "Oprit ⛔"
    return "Pornit ✅" if is_responding() else "Pornește… ⏳"


# ------------------------------------------------------------- iconiță tray

def _make_image():
    """Iconiță simplă: cerc albastru cu 'E' alb."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=(13, 59, 102, 255))
    w = (255, 255, 255, 255)
    d.rectangle((20, 16, 26, 48), fill=w)
    d.rectangle((20, 16, 44, 22), fill=w)
    d.rectangle((20, 29, 40, 35), fill=w)
    d.rectangle((20, 42, 44, 48), fill=w)
    return img


def _notify(icon, msg):
    try:
        icon.notify(msg, "EUROPERSONAL")
    except Exception:
        pass


def main():
    import pystray
    from pystray import Menu, MenuItem as Item

    def _open_when_ready(icon):
        """Rulează în fundal: așteaptă serverul, apoi deschide browserul."""
        _notify(icon, "Serverul pornește… prima pornire poate dura 1-3 minute.")
        if wait_until_up():
            icon.update_menu()
            webbrowser.open(URL)
            _notify(icon, "Aplicația e gata! S-a deschis în browser.")
        else:
            icon.update_menu()
            _notify(icon, "Serverul NU a pornit. Rulați în consolă: streamlit run app.py")

    def on_start(icon, item):
        if start_app():
            threading.Thread(target=_open_when_ready, args=(icon,), daemon=True).start()
        icon.update_menu()

    def on_stop(icon, item):
        if stop_app():
            icon.update_menu()

    def on_open(icon, item):
        if is_responding():
            webbrowser.open(URL)
            return
        if not is_running():
            start_app()
        threading.Thread(target=_open_when_ready, args=(icon,), daemon=True).start()

    def on_info(icon, item):
        msg = (f"EUROPERSONAL — Documente IGM v{VERSION}\n"
               f"Status: {status_text()}\nAdresa: {URL}\nFolder: {APP_DIR}")
        try:
            icon.notify(msg, "EUROPERSONAL")
        except Exception:
            webbrowser.open(URL)

    def on_exit(icon, item):
        stop_app()
        icon.stop()

    menu = Menu(
        Item(lambda item: f"Status: {status_text()}", None, enabled=False),
        Menu.SEPARATOR,
        Item("▶ Start App", on_start, enabled=lambda item: not is_running()),
        Item("⏹ Stop App", on_stop, enabled=lambda item: is_running()),
        Item("🌐 Deschide în browser", on_open, default=True),
        Item("ℹ Info", on_info),
        Menu.SEPARATOR,
        Item("✖ Ieșire", on_exit),
    )
    icon = pystray.Icon("europersonal", _make_image(),
                        "EUROPERSONAL — Documente IGM", menu)

    def _on_ready(icon):
        icon.visible = True
        print("✅ Iconița e ACTIVĂ în tray (cerc albastru cu E).")
        print("   Dacă nu o vedeți, apăsați săgeata ^ de lângă ceas — e în zona ascunsă.")
        print("   Click dreapta pe iconiță -> Start App. Această fereastră rămâne deschisă cât timp rulează.")

    icon.run(setup=_on_ready)


if __name__ == "__main__":
    print(f"EUROPERSONAL — Documente IGM v{VERSION}")
    print("Pornesc iconița din tray... (câteva secunde)")
    from utils.storage import ensure_folders
    ensure_folders()
    try:
        main()
        print("Iconița a fost închisă. La revedere!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ EROARE la pornirea iconiței: {e}")
        print("Alternativă fără tray: rulați  streamlit run app.py")
        input("Apăsați Enter pentru a închide...")
