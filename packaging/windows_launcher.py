"""Entry point dell'eseguibile Windows (PyInstaller).

- Dati utente in %APPDATA%\\Forager (mai dentro la cartella del programma):
  va impostato PRIMA di importare config/db, che leggono FORAGER_DATA_DIR al load.
- Trova una porta libera, avvia Flask e apre il browser.
"""
import os
import socket
import sys
import threading
import webbrowser

if getattr(sys, "frozen", False):
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    data_dir = os.path.join(appdata, "Forager")
    os.makedirs(data_dir, exist_ok=True)
    os.environ.setdefault("FORAGER_DATA_DIR", data_dir)
    # il sorgente impacchettato vive in _MEIPASS/onedir accanto all'exe
    base = os.path.dirname(sys.executable)
    internal = os.path.join(base, "_internal")
    os.chdir(internal if os.path.isdir(internal) else base)

import config  # noqa: E402  (legge FORAGER_DATA_DIR appena impostata)
import db      # noqa: E402


def _free_port(preferred: int) -> int:
    for port in (preferred, 5001, 5050, 8765, 0):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
        except OSError:
            continue
    return preferred


def main() -> None:
    db.init_db()
    from app import app  # import dopo init ambiente

    port = _free_port(config.PORT)
    url = f"http://127.0.0.1:{port}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\n  Forager CRM ready -> {url}\n", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
