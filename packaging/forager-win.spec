# PyInstaller spec — eseguibile Windows (onedir).
# Build: pyinstaller packaging/forager-win.spec  (dalla root del repo)
import os

block_cipher = None
ROOT = os.getcwd()

a = Analysis(
    [os.path.join(ROOT, "packaging", "windows_launcher.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "templates"), "templates"),
        (os.path.join(ROOT, "static"), "static"),
        (os.path.join(ROOT, ".env.example"), "."),
    ],
    hiddenimports=["app", "db", "config", "ai_engine", "hunter", "i18n",
                   "prompts", "avatars", "pdf_export", "guide_content",
                   "translations_auto"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["weasyprint", "pydyf", "tkinter", "unittest", "pydoc"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Forager",
    icon=os.path.join(ROOT, "packaging", "forager.ico"),
    console=True,          # finestra console: log visibile, chiusura = stop server
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Forager",
)
