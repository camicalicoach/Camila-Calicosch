"""Reemplaza el mensaje del chat en los frames del paso 'chat' por uno de bienvenida.

Uso: python3 chat_patch.py <carpeta_frames_chat> [preview.png]
Coordenadas medidas sobre la grabación recortada (1170 px de ancho); los frames están a 648 px.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

import render as R

FONT = os.path.join(R.FONTS, "NunitoSans-Regular.ttf")
SRC_W, FRAME_W = 1170, 648
BG = (240, 241, 248)
BORDER = (223, 224, 231)
TEXT = (20, 26, 46)
TIME = (106, 108, 122)
LINES = ["¡Hola! Te doy la bienvenida", "al equipo 💪", "Ya tenés tu plan listo para", "arrancar. Cualquier duda,", "escribime por acá."]
TOP, X0 = 440, 48  # region to repaint / bubble left edge
BUBBLE_Y = 463


def build_patch():
    f = ImageFont.truetype(FONT, 46)
    ft = ImageFont.truetype(FONT, 32)
    lh = 62
    em = R.emoji_image("💪", 44)
    widths = [f.getlength(l.replace(" 💪", "")) + (em.width + 12 if "💪" in l else 0) for l in LINES]
    bw = int(max(widths) + 2 * 44)
    bh = int(36 + lh * len(LINES) + 52)
    patch = Image.new("RGBA", (SRC_W, BUBBLE_Y - TOP + bh + 30), BG + (255,))
    d = ImageDraw.Draw(patch)
    y0 = BUBBLE_Y - TOP
    d.rounded_rectangle([X0, y0, X0 + bw, y0 + bh], radius=40, fill=(255, 255, 255), outline=BORDER, width=3)
    for i, line in enumerate(LINES):
        base = y0 + 36 + lh * (i + 0.75)
        txt = line.replace(" 💪", "")
        d.text((X0 + 44, base), txt, font=f, fill=TEXT, anchor="ls")
        if "💪" in line:
            patch.alpha_composite(em, (int(X0 + 44 + f.getlength(txt) + 12), int(base - em.height + 6)))
    d.text((X0 + bw - 40, y0 + bh - 24), "19:55", font=ft, fill=TIME, anchor="rs")
    s = FRAME_W / SRC_W
    return patch.resize((FRAME_W, int(patch.height * s)), Image.LANCZOS), int(TOP * s)


if __name__ == "__main__":
    folder = sys.argv[1]
    patch, y = build_patch()
    for name in sorted(os.listdir(folder)):
        p = os.path.join(folder, name)
        im = Image.open(p).convert("RGB")
        im.paste(patch.convert("RGB"), (0, y))
        im.save(p, quality=95)
    if len(sys.argv) > 2:
        Image.open(p).save(sys.argv[2])
    print("patched", len(os.listdir(folder)), "frames")
