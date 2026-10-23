"""Reel explicativo de la app: grabación de pantalla dentro de un celular + títulos animados.

Uso: python3 app_video.py <carpeta_segmentos> <salida.mp4>
La carpeta tiene un subdirectorio por paso (inicio, entrenar, ...) con frames JPG a 30 fps.
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render as R  # paleta, fuentes y helpers del Reel anterior

SEG_DIR, OUT = sys.argv[1], sys.argv[2]
PREVIEW = os.environ.get("PREVIEW")
W, H, FPS = R.W, R.H, R.FPS
BG, INK, ACC, SOFT, WHITE = R.BG, R.INK, R.ACC, R.SOFT, R.WHITE

HOOK, STEP, OUTRO = 3.0, 5.0, 4.5
STEPS = [
    ("inicio", "TU DÍA A DÍA", "Ves qué te toca entrenar hoy"),
    ("entrenar", "ENTRENÁS CON TU RUTINA", "Cada ejercicio con series, kilos y repes"),
    ("guardar", "GUARDÁS Y ME CONTÁS", "Terminás y me dejás tu comentario"),
    ("plan", "TU PLANIFICACIÓN", "Calendario, turnos y pagos en un lugar"),
    ("evolucion", "MIRÁS TU EVOLUCIÓN", "Entrenamientos, medidas y fotos"),
    ("chat", "HABLÁS CONMIGO", "Chat directo con tu coach"),
]
DUR = HOOK + STEP * len(STEPS) + OUTRO
CUTS = [HOOK + STEP * i for i in range(len(STEPS) + 1)]

# ---------------------------------------------------------------- phone mockup
SCR_W, SCR_H = 648, 1262
BEZEL = 20
PH_W, PH_H = SCR_W + 2 * BEZEL, SCR_H + 2 * BEZEL
PHONE_Y = 520  # top of the phone when resting


def _round_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


SCR_MASK = _round_mask(SCR_W, SCR_H, 52)
PHONE_BODY = Image.new("RGBA", (PH_W, PH_H), (0, 0, 0, 0))
ImageDraw.Draw(PHONE_BODY).rounded_rectangle([0, 0, PH_W - 1, PH_H - 1], radius=70, fill=INK)
SHADOW = Image.new("RGBA", (PH_W + 160, PH_H + 160), (0, 0, 0, 0))
ImageDraw.Draw(SHADOW).rounded_rectangle([80, 100, PH_W + 80, PH_H + 100], radius=70, fill=(20, 26, 46, 70))
SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(36))

_frames = {}
def seg_frame(name, i):
    files = _frames.setdefault(name, sorted(os.listdir(os.path.join(SEG_DIR, name))))
    i = max(0, min(len(files) - 1, i))
    return Image.open(os.path.join(SEG_DIR, name, files[i])).convert("RGB")


def phone(screen):
    ph = PHONE_BODY.copy()
    scr = screen.convert("RGBA")
    scr.putalpha(SCR_MASK)
    ph.alpha_composite(scr, (BEZEL, BEZEL))
    return ph


def place_phone(frame, ph, y, scale=1.0, alpha=1.0):
    if scale != 1.0:
        ph = ph.resize((int(PH_W * scale), int(PH_H * scale)), Image.BILINEAR)
    sh = SHADOW if scale == 1.0 else SHADOW.resize((int(SHADOW.width * scale), int(SHADOW.height * scale)))
    x = (W - ph.width) // 2
    R.paste_scaled(frame, sh, W / 2, y + ph.height / 2 + 20 * scale, 1.0, alpha)
    R.paste_scaled(frame, ph, x + ph.width / 2, y + ph.height / 2, 1.0, alpha)


# ---------------------------------------------------------------- text helpers
def punch_words(frame, words, size, color, cy, lt, t0, step=0.1, maxw=900):
    """Single centred line of Anton words that pop in one after another."""
    f = R.font(R.ANTON, size)
    while sum(f.getlength(w) for w in words) + size * 0.22 * (len(words) - 1) > maxw:
        size -= 4
        f = R.font(R.ANTON, size)
    widths = [f.getlength(w) for w in words]
    x = (W - (sum(widths) + size * 0.22 * (len(words) - 1))) / 2
    for i, (w, wd) in enumerate(zip(words, widths)):
        k = lt - (t0 + i * step)
        if k >= 0:
            im, pad, tw, asc, desc = R.word_image(w, size, color)
            sc = 1.0 + 0.22 * (1 - R.ease_out(k / 0.18))
            R.paste_scaled(frame, im, x + tw / 2, cy, sc, R.clamp(k / 0.08))
        x += wd + size * 0.22


def fade_text(frame, text, fnt, color, cy, lt, t0):
    k = lt - t0
    if k < 0:
        return
    a = R.ease_out(k / 0.3)
    tw = int(fnt.getlength(text)) + 20
    im = Image.new("RGBA", (tw, int(fnt.size * 1.6)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((tw / 2, im.height / 2), text, font=fnt, fill=color, anchor="mm")
    R.paste_scaled(frame, im, W / 2, cy + 24 * (1 - a), 1.0, a)


def pill(frame, text, fnt, bg, fg, cx, cy, lt, t0):
    k = lt - t0
    if k < 0:
        return
    tw = fnt.getlength(text)
    pw, ph = int(tw + 56), int(fnt.size * 1.9)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=bg)
    d.text((pw / 2, ph / 2), text, font=fnt, fill=fg, anchor="mm")
    R.paste_scaled(frame, im, cx, cy, 0.7 + 0.3 * R.ease_out_back(k / 0.3), R.clamp(k / 0.1))


def chrome(frame, t, on_dark):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((W / 2, 205), "camicali.coach", font=R.font(R.INTER_SB, 30), anchor="mm",
           fill=(255, 255, 255, 180) if on_dark else (20, 26, 46, 120))
    n = len(STEPS)
    x0, x1, y0, hh, gap = 90, W - 90, 150, 8, 12
    seg = (x1 - x0 - (n - 1) * gap) / n
    for i in range(n):
        sx = x0 + i * (seg + gap)
        d.rounded_rectangle([sx, y0, sx + seg, y0 + hh], radius=4,
                            fill=(255, 255, 255, 90) if on_dark else (20, 26, 46, 30))
        p = R.clamp((t - CUTS[i]) / STEP)
        if p > 0:
            d.rounded_rectangle([sx, y0, sx + seg * p, y0 + hh], radius=4, fill=WHITE if on_dark else ACC)
    frame.alpha_composite(layer)


# ---------------------------------------------------------------- scenes
def hook(frame, lt):
    punch_words(frame, ["¿CÓMO", "FUNCIONA"], 150, INK, 330, lt, 0.05, 0.14)
    punch_words(frame, ["LA", "APP?"], 150, ACC, 490, lt, 0.35, 0.14)
    # phone rises from the bottom showing the home screen
    p = R.ease_out((lt - 0.8) / 0.9)
    if p > 0:
        place_phone(frame, phone(seg_frame("inicio", 0)), int(H + 40 - (H + 40 - (PHONE_Y + 160)) * p))


def step(frame, idx, lt):
    name, title, sub = STEPS[idx]
    # phone: settles from the hook position on step 1, gentle zoom while playing
    y = PHONE_Y
    if idx == 0:
        y = int(PHONE_Y + 160 * (1 - R.ease_out(lt / 0.5)))
    scale = 1.0 + 0.03 * (lt / STEP)
    place_phone(frame, phone(seg_frame(name, int(lt * FPS))), int(y - PH_H * (scale - 1) / 2), scale)
    pill(frame, f"PASO {idx + 1}", R.font(R.INTER_B, 30), ACC, WHITE, W / 2, 262, lt, 0.05)
    punch_words(frame, title.split(), 104, INK, 360, lt, 0.15, 0.1)
    fade_text(frame, sub, R.font(R.INTER_SB, 40), (20, 26, 46, 230), 455, lt, 0.6)


def outro(frame, lt):
    punch_words(frame, ["TU", "COACH"], 170, WHITE, 640, lt, 0.05, 0.14)
    punch_words(frame, ["EN", "EL", "BOLSILLO"], 170, WHITE, 830, lt, 0.35, 0.14)
    k = lt - 1.1
    if k >= 0:
        f = R.font(R.INTER_B, 52)
        txt = "Escribime y te paso el acceso"
        tw = f.getlength(txt)
        em = R.emoji_image("📲", 56)
        im = Image.new("RGBA", (int(tw + 18 + em.width) + 4, 90), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 45), txt, font=f, fill=WHITE, anchor="lm")
        im.alpha_composite(em, (int(tw + 18), 45 - em.height // 2))
        a = R.ease_out(k / 0.3)
        R.paste_scaled(frame, im, W / 2, 1010 + 30 * (1 - a), 1.0, a)
    pill(frame, "@camicali.coach", R.font(R.INTER_B, 46), WHITE, ACC, W / 2, 1170, lt, 1.5)


def render_frame(t):
    on_dark = t >= CUTS[-1]
    frame = Image.new("RGBA", (W, H), ACC + (255,)) if on_dark else R.GRAIN_BG.convert("RGBA")
    if t < HOOK:
        hook(frame, t)
    elif not on_dark:
        i = int((t - HOOK) // STEP)
        step(frame, i, t - CUTS[i])
    else:
        outro(frame, t - CUTS[-1])
    chrome(frame, t, on_dark)
    d = ImageDraw.Draw(frame)
    for c in CUTS[1:]:
        if c - 0.16 <= t < c:
            d.rectangle([0, 0, W * R.ease_in((t - (c - 0.16)) / 0.16), H], fill=ACC)
        elif c <= t < c + 0.16 and c != CUTS[-1]:
            d.rectangle([W * R.ease_out((t - c) / 0.16), 0, W, H], fill=ACC)
    return frame.convert("RGB")


if __name__ == "__main__":
    if PREVIEW:
        for s in PREVIEW.split(","):
            render_frame(float(s)).save(os.path.join(os.path.dirname(OUT), f"app_prev_{s}.png"))
        sys.exit()
    # beat: reuse the Reel synth with this timeline
    R.DUR, R.CUTS, R.SCENES[1]["t0"] = DUR, CUTS[1:], HOOK
    wav = os.path.join(os.path.dirname(os.path.abspath(OUT)), "app_beat.wav")
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
