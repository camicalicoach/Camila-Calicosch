"""Gancho para el Reel: el alumno haciendo el ejercicio + "¿Qué ejercicio es este?" + opciones A/B
y una cuenta regresiva para que piensen antes del spoiler.

A diferencia del gancho de historias (respuestas de la caja de preguntas), este arranca en frío.
Genera video + audio (base suave, pop por cada elemento, subida y golpe al final) y guarda el
último cuadro para el spoiler.

Uso: python3 hook_reel.py <carpeta_frames_broll> <salida.mp4>
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
P900 = os.path.join(FONTS, "Poppins-900.ttf")
P800 = os.path.join(FONTS, "Poppins-800.ttf")
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BROLL, OUT = sys.argv[1], sys.argv[2]
W, H, FPS, DUR = 1080, 1920, 30, 6.5
SRC = [(2.5, 6.7), (0.3, 2.6)]           # full rep at real speed: stand, hinge back, drive forward
T_L1, T_L2, T_EMO, T_A, T_B = 0.15, 0.45, 0.8, 1.4, 1.75
T_COUNT = 3.3                             # 3, 2, 1 countdown, one number per second


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x, s=2.4):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def text_img(txt, path, size, fill=(255, 255, 255)):
    f = ImageFont.truetype(path, size)
    l, t, r, b = f.getbbox(txt)
    pad = int(size * 0.35)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - l + 4, pad - t + 8), txt, font=f, fill=(0, 0, 0, 190))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size * 0.08)))
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=f, fill=fill, stroke_width=4, stroke_fill=(0, 0, 0))
    return im


def emoji(ch, h):
    f = ImageFont.truetype(EMOJI, 109)
    e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(e).text((10, 10), ch, font=f, embedded_color=True)
    e = e.crop(e.getbbox())
    return e.resize((int(e.width * h / e.height), h), Image.LANCZOS)


def option(letter, label):
    """Poll-style button: white pill with a coloured letter badge."""
    f = ImageFont.truetype(P800, 52)
    l, t, r, b = f.getbbox(label)
    w, h = r - l + 150, 112
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([20, 30, 20 + w, 30 + h], radius=h // 2, fill=(0, 0, 0, 120))
    im = im.filter(ImageFilter.GaussianBlur(9))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], radius=h // 2, fill=(255, 255, 255))
    d.ellipse([32, 32, 32 + h - 24, 20 + h - 12], fill=(79, 70, 229))
    fl = ImageFont.truetype(P900, 46)
    d.text((32 + (h - 24) / 2, 20 + h / 2), letter, font=fl, fill=(255, 255, 255), anchor="mm")
    d.text((20 + h + 10 - l, 20 + (h - (b - t)) / 2 - t), label, font=f, fill=(20, 26, 46))
    return im


def paste(frame, im, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    if alpha <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda a: int(a * alpha)))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


L1 = text_img("¿QUÉ EJERCICIO", P900, 108)
L2 = text_img("ES ESTE?", P900, 130)
EMO = emoji("🤔", 130)
OPT_A = option("A", "Peso muerto")
OPT_B = option("B", "Hip thrust")
TOP_SHADE = Image.new("RGBA", (W, H), (0, 0, 0, 0))
for y in range(760):
    ImageDraw.Draw(TOP_SHADE).line([(0, y), (W, y)], fill=(0, 0, 0, int(150 * (1 - y / 760) ** 1.5)))


def src_time(t):
    total = sum(b - a for a, b in SRC)
    pos = t / DUR * total
    for a, b in SRC:
        if pos <= b - a:
            return a + pos
        pos -= b - a
    return SRC[-1][1]


def render(t):
    i = max(1, min(229, int(round(src_time(t) * FPS)) + 1))
    base = Image.open(f"{BROLL}/{i:04d}.jpg").convert("RGB")
    z = 1.04 + 0.04 * t / DUR  # slow push-in
    w, h = int(W * z), int(H * z)
    base = base.resize((w, h), Image.BILINEAR).crop(((w - W) // 2, (h - H) // 3, (w - W) // 2 + W, (h - H) // 3 + H))
    fr = base.convert("RGBA")
    fr.alpha_composite(TOP_SHADE)
    for img, ti, cy in ((L1, T_L1, 330), (L2, T_L2, 470)):
        k = t - ti
        if k >= 0:
            paste(fr, img, W / 2, cy, 1.35 - 0.35 * ease_out(k / 0.18), clamp(k / 0.06))
    k = t - T_EMO
    if k >= 0 and t < T_COUNT:
        paste(fr, EMO, W / 2, 640, ease_back(k / 0.35), clamp(k / 0.08), 10 * math.sin(t * 6) * ease_out(k / 0.4))
    for img, ti, cx in ((OPT_A, T_A, W / 2), (OPT_B, T_B, W / 2)):
        k = t - ti
        if k >= 0:
            cy = 1380 if img is OPT_A else 1530
            paste(fr, img, cx, cy, ease_back(k / 0.3), clamp(k / 0.08))
    k = t - T_COUNT
    if 0 <= k < 3.0:
        n = 3 - int(k)
        frac = k - int(k)
        ring = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
        d = ImageDraw.Draw(ring)
        d.ellipse([10, 10, 210, 210], fill=(14, 19, 36, 200))
        d.arc([10, 10, 210, 210], -90, -90 + 360 * (1 - frac), fill=(255, 221, 64), width=14)
        d.text((110, 112), str(n), font=ImageFont.truetype(P900, 110), fill=(255, 255, 255), anchor="mm")
        paste(fr, ring, W / 2, 660, 1.25 - 0.25 * ease_out(frac / 0.15), clamp(k / 0.1))
    return fr.convert("RGB")


def audio(path):
    sr = 44100
    n = int(sr * DUR)
    L, R = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(8)

    def add(sig, t, g=1.0, pan=0.0):
        i = int(t * sr); j = min(n, i + len(sig))
        if i < n:
            L[i:j] += sig[: j - i] * g * (1 - max(0, pan)); R[i:j] += sig[: j - i] * g * (1 + min(0, pan))

    def pop(f0):
        t = np.arange(int(sr * 0.12)) / sr
        s = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 1.2 * np.exp(-t * 60))) / sr) * np.exp(-t * 38)
        s[:40] += rng.normal(0, 0.6, 40) * np.linspace(1, 0, 40)
        return s

    def thump(f0, f1, dec):
        t = np.arange(int(sr * 0.5)) / sr
        s = np.sin(2 * np.pi * np.cumsum(f1 + f0 * np.exp(-t * 14)) / sr) * np.exp(-t * dec)
        s += 0.4 * np.tanh(3 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 22)
        return s

    pt = np.arange(int(sr * 0.22)) / sr
    notes = [440.0, 523.25, 659.25, 523.25]
    for k in range(int(DUR / 0.25)):
        f = notes[k % 4]
        add((np.sin(2 * np.pi * f * pt) + 0.3 * np.sin(4 * np.pi * f * pt)) * np.exp(-pt * 18), k * 0.25, 0.10,
            0.3 if k % 2 else -0.3)
    ht = np.arange(int(sr * 0.05)) / sr
    hat = np.diff(rng.normal(0, 1, len(ht) + 1)) * np.exp(-ht * 70)
    for k in range(int(DUR / 0.5)):
        add(hat, k * 0.5 + 0.25, 0.10, 0.2)
    add(thump(180, 60, 6), T_L1, 0.55)
    add(thump(200, 60, 6), T_L2, 0.6)
    add(pop(700), T_EMO, 0.5)
    add(pop(560), T_A, 0.55, -0.25)
    add(pop(660), T_B, 0.55, 0.25)
    tick = np.sin(2 * np.pi * 1500 * np.arange(int(sr * 0.05)) / sr) * np.exp(-np.arange(int(sr * 0.05)) / sr * 90)
    for k in range(3):
        add(tick, T_COUNT + k, 0.5)
    rt = np.arange(int(sr * 1.3)) / sr
    add(np.convolve(rng.normal(0, 1, len(rt)), [1, -1], "same") * (rt / rt[-1]) ** 2.5, DUR - 1.35, 0.18)
    out = np.tanh(np.stack([L, R], 1) * 1.4)
    out /= np.max(np.abs(out)) / 0.89
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        for s in os.environ["PREVIEW"].split(","):
            render(float(s)).save(os.path.join(os.path.dirname(OUT), f"hookreel_{s}.png"))
        sys.exit()
    wav = OUT + ".wav"
    audio(wav)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                          "-filter_complex", "[1:a]loudnorm=I=-11:TP=-1:LRA=9[a]", "-map", "0:v", "-map", "[a]",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", OUT],
                         stdin=subprocess.PIPE)
    last = None
    for i in range(int(DUR * FPS)):
        last = render(i / FPS)
        p.stdin.write(last.tobytes())
    p.stdin.close(); p.wait()
    last.save(os.path.splitext(OUT)[0] + "_last.png")
    os.remove(wav)
    print("done", OUT)
