#!/usr/bin/env python3
"""Genera lo sfondo della finestra DMG (dark elegante + accento giallo).

Uso: python _make_dmg_bg.py <SRC_DIR> <OUT_DIR>
Produce: <OUT>/dmg-bg.png (1x) e <OUT>/dmg-bg@2x.png (retina).
Font: Inter del progetto (woff2 -> ttf via fontTools).
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from fontTools.ttLib import TTFont

SRC = sys.argv[1]
OUT = sys.argv[2]

W, H = 640, 440          # punti (logici)
S = 2                    # supersampling / retina
w, h = W * S, H * S

# ---- palette ----
YELLOW = (255, 209, 0)
WHITE = (244, 244, 246)
GRAY = (140, 140, 150)
DGRAY = (96, 96, 104)
BG_TOP = (18, 18, 22)
BG_BOT = (7, 7, 9)

# ---- icone (centri, in punti) — devono combaciare con icon_locations dmgbuild
APP_C = (160, 238)
DST_C = (480, 238)


def _inter(weight_path, sz):
    return ImageFont.truetype(weight_path, int(sz * S))


def load_inter():
    ttf = os.path.join(OUT, "_inter.ttf")
    f = TTFont(os.path.join(SRC, "static", "vendor", "fonts", "inter-400-latin.woff2"))
    f.flavor = None
    f.save(ttf)
    return ttf


def gradient_bg():
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        t = t * t * (3 - 2 * t)  # smoothstep
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        col.putpixel((0, y), c)
    return col.resize((w, h))


def soft_glow(img, cx, cy, radius, color, alpha, blur):
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
              fill=(color[0], color[1], color[2], alpha))
    ov = ov.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def draw_lens(d, cx, cy, r, sw, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=sw)
    a = math.radians(45)
    x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
    x2, y2 = cx + (r + r * 0.85) * math.cos(a), cy + (r + r * 0.85) * math.sin(a)
    d.line([x1, y1, x2, y2], fill=color, width=sw)
    d.ellipse([x2 - sw / 2, y2 - sw / 2, x2 + sw / 2, y2 + sw / 2], fill=color)


def text_bold(d, x, y, s, fnt, fill, anchor="la", strength=1):
    """Faux-bold: ridisegna con micro-offset."""
    off = strength * S
    for dx in range(-off, off + 1):
        for dy in range(-off, off + 1):
            if dx * dx + dy * dy <= off * off:
                d.text((x + dx, y + dy), s, font=fnt, fill=fill, anchor=anchor)


def draw_arrow(d, color, y, x0, x1, head_x, thick, head):
    d.line([x0, y, x1, y], fill=color, width=thick)
    d.ellipse([x0 - thick / 2, y - thick / 2, x0 + thick / 2, y + thick / 2], fill=color)
    d.polygon([(x1 - 1 * S, y - head), (head_x, y), (x1 - 1 * S, y + head)], fill=color)


def main():
    inter = load_inter()
    img = gradient_bg()
    # bagliore morbido in alto e tocco caldo giallo molto tenue in basso
    img = soft_glow(img, w * 0.5, h * 0.02, h * 0.85, (70, 70, 82), 60, 110 * S)
    img = soft_glow(img, w * 0.5, h * 1.06, w * 0.42, YELLOW, 8, 130 * S)

    # watermark lente gigante, molto tenue, in basso a destra
    wm = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wm)
    draw_lens(wd, int(w * 0.86), int(h * 0.82), int(118 * S), int(10 * S), (255, 255, 255, 14))
    img = Image.alpha_composite(img.convert("RGBA"), wm).convert("RGB")

    draw = ImageDraw.Draw(img, "RGBA")

    # ---- hero: lente + wordmark centrati ----
    f_word = _inter(inter, 33)
    word = "Forager"
    wbbox = draw.textbbox((0, 0), word, font=f_word)
    word_w = wbbox[2] - wbbox[0]
    word_h = wbbox[3] - wbbox[1]
    mark_r = 15 * S
    gap = 15 * S
    group_w = mark_r * 2 + gap + word_w
    x0 = (w - group_w) / 2
    cy = 64 * S
    draw_lens(draw, x0 + mark_r, cy, mark_r, int(4.0 * S), WHITE)
    text_bold(draw, x0 + mark_r * 2 + gap, cy, word, f_word, WHITE, anchor="lm", strength=1)

    # tagline centrata
    f_tag = _inter(inter, 14.5)
    tag = "il CRM open-source per i fundraiser"
    draw.text((w / 2, 104 * S), tag, font=f_tag, fill=GRAY, anchor="mm")

    # ---- ombre morbide sotto gli slot delle icone ----
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for (cx, cyy) in (APP_C, DST_C):
        ex, ey = cx * S, (cyy + 74) * S
        sd.ellipse([ex - 64 * S, ey - 13 * S, ex + 64 * S, ey + 13 * S], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(11 * S))
    img = Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    # ---- freccia gialla con glow ----
    ay = APP_C[1] * S
    ax0, ax1, ahx = 236 * S, 374 * S, 406 * S
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    draw_arrow(gd, (255, 209, 0, 170), ay, ax0, ax1, ahx, int(11 * S), int(23 * S))
    glow = glow.filter(ImageFilter.GaussianBlur(9 * S))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    draw_arrow(draw, YELLOW + (255,), ay, ax0, ax1, ahx, int(9 * S), int(20 * S))

    # ---- istruzione centrale sotto la freccia ----
    f_ins = _inter(inter, 13.5)
    ins_y = (APP_C[1] + 120) * S
    a = "Trascina "
    b = "Forager"
    c = " sulla cartella Applicazioni"
    wa = draw.textlength(a, font=f_ins)
    wb = draw.textlength(b, font=f_ins)
    wc = draw.textlength(c, font=f_ins)
    total = wa + wb + wc
    sx = (w - total) / 2
    draw.text((sx, ins_y), a, font=f_ins, fill=WHITE, anchor="lm")
    text_bold(draw, sx + wa, ins_y, b, f_ins, YELLOW, anchor="lm", strength=0)
    draw.text((sx + wa + wb, ins_y), c, font=f_ins, fill=WHITE, anchor="lm")

    # ---- footer versione ----
    f_v = _inter(inter, 11)
    draw.text((w - 24 * S, h - 22 * S), "v1.0.0", font=f_v, fill=DGRAY, anchor="rm")
    draw.text((24 * S, h - 22 * S), "fundraisinglab", font=f_v, fill=DGRAY, anchor="lm")

    img2 = img
    img1 = img.resize((W, H), Image.LANCZOS)
    img2.save(os.path.join(OUT, "dmg-bg@2x.png"))
    img1.save(os.path.join(OUT, "dmg-bg.png"))
    print("ok bg:", os.path.join(OUT, "dmg-bg.png"))


if __name__ == "__main__":
    main()
