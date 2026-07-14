"""Local configuration. Tutto sovrascrivibile via env vars o file .env (auto-caricato)."""
import os
from pathlib import Path

# ---------- .env loader (no extra deps) ----------
def _load_dotenv():
    # .env nella cartella dati scrivibile (config utente) ha priorità, poi quello
    # accanto al codice (default del pacchetto). setdefault: il primo letto vince.
    candidates = []
    data_dir = os.getenv("FORAGER_DATA_DIR")
    if data_dir:
        candidates.append(Path(data_dir) / ".env")
    candidates.append(Path(__file__).parent / ".env")
    for env_file in candidates:
        if not env_file.exists():
            continue
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            # strip inline comments (only if not inside quotes)
            if value and not (value.lstrip().startswith(("'", '"'))):
                if "#" in value:
                    value = value.split("#", 1)[0]
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

_load_dotenv()

__version__ = "1.1.0"


# ---------- Flask ----------
def _ensure_secret_key() -> str:
    """SECRET_KEY da env, altrimenti generata al primo avvio e persistita in data/."""
    env_key = os.getenv("FORAGER_SECRET_KEY", "").strip()
    if env_key:
        return env_key
    key_file = Path(os.getenv("FORAGER_DATA_DIR") or Path(__file__).parent) / "data" / ".secret_key"
    try:
        if key_file.exists():
            stored = key_file.read_text(encoding="utf-8").strip()
            if stored:
                return stored
        import secrets
        key = secrets.token_hex(32)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(key, encoding="utf-8")
        try:
            key_file.chmod(0o600)
        except OSError:
            pass
        return key
    except OSError:
        import secrets
        return secrets.token_hex(32)

SECRET_KEY = _ensure_secret_key()
HOST = os.getenv("FORAGER_HOST", "127.0.0.1")
PORT = int(os.getenv("FORAGER_PORT", "5000"))
# Default SPENTO: con debug attivo, un'eccezione apre la console Werkzeug
# (esecuzione codice arbitrario). Attivalo solo in sviluppo: FORAGER_DEBUG=1
DEBUG = os.getenv("FORAGER_DEBUG", "0") == "1"


# ---------- Hunter.io (OPZIONALE) ----------
# Lasciare vuoto se non si usa Hunter. La funzione "Trova decision maker" mostrerà
# un messaggio chiaro invece di chiamare l'API.
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "").strip()
HUNTER_CACHE_DAYS = int(os.getenv("HUNTER_CACHE_DAYS", "30"))
HUNTER_SENIORITY = os.getenv("HUNTER_SENIORITY", "executive")
HUNTER_MAX_PER_DOMAIN = int(os.getenv("HUNTER_MAX_PER_DOMAIN", "25"))


# ---------- Motore AI ----------
# Quale CLI usare come motore: "claude" (Claude Code, default) o "codex" (OpenAI Codex CLI).
# Entrambi girano in locale con il rispettivo abbonamento — nessuna API key in Forager.
AI_ENGINE = (os.getenv("FORAGER_AI_ENGINE", "claude").strip().lower() or "claude")
if AI_ENGINE not in ("claude", "codex"):
    AI_ENGINE = "claude"

# Path al binary `claude`. Auto-detect se vuoto.
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "").strip()

# Path al binary `codex`. Auto-detect se vuoto.
CODEX_BIN = os.getenv("CODEX_BIN", "").strip()
# Modello per Codex (vuoto = default del CLI). Es: gpt-5-codex
CODEX_MODEL = os.getenv("CODEX_MODEL", "").strip()


# ---------- Diagnostica ----------
def status() -> dict:
    import shutil
    return {
        "version": __version__,
        "secret_set": bool(SECRET_KEY),
        "hunter_set": bool(HUNTER_API_KEY),
        "ai_engine": AI_ENGINE,
        "claude_bin": shutil.which(CLAUDE_BIN or "claude"),
        "codex_bin": shutil.which(CODEX_BIN or "codex"),
        "host": HOST,
        "port": PORT,
    }
