#!/usr/bin/env python3
"""Crea il DMG "bello": finestra con sfondo grafico dark + freccia gialla,
icone posizionate, niente barre, icona del volume brandizzata.

Riusa packaging/build/Forager.app (già costruita da build_macapp.py).
Dipendenze in un venv di build dedicato: Pillow, fonttools, brotli, dmgbuild.

Uso: python3 packaging/build_dmg_fancy.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
SRC_DIR = PKG_DIR.parent
REPO_DIR = SRC_DIR.parent
BUILD_DIR = PKG_DIR / "build"
VENV = PKG_DIR / ".cache" / "buildvenv"
APP_BUNDLE = BUILD_DIR / "Forager.app"
ICNS = APP_BUNDLE / "Contents" / "Resources" / "Forager.icns"
APP_NAME = "Forager"


def log(m): print(f"\033[36m→\033[0m {m}", flush=True)
def ok(m): print(f"\033[32m✓\033[0m {m}", flush=True)


def read_version() -> str:
    for line in (SRC_DIR / "config.py").read_text().splitlines():
        if line.strip().startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "1.0.0"


def ensure_venv() -> Path:
    py = VENV / "bin" / "python"
    if not py.exists():
        log("Creo il venv di build …")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    log("Installo gli strumenti di packaging (Pillow, fonttools, dmgbuild) …")
    pip = VENV / "bin" / "pip"
    subprocess.run([str(pip), "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run([str(pip), "install", "-q", "Pillow", "fonttools", "brotli", "dmgbuild"], check=True)
    return py


def make_background(py: Path) -> Path:
    log("Genero lo sfondo della finestra …")
    subprocess.run([str(py), str(PKG_DIR / "_make_dmg_bg.py"), str(SRC_DIR), str(BUILD_DIR)], check=True)
    bg1 = BUILD_DIR / "dmg-bg.png"
    bg2 = BUILD_DIR / "dmg-bg@2x.png"
    tiff = BUILD_DIR / "dmg-bg.tiff"
    # TIFF multi-risoluzione: nitido anche su display Retina
    subprocess.run(["tiffutil", "-cathidpicheck", str(bg1), str(bg2), "-out", str(tiff)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok("Sfondo retina pronto")
    return tiff


SETTINGS_TMPL = '''# generato da build_dmg_fancy.py
app_path = {app!r}
background = {bg!r}
volume_icon = {icns!r}

format = "UDZO"
size = None
files = [app_path]
symlinks = {{"Applications": "/Applications"}}
icon = volume_icon

default_view = "icon-view"
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
arrange_by = None

window_rect = ((360, 180), (640, 440))
icon_size = 128
text_size = 13

icon_locations = {{
    "Forager.app": (160, 238),
    "Applications": (480, 238),
}}
hide_extension = ["Forager.app"]
'''


def build(py: Path, tiff: Path, version: str) -> Path:
    settings = BUILD_DIR / "dmg_settings.py"
    settings.write_text(SETTINGS_TMPL.format(app=str(APP_BUNDLE), bg=str(tiff), icns=str(ICNS)))
    out = REPO_DIR / f"{APP_NAME}-{version}.dmg"
    if out.exists():
        out.unlink()
    log("Assemblo il DMG con dmgbuild …")
    dmgbuild = VENV / "bin" / "dmgbuild"
    subprocess.run([str(dmgbuild), "-s", str(settings), APP_NAME, str(out)], check=True)
    set_file_icon(out, ICNS)
    return out


def set_file_icon(target: Path, icns: Path) -> None:
    """Assegna l'icona brandizzata al FILE .dmg (NSWorkspace.setIcon via JXA, no Xcode)."""
    js = (
        "ObjC.import('AppKit');"
        f"var img = $.NSImage.alloc.initWithContentsOfFile({json.dumps(str(icns))});"
        f"var ok = $.NSWorkspace.sharedWorkspace.setIconForFileOptions(img, {json.dumps(str(target))}, 0);"
        "ok ? 'ok' : 'fail';"
    )
    try:
        subprocess.run(["osascript", "-l", "JavaScript", "-e", js], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ok("Icona assegnata al file .dmg")
    except subprocess.CalledProcessError:
        pass


def main():
    if not APP_BUNDLE.exists():
        raise SystemExit("Forager.app non trovata: lancia prima build_macapp.py")
    version = read_version()
    py = ensure_venv()
    tiff = make_background(py)
    out = build(py, tiff, version)
    size_mb = subprocess.check_output(["du", "-sm", str(out)], text=True).split()[0]
    print()
    ok(f"DMG creato: {out}  ({size_mb} MB)")


if __name__ == "__main__":
    main()
