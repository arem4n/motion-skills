import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { createTikTokStyleCaptions, type Caption } from "@remotion/captions";

type Props = {
  captions: Caption[]; // de scripts/transcribe.py (faster-whisper) o de cualquier fuente en el formato Caption
  combineMs?: number; // más alto = frases más largas por "página" (800–1500 en vertical)
  offsetMs?: number; // si el audio empieza más tarde que la composición
  fontFamily: string; // cárgala antes (FontFace + delayRender, @remotion/fonts o @remotion/google-fonts)
  color?: string;
  active?: string; // color de la palabra que se dice
  bottom?: number; // px (a 1080 de lado corto) desde el borde inferior: en vertical > 340 para librar la UI de la app
};

/**
 * Subtítulos por palabra sincronizados con el audio. Todo es función del fotograma: tiempo = frame / fps.
 * Tamaño relativo (u = lado corto / 1080) para servir en 9:16, 16:9, 1:1 y 4:5. Sin cambio de ancho al resaltar
 * (solo cambia el color), así la línea no salta.
 */
export const Captions: React.FC<Props> = ({ captions, combineMs = 1100, offsetMs = 0, fontFamily, color = "#fff", active = "#FFD23F", bottom = 420 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  const { pages } = useMemo(() => createTikTokStyleCaptions({ captions, combineTokensWithinMilliseconds: combineMs }), [captions, combineMs]);
  const t = (frame / fps) * 1000 - offsetMs;
  const page = pages.find((p, i) => t >= p.startMs && t < (pages[i + 1]?.startMs ?? p.startMs + p.durationMs));
  if (!page) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center" }}>
      <div style={{ width: width - 160 * u, marginBottom: bottom * u, textAlign: "center", fontFamily, fontWeight: 700, fontSize: 68 * u, lineHeight: 1.18, whiteSpace: "pre-wrap", textShadow: `0 ${4 * u}px ${18 * u}px rgba(0,0,0,.75)` }}>
        {page.tokens.map((tok) => (
          <span key={tok.fromMs} style={{ color: t >= tok.fromMs && t < tok.toMs ? active : color }}>
            {tok.text}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
