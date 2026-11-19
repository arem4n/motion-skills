import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, Composition, useCurrentFrame, useVideoConfig} from 'remotion';
import gsap from 'gsap';
// @ts-ignore  (UMD/CommonJS)
import MotionKit from './motion-kit';
// @ts-ignore
import buildTimeline from './timeline';
import LAYERS from './layers.json';
import TOKENS from './motion-tokens.json';

const ARCHETYPE = 'ancestro';
const [, , vbw, vbh] = (LAYERS as any).viewBox;

const LogoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const box = useRef<HTMLDivElement>(null);
  const tl = useRef<gsap.core.Timeline | null>(null);

  // Mount the stage and build the paused timeline once (before first paint).
  useLayoutEffect(() => {
    const kit = MotionKit.use(gsap);
    const T = kit.tokens(TOKENS, ARCHETYPE);
    const stg = kit.stage(box.current, LAYERS, {ink: '#0a0a0b'});
    const t = gsap.timeline({paused: true});
    buildTimeline(kit, stg, T, t);
    tl.current = t;
    return () => { t.kill(); tl.current = null; if (box.current) box.current.innerHTML = ''; };
  }, []);

  // Every frame is a pure function of the frame number. Runs after the mount effect above (declaration order),
  // so the timeline exists on the very first render too.
  useLayoutEffect(() => {
    if (tl.current) tl.current.time(frame / fps, false);
  }, [frame, fps]);

  return (
    <AbsoluteFill style={{background: '#f6f4ee', display: 'grid', placeItems: 'center'}}>
      <div ref={box} style={{position: 'relative', width: 'min(88vw, calc(88vh * ' + vbw / vbh + '))', aspectRatio: `${vbw} / ${vbh}`}} />
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition id="LogoScene" component={LogoScene} durationInFrames={195} fps={30} width={1080} height={1920} />
);
