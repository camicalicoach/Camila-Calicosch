import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { createTikTokStyleCaptions, type Caption, type TikTokPage } from "@remotion/captions";

// Paleta camicali.coach
const INK = "#141A2E";
const ACC = "#4F46E5";
const WHITE = "#FFFFFF";

export type subtitulosSchema = {
  video: string; // archivo dentro de public/
  captions: string; // JSON generado por tools/transcribe.py
  msPorBloque: number; // agrupa en un bloque las palabras dentro de esta ventana (ms)
};

const fontFace = new FontFace("Anton", `url(${staticFile("fonts/Anton-Regular.ttf")})`);
const fontHandle = delayRender("Cargando fuente Anton");
fontFace.load().then((f) => {
  document.fonts.add(f);
  continueRender(fontHandle);
});

const Pagina: React.FC<{ page: TikTokPage }> = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = page.startMs + (frame / fps) * 1000;
  const entrada = spring({ frame, fps, config: { damping: 14, mass: 0.6 } });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 520 }}>
      <div
        style={{
          fontFamily: "Anton",
          fontSize: 96,
          lineHeight: 1.15,
          textTransform: "uppercase",
          textAlign: "center",
          maxWidth: 860,
          color: WHITE,
          WebkitTextStroke: `10px ${INK}`,
          paintOrder: "stroke",
          transform: `scale(${interpolate(entrada, [0, 1], [0.85, 1])})`,
        }}
      >
        {page.tokens.map((t) => {
          const activa = t.fromMs <= ms && ms < t.toMs;
          return (
            <span
              key={t.fromMs}
              style={{
                backgroundColor: activa ? ACC : "transparent",
                WebkitTextStroke: activa ? "0px" : `10px ${INK}`,
                borderRadius: 16,
                padding: "0 10px",
                whiteSpace: "pre",
              }}
            >
              {t.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Subtitulos: React.FC<subtitulosSchema> = ({ video, captions, msPorBloque }) => {
  const { fps } = useVideoConfig();
  const [lista, setLista] = useState<Caption[] | null>(null);
  const [handle] = useState(() => delayRender("Cargando subtítulos"));

  const cargar = useCallback(async () => {
    const res = await fetch(staticFile(captions));
    setLista((await res.json()) as Caption[]);
    continueRender(handle);
  }, [captions, handle]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const pages = useMemo(
    () =>
      lista
        ? createTikTokStyleCaptions({ captions: lista, combineTokensWithinMilliseconds: msPorBloque }).pages
        : [],
    [lista, msPorBloque],
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <OffthreadVideo src={staticFile(video)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      {pages.map((page, i) => {
        const next = pages[i + 1] ?? null;
        const from = Math.round((page.startMs / 1000) * fps);
        const endMs = next ? Math.min(next.startMs, page.startMs + page.durationMs + 600) : page.startMs + page.durationMs + 600;
        const dur = Math.max(1, Math.round(((endMs - page.startMs) / 1000) * fps));
        return (
          <Sequence key={page.startMs} from={from} durationInFrames={dur}>
            <Pagina page={page} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
