"""Generatore di avatar SVG deterministici per prospect.

Stessa persona → sempre stessa palette + iniziali. Stile editoriale:
- Individuali: cerchio con gradient sottile + iniziali bold + arco decorativo
- Corporate: rounded square con gradient + iniziali + linee orizzontali
"""
from __future__ import annotations
import hashlib
import re
import unicodedata


# Palette curate — scelte dal hash del nome
PALETTES = [
    {"bg1": "#fef3c7", "bg2": "#fde68a", "fg": "#78350f", "accent": "#f59e0b"},   # amber
    {"bg1": "#dbeafe", "bg2": "#bfdbfe", "fg": "#1e3a8a", "accent": "#3b82f6"},   # blue
    {"bg1": "#dcfce7", "bg2": "#bbf7d0", "fg": "#14532d", "accent": "#22c55e"},   # green
    {"bg1": "#fce7f3", "bg2": "#fbcfe8", "fg": "#831843", "accent": "#ec4899"},   # pink
    {"bg1": "#e0e7ff", "bg2": "#c7d2fe", "fg": "#312e81", "accent": "#6366f1"},   # indigo
    {"bg1": "#ccfbf1", "bg2": "#99f6e4", "fg": "#134e4a", "accent": "#14b8a6"},   # teal
    {"bg1": "#fee2e2", "bg2": "#fecaca", "fg": "#7f1d1d", "accent": "#ef4444"},   # red
    {"bg1": "#ede9fe", "bg2": "#ddd6fe", "fg": "#4c1d95", "accent": "#8b5cf6"},   # purple
    {"bg1": "#fef9c3", "bg2": "#fef08a", "fg": "#713f12", "accent": "#eab308"},   # yellow
    {"bg1": "#cffafe", "bg2": "#a5f3fc", "fg": "#164e63", "accent": "#06b6d4"},   # cyan
    {"bg1": "#ffedd5", "bg2": "#fed7aa", "fg": "#7c2d12", "accent": "#f97316"},   # orange
    {"bg1": "#ecfccb", "bg2": "#d9f99d", "fg": "#365314", "accent": "#84cc16"},   # lime
    {"bg1": "#f1f5f9", "bg2": "#e2e8f0", "fg": "#0f172a", "accent": "#475569"},   # slate (sobria)
    {"bg1": "#fdf2f8", "bg2": "#fbcfe8", "fg": "#500724", "accent": "#db2777"},   # fuchsia
    {"bg1": "#fef3c7", "bg2": "#fcd34d", "fg": "#451a03", "accent": "#d97706"},   # gold deep
    {"bg1": "#e0f2fe", "bg2": "#bae6fd", "fg": "#0c4a6e", "accent": "#0284c7"},   # sky
]


def _normalize(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def _initials(name: str, corporate: bool) -> str:
    n = _normalize(name or "").strip()
    if not n:
        return "?"
    # rimuovi forme societarie comuni per corporate
    if corporate:
        n = re.sub(r"\b(spa|srl|sas|snc|s\.r\.l\.|s\.p\.a\.|sa|ag|gmbh|ltd|inc|co|llc|plc|nv|bv|holding|group|company|corporation|corp)\b\.?", "", n, flags=re.IGNORECASE)
        n = re.sub(r"\s+", " ", n).strip()
    parts = [p for p in re.split(r"\s+", n) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _palette_for(name: str) -> dict:
    h = hashlib.md5((name or "?").encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(PALETTES)
    return PALETTES[idx]


def _seed_int(name: str, offset: int = 0) -> int:
    h = hashlib.md5(((name or "?") + str(offset)).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def generate_svg(name: str, ptype: str = "individual", size: int = 256) -> str:
    """Genera un SVG (str) deterministico per il prospect."""
    corporate = (ptype == "corporate")
    foundation = (ptype == "foundation")
    org = corporate or foundation
    initials = _initials(name, org)
    pal = _palette_for(name or "?")
    bg1, bg2, fg, accent = pal["bg1"], pal["bg2"], pal["fg"], pal["accent"]
    gid = "g" + hashlib.md5((name or "?").encode()).hexdigest()[:8]

    # font-size: 1 letter più grande, 2 letter più piccolo
    font_size = 130 if len(initials) <= 1 else 108
    # spostamento verticale per centrare baseline
    text_y = 170 if len(initials) <= 1 else 165

    if foundation:
        # Rounded square + "colonne" (motivo istituzionale) che evoca una fondazione
        s = _seed_int(name, 3)
        n_cols = 3 + (s % 2)  # 3 o 4 colonne
        col_w, gap = 16, 14
        total = n_cols * col_w + (n_cols - 1) * gap
        start_x = 128 - total / 2
        cols = "".join(
            f'<rect x="{start_x + i*(col_w+gap):.0f}" y="196" width="{col_w}" height="26" rx="2" fill="{accent}" fill-opacity="0.22"/>'
            for i in range(n_cols)
        )
        body = f'''
  <rect width="256" height="256" rx="40" fill="url(#{gid})"/>
  <!-- architrave + colonne -->
  <rect x="{start_x-6:.0f}" y="188" width="{total+12:.0f}" height="5" rx="2" fill="{accent}" fill-opacity="0.30"/>
  {cols}
  <text x="128" y="{text_y - 14}" font-family="Inter, system-ui, sans-serif" font-size="{font_size}" font-weight="800" fill="{fg}" text-anchor="middle" letter-spacing="-4">{initials}</text>
'''
    elif corporate:
        # Rounded square + linee orizzontali decorative
        ang_x1, ang_y1 = 40, 36
        ang_x2, ang_y2 = 220, 36
        # variazione: una serie di linee sottili in basso seedate
        s = _seed_int(name, 1)
        line_y_base = 200 + (s % 14) - 7
        body = f'''
  <rect width="256" height="256" rx="40" fill="url(#{gid})"/>
  <!-- linee architetturali -->
  <line x1="{ang_x1}" y1="{line_y_base}" x2="{ang_x2}" y2="{line_y_base}" stroke="{accent}" stroke-width="3" stroke-opacity="0.22"/>
  <line x1="{ang_x1}" y1="{line_y_base+12}" x2="{ang_x1+120}" y2="{line_y_base+12}" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.14"/>
  <circle cx="222" cy="34" r="6" fill="{accent}" fill-opacity="0.35"/>
  <text x="128" y="{text_y}" font-family="Inter, system-ui, sans-serif" font-size="{font_size}" font-weight="800" fill="{fg}" text-anchor="middle" letter-spacing="-4">{initials}</text>
'''
    else:
        # Cerchio + arco decorativo che richiama "ricerca"
        s = _seed_int(name, 2)
        arc_offset_deg = s % 360
        body = f'''
  <circle cx="128" cy="128" r="128" fill="url(#{gid})"/>
  <!-- arco "research" decorativo, rotato seedato -->
  <g transform="rotate({arc_offset_deg} 128 128)">
    <path d="M 30 128 A 98 98 0 0 1 226 128" fill="none" stroke="{accent}" stroke-width="3" stroke-opacity="0.25" stroke-linecap="round" stroke-dasharray="2 10"/>
  </g>
  <text x="128" y="{text_y}" font-family="Inter, system-ui, sans-serif" font-size="{font_size}" font-weight="800" fill="{fg}" text-anchor="middle" letter-spacing="-5">{initials}</text>
'''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="{size}" height="{size}" role="img" aria-label="{(_normalize(name) or '?')}">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="{ '1' if org else '0' }" y2="1">
      <stop offset="0" stop-color="{bg1}"/>
      <stop offset="1" stop-color="{bg2}"/>
    </linearGradient>
  </defs>{body}</svg>'''
    return svg
