"""Reel explicativo de la app, versión 2: estilo oscuro premium.

Celular inclinado y flotando, toque animado en la pestaña activa, tarjetas de vidrio
esmerilado con los detalles de cada paso y transiciones suaves.

Uso: python3 app_video_v2.py <carpeta_segmentos> <salida.mp4>
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render as R

SEG_DIR, OUT = sys.argv[1], sys.argv[2]
PREVIEW = os.environ.get("PREVIEW")
W, H, FPS = R.W, R.H, R.FPS

NAVY = (14, 19, 36)
NAVY2 = (27, 34, 64)
ACC = R.ACC
ACC_LIGHT = (139, 133, 255)
WHITE = R.WHITE
INTER_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

HOOK, STEP, OUTRO = 3.0, 5.0, 4.5
# (segment, nav tab index, title line 1, title line 2 (accent), two detail cards)
STEPS = [
    ("inicio", 0, "Sabés qué", "te toca hoy", [("📅", "Tu entrenamiento del día"), ("📈", "Tu adherencia semanal")]),
    ("entrenar", 1, "Entrenás con", "tu rutina", [("🏋️", "Series, kilos y repes"), ("▶️", "Video de cada ejercicio")]),
    ("guardar", 1, "Guardás y", "me contás", [("💬", "Comentarios para mí"), ("✅", "Terminar y guardar")]),
    ("plan", 2, "Todo tu plan,", "en un lugar", [("🗓️", "Calendario y turnos"), ("💳", "Pagos y renovación")]),
    ("evolucion", 3, "Mirás tu", "evolución", [("📊", "Volumen y récords"), ("📏", "Medidas y fotos")]),
    ("chat", 4, "Hablás", "conmigo", [("💜", "Chat directo con tu coach"), ("🔔", "Avisos de cada turno")]),
]
DUR = HOOK + STEP * len(STEPS) + OUTRO
CUTS = [HOOK + STEP * i for i in range(len(STEPS) + 1)]

# ---------------------------------------------------------------- background
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

# ---------------------------------------------------------------- phone
SCR_W, SCR_H = 648, 1262
BEZEL = 18
PH_W, PH_H = SCR_W + 2 * BEZEL, SCR_H + 2 * BEZEL
PH_SCALE = 0.86
REST_X, REST_Y = 650, 560 + PH_H * PH_SCALE / 2  # phone centre at rest
TILT = -4.0
NAV_X = [0.1, 0.3, 0.5, 0.7, 0.9]
NAV_Y = 0.952

def _mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m
SCR_MASK = _mask(SCR_W, SCR_H, 54)
BODY = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
bd = ImageDraw.Draw(BODY)
bd.rounded_rectangle([0, 0, PH_W - 1, PH_H - 1], radius=72, fill=(8, 10, 20))
bd.rounded_rectangle([1, 1, PH_W - 2, PH_H - 2], radius=71, outline=(90, 96, 140), width=3)

_files = {}
def seg_frame(name, i):
    files = _files.setdefault(name, sorted(os.listdir(os.path.join(SEG_DIR, name))))
    return Image.open(os.path.join(SEG_DIR, name, files[max(0, min(len(files) - 1, i))])).convert("RGBA")

def screen_at(idx, lt):
    """Screen image for step idx at local time lt, crossfading into the next step."""
    name, tab = STEPS[idx][0], STEPS[idx][1]
    scr = seg_frame(name, int(lt * FPS))
    # tap ripple on the active tab at the start of the step
    k = lt - 0.25
    if 0 <= k < 0.9:
        layer = Image.new("RGBA", scr.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cx, cy = NAV_X[tab] * SCR_W, NAV_Y * SCR_H
        r = 20 + 70 * R.ease_out(k / 0.9)
        a = int(200 * (1 - k / 0.9))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACC + (a,), width=6)
        if k < 0.35:
            rr = 26
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(79, 70, 229, int(120 * (1 - k / 0.35))))
        scr.alpha_composite(layer)
    return scr

def phone_img(scr):
    ph = BODY.copy()
    s = scr.copy()
    s.putalpha(SCR_MASK)
    ph.alpha_composite(s, (BEZEL, BEZEL))
    # glass reflection
    gl = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(0, 0), (PH_W * 0.55, 0), (0, PH_H * 0.42)], fill=(255, 255, 255, 14))
    gl.putalpha(Image.composite(gl.getchannel("A"), Image.new("L", gl.size, 0), _mask(PH_W, PH_H, 72)))
    ph.alpha_composite(gl)
    return ph

SHADOW = Image.new("RGBA", (PH_W + 240, PH_H + 240), (0, 0, 0, 0))
ImageDraw.Draw(SHADOW).rounded_rectangle([120, 150, PH_W + 120, PH_H + 150], radius=72, fill=(0, 0, 0, 140))
SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(45))
GLOW = blob(380, ACC, 90)

def place_phone(frame, scr, cx, cy, scale, angle, t):
    ph = phone_img(scr)
    size = (int(PH_W * scale), int(PH_H * scale))
    ph = ph.resize(size, Image.BICUBIC).rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = SHADOW.resize((int(SHADOW.width * scale), int(SHADOW.height * scale))).rotate(angle, expand=True)
    frame.alpha_composite(GLOW, (int(cx - GLOW.width / 2), int(cy - GLOW.height / 2)))
    frame.alpha_composite(sh, (int(cx - sh.width / 2), int(cy - sh.height / 2 + 30 * scale)))
    frame.alpha_composite(ph, (int(cx - ph.width / 2), int(cy - ph.height / 2)))

# ---------------------------------------------------------------- text & cards
def text_img(text, fnt, color):
    w = int(fnt.getlength(text)) + 8
    asc, desc = fnt.getmetrics()
    im = Image.new("RGBA", (w, asc + desc + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 4 + asc), text, font=fnt, fill=color, anchor="ls")
    return im

def slide_text(frame, im, x, y, lt, t_in, t_out=None, dx=60):
    """Left-aligned text that slides in from the left and out to the left."""
    a = R.ease_out((lt - t_in) / 0.4)
    if t_out is not None:
        a *= 1 - R.ease_in((lt - t_out) / 0.3)
    if a <= 0.01:
        return
    shift = -dx * (1 - a)
    if a < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(x + shift), int(y)))

def glass_card(frame, emoji, label, x, cy, a, dy):
    if a <= 0.01:
        return
    f = R.font(R.INTER_SB, 34)
    em = R.emoji_image(emoji, 40)
    cw, ch = int(f.getlength(label) + 130), 104
    y = int(cy - ch / 2 + dy)
    x = int(x)
    # frosted glass: blur what's underneath
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

def header(frame, t, step_idx=None, on=True):
    d = ImageDraw.Draw(frame)
    f = R.font(R.INTER_B, 30)
    d.ellipse([70, 141, 86, 157], fill=ACC_LIGHT)
    d.text((98, 150), "camicali.coach", font=f, fill=(255, 255, 255, 220), anchor="lm")
    # step dots top-right
    n = len(STEPS)
    for i in range(n):
        x = W - 70 - (n - 1 - i) * 30
        active = step_idx is not None and i == step_idx
        done = step_idx is not None and i < step_idx or t >= CUTS[-1]
        if active:
            d.rounded_rectangle([x - 26, 143, x + 6, 157], radius=7, fill=ACC_LIGHT)
        else:
            d.ellipse([x - 7, 143, x + 7, 157], fill=ACC_LIGHT if done else (255, 255, 255, 60))

# ---------------------------------------------------------------- scenes
def float_offset(t):
    return 12 * math.sin(t * 1.6), 1.2 * math.sin(t * 0.9)

def scene_hook(frame, t):
    f1, f2 = R.font(INTER_BLACK, 108), R.font(INTER_BLACK, 150)
    im1 = text_img("Así funciona", f1, WHITE)
    im2 = text_img("la app", f2, ACC_LIGHT)
    slide_text(frame, im1, (W - im1.width) / 2, 330, t, 0.1, 2.6, dx=0)
    slide_text(frame, im2, (W - im2.width) / 2, 450, t, 0.35, 2.6, dx=0)
    chip_f = R.font(R.INTER_SB, 34)
    if t > 0.7:
        a = R.ease_out((t - 0.7) / 0.3) * (1 - R.ease_in((t - 2.6) / 0.3))
        em = R.emoji_image("⏱", 34)
        cw = int(chip_f.getlength("en 30 segundos") + em.width + 74)
        chip = Image.new("RGBA", (cw, 72), (0, 0, 0, 0))
        cd = ImageDraw.Draw(chip)
        cd.rounded_rectangle([0, 0, cw - 1, 71], radius=36, outline=(255, 255, 255, 90), width=2)
        cd.text((30, 36), "en 30 segundos", font=chip_f, fill=WHITE, anchor="lm")
        chip.alpha_composite(em, (cw - 30 - em.width, 36 - em.height // 2))
        R.paste_scaled(frame, chip, W / 2, 690, 1.0, max(0, a))
    # phone rises from the bottom, centred, then moves to rest in step 1
    p = R.ease_out((t - 0.9) / 1.4)
    if p > 0:
        fy, fa = float_offset(t)
        cy = H + 700 - (H + 700 - (REST_Y + 260)) * p
        place_phone(frame, screen_at(0, 0), W / 2, cy + fy, PH_SCALE, TILT * p + fa, t)

def scene_step(frame, idx, lt, t):
    name, tab, l1, l2, cards = STEPS[idx]
    fy, fa = float_offset(t)
    cx, cy = REST_X, REST_Y
    if idx == 0:  # glide in from the hook position
        p = R.ease_out(lt / 0.7)
        cx, cy = W / 2 + (REST_X - W / 2) * p, REST_Y + 260 * (1 - p)
    scr = screen_at(idx, lt)
    if lt > STEP - 0.3 and idx + 1 < len(STEPS):  # crossfade into the next screen
        nxt = screen_at(idx + 1, 0)
        scr = Image.blend(scr, nxt, R.ease_in((lt - (STEP - 0.3)) / 0.3))
    bump = 1 - 0.025 * math.sin(math.pi * R.clamp(lt / 0.35)) if idx else 1
    place_phone(frame, scr, cx, cy + fy, PH_SCALE * bump, TILT + fa, t)
    # titles
    t_out = STEP - 0.35
    ey = text_img(f"PASO {idx + 1:02d} / {len(STEPS):02d}", R.font(R.INTER_B, 28), ACC_LIGHT)
    slide_text(frame, ey, 70, 232, lt, 0.05, t_out)
    slide_text(frame, text_img(l1, R.font(INTER_BLACK, 92), WHITE), 66, 278, lt, 0.12, t_out)
    slide_text(frame, text_img(l2, R.font(INTER_BLACK, 92), ACC_LIGHT), 66, 384, lt, 0.22, t_out)
    # detail cards
    for j, (em, label) in enumerate(cards):
        t_in = 0.9 + j * 0.45
        a = R.ease_out((lt - t_in) / 0.35) * (1 - R.ease_in((lt - (t_out - 0.1)) / 0.3))
        glass_card(frame, em, label, 50, 1020 + j * 150, max(0, a), 30 * (1 - R.ease_out((lt - t_in) / 0.35)))

def scene_outro(frame, lt, t):
    fy, fa = float_offset(t)
    p = R.ease_in(lt / 0.8)
    if p < 1:
        place_phone(frame, screen_at(len(STEPS) - 1, int(STEP * FPS)), REST_X, REST_Y + fy + 1500 * p, PH_SCALE, TILT + fa + 8 * p, t)
    f1, f2 = R.font(INTER_BLACK, 116), R.font(INTER_BLACK, 116)
    for i, (txt, col) in enumerate([("Tu coach", WHITE), ("en el", WHITE), ("bolsillo", ACC_LIGHT)]):
        im = text_img(txt, f1 if col == WHITE else f2, col)
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
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([40, 40, 40 + pw, 40 + ph], radius=ph // 2, fill=ACC + (150,))
        im = im.filter(ImageFilter.GaussianBlur(18))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([40, 40, 40 + pw, 40 + ph], radius=ph // 2, fill=ACC)
        d.text((40 + pw / 2, 40 + ph / 2), txt, font=f, fill=WHITE, anchor="mm")
        R.paste_scaled(frame, im, W / 2, 1190, 0.8 + 0.2 * R.ease_out_back(k / 0.35), R.clamp(k / 0.12))

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
    if t < 0.25:  # fade in from black
        frame = Image.blend(Image.new("RGBA", (W, H), NAVY + (255,)), frame, t / 0.25)
    if t > DUR - 0.4:
        frame = Image.blend(frame, Image.new("RGBA", (W, H), NAVY + (255,)), (t - (DUR - 0.4)) / 0.4)
    return frame.convert("RGB")


if __name__ == "__main__":
    if PREVIEW:
        for s in PREVIEW.split(","):
            render_frame(float(s)).save(os.path.join(os.path.dirname(OUT), f"v2_prev_{s}.png"))
        sys.exit()
    R.DUR, R.CUTS, R.SCENES[1]["t0"] = DUR, CUTS[1:], HOOK
    wav = os.path.join(os.path.dirname(os.path.abspath(OUT)), "v2_beat.wav")
    R.synth_audio(wav)
    n = int(DUR * FPS)
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
