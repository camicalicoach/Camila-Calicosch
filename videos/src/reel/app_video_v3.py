"""Reel explicativo de la app, versión 3: 3D + interacciones.

Sobre el estilo oscuro de la v2 agrega: celular en perspectiva 3D con grosor, cursor
sincronizado con los toques reales de la grabación (clics, arrastres) y la tarjeta de
un ejercicio que sale flotando de la pantalla.

Uso: python3 app_video_v3.py <carpeta_segmentos> <press_full.png> <salida.mp4>
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render as R

SEG_DIR, PRESS_SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PREVIEW = os.environ.get("PREVIEW")
W, H, FPS = R.W, R.H, R.FPS

NAVY, NAVY2 = (14, 19, 36), (27, 34, 64)
ACC, ACC_LIGHT, WHITE = R.ACC, (139, 133, 255), R.WHITE
INTER_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

HOOK, STEP, OUTRO = 3.0, 5.0, 4.5
NAV_Y = 0.954
TAB = {"inicio": 0.1, "entrenar": 0.3, "plan": 0.5, "evolucion": 0.7, "chat": 0.9}

# Cursor keyframes per step, in step-local seconds, screen coords (u, v) in 0..1.
#   ("move", t, u, v)  arrive at (u, v) at t
#   ("down", t, u, v) / ("up", t, u, v)  drag start / end (finger pressed in between)
#   ("tap", t, u, v)   click at t
# Times come from the screen changes detected in the recording, divided by each window's speed.
STEPS = [
    dict(seg="login", l1="Entrás con", l2="tu cuenta",
         cards=[("🔐", "Tu acceso personal"), ("💬", "¿Dudas? Ayuda por WhatsApp")],
         cursor=[("move", 0.65, 0.5, 0.279), ("tap", 0.8, 0.5, 0.279),
                 ("move", 2.65, 0.5, 0.378), ("tap", 2.8, 0.5, 0.378),
                 ("move", 4.2, 0.5, 0.449), ("tap", 4.4, 0.5, 0.449)]),
    dict(seg="inicio", l1="Sabés qué", l2="te toca hoy",
         cards=[("📅", "Tu entrenamiento del día"), ("📈", "Tu adherencia semanal")],
         cursor=[("move", 0.6, 0.62, 0.72), ("down", 1.0, 0.62, 0.72), ("up", 2.42, 0.62, 0.38),
                 ("move", 2.75, 0.62, 0.72), ("down", 2.85, 0.62, 0.72), ("up", 3.64, 0.62, 0.42),
                 ("move", 4.45, TAB["entrenar"], NAV_Y), ("tap", 4.66, TAB["entrenar"], NAV_Y)]),
    dict(seg="entrenar", l1="Abrís tu rutina", l2="y cada ejercicio", cards=[], popout=(2.2, 3.95),
         cursor=[("move", 1.5, 0.42, 0.25), ("tap", 1.76, 0.42, 0.25),
                 ("move", 4.0, 0.62, 0.72), ("down", 4.05, 0.62, 0.72), ("up", 4.9, 0.62, 0.42)]),
    dict(seg="guardar", l1="Cargás kilos", l2="y repeticiones",
         cards=[("✍️", "Anotás cada serie"), ("💬", "Comentarios para mí")],
         cursor=[("down", 0.05, 0.62, 0.75), ("up", 1.6, 0.62, 0.35), ("move", 1.9, 0.62, 0.75),
                 ("down", 1.95, 0.62, 0.75), ("up", 3.4, 0.62, 0.35), ("move", 3.5, 0.62, 0.72),
                 ("down", 3.52, 0.62, 0.72), ("up", 4.1, 0.62, 0.48),
                 ("move", 4.55, 0.5, 0.774), ("tap", 4.72, 0.5, 0.774)]),
    dict(seg="plan", l1="Todo tu plan,", l2="en un lugar",
         cards=[("🗓️", "Calendario y turnos"), ("💳", "Pagos y renovación")],
         cursor=[("move", 0.4, TAB["plan"], NAV_Y), ("tap", 0.55, TAB["plan"], NAV_Y),
                 ("move", 1.4, 0.55, 0.62), ("down", 1.47, 0.55, 0.62), ("up", 2.66, 0.55, 0.42),
                 ("move", 3.45, 0.495, 0.186), ("tap", 3.67, 0.495, 0.186),
                 ("move", 4.3, 0.8, 0.186), ("tap", 4.51, 0.8, 0.186)]),
    dict(seg="evolucion", l1="Mirás tu", l2="evolución",
         cards=[("📊", "Entrenamientos y volumen"), ("📏", "Medidas y fotos")],
         cursor=[("move", 0.22, TAB["evolucion"], NAV_Y), ("tap", 0.34, TAB["evolucion"], NAV_Y),
                 ("move", 0.85, 0.58, 0.75), ("down", 0.92, 0.58, 0.75), ("up", 2.3, 0.58, 0.3),
                 ("move", 2.6, 0.58, 0.3), ("down", 2.65, 0.58, 0.3), ("up", 3.82, 0.58, 0.75),
                 ("move", 4.05, 0.5, 0.19), ("tap", 4.25, 0.5, 0.19),
                 ("move", 4.7, TAB["chat"], NAV_Y), ("tap", 4.85, TAB["chat"], NAV_Y)]),
    dict(seg="chat", l1="Hablás", l2="conmigo",
         cards=[("💜", "Chat directo con tu coach"), ("🔔", "Avisos de cada turno")],
         cursor=[("move", 1.4, 0.64, 0.36), ("move", 5.0, 0.66, 0.37)], hover=(0.32, 0.29, 1.5)),
]
DUR = HOOK + STEP * len(STEPS) + OUTRO
CUTS = [HOOK + STEP * i for i in range(len(STEPS) + 1)]

# ---------------------------------------------------------------- background (same mood as v2)
def make_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    t = np.clip(0.65 * y + 0.35 * x, 0, 1)
    img = np.array(NAVY, float) * (1 - t) + np.array(NAVY2, float) * t
    img = img + np.random.default_rng(5).normal(0, 2.2, (H, W, 1))
    bg = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(dots)
    for gy in range(30, H, 54):
        for gx in range(30, W, 54):
            d.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(255, 255, 255, 14))
    bg.alpha_composite(dots)
    return bg
BG = make_bg()

def blob(radius, color, alpha):
    im = Image.new("RGBA", (radius * 4, radius * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([radius, radius, radius * 3, radius * 3], fill=color + (alpha,))
    return im.filter(ImageFilter.GaussianBlur(radius * 0.55))
BLOBS = [(blob(300, ACC, 120), 0.9, 0.23, 0.30), (blob(240, (168, 85, 247), 80), 0.15, 0.62, 0.41),
         (blob(200, ACC, 70), 0.75, 0.88, 0.53)]

def background(t):
    frame = BG.copy()
    for im, bx, by, sp in BLOBS:
        cx = W * bx + 90 * math.sin(t * sp + bx * 6)
        cy = H * by + 70 * math.cos(t * sp * 0.8 + by * 5)
        frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
    return frame

def _mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m

# ---------------------------------------------------------------- 3D projection
FOCAL = 2400.0

def project(pts, yaw, pitch, scale, cx, cy):
    """pts: (N,3) in phone-local pixels (origin at centre). Returns (N,2) canvas coords."""
    a, b = math.radians(yaw), math.radians(pitch)
    p = np.asarray(pts, float) * scale
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
    k = FOCAL / (FOCAL + z)
    return np.stack([cx + x * k, cy + y * k], 1)

def warp(img, dst):
    """Perspective-warp img so its corners land on dst (TL, TR, BR, BL). Returns (image, offset)."""
    w, h = img.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    x0, y0 = np.floor(dst.min(0)).astype(int)
    x1, y1 = np.ceil(dst.max(0)).astype(int)
    d = dst - [x0, y0]
    A, B = [], []
    for (X, Y), (u, v) in zip(d, src):
        A += [[X, Y, 1, 0, 0, 0, -u * X, -u * Y], [0, 0, 0, X, Y, 1, -v * X, -v * Y]]
        B += [u, v]
    coeffs = np.linalg.solve(np.array(A, float), np.array(B, float))
    out = img.transform((int(x1 - x0), int(y1 - y0)), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)
    return out, (int(x0), int(y0))

# ---------------------------------------------------------------- phone
SCR_W, SCR_H = 648, 1262
BEZEL = 18
PH_W, PH_H = SCR_W + 2 * BEZEL, SCR_H + 2 * BEZEL
PH_SCALE = 0.86
REST_X, REST_Y = 640, 560 + PH_H * PH_SCALE / 2
DEPTH = 34  # phone thickness in px

SCR_MASK = _mask(SCR_W, SCR_H, 54)
BODY = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
bd = ImageDraw.Draw(BODY)
bd.rounded_rectangle([0, 0, PH_W - 1, PH_H - 1], radius=72, fill=(8, 10, 20))
bd.rounded_rectangle([1, 1, PH_W - 2, PH_H - 2], radius=71, outline=(90, 96, 140), width=3)
SIDE = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
ImageDraw.Draw(SIDE).rounded_rectangle([0, 0, PH_W - 1, PH_H - 1], radius=72, fill=(52, 58, 92))
SHADOW = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
ImageDraw.Draw(SHADOW).rounded_rectangle([0, 0, PH_W - 1, PH_H - 1], radius=72, fill=(0, 0, 0, 150))
GLOW = blob(380, ACC, 90)

_files = {}
def seg_frame(name, i):
    files = _files.setdefault(name, sorted(os.listdir(os.path.join(SEG_DIR, name))))
    return Image.open(os.path.join(SEG_DIR, name, files[max(0, min(len(files) - 1, i))])).convert("RGBA")

def corners(z=0.0):
    hw, hh = PH_W / 2, PH_H / 2
    return [(-hw, -hh, z), (hw, -hh, z), (hw, hh, z), (-hw, hh, z)]

def screen_to_local(u, v):
    return (BEZEL + u * SCR_W - PH_W / 2, BEZEL + v * SCR_H - PH_H / 2, 0.0)

class Pose:
    def __init__(self, cx, cy, scale, yaw, pitch):
        self.cx, self.cy, self.scale, self.yaw, self.pitch = cx, cy, scale, yaw, pitch
    def pt(self, local):
        return project([local], self.yaw, self.pitch, self.scale, self.cx, self.cy)[0]
    def screen(self, u, v):
        return self.pt(screen_to_local(u, v))

def draw_phone(frame, scr, pose):
    ph = BODY.copy()
    s = scr.copy()
    s.putalpha(SCR_MASK)
    ph.alpha_composite(s, (BEZEL, BEZEL))
    gl = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(0, 0), (PH_W * 0.55, 0), (0, PH_H * 0.42)], fill=(255, 255, 255, 16))
    gl.putalpha(Image.composite(gl.getchannel("A"), Image.new("L", gl.size, 0), _mask(PH_W, PH_H, 72)))
    ph.alpha_composite(gl)
    P = lambda z: project(corners(z), pose.yaw, pose.pitch, pose.scale, pose.cx, pose.cy)
    frame.alpha_composite(GLOW, (int(pose.cx - GLOW.width / 2), int(pose.cy - GLOW.height / 2)))
    # soft shadow on the "floor" behind and below
    sh, off = warp(SHADOW, P(DEPTH * 6) + [40, 70])
    sh = sh.filter(ImageFilter.GaussianBlur(40))
    frame.alpha_composite(sh, off)
    # thickness: stack a few back layers to fake the side edge
    for z in (DEPTH, DEPTH * 0.66, DEPTH * 0.33):
        side, off = warp(SIDE, P(z))
        frame.alpha_composite(side, off)
    front, off = warp(ph, P(0))
    frame.alpha_composite(front, off)

# ---------------------------------------------------------------- cursor
ARROW = [(0, 0), (0, 44), (11, 33), (19, 52), (27, 48), (19, 31), (34, 31)]

def cursor_img(pressed):
    s = 1.6
    im = Image.new("RGBA", (90, 110), (0, 0, 0, 0))
    pts = [(14 + x * s, 10 + y * s) for x, y in ARROW]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + 4, y + 6) for x, y in pts], fill=(0, 0, 0, 120))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=WHITE if not pressed else (225, 224, 255), outline=INK_DARK)
    d.line(pts + [pts[0]], fill=INK_DARK, width=3, joint="curve")
    return im
INK_DARK = (14, 19, 36)
CUR_UP, CUR_DOWN = cursor_img(False), cursor_img(True)
CUR_TIP = (14, 10)

def cursor_state(keys, lt):
    """Return (u, v, pressed, click_k) where click_k is time since the last tap (or None)."""
    prev = None
    pressed = False
    click = None
    for kind, t, u, v in keys:
        if lt < t:
            if prev is None:
                return u, v, False, None
            pk, pt, pu, pv = prev
            span = max(1e-3, t - pt)
            # drags move linearly with the content; free moves ease in/out
            k = R.clamp((lt - pt) / span)
            if not (pk == "down" and kind == "up"):
                k = 0.5 - 0.5 * math.cos(math.pi * k)
                # hold still briefly after a tap or drag release
                k = R.clamp((lt - pt - 0.12) / max(1e-3, span - 0.12))
                k = 0.5 - 0.5 * math.cos(math.pi * k)
            pressed = pk == "down" and kind == "up"
            return pu + (u - pu) * k, pv + (v - pv) * k, pressed, click
        if kind == "tap":
            click = lt - t
        prev = (kind, t, u, v)
    kind, t, u, v = prev
    return u, v, False, click

def tap_ripple(scr, u, v, k):
    if k is None or k < 0 or k > 0.7:
        return
    layer = Image.new("RGBA", scr.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = u * SCR_W, v * SCR_H
    r = 18 + 80 * R.ease_out(k / 0.7)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACC + (int(220 * (1 - k / 0.7)),), width=6)
    if k < 0.3:
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(79, 70, 229, int(110 * (1 - k / 0.3))))
    scr.alpha_composite(layer)

def touch_dot(scr, u, v):
    layer = Image.new("RGBA", scr.size, (0, 0, 0, 0))
    cx, cy = u * SCR_W, v * SCR_H
    ImageDraw.Draw(layer).ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(79, 70, 229, 70), outline=(79, 70, 229, 150), width=3)
    scr.alpha_composite(layer)

def draw_cursor(frame, xy, pressed, click_k, alpha=1.0):
    if alpha <= 0.01:
        return
    im = CUR_DOWN if pressed else CUR_UP
    s = 0.86 if pressed else 1.0
    if click_k is not None and 0 <= click_k < 0.25:
        s = 1.0 - 0.18 * math.sin(math.pi * click_k / 0.25)
    if s != 1.0:
        im = im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda a: int(a * alpha)))
    frame.alpha_composite(im, (int(xy[0] - CUR_TIP[0] * s), int(xy[1] - CUR_TIP[1] * s)))

# ---------------------------------------------------------------- pop-out exercise card
PRESS_BOX = (23, 467, 1147, 1653)  # "Press de banca" card in the 1170-wide recording
def make_press_card():
    src = Image.open(PRESS_SRC).convert("RGB").crop(PRESS_BOX)
    w = 600
    card = src.resize((w, int(src.height * w / src.width)), Image.LANCZOS).convert("RGBA")
    card.putalpha(_mask(card.width, card.height, 34))
    edge = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle([0, 0, card.width - 1, card.height - 1], radius=34, outline=ACC_LIGHT, width=5)
    card.alpha_composite(edge)
    return card
PRESS = make_press_card()
PRESS_LINK = (0.22, 0.30)  # "Ver cómo se hace" in card-local coords

def draw_popout(frame, pose, lt, t0, t1):
    """Card flies out of the phone towards the viewer, floats, then returns. Returns cursor override."""
    k_in = R.ease_out((lt - t0) / 0.5)
    k_out = R.ease_in((lt - (t1 - 0.4)) / 0.4)
    k = k_in * (1 - k_out)
    if k <= 0.001:
        return None
    # start: where the card sits on the screen; end: floating left of the phone, closer to camera
    u0, v0 = (PRESS_BOX[0] + PRESS_BOX[2]) / 2 / 1170, (PRESS_BOX[1] + PRESS_BOX[3]) / 2 / 2280
    sx, sy = pose.screen(u0, v0)
    ex, ey = 420, 1040
    cx, cy = sx + (ex - sx) * k, sy + (ey - sy) * k
    start_scale = (PRESS_BOX[2] - PRESS_BOX[0]) / 1170 * SCR_W * PH_SCALE / PRESS.width
    sc = start_scale + (1.0 - start_scale) * k
    yaw = pose.yaw * (1 - k) + 10 * k + 3 * math.sin(lt * 2.2) * k
    pitch = pose.pitch * (1 - k) - 6 * k
    hw, hh = PRESS.width / 2, PRESS.height / 2
    quad = project([(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)], yaw, pitch, sc, cx, cy)
    # shadow
    sh = Image.new("RGBA", PRESS.size, (0, 0, 0, int(160 * k)))
    sh.putalpha(Image.composite(sh.getchannel("A"), Image.new("L", sh.size, 0), _mask(PRESS.width, PRESS.height, 34)))
    shw, off = warp(sh, quad + [30 * k, 60 * k])
    frame.alpha_composite(shw.filter(ImageFilter.GaussianBlur(30)), off)
    card = PRESS.copy()
    # pulsing highlight on "Ver cómo se hace" while floating
    if k > 0.95:
        g = Image.new("RGBA", card.size, (0, 0, 0, 0))
        lx, ly = PRESS_LINK[0] * card.width, PRESS_LINK[1] * card.height
        p = 0.5 + 0.5 * math.sin(lt * 9)
        ImageDraw.Draw(g).rounded_rectangle([lx - 120, ly - 26, lx + 120, ly + 26], radius=26,
                                            outline=ACC + (int(120 + 120 * p),), width=5, fill=(79, 70, 229, int(30 + 30 * p)))
        card.alpha_composite(g)
    cw, off = warp(card, quad)
    frame.alpha_composite(cw, off)
    # caption chip under the card
    if k > 0.6:
        a = R.clamp((k - 0.6) / 0.4)
        f = R.font(R.INTER_SB, 34)
        em = R.emoji_image("▶️", 38)
        label = "Cada ejercicio con su video"
        cwid = int(f.getlength(label) + em.width + 70)
        chip = Image.new("RGBA", (cwid, 76), (0, 0, 0, 0))
        d = ImageDraw.Draw(chip)
        d.rounded_rectangle([0, 0, cwid - 1, 75], radius=38, fill=(20, 26, 46, 220), outline=(139, 133, 255, 120), width=2)
        chip.alpha_composite(em, (26, 38 - em.height // 2))
        d.text((26 + em.width + 14, 38), label, font=f, fill=WHITE, anchor="lm")
        R.paste_scaled(frame, chip, cx, quad[:, 1].max() + 70, 1.0, a)
    # cursor points at the link on the floating card
    link = project([((PRESS_LINK[0] - 0.5) * PRESS.width, (PRESS_LINK[1] - 0.5) * PRESS.height, 0)], yaw, pitch, sc, cx, cy)[0]
    return link if k > 0.9 else None

# ---------------------------------------------------------------- text & cards
def text_img(text, fnt, color):
    w = int(fnt.getlength(text)) + 8
    asc, desc = fnt.getmetrics()
    im = Image.new("RGBA", (w, asc + desc + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 4 + asc), text, font=fnt, fill=color, anchor="ls")
    return im

def slide_text(frame, im, x, y, lt, t_in, t_out=None, dx=60):
    a = R.ease_out((lt - t_in) / 0.4)
    if t_out is not None:
        a *= 1 - R.ease_in((lt - t_out) / 0.3)
    if a <= 0.01:
        return
    if a < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(x - dx * (1 - a)), int(y)))

def glass_card(frame, emoji, label, x, cy, a, dy):
    if a <= 0.01:
        return
    f = R.font(R.INTER_SB, 34)
    em = R.emoji_image(emoji, 40)
    cw, ch = int(f.getlength(label) + 130), 104
    y, x = int(cy - ch / 2 + dy), int(x)
    region = frame.crop((x, y, x + cw, y + ch)).filter(ImageFilter.GaussianBlur(16))
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    card.alpha_composite(region)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=30, fill=(20, 26, 46, 205), outline=(139, 133, 255, 110), width=2)
    d.ellipse([20, ch / 2 - 32, 84, ch / 2 + 32], fill=ACC)
    card.alpha_composite(em, (52 - em.width // 2, int(ch / 2 - em.height / 2)))
    d.text((104, ch / 2), label, font=f, fill=WHITE, anchor="lm")
    card.putalpha(Image.composite(card.getchannel("A"), Image.new("L", card.size, 0), _mask(cw, ch, 30)).point(lambda v: int(v * a)))
    frame.alpha_composite(card, (x, y))

def header(frame, t, step_idx=None):
    d = ImageDraw.Draw(frame)
    d.ellipse([70, 141, 86, 157], fill=ACC_LIGHT)
    d.text((98, 150), "camicali.coach", font=R.font(R.INTER_B, 30), fill=(255, 255, 255, 220), anchor="lm")
    n = len(STEPS)
    for i in range(n):
        x = W - 70 - (n - 1 - i) * 30
        if step_idx is not None and i == step_idx:
            d.rounded_rectangle([x - 26, 143, x + 6, 157], radius=7, fill=ACC_LIGHT)
        else:
            done = (step_idx is not None and i < step_idx) or t >= CUTS[-1]
            d.ellipse([x - 7, 143, x + 7, 157], fill=ACC_LIGHT if done else (255, 255, 255, 60))

# ---------------------------------------------------------------- scenes
def phone_pose(t, idx=None, lt=0.0):
    yaw = -21 + 5 * math.sin(t * 0.55)
    pitch = 7 + 2.5 * math.sin(t * 0.8 + 1)
    fy = 12 * math.sin(t * 1.6)
    cx, cy = REST_X, REST_Y + fy
    if idx == 0:
        p = R.ease_out(lt / 0.7)
        cx, cy = W / 2 + (REST_X - W / 2) * p, cy + 260 * (1 - p)
        yaw = yaw * p + 0 * (1 - p)
    return Pose(cx, cy, PH_SCALE, yaw, pitch)

def scene_hook(frame, t):
    im1 = text_img("Así funciona", R.font(INTER_BLACK, 108), WHITE)
    im2 = text_img("la app", R.font(INTER_BLACK, 150), ACC_LIGHT)
    slide_text(frame, im1, (W - im1.width) / 2, 330, t, 0.1, 2.6, dx=0)
    slide_text(frame, im2, (W - im2.width) / 2, 450, t, 0.35, 2.6, dx=0)
    if t > 0.7:
        a = R.ease_out((t - 0.7) / 0.3) * (1 - R.ease_in((t - 2.6) / 0.3))
        f = R.font(R.INTER_SB, 34)
        em = R.emoji_image("👇", 34)
        cw = int(f.getlength("paso a paso") + em.width + 74)
        chip = Image.new("RGBA", (cw, 72), (0, 0, 0, 0))
        cd = ImageDraw.Draw(chip)
        cd.rounded_rectangle([0, 0, cw - 1, 71], radius=36, outline=(255, 255, 255, 90), width=2)
        cd.text((30, 36), "paso a paso", font=f, fill=WHITE, anchor="lm")
        chip.alpha_composite(em, (cw - 30 - em.width, 36 - em.height // 2))
        R.paste_scaled(frame, chip, W / 2, 690, 1.0, max(0, a))
    p = R.ease_out((t - 0.9) / 1.4)
    if p > 0:
        cy = H + 760 - (H + 760 - (REST_Y + 260)) * p
        pose = Pose(W / 2, cy + 12 * math.sin(t * 1.6), PH_SCALE, 24 * (1 - p), 18 * (1 - p) + 7 * p)
        draw_phone(frame, seg_frame(STEPS[0]["seg"], 0), pose)
    # cursor glides in from the right at the end of the hook
    k = R.ease_out((t - 2.2) / 0.8)
    if k > 0:
        draw_cursor(frame, (W + 60 - (W + 60 - 820) * k, 1500 - 200 * k), False, None, k)

def scene_step(frame, idx, lt, t):
    st = STEPS[idx]
    pose = phone_pose(t, idx, lt)
    scr = seg_frame(st["seg"], int(lt * FPS))
    keys = st["cursor"]
    if idx > 0:  # start from wherever the previous step left the cursor
        _, _, pu, pv = STEPS[idx - 1]["cursor"][-1]
        keys = [("move", 0.0, pu, pv)] + keys
    u, v, pressed, click = cursor_state(keys, lt)
    tap_ripple(scr, u, v, click)
    if pressed:
        touch_dot(scr, u, v)
    if lt > STEP - 0.3 and idx + 1 < len(STEPS):  # crossfade into next screen
        nxt = seg_frame(STEPS[idx + 1]["seg"], 0)
        tap_ripple(nxt, u, v, click)
        scr = Image.blend(scr, nxt, R.ease_in((lt - (STEP - 0.3)) / 0.3))
    if st.get("hover") and lt > st["hover"][2]:  # glow around the welcome message
        hu, hv, h0 = st["hover"]
        g = Image.new("RGBA", scr.size, (0, 0, 0, 0))
        p = 0.5 + 0.5 * math.sin((lt - h0) * 5)
        a = R.ease_out((lt - h0) / 0.4)
        ImageDraw.Draw(g).rounded_rectangle([10, 0.195 * SCR_H, 0.6 * SCR_W + 20, 0.385 * SCR_H], radius=30,
                                            outline=ACC + (int(a * (110 + 110 * p)),), width=6)
        scr.alpha_composite(g)
    draw_phone(frame, scr, pose)
    t_out = STEP - 0.35
    slide_text(frame, text_img(f"PASO {idx + 1:02d} / {len(STEPS):02d}", R.font(R.INTER_B, 28), ACC_LIGHT), 70, 232, lt, 0.05, t_out)
    slide_text(frame, text_img(st["l1"], R.font(INTER_BLACK, 92), WHITE), 66, 278, lt, 0.12, t_out)
    slide_text(frame, text_img(st["l2"], R.font(INTER_BLACK, 92), ACC_LIGHT), 66, 384, lt, 0.22, t_out)
    for j, (em, label) in enumerate(st["cards"]):
        t_in = 0.9 + j * 0.45
        a = R.ease_out((lt - t_in) / 0.35) * (1 - R.ease_in((lt - (t_out - 0.1)) / 0.3))
        glass_card(frame, em, label, 40, 1060 + j * 150, max(0, a), 30 * (1 - R.ease_out((lt - t_in) / 0.35)))
    link = draw_popout(frame, pose, lt, *st["popout"]) if st.get("popout") else None
    xy = pose.screen(u, v)
    if link is not None:  # glide to the link on the floating card
        xy = link + [10, 6]
    draw_cursor(frame, xy, pressed, click)

def scene_outro(frame, lt, t):
    p = R.ease_in(lt / 0.8)
    if p < 1:
        pose = phone_pose(t)
        pose.cy += 1500 * p
        pose.pitch += 25 * p
        draw_phone(frame, seg_frame(STEPS[-1]["seg"], int(STEP * FPS)), pose)
        draw_cursor(frame, (pose.screen(0.66, 0.37)[0], pose.screen(0.66, 0.37)[1]), False, None, 1 - R.clamp(lt / 0.4))
    f1 = R.font(INTER_BLACK, 116)
    for i, (txt, col) in enumerate([("Tu coach", WHITE), ("en el", WHITE), ("bolsillo", ACC_LIGHT)]):
        im = text_img(txt, f1, col)
        slide_text(frame, im, (W - im.width) / 2, 560 + i * 135, lt, 0.4 + i * 0.15, dx=0)
    k = lt - 1.3
    if k >= 0:
        f = R.font(R.INTER_SB, 46)
        txt = "Escribime y te paso el acceso"
        tw = f.getlength(txt)
        em = R.emoji_image("📲", 50)
        im = Image.new("RGBA", (int(tw + 16 + em.width) + 4, 80), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 40), txt, font=f, fill=(255, 255, 255, 230), anchor="lm")
        im.alpha_composite(em, (int(tw + 16), 40 - em.height // 2))
        a = R.ease_out(k / 0.35)
        R.paste_scaled(frame, im, W / 2, 1020 + 24 * (1 - a), 1.0, a)
    k = lt - 1.8
    if k >= 0:
        f = R.font(INTER_XB, 46)
        txt = "@camicali.coach"
        pw, ph = int(f.getlength(txt) + 90), 104
        im = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([40, 40, 40 + pw, 40 + ph], radius=ph // 2, fill=ACC + (150,))
        im = im.filter(ImageFilter.GaussianBlur(18))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([40, 40, 40 + pw, 40 + ph], radius=ph // 2, fill=ACC)
        d.text((40 + pw / 2, 40 + ph / 2), txt, font=f, fill=WHITE, anchor="mm")
        R.paste_scaled(frame, im, W / 2, 1190, 0.8 + 0.2 * R.ease_out_back(k / 0.35), R.clamp(k / 0.12))
        # the cursor comes back and clicks the handle
        kc = R.ease_out((lt - 2.3) / 0.6)
        if kc > 0:
            click = lt - 3.05 if lt > 3.05 else None
            draw_cursor(frame, (W + 60 - (W + 60 - (W / 2 + 120)) * kc, 1500 - (1500 - 1205) * kc), False, click)

def render_frame(t):
    frame = background(t)
    if t < HOOK:
        scene_hook(frame, t)
        header(frame, t)
    elif t < CUTS[-1]:
        i = int((t - HOOK) // STEP)
        scene_step(frame, i, t - CUTS[i], t)
        header(frame, t, i)
    else:
        scene_outro(frame, t - CUTS[-1], t)
        header(frame, t)
    if t < 0.25:
        frame = Image.blend(Image.new("RGBA", (W, H), NAVY + (255,)), frame, t / 0.25)
    if t > DUR - 0.4:
        frame = Image.blend(frame, Image.new("RGBA", (W, H), NAVY + (255,)), (t - (DUR - 0.4)) / 0.4)
    return frame.convert("RGB")


if __name__ == "__main__":
    if PREVIEW:
        for s in PREVIEW.split(","):
            render_frame(float(s)).save(os.path.join(os.path.dirname(OUT), f"v3_prev_{s}.png"))
        sys.exit()
    R.DUR, R.CUTS, R.SCENES[1]["t0"] = DUR, CUTS[1:], HOOK
    wav = os.path.join(os.path.dirname(os.path.abspath(OUT)), "v3_beat.wav")
    R.synth_audio(wav)
    n = int(DUR * FPS)
    start = int(os.environ.get("START", 0))
    end = int(os.environ.get("END", n))
    raw = os.environ.get("RAW")  # render a frame range to a raw file (for parallel rendering)
    if raw:
        with open(raw, "wb") as fh:
            for i in range(start, end):
                fh.write(render_frame(i / FPS).tobytes())
        sys.exit()
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT,
    ], stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(render_frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("done", OUT)
