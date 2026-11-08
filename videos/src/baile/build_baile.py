"""Reel 3 · "POV: bailás y tenés 20 minutos para entrenar en casa".

Edición simple como la referencia: dos ángulos por ejercicio, color cálido tipo película con grano
suave y textos solo en blanco (serif cursiva + detalle chico en mayúsculas). La primera toma va
en blanco y negro y desenfocada con el POV encima, y el video pasa a color al arrancar el primer
ejercicio. Sin música (se agrega al publicar). No hay toma de baile, así que abre con la sentadilla.

Uso: python3 build_baile.py <carpeta_raw> <salida.mp4>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
SERIF = os.path.join(FONTS, "PlayfairDisplay-SemiBoldItalic.ttf")
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
RAW, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30

# (clip, source start, source end, output seconds, style) — two angles per exercise
CLIPS = [
    ("IMG_2311", 0.3, 3.3, 3.0, "intro"),   # POV: black & white, blurred
    ("IMG_2311", 3.3, 5.3, 2.0, ""),        # sentadilla con salto · de frente
    ("IMG_2311", 9.4, 11.4, 2.0, ""),       #                      · de costado
    ("IMG_2312", 1.5, 4.0, 2.0, ""),        # estocada atrás · de frente
    ("IMG_2312", 15.5, 18.0, 2.0, ""),      #                · de perfil
    ("IMG_2315", 4.5, 7.0, 2.5, ""),        # puente de glúteo · un lado (ya en posición, velocidad real)
    ("IMG_2315", 24.2, 27.2, 3.0, ""),      #                  · el otro lado, sin la preparación
    ("IMG_2313", 4.0, 6.4, 2.0, ""),        # plancha con toques · con rodillas
    ("IMG_2313", 17.6, 20.0, 2.0, ""),      #                    · completa
    ("IMG_2314", 3.0, 6.05, 3.05, ""),      # mountain climbers: 2 repeticiones completas, velocidad real
    ("IMG_2314", 9.3, 12.3, 3.0, ""),
    ("IMG_2311", 11.4, 14.9, 3.5, ""),      # cierre
]
starts, t = [], 0.0
for c in CLIPS:
    starts.append(t); t += c[3]
DUR = t

# (start, end, title, detail) — title None is the POV card
TEXTS = [
    (0.2, 3.0, None, None),
    (starts[1], starts[3], "Sentadilla con salto", "40 SEG"),
    (starts[3], starts[5], "Estocada atrás alternada", "40 SEG"),
    (starts[5], starts[7], "Puente de glúteo a una pierna", "40 SEG POR LADO"),
    (starts[7], starts[9], "Plancha con toques de hombro", "40 SEG"),
    (starts[9], starts[11], "Mountain climbers", "40 SEG"),
    (starts[11] + 0.2, DUR, "4 vueltas", "20 SEG DE PAUSA ENTRE EJERCICIOS"),
]
TITLE_Y = 1330  # over the darker floor so white text reads without a box

# warm, soft film look like the reference; the intro shot is black & white and blurred
GRADE = ("eq=contrast=0.93:saturation=0.82:gamma=1.03,"
         "colorbalance=rs=0.06:gs=0.02:bs=-0.08:rm=0.05:gm=0.01:bm=-0.06:rh=0.04:bh=-0.07,"
         "curves=all='0/0.04 0.5/0.52 1/0.96'")
INTRO = "hue=s=0,gblur=sigma=9,eq=brightness=-0.06:contrast=0.9"


def spaced(d, xy, txt, fnt, spacing):
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=fnt, fill=(255, 255, 255))
        x += fnt.getlength(ch) + spacing


def spaced_width(txt, fnt, spacing):
    return sum(fnt.getlength(c) for c in txt) + spacing * (len(txt) - 1)


def soft(im):
    """Soft dark glow behind white text so it reads over bright areas without a box."""
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda a: int(a * 0.55)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (0, 3))
    out.alpha_composite(im)
    return out


def title_card(title, detail):
    im = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 88
    ft = ImageFont.truetype(SERIF, size)
    while ft.getlength(title) > W - 120:
        size -= 4
        ft = ImageFont.truetype(SERIF, size)
    d.text(((W - ft.getlength(title)) / 2, 40), title, font=ft, fill=(255, 255, 255))
    fd = ImageFont.truetype(INTER_SB, 30)
    dw = spaced_width(detail, fd, 6)
    y = 40 + size * 1.25 + 14
    for x0, x1 in (((W - dw) / 2 - 70, (W - dw) / 2 - 24), ((W + dw) / 2 + 24, (W + dw) / 2 + 70)):
        d.line([(x0, y + 17), (x1, y + 17)], fill=(255, 255, 255), width=2)
    spaced(d, ((W - dw) / 2, y), detail, fd, 6)
    return soft(im)


def pov_card():
    im = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fd = ImageFont.truetype(INTER_SB, 34)
    spaced(d, ((W - spaced_width("POV", fd, 14)) / 2, 40), "POV", fd, 14)
    ft = ImageFont.truetype(SERIF, 92)
    for i, line in enumerate(["bailás y tenés", "20 minutos para", "entrenar en casa"]):
        d.text(((W - ft.getlength(line)) / 2, 110 + i * 118), line, font=ft, fill=(255, 255, 255))
    return soft(im)


def main():
    tmp = os.path.join(os.path.dirname(os.path.abspath(OUT)), "baile_txt")
    os.makedirs(tmp, exist_ok=True)
    inputs, filters = [], []
    for i, (clip, s, e, d, style) in enumerate(CLIPS):
        inputs += ["-ss", f"{s}", "-t", f"{e - s + 0.2}", "-i", os.path.join(RAW, f"{clip}.MOV")]
        speed = (e - s) / d
        look = INTRO if style == "intro" else GRADE
        filters.append(f"[{i}:v]setpts=(PTS-STARTPTS)/{speed:.4f},fps={FPS},"
                       f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                       f"trim=duration={d},setpts=PTS-STARTPTS,{look}[c{i}]")
    filters.append("".join(f"[c{i}]" for i in range(len(CLIPS))) +
                   f"concat=n={len(CLIPS)}:v=1:a=0,noise=alls=7:allf=t[base]")
    last, n0 = "base", len(CLIPS)
    for j, (t0, t1, title, detail) in enumerate(TEXTS):
        im = pov_card() if title is None else title_card(title, detail)
        cy = 960 if title is None else TITLE_Y
        png = os.path.join(tmp, f"t{j}.png")
        im.save(png)
        inputs += ["-loop", "1", "-t", f"{DUR}", "-i", png]
        k = n0 + j
        fade = f"fade=t=in:st={t0:.2f}:d=0.3:alpha=1,fade=t=out:st={max(t0, t1 - 0.25):.2f}:d=0.25:alpha=1"
        filters.append(f"[{k}:v]format=rgba,{fade}[tx{j}]")
        filters.append(f"[{last}][tx{j}]overlay=0:{int(cy - im.height / 2)}:enable='between(t,{t0:.2f},{t1:.2f})'[v{j}]")
        last = f"v{j}"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs,
           "-f", "lavfi", "-t", f"{DUR}", "-i", "anullsrc=r=44100:cl=stereo",
           "-filter_complex", ";".join(filters), "-map", f"[{last}]", "-map", f"{n0 + len(TEXTS)}:a",
           "-t", f"{DUR}", "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "10M", "-bufsize", "20M",
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print("done", OUT, f"{DUR:.1f}s")


if __name__ == "__main__":
    main()
