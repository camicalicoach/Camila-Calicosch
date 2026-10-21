"""Render the '6 verdades brutales' Reel: 1080x1920, 30fps, kinetic typography."""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "reel.mp4")
PREVIEW = os.environ.get("PREVIEW")  # comma-separated seconds -> PNG stills only

W, H, FPS = 1080, 1920, 30
DUR = 37.5
BPM = 120

BG = (244, 245, 250)
INK = (20, 26, 46)
ACC = (79, 70, 229)
SOFT = (236, 235, 253)
WHITE = (255, 255, 255)

ANTON = os.path.join(FONTS, "Anton-Regular.ttf")
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

_fonts = {}
def font(path, size):
    k = (path, int(size))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, int(size))
    return _fonts[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x); return x ** 3
def ease_out_back(x, s=2.2):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1

# ---------------------------------------------------------------- scenes
# Each title line: list of (word, style). style keys: c=color, m=size mult,
# u=underline, s=strike time offset (s after scene start).
def L(*words): return list(words)
def w(t, **k): return (t, k)

SCENES = [
    dict(t0=0.0, t1=3.0, kind="hook", num=None,
         lines=[L(w("6"), w("VERDADES")),
                L(w("BRUTALES", c=ACC, m=1.35)),
                L(w("QUE"), w("NADIE"), w("TE"), w("DICE")),
                L(w("DEL"), w("GYM", u=True))],
         base=150, step=0.13, sub=None),
    dict(t0=3.0, t1=8.0, num="01",
         lines=[L(w("IR"), w("AL"), w("GYM")),
                L(w("NO"), w("ES"), w("EVOLUCIONAR", u=True))],
         sub="Sin estrategia ni progresión,\nentrenás para quedarte igual."),
    dict(t0=8.0, t1=13.0, num="02",
         lines=[L(w("NO"), w("PODÉS"), w("ENTRENAR")),
                L(w("MÁS"), w("DE"), w("LO"), w("QUE")),
                L(w("COMÉS"), w("MAL", u=True))],
         sub="El físico también se\nconstruye en la cocina."),
    dict(t0=13.0, t1=18.0, num="03",
         lines=[L(w("A"), w("NADIE"), w("LE"), w("IMPORTA")),
                L(w("CUÁNTO"), w("LEVANTÁS", u=True))],
         sub="Técnica y control > ego."),
    dict(t0=18.0, t1=23.0, num="04",
         lines=[L(w("TU"), w("CUERPO"), w("NO")),
                L(w("CAMBIA"), w("EN")),
                L(w("30", s=1.5), w("DÍAS", s=1.5))],
         swap=("12 MESES", 1.8),
         sub="Son meses de constancia.\nNo hay atajos."),
    dict(t0=23.0, t1=28.0, num="05",
         lines=[L(w("NO"), w("NECESITÁS")),
                L(w("MOTIVACIÓN.", s=1.2)),
                L(w("NECESITÁS")),
                L(w("DISCIPLINA.", c=ACC, m=1.3))],
         step=0.11, sub=None),
    dict(t0=28.0, t1=33.0, num="06",
         lines=[L(w("SI"), w("DORMÍS"), w("MAL,")),
                L(w("SABOTEÁS"), w("TUS")),
                L(w("RESULTADOS", u=True))],
         sub="El músculo crece\ncuando descansás."),
    dict(t0=33.0, t1=DUR, kind="outro", num=None,
         lines=[L(w("COMPARATE")),
                L(w("CON"), w("VOS"), w("DE")),
                L(w("HACE"), w("3"), w("MESES.", u=True))],
         base=165, step=0.14, sub=None),
]
CUTS = [s["t0"] for s in SCENES[1:]]
MAXW = 820

# ---------------------------------------------------------------- caches
_word_img = {}
def word_image(text, size, color):
    k = (text, size, color)
    if k in _word_img: return _word_img[k]
    f = font(ANTON, size)
    asc, desc = f.getmetrics()
    pad = int(size * 0.25)
    tw = int(f.getlength(text))
    im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad + asc), text, font=f, fill=color, anchor="ls")
    _word_img[k] = (im, pad, tw, asc, desc)
    return _word_img[k]

def emoji_image(ch, height):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    r = height / im.height
    return im.resize((max(1, int(im.width * r)), int(height)), Image.LANCZOS)

def make_grain():
    rng = np.random.default_rng(7)
    n = rng.normal(0, 4.0, (H, W, 1))
    base = np.array(BG, dtype=np.float32)[None, None, :] + n
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
GRAIN_BG = make_grain()

# ---------------------------------------------------------------- layout
def layout_scene(sc):
    """Return word placements, number placement, subtitle card, total block."""
    on_dark = sc.get("kind") == "outro"
    ink = WHITE if on_dark else INK
    base = sc.get("base", 150)
    # shrink base until widest line fits
    while True:
        ok = True
        for line in sc["lines"]:
            lw = 0
            for i, (t, st) in enumerate(line):
                sz = int(base * st.get("m", 1))
                lw += font(ANTON, sz).getlength(t) + (sz * 0.2 if i else 0)
            if lw > MAXW: ok = False
        if ok: break
        base -= 4
    words, y = [], 0
    for line in sc["lines"]:
        szs = [int(base * st.get("m", 1)) for _, st in line]
        lsz = max(szs)
        widths = [font(ANTON, s).getlength(t) for (t, _), s in zip(line, szs)]
        total = sum(widths) + sum(s * 0.2 for s in szs[1:])
        x = (W - total) / 2
        baseline = y + lsz * 1.02
        for (t, st), s, wd in zip(line, szs, widths):
            words.append(dict(text=t, size=s, x=x, baseline=baseline, w=wd,
                              color=st.get("c", ink), u=st.get("u"), s=st.get("s")))
            x += wd + s * 0.2
        y += lsz * 1.17
    title_h = y
    block = []  # (kind, height)
    num_h = 200 if sc.get("num") else 0
    gap1 = 30 if num_h else 0
    sub = sc.get("sub")
    sub_lines = sub.split("\n") if sub else []
    sub_size = 46
    sub_h = (len(sub_lines) * sub_size * 1.3 + 2 * 34) if sub else 0
    swap_h = 150 if sc.get("swap") else 0
    gap2 = 56 if (sub or swap_h) else 0
    total = num_h + gap1 + title_h + gap2 + swap_h + (24 if swap_h and sub else 0) + sub_h
    top = 900 - total / 2
    top = max(top, 300)
    for wd in words: wd["baseline"] += top + num_h + gap1
    return dict(words=words, num_y=top, title_top=top + num_h + gap1,
                after=top + num_h + gap1 + title_h + gap2,
                sub_lines=sub_lines, sub_size=sub_size, sub_h=sub_h, swap_h=swap_h,
                ink=ink, on_dark=on_dark)

LAYOUTS = [layout_scene(s) for s in SCENES]

# ---------------------------------------------------------------- drawing
def paste_scaled(frame, im, cx, cy, scale, alpha):
    if alpha <= 0.01: return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def draw_scene(frame, idx, lt):
    sc, lay = SCENES[idx], LAYOUTS[idx]
    d = ImageDraw.Draw(frame)
    step = sc.get("step", 0.12)
    start = 0.12 if sc.get("num") else 0.0
    # big number
    if sc.get("num"):
        p = ease_out_back(lt / 0.3)
        im, pad, tw, asc, desc = word_image(sc["num"], 200, ACC)
        bp = ((sc["t0"] + lt) % (60 / BPM)) / (60 / BPM)
        pulse = 0.045 * math.exp(-bp * 6) if lt > 0.4 else 0
        paste_scaled(frame, im, W / 2, lay["num_y"] + 100, 0.6 + 0.4 * p + pulse, clamp(lt / 0.12))
    # words
    last_in = start
    for i, wd in enumerate(lay["words"]):
        t_in = start + 0.05 + i * step
        last_in = t_in
        k = lt - t_in
        if k < 0: continue
        im, pad, tw, asc, desc = word_image(wd["text"], wd["size"], wd["color"])
        cx = wd["x"] + tw / 2
        cy = wd["baseline"] - asc + (im.height / 2 - pad)
        scale = 1.0 + 0.22 * (1 - ease_out(k / 0.18))
        paste_scaled(frame, im, cx, cy, scale, clamp(k / 0.08))
        wd["_in"] = t_in
    # underlines / strikes (after words so they sit on top)
    for wd in lay["words"]:
        if "_in" not in wd or lt < wd["_in"]: continue
        f = font(ANTON, wd["size"])
        if wd["u"]:
            p = ease_out((lt - wd["_in"] - 0.15) / 0.25)
            if p > 0:
                th = max(8, int(wd["size"] * 0.075))
                y0 = wd["baseline"] + wd["size"] * 0.06
                col = WHITE if lay["on_dark"] else ACC
                if lay["on_dark"]: col = (255, 214, 102)
                d.rounded_rectangle([wd["x"], y0, wd["x"] + wd["w"] * p, y0 + th], radius=th // 2, fill=col)
        if wd["s"] is not None:
            p = ease_out((lt - wd["s"]) / 0.18)
            if p > 0:
                cap = -f.getbbox("H", anchor="ls")[1]
                th = max(10, int(wd["size"] * 0.1))
                ym = wd["baseline"] - cap * 0.5
                d.rectangle([wd["x"] - 8, ym - th / 2, wd["x"] - 8 + (wd["w"] + 16) * p, ym + th / 2], fill=ACC)
    y = lay["after"]
    # swap pill ("30 DÍAS" -> "12 MESES")
    if sc.get("swap"):
        text, ts = sc["swap"]
        k = lt - ts
        if k >= 0:
            f = font(ANTON, 110)
            tw = f.getlength(text)
            pw, ph = tw + 90, 140
            pill = Image.new("RGBA", (int(pw), ph), (0, 0, 0, 0))
            pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=ACC)
            pd.text((pw / 2, ph / 2 + 4), text, font=f, fill=WHITE, anchor="mm")
            paste_scaled(frame, pill, W / 2, y + ph / 2, 0.7 + 0.3 * ease_out_back(k / 0.3), clamp(k / 0.1))
        y += lay["swap_h"] + 24
    # subtitle card
    if lay["sub_lines"]:
        ts = max(last_in + 0.35, 1.2) if not sc.get("swap") else 2.2
        k = lt - ts
        if k >= 0:
            a, off = ease_out(k / 0.3), 40 * (1 - ease_out(k / 0.3))
            f = font(INTER_SB, lay["sub_size"])
            lw = max(f.getlength(s) for s in lay["sub_lines"])
            cw, ch = lw + 2 * 44, lay["sub_h"]
            card = Image.new("RGBA", (int(cw), int(ch)), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=30, fill=SOFT)
            cd.rounded_rectangle([0, 0, 10, ch - 1], radius=5, fill=ACC)
            for j, s in enumerate(lay["sub_lines"]):
                cd.text((cw / 2, 34 + lay["sub_size"] * 1.3 * (j + 0.5)), s, font=f, fill=INK, anchor="mm")
            paste_scaled(frame, card, W / 2, y + ch / 2 + off, 1.0, a)

def draw_outro_extras(frame, lt):
    # CTA + handle under the headline
    lay = LAYOUTS[-1]
    y = lay["after"] + 40
    k = lt - 1.35
    if k >= 0:
        f = font(INTER_B, 54)
        txt = "Guardalo y empezá hoy"
        tw = f.getlength(txt)
        em = emoji_image("💪", 58)
        cw = int(tw + 18 + em.width)
        im = Image.new("RGBA", (cw + 4, 90), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 45), txt, font=f, fill=WHITE, anchor="lm")
        im.alpha_composite(em, (int(tw + 18), 45 - em.height // 2 - 2))
        a = ease_out(k / 0.3)
        paste_scaled(frame, im, W / 2, y + 45 + 30 * (1 - a), 1.0, a)
    k = lt - 1.8
    if k >= 0:
        f = font(INTER_B, 44)
        txt = "@camicali.coach"
        tw = f.getlength(txt)
        pw, ph = int(tw + 80), 92
        im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=WHITE)
        dd.text((pw / 2, ph / 2), txt, font=f, fill=ACC, anchor="mm")
        paste_scaled(frame, im, W / 2, y + 200, 0.8 + 0.2 * ease_out_back(k / 0.3), clamp(k / 0.1))

def draw_chrome(frame, t, idx, on_dark):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # brand tag
    f = font(INTER_SB, 30)
    d.text((W / 2, 205), "camicali.coach", font=f, anchor="mm",
           fill=(255, 255, 255, 180) if on_dark else (20, 26, 46, 120))
    # 6-segment progress bar
    x0, x1, y0, hh, gap = 90, W - 90, 150, 8, 12
    seg = (x1 - x0 - 5 * gap) / 6
    for i in range(6):
        sx = x0 + i * (seg + gap)
        track = (255, 255, 255, 90) if on_dark else (20, 26, 46, 30)
        d.rounded_rectangle([sx, y0, sx + seg, y0 + hh], radius=4, fill=track)
        sc = SCENES[i + 1]
        p = clamp((t - sc["t0"]) / (sc["t1"] - sc["t0"]))
        if p > 0:
            d.rounded_rectangle([sx, y0, sx + seg * p, y0 + hh], radius=4,
                                fill=WHITE if on_dark else ACC)
    frame.alpha_composite(layer)

def scene_at(t):
    for i, s in enumerate(SCENES):
        if s["t0"] <= t < s["t1"]: return i
    return len(SCENES) - 1

def render_frame(t):
    idx = scene_at(t)
    sc = SCENES[idx]
    on_dark = sc.get("kind") == "outro"
    frame = Image.new("RGBA", (W, H), ACC + (255,)) if on_dark else GRAIN_BG.convert("RGBA")
    lt = t - sc["t0"]
    draw_scene(frame, idx, lt)
    if on_dark: draw_outro_extras(frame, lt)
    # beat pulse: tiny zoom on hook
    draw_chrome(frame, t, idx, on_dark)
    # horizontal wipe at each cut
    d = ImageDraw.Draw(frame)
    for c in CUTS:
        if c - 0.16 <= t < c:
            p = ease_in((t - (c - 0.16)) / 0.16)
            d.rectangle([0, 0, W * p, H], fill=ACC if c != SCENES[-1]["t0"] else ACC)
        elif c <= t < c + 0.16:
            p = ease_out((t - c) / 0.16)
            if c != SCENES[-1]["t0"]:
                d.rectangle([W * p, 0, W, H], fill=ACC)
    # fade in from white on frame 0, fade at end
    if t < 0.12:
        frame = Image.blend(Image.new("RGBA", (W, H), BG + (255,)), frame, t / 0.12)
    return frame.convert("RGB")

# ---------------------------------------------------------------- audio
def synth_audio(path):
    sr = 44100
    n = int(sr * DUR)
    out = np.zeros(n, dtype=np.float64)
    beat = 60 / BPM
    rng = np.random.default_rng(3)
    def add(sig, t):
        i = int(t * sr)
        if i >= n: return
        j = min(n, i + len(sig))
        out[i:j] += sig[: j - i]
    # kick
    kt = np.arange(int(sr * 0.35)) / sr
    freq = 45 + 110 * np.exp(-kt * 30)
    kick = np.sin(2 * np.pi * np.cumsum(freq) / sr) * np.exp(-kt * 9)
    kick += 0.3 * np.exp(-kt * 400) * rng.normal(0, 1, len(kt))
    # clap
    ct = np.arange(int(sr * 0.25)) / sr
    clap_noise = rng.normal(0, 1, len(ct))
    clap_noise = np.convolve(clap_noise, [1, -0.9], "same")
    clap = clap_noise * (np.exp(-ct * 25) + 0.6 * np.exp(-((ct - 0.012) ** 2) / 1e-5))
    # hat
    ht = np.arange(int(sr * 0.06)) / sr
    hat_n = np.diff(rng.normal(0, 1, len(ht) + 1))
    hat = hat_n * np.exp(-ht * 70)
    # impact for cuts
    it = np.arange(int(sr * 1.2)) / sr
    ifreq = 38 + 80 * np.exp(-it * 12)
    impact = np.sin(2 * np.pi * np.cumsum(ifreq) / sr) * np.exp(-it * 3.2)
    impact += 0.25 * rng.normal(0, 1, len(it)) * np.exp(-it * 18)
    # riser into each cut
    rt = np.arange(int(sr * 0.5)) / sr
    riser = rng.normal(0, 1, len(rt)) * (rt / rt[-1]) ** 2
    riser = np.convolve(riser, np.ones(6) / 6, "same")
    # bass + chord pad (Am F C G, one bar = 4 beats = 2s)
    roots = [55.0, 43.65, 65.41, 49.0]
    chords = [[220, 261.63, 329.63], [174.61, 220, 261.63], [196, 261.63, 329.63], [196, 246.94, 293.66]]
    tt = np.arange(n) / sr
    bar = (tt // (4 * beat)).astype(int) % 4
    root = np.array(roots)[bar]
    phase = np.cumsum(root) / sr
    bass = np.sign(np.sin(2 * np.pi * phase)) * 0.5 + np.sin(2 * np.pi * phase)
    bass = np.convolve(bass, np.ones(40) / 40, "same")
    # sidechain-ish envelope on beats
    pos = (tt % beat) / beat
    duck = 0.35 + 0.65 * np.clip(pos * 3, 0, 1)
    pad = np.zeros(n)
    for ci, ch in enumerate(chords):
        mask = bar == ci
        for fq in ch:
            pad += mask * (np.sin(2 * np.pi * fq * tt) + 0.4 * np.sin(2 * np.pi * fq * 2.003 * tt))
    pad = np.convolve(pad, np.ones(200) / 200, "same")
    out += 0.22 * bass * duck + 0.035 * pad * duck
    end_beat = int(DUR / beat)
    for b in range(end_beat):
        t = b * beat
        intro = t < SCENES[1]["t0"]
        add(kick * 0.95, t)
        if b % 2 == 1 and not intro: add(clap * 0.32, t)
        add(hat * (0.10 if intro else 0.16), t + beat / 2)
        if not intro and b % 2 == 0: add(hat * 0.07, t + beat * 0.75)
    for c in CUTS:
        add(riser * 0.08, c - 0.5)
        add(impact * 0.55, c)
    # outro: let it ring, fade last 1s
    fade = np.ones(n)
    k = int(sr * 1.5)
    fade[-k:] = np.linspace(1, 0, k)
    out *= fade
    out = np.tanh(out * 1.3)
    out /= np.max(np.abs(out)) / 0.89
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- main
if __name__ == "__main__":
    if PREVIEW:
        for s in PREVIEW.split(","):
            render_frame(float(s)).save(os.path.join(HERE, f"preview_{s}.png"))
        sys.exit()
    wav = os.path.join(HERE, "beat.wav")
    synth_audio(wav)
    nframes = int(DUR * FPS)
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", OUT,
    ], stdin=subprocess.PIPE)
    for i in range(nframes):
        proc.stdin.write(render_frame(i / FPS).tobytes())
        if i % 60 == 0: print(f"frame {i}/{nframes}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done", OUT)
