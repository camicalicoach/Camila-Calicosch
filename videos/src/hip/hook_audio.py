"""Audio para el gancho "Peso muerto?": base suave + un pop por cada comentario + golpe final.

Uso: python3 hook_audio.py <video_entrada> <video_salida>
Los tiempos de los pops salen de detectar cuándo aparece cada comentario en el video.
"""
import subprocess, sys, wave
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
SR = 44100
POPS = [0.70, 1.20, 1.68, 2.15, 2.65, 3.12]   # tarjetas de comentarios
BIG_POP = 3.85                                # burbuja oscura "Peso muerto ??"

dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                     "-of", "csv=p=0", SRC]).decode())
n = int(SR * dur)
L, R = np.zeros(n), np.zeros(n)
rng = np.random.default_rng(11)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= n:
        return
    j = min(n, i + len(sig))
    L[i:j] += sig[: j - i] * gain * (1 - max(0, pan))
    R[i:j] += sig[: j - i] * gain * (1 + min(0, pan))


def pop(f0):
    """Bubbly UI pop: fast downward pitch sweep plus a tiny click."""
    t = np.arange(int(SR * 0.12)) / SR
    f = f0 * (1 + 1.2 * np.exp(-t * 60))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    s[:40] += rng.normal(0, 0.6, 40) * np.linspace(1, 0, 40)
    return s


# --- music bed: muted plucks on A minor + soft hats, ducked under the pops
beat = 0.5  # 120 BPM
notes = [440.0, 523.25, 659.25, 523.25]
pt = np.arange(int(SR * 0.22)) / SR
for k in range(int(dur / (beat / 2))):
    f = notes[k % 4]
    tone = (np.sin(2 * np.pi * f * pt) + 0.3 * np.sin(2 * np.pi * 2 * f * pt)) * np.exp(-pt * 18)
    add(tone, k * beat / 2, 0.10, pan=0.3 if k % 2 else -0.3)
ht = np.arange(int(SR * 0.05)) / SR
hat = np.diff(rng.normal(0, 1, len(ht) + 1)) * np.exp(-ht * 70)
for k in range(int(dur / beat)):
    add(hat, k * beat + beat / 2, 0.10, pan=0.2)
    kt = np.arange(int(SR * 0.2)) / SR
    add(np.sin(2 * np.pi * np.cumsum(70 + 90 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 14), k * beat, 0.25)

# --- pops, each one a step higher, the last bubble bigger
for i, t in enumerate(POPS):
    add(pop(520 * 2 ** (i / 12 * 2)), t, 0.55, pan=(-0.25, 0.25)[i % 2])
add(pop(1100), BIG_POP, 0.75)
add(pop(550), BIG_POP + 0.015, 0.45)

# --- riser into the end + hit that leads into the reveal
rt = np.arange(int(SR * 1.1)) / SR
riser = np.convolve(rng.normal(0, 1, len(rt)), [1, -1], "same") * (rt / rt[-1]) ** 2.5
add(riser, dur - 1.15, 0.18)
it = np.arange(int(SR * 0.6)) / SR
hit = np.sin(2 * np.pi * np.cumsum(70 + 180 * np.exp(-it * 12)) / SR) * np.exp(-it * 6)
hit += 0.5 * np.convolve(rng.normal(0, 1, len(it)), [1, -1], "same") * np.exp(-it * 25)
add(hit, dur - 0.08, 0.6)

out = np.tanh(np.stack([L, R], 1) * 1.4)
out /= np.max(np.abs(out)) / 0.89
wav = OUT + ".wav"
with wave.open(wav, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((out * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SRC, "-i", wav,
                "-filter_complex", "[1:a]loudnorm=I=-11:TP=-1:LRA=9[a]", "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest",
                "-movflags", "+faststart", OUT], check=True)
import os; os.remove(wav)
print("done", OUT)
