"""Export PDF di un prospect — render server-side via WeasyPrint.

Su macOS WeasyPrint richiede pango/cairo via Homebrew. Le env var DYLD_* devono
essere settate PRIMA che Python parta (altrimenti il loader non le legge e
write_pdf() può segfaultare).

Il launcher `forager start` setta DYLD_FALLBACK_LIBRARY_PATH per noi.
Quando l'env var non è disponibile e siamo su macOS, marchiamo WEASY_OK=False
e il caller usa il fallback "print via browser".
"""
import os
import sys

_BREW_LIBS = ("/opt/homebrew/lib", "/usr/local/lib")
# Marcatori: se una dir del DYLD path contiene queste librerie, è abilitante.
# Vale sia per Homebrew sia per le libs impacchettate dentro Forager.app.
_LIB_MARKERS = ("libgobject-2.0.dylib", "libgobject-2.0.0.dylib", "libpango-1.0.0.dylib")

def _macos_libs_ready() -> bool:
    """Su macOS verifica che DYLD_FALLBACK_LIBRARY_PATH punti a una dir con pango/glib."""
    if sys.platform != "darwin":
        return True
    for d in os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "").split(":"):
        if not d:
            continue
        try:
            if os.path.isdir(d) and any(os.path.exists(os.path.join(d, m)) for m in _LIB_MARKERS):
                return True
        except OSError:
            continue
    return False


WEASY_OK = False
WEASY_ERR = None

if sys.platform != "darwin" or _macos_libs_ready():
    try:
        from weasyprint import HTML  # type: ignore
        WEASY_OK = True
    except Exception as e:
        WEASY_ERR = f"WeasyPrint import error: {e}"
else:
    WEASY_ERR = "macOS: avvia con `./forager start` per abilitare l'export PDF server-side (DYLD_FALLBACK_LIBRARY_PATH non settato)."


def render_pdf(html_string: str, base_url: str | None = None) -> bytes | None:
    """Render HTML → PDF. None se WeasyPrint non è disponibile o crasha."""
    if not WEASY_OK:
        return None
    try:
        return HTML(string=html_string, base_url=base_url).write_pdf()
    except Exception:
        return None
