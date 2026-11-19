import React, { useLayoutEffect, useRef, useState } from "react";
import { continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import gsap from "gsap";
// @ts-ignore  UMD
import MG from "./mg.js";
import "./tokens.js";

type Props = { scene: any; personality: string; fonts: string[]; vars: Record<string, string>; w: number; h: number };

/** Una escena GSAP/MG montada como componente: varias pueden convivir en una composición (en secuencia). */
export const GsapScene: React.FC<Props> = ({ scene, personality, fonts, vars, w, h }) => {
  const frame = useCurrentFrame(); // relativo al <Sequence> que lo contiene
  const { fps } = useVideoConfig();
  const host = useRef<HTMLDivElement>(null);
  const seek = useRef<null | ((t: number) => void)>(null);
  const [, setMounted] = useState(false);
  const [handle] = useState(() => delayRender("mg-build-" + personality));

  useLayoutEffect(() => {
    let tl: gsap.core.Timeline | null = null;
    // IMPRESCINDIBLE: sin este setState síncrono al montar (antes de la promesa de fuentes) Remotion captura el fotograma vacío.
    setMounted(true);
    if (!document.querySelector("base[data-mg]")) {
      const b = document.createElement("base");
      b.dataset.mg = "1";
      b.href = new URL(staticFile("fonts.css").replace(/fonts\.css$/, ""), window.location.href).href;
      document.head.appendChild(b);
    }
    MG.use(gsap);
    const T = MG.tokens((window as any).TOKENS, personality);
    MG.ready(fonts, () => {
      if (MG.reset) MG.reset(); // estado de módulo del kit (señales, finalizadores, MG.stepped): no heredar el de la escena anterior
      const S = MG.stage({ w, h, bg: scene.bg, host: host.current });
      tl = gsap.timeline({ paused: true });
      const end = scene.build(MG, T, S, tl);
      tl.set({}, {}, end);
      MG.expose(tl);
      seek.current = (window as any).__seek; // se guarda AHORA: otra escena pisará window.__seek
      seek.current!(frame / fps);
      continueRender(handle);
    });
    return () => {
      tl?.kill();
      seek.current = null;
      if (host.current) host.current.innerHTML = "";
    };
  }, []);

  useLayoutEffect(() => {
    seek.current?.(frame / fps);
  }, [frame, fps]);

  return <div ref={host} style={{ width: w, height: h, position: "absolute", left: 0, top: 0, ...vars } as React.CSSProperties} />;
};
