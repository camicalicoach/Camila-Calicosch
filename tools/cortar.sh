#!/bin/bash
# Corta un tramo de un video con FFmpeg y lo deja en 9:16 (1080x1920) para Reels.
# Uso: tools/cortar.sh entrada.mp4 00:00:05 00:00:20 salida.mp4
set -euo pipefail
if [ $# -lt 4 ]; then
  echo "Uso: $0 entrada inicio fin salida   (tiempos en HH:MM:SS o segundos)" >&2
  exit 1
fi
ffmpeg -y -ss "$2" -to "$3" -i "$1" \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart "$4"
