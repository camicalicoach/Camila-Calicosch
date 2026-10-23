"""Logo camicali.coach: dos "c" entrelazadas con una mancuerna, PNG con fondo transparente.

Redibujado a partir del boceto de Gemini. Se dibuja con máscaras a 4x y se reduce para
tener bordes suaves. Uso: python3 make_logo.py <carpeta_salida>
"""
import os, sys
import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
S = 4                     # supersampling
N = 1024 * S              # canvas
U = N / 1024              # 1 unit = 1px of the final 1024 image

yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / U

CY = 512
LX, RX = 362, 662         # centres of the two c's
R_OUT, R_IN = 250, 148
GAP = 14                  # separation where shapes cross


def ring(cx, grow=0.0):
    d = np.hypot(xx - cx, yy - CY)
    return (d <= R_OUT + grow) & (d >= R_IN - grow)


def opening(cx, grow=0.0, half=56):
    return (xx > cx + grow) & (np.abs(yy - CY) < half - grow)


def rrect(x0, y0, x1, y1, r, grow=0.0):
    x0, y0, x1, y1, r = x0 - grow, y0 - grow, x1 + grow, y1 + grow, r + grow
    cx = np.clip(xx, x0 + r, x1 - r)
    cy = np.clip(yy, y0 + r, y1 - r)
    return np.hypot(xx - cx, yy - cy) <= r


def wedge(cx, deg, grow=0.0):
    """Angular opening on the right side (classic "c" mouth), shrunk by grow."""
    ang = np.degrees(np.arctan2(yy - CY, xx - cx))
    return np.abs(ang) < deg - grow * 0.25


def c_shape(cx, grow=0.0):
    # the left c gets an angular mouth so its ends tuck under the right c without leftovers
    mouth = wedge(cx, 42, grow) if cx == LX else opening(cx, grow)
    return ring(cx, grow) & ~mouth


def dumbbell(grow=0.0):
    return (rrect(318, 488, 706, 536, 12, grow)          # bar
            | rrect(358, 410, 410, 614, 18, grow)        # inner plates
            | rrect(614, 410, 666, 614, 18, grow)
            | rrect(300, 446, 340, 578, 14, grow)        # outer plates
            | rrect(684, 446, 724, 578, 14, grow))


left, right, bell = c_shape(LX), c_shape(RX), dumbbell()

# the right c sits on top of the left one; shapes are analytic, so the separation gap is
# just the same shape grown by GAP
left_v = left & ~c_shape(RX, GAP)
right_v = right
rings = (left_v | right_v) & ~dumbbell(GAP)


def save(name, parts):
    rgba = np.zeros((N, N, 4), np.uint8)
    for mask, color in parts:
        rgba[mask] = color + (255,)
    im = Image.fromarray(rgba, "RGBA").resize((1024, 1024), Image.LANCZOS)
    # trim to content and re-centre with padding so it survives a circular crop
    bbox = im.getbbox()
    logo = im.crop(bbox)
    side = 1024
    scale = (side * 0.78) / max(logo.size)
    logo = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(logo, ((side - logo.width) // 2, (side - logo.height) // 2))
    canvas.save(os.path.join(OUT, name + ".png"))
    canvas.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, name + "-512.png"))


INK, ACC, WHITE = (20, 26, 46), (79, 70, 229), (255, 255, 255)
save("logo-negro", [(rings | bell, (17, 17, 17))])
save("logo-indigo", [(rings | bell, ACC)])
save("logo-blanco", [(rings | bell, WHITE)])
save("logo-dos-tonos", [(left_v & rings, INK), (right_v & rings, ACC), (bell, INK)])
print("ok")
