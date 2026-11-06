"""Clip "SPOILER: NO es peso muerto ❌" que sigue al gancho.

Arranca del último cuadro del gancho (zoom + desenfoque + oscurecer) y anima el texto con
la misma estética del gancho (Poppins blanca con sombra). Genera también su audio.

Uso: python3 spoiler.py <ultimo_cuadro_gancho.png> <salida.mp4>
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
P900 = os.path.join(FONTS, "Poppins-900.ttf")
P800 = os.path.join(FONTS, "Poppins-800.ttf")
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
SRC, OUT = sys.argv[1], sys.argv[2]
W, H, FPS, DUR = 1080, 1920, 30, 3.5
RED = (229, 57, 70)
T_PILL, T_NO, T_PESO, T_X, T_SUB = 0.25, 0.6, 0.8, 1.05, 1.6


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_out_back(x, s=2.4):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def text_img(txt, path, size, fill=(255, 255, 255)):
    f = ImageFont.truetype(path, size)
    l, t, r, b = f.getbbox(txt)
    pad = int(size * 0.35)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - l + 4, pad - t + 8), txt, font=f, fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size * 0.08)))
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=f, fill=fill)
    return im


def emoji(ch, h):
    f = ImageFont.truetype(EMOJI, 109)
    e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(e).text((10, 10), ch, font=f, embedded_color=True)
    e = e.crop(e.getbbox())
    return e.resize((int(e.width * h / e.height), h), Image.LANCZOS)


def pill(txt):
    f = ImageFont.truetype(P900, 74)
    l, t, r, b = f.getbbox(txt)
    w, h = r - l + 90, b - t + 56
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([20, 28, 20 + w, 28 + h], radius=26, fill=(0, 0, 0, 110))
    im = im.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], radius=26, fill=RED)
    d.text((20 + 45 - l, 20 + 28 - t), txt, font=f, fill=(255, 255, 255))
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


BASE = Image.open(SRC).convert("RGB")
BLURRED = [None] * 16
PILL = pill("SPOILER")
NO = text_img("NO ES", P900, 150)
PESO = text_img("PESO MUERTO", P900, 128)
X = emoji("❌", 190)
SUB = text_img("Es un hip thrust de pie", P800, 58)
POINT = emoji("👇", 56)


def background(t):
    k = ease_out(t / 0.4)
    z = 1.0 + 0.12 * k + 0.02 * (t / DUR)
    w, h = int(W * z), int(H * z)
    im = BASE.resize((w, h), Image.BILINEAR).crop(((w - W) // 2, (h - H) // 2, (w - W) // 2 + W, (h - H) // 2 + H))
    r = 16 * k
    if r > 0.3:
        im = im.filter(ImageFilter.GaussianBlur(r))
    dark = Image.new("RGB", (W, H), (8, 8, 14))
    return Image.blend(im, dark, 0.55 * k).convert("RGBA")


def render(t):
    fr = background(t)
    # camera shake on the two impacts
    shake = 0
    for ti, amp in ((T_NO, 10), (T_X, 18)):
        if 0 <= t - ti < 0.25:
            shake += amp * math.sin((t - ti) * 90) * (1 - (t - ti) / 0.25)
    cy0 = 860 + shake
    k = t - T_PILL
    if k >= 0:
        paste(fr, PILL, W / 2, cy0 - 230, 1.4 - 0.4 * ease_out_back(k / 0.3), clamp(k / 0.08), -4 * ease_out(k / 0.3))
    k = t - T_NO
    if k >= 0:
        paste(fr, NO, W / 2, cy0 - 40, 1.35 - 0.35 * ease_out(k / 0.18), clamp(k / 0.06))
    k = t - T_PESO
    if k >= 0:
        paste(fr, PESO, W / 2, cy0 + 120, 1.35 - 0.35 * ease_out(k / 0.18), clamp(k / 0.06))
    k = t - T_X
    if k >= 0:
        paste(fr, X, W / 2, cy0 + 330, 2.2 - 1.2 * ease_out_back(k / 0.3, 1.6), clamp(k / 0.06), 12 * (1 - ease_out(k / 0.3)))
    k = t - T_SUB
    if k >= 0:
        a = ease_out(k / 0.35)
        line = Image.new("RGBA", (SUB.width + POINT.width, max(SUB.height, POINT.height)), (0, 0, 0, 0))
        line.alpha_composite(SUB, (0, (line.height - SUB.height) // 2))
        line.alpha_composite(POINT, (SUB.width - int(58 * 0.35) + 14, (line.height - POINT.height) // 2))
        paste(fr, line, W / 2, cy0 + 520 + 30 * (1 - a), 1.0, a)
    if t < 0.08:  # quick white flash on the cut
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.6 * (1 - t / 0.08))
    return fr.convert("RGB")


def audio(path):
    sr = 44100
    n = int(sr * DUR)
    L, R = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(4)

    def add(sig, t, g=1.0, pan=0.0):
        i = int(t * sr); j = min(n, i + len(sig))
        L[i:j] += sig[: j - i] * g * (1 - max(0, pan)); R[i:j] += sig[: j - i] * g * (1 + min(0, pan))

    wt = np.arange(int(sr * 0.4)) / sr  # whoosh
    wn = rng.normal(0, 1, len(wt))
    whoosh = np.convolve(wn, np.ones(12) / 12, "same") * np.sin(np.pi * wt / wt[-1]) ** 2
    add(whoosh, 0.0, 0.9)

    def impact(f0, f1, dec, noise):
        t = np.arange(int(sr * 0.7)) / sr
        s = np.sin(2 * np.pi * np.cumsum(f1 + f0 * np.exp(-t * 14)) / sr) * np.exp(-t * dec)
        s += 0.4 * np.tanh(3 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 22)
        s += noise * np.convolve(rng.normal(0, 1, len(t)), [1, -1], "same") * np.exp(-t * 30)
        return s

    add(impact(160, 60, 6, 0.4), T_PILL, 0.35)
    add(impact(200, 60, 5, 0.5), T_NO, 0.7)
    add(impact(200, 55, 5, 0.5), T_PESO, 0.55)
    add(impact(260, 50, 3.5, 0.9), T_X, 0.95)  # stamp
    # soft pluck bed coming back after the stamp
    pt = np.arange(int(sr * 0.22)) / sr
    notes = [440.0, 523.25, 659.25, 523.25]
    for k in range(int((DUR - 1.3) / 0.25)):
        f = notes[k % 4]
        add((np.sin(2 * np.pi * f * pt) + 0.3 * np.sin(4 * np.pi * f * pt)) * np.exp(-pt * 18), 1.3 + k * 0.25, 0.12,
            0.3 if k % 2 else -0.3)
    out = np.tanh(np.stack([L, R], 1) * 1.4)
    out /= np.max(np.abs(out)) / 0.89
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        for s in os.environ["PREVIEW"].split(","):
            render(float(s)).save(os.path.join(os.path.dirname(OUT), f"spoiler_{s}.png"))
        sys.exit()
    wav = OUT + ".wav"
    audio(wav)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                          "-filter_complex", "[1:a]loudnorm=I=-11:TP=-1:LRA=9[a]", "-map", "0:v", "-map", "[a]",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", OUT],
                         stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("done", OUT)
