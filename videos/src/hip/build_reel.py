"""Arma la parte explicativa del Reel "No es peso muerto" y el cierre.

Toma las tomas de Camila hablando (copias 1080x1920), saca las pausas, agrega subtítulos
palabra por palabra (Whisper), intercala la toma del alumno con flechas, las ilustraciones
de hip thrust / peso muerto, etiquetas de beneficios y un cierre con llamado a comentar.

Uso: python3 build_reel.py <carpeta_hip> <salida.mp4>
  <carpeta_hip> contiene proxy/, audio/, transcripts/, broll/ y raw/ (imágenes).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
P900 = os.path.join(FONTS, "Poppins-900.ttf")
P800 = os.path.join(FONTS, "Poppins-800.ttf")
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
D, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
RED, GREEN, YELLOW = (229, 57, 70), (34, 177, 96), (255, 221, 64)
ACC = (79, 70, 229)
OUTRO = 4.0

# --- edit decision list: (take, start, end) in source seconds, pauses removed
EDL = [
    ("IMG_2246", 0.00, 6.10),
    ("IMG_2248", 0.00, 2.30), ("IMG_2248", 2.80, 3.25),
    ("IMG_2246", 6.45, 8.40),
    ("IMG_2251", 0.00, 3.10), ("IMG_2251", 3.35, 5.60), ("IMG_2251", 5.80, 10.45),
    ("IMG_2253", 0.85, 3.62), ("IMG_2253", 3.88, 6.63), ("IMG_2253", 6.86, 8.30),
    ("IMG_2253", 8.49, 10.75), ("IMG_2253", 10.95, 12.59), ("IMG_2253", 12.82, 17.30),
    ("IMG_2254", 0.15, 3.72), ("IMG_2254", 3.98, 6.21), ("IMG_2254", 6.47, 7.26),
    ("IMG_2254", 7.57, 10.98), ("IMG_2254", 11.18, 12.31), ("IMG_2254", 12.61, 17.70),
]
FIX = {"comience": "comienza", "truss": "thrust", "necesitas": "necesitás", "cargas": "cargás",
       "está trabajando": "estás trabajando"}

# output start time of every piece
starts, t = [], 0.0
for take, s, e in EDL:
    starts.append(t)
    t += round((e - s) * FPS) / FPS
BODY = t
DUR = BODY + OUTRO


def out_t(take, src):
    """Map a source time in a take to output time (first piece that contains it)."""
    for (tk, s, e), st in zip(EDL, starts):
        if tk == take and s - 0.05 <= src <= e + 0.05:
            return st + min(max(src - s, 0), e - s)
    best = min(((abs(src - s), st) for (tk, s, e), st in zip(EDL, starts) if tk == take))
    return best[1]


# --- words -> caption chunks on the output timeline
def load_words():
    words = []
    pieces = list(zip(EDL, starts))
    for take in dict.fromkeys(tk for tk, _, _ in EDL):
        r = json.load(open(f"{D}/transcripts/{take}.json"))
        for seg in r["segments"]:
            for w in seg["words"]:
                # assign each word to the piece of its take it overlaps most
                best, ov = None, 0.02
                for (tk, s, e), st in pieces:
                    o = min(e, w["end"]) - max(s, w["start"])
                    if tk == take and o > ov:
                        best, ov = (s, e, st), o
                if best:
                    s, e, st = best
                    words.append(dict(text=w["word"].strip(), t0=st + max(0, w["start"] - s),
                                      t1=st + min(e - s, w["end"] - s)))
    words.sort(key=lambda w: w["t0"])
    # spelling fixes (Whisper mishears a few words)
    for i, w in enumerate(words):
        key = w["text"].strip(".,").lower()
        if key in FIX:
            w["text"] = FIX[key] + w["text"][len(key):]
        if key == "está" and i + 1 < len(words) and words[i + 1]["text"].lower().startswith("trabajando"):
            w["text"] = "estás"
    return words


def chunk(words):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        n_chars = sum(len(x["text"]) for x in cur)
        if len(cur) >= 3 or n_chars > 16 or w["text"][-1:] in ",.?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0]["t0"] if i + 1 < len(chunks) else c[-1]["t1"] + 0.3
        for w in c:
            w["text"] = w["text"].strip(".,")
        c[0]["show"], c[-1]["hide"] = c[0]["t0"], end
    return chunks


CHUNKS = chunk(load_words())


# --- drawing helpers
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x, s=2.2):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


_fc = {}
def font(p, s):
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


_ec = {}
def emoji(ch, h):
    if (ch, h) not in _ec:
        f = ImageFont.truetype(EMOJI, 109)
        e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(e).text((10, 10), ch, font=f, embedded_color=True)
        e = e.crop(e.getbbox())
        _ec[(ch, h)] = e.resize((int(e.width * h / e.height), h), Image.LANCZOS)
    return _ec[(ch, h)]


def paste(frame, im, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda a: int(a * alpha)))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


_pc = {}
def pill(text, bg, size=50, em=None):
    key = (text, bg, size, em)
    if key in _pc:
        return _pc[key]
    f = font(P800, size)
    l, t, r, b = f.getbbox(text)
    e = emoji(em, int(size * 1.05)) if em else None
    ew = e.width + 16 if e else 0
    w, h = r - l + 60 + ew, int(size * 1.75)
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([20, 28, 20 + w, 28 + h], radius=h // 2, fill=(0, 0, 0, 110))
    im = im.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], radius=h // 2, fill=bg)
    x = 20 + 30
    if e:
        im.alpha_composite(e, (x, 20 + (h - e.height) // 2)); x += ew
    d.text((x - l, 20 + (h - (b - t)) // 2 - t), text, font=f, fill=(255, 255, 255))
    _pc[key] = im
    return im


def card(path, width):
    src = Image.open(path).convert("RGB")
    pad = 26
    inner = src.resize((width - 2 * pad, int(src.height * (width - 2 * pad) / src.width)), Image.LANCZOS)
    w, h = width, inner.height + 2 * pad
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([30, 44, 30 + w, 44 + h], radius=34, fill=(0, 0, 0, 120))
    im = im.filter(ImageFilter.GaussianBlur(14))
    ImageDraw.Draw(im).rounded_rectangle([30, 30, 30 + w, 30 + h], radius=34, fill=(255, 255, 255))
    im.paste(inner, (30 + pad, 30 + pad))
    return im


DEADLIFT = card(f"{D}/raw/IMG_2073.JPG", 960)
HIPTHRUST = card(f"{D}/raw/IMG_2070.JPG", 960)


def cover(img):
    s = max(W / img.width, H / img.height)
    im = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    return im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))


TOP_STILL = cover(Image.open(f"{D}/raw/IMG_2075.PNG").convert("RGB"))


def broll(src_t):
    i = int(round(src_t * FPS)) + 1
    i = max(1, min(229, i))
    return Image.open(f"{D}/broll/{i:04d}.jpg").convert("RGB")


def arrow(frame, x0, y0, x1, y1, color, width=22, k=1.0):
    """Animated arrow growing from (x0,y0) to (x1,y1)."""
    if k <= 0:
        return
    x1, y1 = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ang = math.atan2(y1 - y0, x1 - x0)
    hl = width * 2.4
    bx, by = x1 - hl * math.cos(ang), y1 - hl * math.sin(ang)
    for c, wd in (((0, 0, 0, 120), width + 10), (color + (255,), width)):
        d.line([(x0, y0), (bx, by)], fill=c, width=wd)
        pts = [(x1, y1), (bx + hl * 0.75 * math.sin(ang), by - hl * 0.75 * math.cos(ang)),
               (bx - hl * 0.75 * math.sin(ang), by + hl * 0.75 * math.cos(ang))]
        d.polygon(pts, fill=c)
    frame.alpha_composite(layer)


# --- timeline of overlays (output seconds)
T = dict(
    broll_a=(out_t("IMG_2246", 2.45), out_t("IMG_2246", 6.10)),
    dead=(out_t("IMG_2251", 1.24), out_t("IMG_2251", 10.45)),
    dead_hard=out_t("IMG_2251", 3.56),
    broll_b=(out_t("IMG_2253", 0.85), out_t("IMG_2253", 7.70)),
    top=(out_t("IMG_2253", 7.70), out_t("IMG_2253", 14.70)),
    glute=out_t("IMG_2253", 11.30),
    hip=(out_t("IMG_2253", 15.36), out_t("IMG_2254", 4.54)),
    tags=[(out_t("IMG_2254", 4.70), "Sin barra ni banco"),
          (out_t("IMG_2254", 9.54), "Zona media y equilibrio"),
          (out_t("IMG_2254", 11.36), "No carga la espalda"),
          (out_t("IMG_2254", 12.72), "Ideal para personas mayores")],
)


def broll_src(seq, t, t0, t1):
    """Play a list of (src_start, src_end) ranges stretched over [t0, t1]."""
    total = sum(b - a for a, b in seq)
    pos = (t - t0) / (t1 - t0) * total
    for a, b in seq:
        if pos <= b - a:
            return a + pos
        pos -= b - a
    return seq[-1][1]


def draw_captions(frame, t):
    for c in CHUNKS:
        if c[0]["show"] <= t < c[-1]["hide"]:
            f = font(P800, 74)
            parts, x = [], 0
            space = f.getlength(" ")
            for w in c:
                wd = f.getlength(w["text"])
                parts.append((w, x, wd)); x += wd + space
            total = x - space
            k = ease_out((t - c[0]["show"]) / 0.12)
            y = 1440 + 20 * (1 - k)
            x0 = (W - total) / 2
            layer = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            for w, xo, wd in parts:
                active = w["t0"] <= t < max(w["t1"], w["t0"] + 0.12)
                d.text((x0 + xo, 100), w["text"], font=f, anchor="lm",
                       fill=YELLOW if active else (255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0))
            if k < 0.99:
                layer.putalpha(layer.getchannel("A").point(lambda a: int(a * k)))
            frame.alpha_composite(layer, (0, int(y - 100)))
            return


def zoom(img, z, cy_bias=0.42):
    if z == 1.0:
        return img
    w, h = int(W * z), int(H * z)
    im = img.resize((w, h), Image.BILINEAR)
    x0 = (w - W) // 2
    y0 = int((h - H) * cy_bias)
    return im.crop((x0, y0, x0 + W, y0 + H))


def overlay(frame, t):
    # 1) student B-roll during "comienza de pie, lleva la cadera hacia atrás y empuja..."
    a0, a1 = T["broll_a"]
    if a0 <= t < a1:
        src = broll_src([(3.6, 6.7), (0.3, 2.4)], t, a0, a1)
        frame.paste(broll(src).convert("RGBA"), (0, 0))
        paste(frame, pill("Hip thrust de pie con banda", ACC, 50), W / 2, 300, ease_back((t - a0) / 0.35), clamp((t - a0) / 0.1))
    # 2) deadlift card
    d0, d1 = T["dead"]
    if d0 <= t < d1:
        k = ease_back((t - d0) / 0.4) * (1 - ease_out((t - (d1 - 0.25)) / 0.25))
        paste(frame, DEADLIFT, W / 2, 1095, 0.6 + 0.4 * k, clamp(k))
        if t < T["dead_hard"]:
            paste(frame, pill("El peso tira hacia ABAJO", RED, 50, "⬇️"), W / 2, 800, ease_back((t - d0 - 0.2) / 0.35), clamp((t - d0 - 0.2) / 0.1))
        else:
            paste(frame, pill("Más difícil: ABAJO", RED, 50, "⬇️"), W / 2, 800, ease_back((t - T["dead_hard"]) / 0.35), 1.0)
    # 3) student B-roll with band arrow
    b0, b1 = T["broll_b"]
    if b0 <= t < b1:
        src = broll_src([(3.6, 6.7), (0.3, 2.6)], t, b0, b1)
        frame.paste(broll(src).convert("RGBA"), (0, 0))
        arrow(frame, 470, 1000, 150, 1000, GREEN, 24, ease_out((t - b0 - 0.2) / 0.5))
        paste(frame, pill("La banda tira hacia ATRÁS", GREEN, 50, "⬅️"), W / 2, 300, ease_back((t - b0) / 0.35), clamp((t - b0) / 0.1))
    # 4) top position still
    s0, s1 = T["top"]
    if s0 <= t < s1:
        z = 1.0 + 0.06 * (t - s0) / (s1 - s0)
        frame.paste(zoom(TOP_STILL, z, 0.4).convert("RGBA"), (0, 0))
        paste(frame, pill("Más difícil: ARRIBA", GREEN, 50, "⬆️"), W / 2, 300, ease_back((t - s0) / 0.35), clamp((t - s0) / 0.1))
        if t >= T["glute"]:
            paste(frame, pill("Glúteo en contracción máxima", ACC, 46, "🍑"), W / 2, 420, ease_back((t - T["glute"]) / 0.35), clamp((t - T["glute"]) / 0.1))
    # 5) hip thrust card
    h0, h1 = T["hip"]
    if h0 <= t < h1:
        k = ease_back((t - h0) / 0.4) * (1 - ease_out((t - (h1 - 0.25)) / 0.25))
        paste(frame, HIPTHRUST, W / 2, 1040, 0.6 + 0.4 * k, clamp(k))
        paste(frame, pill("Hip thrust en banco", ACC, 50), W / 2, 700, ease_back((t - h0 - 0.2) / 0.35), clamp((t - h0 - 0.2) / 0.1))
    # 6) benefit tags
    for i, (ti, label) in enumerate(T["tags"]):
        if t >= ti:
            k = ease_out((t - ti) / 0.3)
            im = pill(label, (20, 26, 46), 44, "✅")
            frame.alpha_composite(im if k > 0.99 else _fade(im, k), (int(40 - 60 * (1 - k)), 820 + i * 128))


def _fade(im, k):
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda a: int(a * k)))
    return im


def outro(last, t):
    k = ease_out(t / 0.4)
    bg = last.filter(ImageFilter.GaussianBlur(18 * k))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (8, 8, 14)), 0.6 * k).convert("RGBA")
    lines = [("¿Vos también", (255, 255, 255)), ("pensaste que era", (255, 255, 255)), ("peso muerto?", YELLOW)]
    for i, (txt, col) in enumerate(lines):
        ki = t - 0.25 - i * 0.15
        if ki >= 0:
            f = font(P900, 104)
            l, tt, r, b = f.getbbox(txt)
            im = Image.new("RGBA", (r - l + 60, b - tt + 60), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((30 - l, 30 - tt), txt, font=f, fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
            paste(bg, im, W / 2, 640 + i * 140, 1.3 - 0.3 * ease_out(ki / 0.2), clamp(ki / 0.08))
    if t > 0.9:
        paste(bg, emoji("👀", 110), W / 2, 1040, ease_back((t - 0.9) / 0.35), clamp((t - 0.9) / 0.1))
    if t > 1.3:
        paste(bg, pill("Comentá", RED, 58, "👇"), W / 2, 1230, ease_back((t - 1.3) / 0.35), clamp((t - 1.3) / 0.1))
    if t > 1.7:
        paste(bg, pill("@camicali.coach", ACC, 46), W / 2, 1380, ease_back((t - 1.7) / 0.35), clamp((t - 1.7) / 0.1))
    return bg


def frames_of(take, s, e):
    n = round((e - s) * FPS)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s:.3f}", "-i", f"{D}/proxy/{take}.mp4",
                          "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    last = None
    for _ in range(n):
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            buf = last
        last = buf
        yield Image.frombytes("RGB", (W, H), buf)
    p.stdout.close(); p.wait()


# --- audio: voice pieces + soft music bed
def build_audio(path):
    sr = 44100
    voice = []
    for take, s, e in EDL:
        n = round((e - s) * FPS) / FPS
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{s:.3f}", "-t", f"{n:.3f}", "-i",
                                       f"{D}/proxy/{take}.mp4", "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"])
        x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
        x = np.pad(x, (0, max(0, int(n * sr) - len(x))))[: int(n * sr)]
        f = int(0.012 * sr)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        voice.append(x)
    v = np.concatenate(voice)
    v = np.pad(v, (0, int(DUR * sr) - len(v)))
    v /= max(1e-6, np.percentile(np.abs(v), 99.5)) / 0.6
    n = len(v)
    tt = np.arange(n) / sr
    bed = np.zeros(n)
    pt = np.arange(int(sr * 0.22)) / sr
    notes = [440.0, 523.25, 659.25, 523.25]
    for k in range(int(DUR / 0.25)):
        f = notes[k % 4]
        tone = (np.sin(2 * np.pi * f * pt) + 0.3 * np.sin(4 * np.pi * f * pt)) * np.exp(-pt * 18)
        i = int(k * 0.25 * sr); j = min(n, i + len(tone))
        bed[i:j] += tone[: j - i]
    rng = np.random.default_rng(2)
    ht = np.arange(int(sr * 0.05)) / sr
    hat = np.diff(rng.normal(0, 1, len(ht) + 1)) * np.exp(-ht * 70)
    for k in range(int(DUR / 0.5)):
        i = int((k * 0.5 + 0.25) * sr); j = min(n, i + len(hat))
        bed[i:j] += 0.6 * hat[: j - i]
    gain = np.where(tt < BODY, 0.05, 0.16)  # quiet under the voice, up in the outro
    out = v + bed * gain
    k = int(sr * 0.8)
    out[-k:] *= np.linspace(1, 0, k)
    out = np.tanh(out * 1.1)
    out /= np.max(np.abs(out)) / 0.89
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())


def render_all():
    wav = OUT + ".wav"
    build_audio(wav)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                          "-filter_complex", "[1:a]loudnorm=I=-12:TP=-1:LRA=9,aformat=channel_layouts=stereo[a]",
                          "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest",
                          "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    i, prev_take, piece_in_take, last = 0, None, 0, None
    for (take, s, e), st in zip(EDL, starts):
        piece_in_take = piece_in_take + 1 if take == prev_take else 0
        prev_take = take
        z = 1.0 if piece_in_take % 2 == 0 else 1.08  # punch-in on jump cuts
        for img in frames_of(take, s, e):
            t = i / FPS
            fr = zoom(img, z).convert("RGBA")
            overlay(fr, t)
            draw_captions(fr, t)
            p.stdin.write(fr.convert("RGB").tobytes())
            last = img; i += 1
            if i % 150 == 0:
                print(f"frame {i}/{int(DUR * FPS)}", flush=True)
    for k in range(int(OUTRO * FPS)):
        p.stdin.write(outro(last, k / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("done", OUT, f"{DUR:.2f}s")


def preview(t):
    if t >= BODY:
        last = next(frames_of(EDL[-1][0], EDL[-1][2] - 0.05, EDL[-1][2]))
        return outro(last, t - BODY).convert("RGB")
    idx = max(i for i, st in enumerate(starts) if st <= t)
    take, s, e = EDL[idx]
    k = sum(1 for j in range(idx) if EDL[j][0] == take and all(EDL[m][0] == take for m in range(j, idx)))
    img = next(frames_of(take, s + (t - starts[idx]), e))
    fr = zoom(img, 1.0 if k % 2 == 0 else 1.08).convert("RGBA")
    overlay(fr, t)
    draw_captions(fr, t)
    return fr.convert("RGB")


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        for v in os.environ["PREVIEW"].split(","):
            preview(float(v)).save(os.path.join(os.path.dirname(OUT), f"reel_{v}.png"))
        sys.exit()
    if os.environ.get("INFO"):
        print(f"body {BODY:.2f}s, total {DUR:.2f}s")
        for k, v in T.items():
            print(k, v)
        for c in CHUNKS:
            print(f"{c[0]['show']:6.2f} {' '.join(w['text'] for w in c)}")
        sys.exit()
    render_all()
