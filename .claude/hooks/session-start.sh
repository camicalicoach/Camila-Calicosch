#!/bin/bash
# Instala las herramientas de video (FFmpeg, Whisper, Remotion) en sesiones de Claude Code en la nube.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# FFmpeg: cortes y conversión
if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq ffmpeg
fi

# Whisper (faster-whisper): transcripción palabra por palabra
if ! python3 -c "import faster_whisper" >/dev/null 2>&1; then
  pip install -q --break-system-packages faster-whisper
fi

# Remotion: subtítulos y animaciones
cd "$CLAUDE_PROJECT_DIR/videos/remotion"
npm install --no-audit --no-fund --loglevel=error

# Chromium preinstalado para renderizar con Remotion
SHELL_BIN=$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | head -1 || true)
if [ -n "$SHELL_BIN" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export REMOTION_BROWSER_EXECUTABLE=$SHELL_BIN" >> "$CLAUDE_ENV_FILE"
fi
