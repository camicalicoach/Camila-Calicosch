"""Reel 3 · "POV: bailás y tenés 20 minutos para entrenar en casa".

Edición simple como la referencia: cortes limpios de 3-4 repeticiones por ejercicio, color cálido
tipo película con grano suave, textos blancos sobrios estilo Instagram. Sin música (se agrega al
publicar). Arranca sobre la sentadilla con salto porque no hay toma de baile.

Uso: python3 build_baile.py <carpeta_raw> <salida.mp4>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

RAW, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
INTER_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

# (clip, source start, source end, output seconds) — 3-4 reps each
CLIPS = [
    ("IMG_2311", 0.3, 7.3, 7.0),    # sentadilla con salto (de frente); el POV va arriba los primeros 3 s
    ("IMG_2312", 1.0, 7.0, 4.0),    # estocada atrás alternada
    ("IMG_2315", 4.0, 9.0, 4.0),    # puente de glúteo a una pierna
    ("IMG_2313", 17.6, 21.6, 4.0),  # plancha con toques de hombro (plancha completa)
    ("IMG_2314", 2.5, 6.5, 4.0),    # mountain climbers
    ("IMG_2311", 9.4, 14.9, 5.5),   # cierre: sentadilla con salto de costado, la toma con más energía
]
starts, t = [], 0.0
for c in CLIPS:
    starts.append(t); t += c[3]
DUR = t

# text cards: (start, end, lines) — lines are (text, font, size)
TEXTS = [
    (0.15, 3.0, [("POV: bailás y tenés", INTER_B, 64), ("20 minutos para", INTER_B, 64),
                 ("entrenar en casa", INTER_B, 64)], 1300),
    (3.0, 7.0, [("Sentadilla con salto", INTER_B, 58), ("40 seg", INTER_M, 46)], 330),
    (starts[1], starts[2], [("Estocada atrás alternada", INTER_B, 58), ("40 seg", INTER_M, 46)], 330),
    (starts[2], starts[3], [("Puente de glúteo a una pierna", INTER_B, 54), ("40 seg por lado", INTER_M, 46)], 330),
    (starts[3], starts[4], [("Plancha con toques de hombro", INTER_B, 54), ("40 seg", INTER_M, 46)], 330),
    (starts[4], starts[5], [("Mountain climbers", INTER_B, 58), ("40 seg", INTER_M, 46)], 330),
    (starts[5] + 0.2, DUR, [("4 vueltas", INTER_B, 72), ("20 seg de pausa entre ejercicios", INTER_M, 46)], 520),
]

# warm, soft film look like the reference
GRADE = ("eq=contrast=0.93:saturation=0.82:gamma=1.03,"
         "colorbalance=rs=0.06:gs=0.02:bs=-0.08:rm=0.05:gm=0.01:bm=-0.06:rh=0.04:bh=-0.07,"
         "curves=all='0/0.04 0.5/0.52 1/0.96',noise=alls=7:allf=t")


def card(lines):
    """White text on a translucent dark box, centred — like Instagram's text-with-background style,
    so it stays readable over the bright window."""
    rows = []
    for txt, f, sz in lines:
        fnt = ImageFont.truetype(f, sz)
        l, tp, r, b = fnt.getbbox(txt)
        rows.append((txt, fnt, l, tp, r - l, b - tp))
    gap, padx, pady = 14, 34, 24
    bw = max(r[4] for r in rows) + 2 * padx
    bh = sum(r[5] for r in rows) + gap * (len(rows) - 1) + 2 * pady
    im = Image.new("RGBA", (W, bh + 40), (0, 0, 0, 0))
    x0 = (W - bw) // 2
    ImageDraw.Draw(im).rounded_rectangle([x0, 20, x0 + bw, 20 + bh], radius=26, fill=(0, 0, 0, 120))
    d = ImageDraw.Draw(im)
    y = 20 + pady
    for txt, fnt, l, tp, rw, rh in rows:
        d.text(((W - rw) / 2 - l, y - tp), txt, font=fnt, fill=(255, 255, 255))
        y += rh + gap
    return im


def main():
    tmp = os.path.join(os.path.dirname(os.path.abspath(OUT)), "baile_txt")
    os.makedirs(tmp, exist_ok=True)
    inputs, filters = [], []
    for i, (clip, s, e, d) in enumerate(CLIPS):
        inputs += ["-ss", f"{s}", "-t", f"{e - s + 0.2}", "-i", os.path.join(RAW, f"{clip}.MOV")]
        speed = (e - s) / d
        filters.append(f"[{i}:v]setpts=(PTS-STARTPTS)/{speed:.4f},fps={FPS},"
                       f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                       f"trim=duration={d},setpts=PTS-STARTPTS[c{i}]")
    filters.append("".join(f"[c{i}]" for i in range(len(CLIPS))) + f"concat=n={len(CLIPS)}:v=1:a=0,{GRADE}[base]")
    last = "base"
    n0 = len(CLIPS)
    for j, (t0, t1, lines, cy) in enumerate(TEXTS):
        png = os.path.join(tmp, f"t{j}.png")
        im = card(lines)
        im.save(png)
        inputs += ["-loop", "1", "-t", f"{DUR}", "-i", png]
        k = n0 + j
        y = int(cy - im.height / 2)
        fade = f"fade=t=in:st={t0:.2f}:d=0.25:alpha=1,fade=t=out:st={max(t0, t1 - 0.25):.2f}:d=0.25:alpha=1"
        filters.append(f"[{k}:v]format=rgba,{fade}[tx{j}]")
        filters.append(f"[{last}][tx{j}]overlay=0:{y}:enable='between(t,{t0:.2f},{t1:.2f})'[v{j}]")
        last = f"v{j}"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs,
           "-f", "lavfi", "-t", f"{DUR}", "-i", "anullsrc=r=44100:cl=stereo",
           "-filter_complex", ";".join(filters), "-map", f"[{last}]", "-map", f"{n0 + len(TEXTS)}:a",
           "-t", f"{DUR}", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print("done", OUT, f"{DUR:.1f}s")


if __name__ == "__main__":
    main()
