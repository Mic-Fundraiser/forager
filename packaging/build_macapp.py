#!/usr/bin/env python3
"""Costruisce Forager.app (autonoma, Python incluso) e il DMG di installazione.

Uso:
    python3 packaging/build_macapp.py

Output:
    packaging/build/Forager.app
    <repo>/Forager-<versione>.dmg   (cartella superiore al sorgente)

Cosa fa, in ordine:
 1. Scarica (e mette in cache) un CPython relocabile (python-build-standalone).
 2. Crea lo scheletro del bundle .app e ci copia il sorgente (senza dati utente).
 3. Installa le dipendenze (requirements.txt) nel Python del bundle.
 4. Genera l'icona .icns dal marchio dell'app (lente su quadrato nero).
 5. Impacchetta le librerie native di WeasyPrint (pango/cairo/glib + transitivi)
    così l'export PDF funziona anche su Mac senza Homebrew (best-effort).
 6. Firma ad-hoc le librerie modificate e l'app.
 7. Crea il DMG drag-to-Applications.

Richiede macOS arm64 (Apple Silicon), connessione a internet per la prima build.
"""
from __future__ import annotations

import os
import plistlib
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

# ----------------------------------------------------------------------------
# Percorsi e costanti
# ----------------------------------------------------------------------------
PKG_DIR = Path(__file__).resolve().parent          # .../osint_crm/packaging
SRC_DIR = PKG_DIR.parent                            # .../osint_crm  (sorgente app)
REPO_DIR = SRC_DIR.parent                           # cartella superiore (output DMG)
BUILD_DIR = PKG_DIR / "build"
CACHE_DIR = PKG_DIR / ".cache"
APP_NAME = "Forager"
APP_BUNDLE = BUILD_DIR / f"{APP_NAME}.app"
BUNDLE_ID = "com.fundraisinglab.forager"
PORT = "7421"                                       # porta locale fissa (evita 5000 = AirPlay)

# Python relocabile (arm64, install_only)
PY_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    "20260610/cpython-3.12.13%2B20260610-aarch64-apple-darwin-install_only.tar.gz"
)
PY_TARBALL = CACHE_DIR / "cpython-3.12-aarch64-install_only.tar.gz"

# Sorgenti delle librerie native (Homebrew) e librerie "seme" per WeasyPrint
BREW_LIB_DIRS = ["/opt/homebrew/lib", "/usr/local/lib"]
WEASY_SEEDS = [
    "libgobject-2.0.0.dylib", "libglib-2.0.0.dylib", "libgio-2.0.0.dylib",
    "libpango-1.0.0.dylib", "libpangocairo-1.0.0.dylib", "libpangoft2-1.0.0.dylib",
    "libcairo.2.dylib", "libfontconfig.1.dylib", "libfreetype.6.dylib",
    "libharfbuzz.0.dylib", "libgdk_pixbuf-2.0.0.dylib", "libfribidi.0.dylib",
]

EXCLUDES = {
    ".venv", "__pycache__", ".git", ".pytest_cache", "data", "backups",
    ".env", ".DS_Store", "node_modules", "packaging", "tests", ".github",
}


# ----------------------------------------------------------------------------
# Helper
# ----------------------------------------------------------------------------
def log(msg: str) -> None:
    print(f"\033[36m→\033[0m {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"\033[32m✓\033[0m {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"\033[33m⚠\033[0m {msg}", flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def read_version() -> str:
    for line in (SRC_DIR / "config.py").read_text().splitlines():
        if line.strip().startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "1.0.0"


# ----------------------------------------------------------------------------
# 1. Python relocabile
# ----------------------------------------------------------------------------
def fetch_python(resources: Path) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not PY_TARBALL.exists():
        log(f"Scarico Python standalone ({PY_URL.rsplit('/', 1)[-1]}) …")
        urllib.request.urlretrieve(PY_URL, PY_TARBALL)
    ok(f"Python tarball pronto ({PY_TARBALL.stat().st_size // 1_000_000} MB)")

    py_dest = resources / "python"
    if py_dest.exists():
        shutil.rmtree(py_dest)
    log("Estraggo Python nel bundle …")
    run(["tar", "-xzf", str(PY_TARBALL), "-C", str(resources)])
    # il tarball estrae in 'python/'
    pybin = py_dest / "bin" / "python3"
    if not pybin.exists():
        raise SystemExit(f"python3 non trovato in {pybin}")
    ok("Python estratto nel bundle")
    return pybin


# ----------------------------------------------------------------------------
# 2. Scheletro bundle + sorgente
# ----------------------------------------------------------------------------
def _ignore(_dir, names):
    return [n for n in names if n in EXCLUDES or n.endswith(".pyc")]


def make_skeleton() -> tuple[Path, Path]:
    if APP_BUNDLE.exists():
        shutil.rmtree(APP_BUNDLE)
    contents = APP_BUNDLE / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    log("Copio il sorgente dell'app nel bundle …")
    shutil.copytree(SRC_DIR, resources / "app", ignore=_ignore)
    ok("Sorgente copiato (senza dati utente, .env, .venv)")
    return contents, resources


# ----------------------------------------------------------------------------
# 3. Dipendenze Python nel bundle
# ----------------------------------------------------------------------------
def install_deps(pybin: Path) -> None:
    log("Aggiorno pip nel bundle …")
    run([str(pybin), "-m", "pip", "install", "-q", "--upgrade", "pip"])
    log("Installo le dipendenze (Flask, WeasyPrint, …) — può richiedere 1-2 min …")
    run([str(pybin), "-m", "pip", "install", "-q", "-r", str(SRC_DIR / "requirements.txt")])
    ok("Dipendenze installate nel Python del bundle")


# ----------------------------------------------------------------------------
# 4. Icona .icns (marchio: lente su quadrato nero #18181b)
# ----------------------------------------------------------------------------
ICON_SCRIPT = r'''
import sys
from PIL import Image, ImageDraw
S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# quadrato nero arrotondato (favicon: rx=8 su 32 -> 0.25)
r = int(S * 0.235)
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=(24, 24, 27, 255))
# lente: cerchio (cx=13 cy=13 r=5 su 32) + manico (17,17)->(23,23)
k = S / 32.0
cx, cy, rr = 13 * k, 13 * k, 5 * k
sw = max(2, int(2.6 * k))
d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, 255), width=sw)
d.line([17 * k, 17 * k, 23 * k, 23 * k], fill=(255, 255, 255, 255), width=sw)
# tondi sulle estremita' del manico per il cap "round"
hr = sw / 2.0
for (px, py) in [(17 * k, 17 * k), (23 * k, 23 * k)]:
    d.ellipse([px - hr, py - hr, px + hr, py + hr], fill=(255, 255, 255, 255))
img.save(sys.argv[1])
'''


def make_icon(pybin: Path, resources: Path) -> None:
    log("Genero l'icona dell'app …")
    master = BUILD_DIR / "icon_1024.png"
    run([str(pybin), "-c", ICON_SCRIPT, str(master)])
    iconset = BUILD_DIR / f"{APP_NAME}.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    sizes = [16, 32, 128, 256, 512]
    for s in sizes:
        for scale, suffix in ((1, ""), (2, "@2x")):
            px = s * scale
            out = iconset / f"icon_{s}x{s}{suffix}.png"
            run(["sips", "-z", str(px), str(px), str(master), "--out", str(out)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(["iconutil", "-c", "icns", str(iconset), "-o", str(resources / f"{APP_NAME}.icns")])
    ok("Icona .icns generata")


# ----------------------------------------------------------------------------
# 5. Librerie native WeasyPrint (best-effort)
# ----------------------------------------------------------------------------
def _otool_deps(path: Path) -> list[str]:
    out = subprocess.check_output(["otool", "-L", str(path)], text=True)
    deps = []
    for ln in out.splitlines()[1:]:                 # salta riga header col nome file
        ln = ln.strip()
        if not ln:
            continue
        deps.append(ln.split(" (")[0].strip())
    return deps


def _find_lib(leaf: str) -> Path | None:
    for d in BREW_LIB_DIRS:
        p = Path(d) / leaf
        if p.exists():
            return p
    return None


def bundle_dylibs(resources: Path) -> bool:
    libs = resources / "libs"
    if libs.exists():
        shutil.rmtree(libs)
    libs.mkdir(parents=True)

    seeds = [p for leaf in WEASY_SEEDS if (p := _find_lib(leaf))]
    if not seeds:
        warn("Librerie native (Homebrew pango/cairo) non trovate: "
             "l'export PDF userà il fallback 'stampa da browser'.")
        shutil.rmtree(libs)
        return False

    log("Raccolgo le librerie native di WeasyPrint (chiusura transitiva) …")
    copied: dict[str, Path] = {}                     # leaf -> path nel bundle
    queue = list(seeds)
    while queue:
        src = queue.pop()
        leaf = src.name
        if leaf in copied:
            continue
        dst = libs / leaf
        shutil.copy2(src.resolve(), dst)             # copia il file reale, nome = leaf
        os.chmod(dst, 0o644)
        copied[leaf] = dst
        for dep in _otool_deps(src):
            if dep.startswith("/usr/lib") or dep.startswith("/System"):
                continue                              # libreria di sistema: la lascio
            dep_leaf = Path(dep).name
            if dep_leaf in copied:
                continue
            sp = Path(dep) if (dep.startswith("/") and Path(dep).exists()) else _find_lib(dep_leaf)
            if sp:
                queue.append(sp)

    # riscrivo gli install name su @loader_path e firmo ad-hoc
    for leaf, dst in copied.items():
        run(["install_name_tool", "-id", f"@loader_path/{leaf}", str(dst)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for dep in _otool_deps(dst):
            dep_leaf = Path(dep).name
            if dep_leaf in copied and dep != f"@loader_path/{dep_leaf}":
                run(["install_name_tool", "-change", dep, f"@loader_path/{dep_leaf}", str(dst)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run(["codesign", "--force", "--sign", "-", str(dst)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ricreo gli alias-symlink di Homebrew (es. libpango-1.0.dylib -> ...-1.0.0.dylib)
    # cosi i nomi richiesti da WeasyPrint via dlopen risolvono nella cartella libs.
    for d in BREW_LIB_DIRS:
        bd = Path(d)
        if not bd.is_dir():
            continue
        for entry in bd.iterdir():
            try:
                if not entry.is_symlink():
                    continue
                real_leaf = entry.resolve().name
                if real_leaf in copied and entry.name not in copied:
                    link = libs / entry.name
                    if not link.exists():
                        link.symlink_to(real_leaf)
            except OSError:
                continue

    ok(f"Impacchettate {len(copied)} librerie native + alias")
    return True


# ----------------------------------------------------------------------------
# 6. Info.plist + launcher nativo (Swift WKWebView)
# ----------------------------------------------------------------------------
def compile_launcher(contents: Path) -> None:
    """Compila il guscio nativo Swift in Contents/MacOS/Forager.

    Il binario avvia il server Python in background e mostra l'app in una
    finestra nativa WKWebView (niente browser).
    """
    src = PKG_DIR / "ForagerLauncher.swift"
    out = contents / "MacOS" / APP_NAME
    log("Compilo il guscio nativo Swift (finestra WKWebView) …")
    run(["swiftc", "-swift-version", "5", "-O", "-o", str(out), str(src),
         "-framework", "Cocoa", "-framework", "WebKit"])
    out.chmod(out.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    ok("Guscio nativo compilato")


def write_plist(contents: Path, version: str) -> None:
    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": f"{APP_NAME}.icns",
        "CFBundlePackageType": "APPL",
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHighResolutionCapable": True,
        # WKWebView deve poter caricare http://127.0.0.1 (server locale)
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
        "NSHumanReadableCopyright": "© 2026 Michelangelo Gigli · Open Source · info@michelangelogigli.it",
        "LSEnvironment": {"LANG": "it_IT.UTF-8"},
    }
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    ok("Info.plist scritto")


# ----------------------------------------------------------------------------
# 7. Firma + DMG
# ----------------------------------------------------------------------------
def sign_app() -> None:
    log("Firma ad-hoc del bundle …")
    try:
        run(["codesign", "--force", "--deep", "--sign", "-", str(APP_BUNDLE)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ok("App firmata (ad-hoc)")
    except subprocess.CalledProcessError:
        warn("Firma --deep fallita (le librerie native sono comunque già firmate).")


def build_dmg(version: str) -> Path:
    stage = BUILD_DIR / "dmg_root"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    log("Preparo il contenuto del DMG …")
    run(["cp", "-R", str(APP_BUNDLE), str(stage / f"{APP_NAME}.app")])
    (stage / "Applications").symlink_to("/Applications")

    dmg = REPO_DIR / f"{APP_NAME}-{version}.dmg"
    if dmg.exists():
        dmg.unlink()
    log("Creo il DMG compresso …")
    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", str(stage),
         "-ov", "-format", "UDZO", str(dmg)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dmg


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("Questo build gira solo su macOS.")
    version = read_version()
    print(f"\n  Build di {APP_NAME}.app v{version}\n")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    contents, resources = make_skeleton()
    pybin = fetch_python(resources)
    install_deps(pybin)
    make_icon(pybin, resources)
    bundle_dylibs(resources)
    compile_launcher(contents)
    write_plist(contents, version)
    sign_app()

    # DMG grafico (sfondo dark + freccia gialla). Fallback al DMG semplice.
    try:
        import build_dmg_fancy as fancy
        buildpy = fancy.ensure_venv()
        tiff = fancy.make_background(buildpy)
        dmg = fancy.build(buildpy, tiff, version)
    except Exception as e:
        warn(f"DMG grafico non riuscito ({e}); creo il DMG semplice.")
        dmg = build_dmg(version)

    size_mb = subprocess.check_output(["du", "-sm", str(dmg)], text=True).split()[0]
    print()
    ok(f"DMG creato: {dmg}  ({size_mb} MB)")
    print(f"\n  Apri il DMG, trascina {APP_NAME} in Applicazioni, poi doppio click.\n")


if __name__ == "__main__":
    main()
