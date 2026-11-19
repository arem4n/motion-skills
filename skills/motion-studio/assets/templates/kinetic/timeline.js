/*
 * KINETIC TYPOGRAPHY — a message in three beats: hook (big words hit one by one) → support line → call to action.
 * Edit CONTENT and the colours; keep the structure (one hero element at a time, a cue on every hit, end hold).
 * Works in portrait or landscape: sizes scale with u = min(w,h)/1080.
 * Structure of time:  hook 0–~2.4 s | the accent bar grows into the CTA button | support + CTA | end hold.
 */
window.SCENE = {
  bg: '#0c0c0f',
  build: function (MG, T, S, tl) {
    var u = Math.min(S.w, S.h) / 1080, d = T.d, cx = S.w / 2;
    var CONTENT = {
      hook: ['TITULAR', 'EN TRES', 'GOLPES'],           // one line per hit; max ~3 lines, ~10 characters each
      accentLine: 2,                                     // which line takes the accent colour
      support: 'Una línea de apoyo\nque explica el porqué',
      cta: 'Llamado a la acción'
    };
    var C = { fg: '#f4f1ea', accent: '#ff4d2e', muted: 'rgba(244,241,234,.72)', bg2: '#16161b' };

    /* ── scene 1: hook ── words rise out of a hard edge, one line per hit ── */
    var s1 = S.scene('hook'); MG.show(tl, s1, 0);
    var size = 235 * u, lh = 0.9, lines = [], totalH = CONTENT.hook.length * size * lh, y0 = S.h / 2 - totalH / 2;
    CONTENT.hook.forEach(function (ln, i) {
      lines.push(MG.text(s1, { text: ln, x: cx, y: y0 + i * size * lh, w: S.w * 0.92, size: size, weight: 400, align: 'center', lh: lh,
        font: 'var(--font-display)', split: 'words', color: i === CONTENT.accentLine ? C.accent : C.fg }));
    });
    var bar = MG.box(s1, { x: cx - 170 * u, y: y0 + totalH + 40 * u, w: 340 * u, h: 12 * u, bg: C.accent, radius: 6 * u, css: 'transform-origin:0 50%' });
    var t = 0.25;
    lines.forEach(function (L, i) {
      var at = t + i * d(0.38);
      MG.in(tl, L, { how: 'mask', at: at, dur: d(0.55), ease: T.ease.in });
      MG.cue('hit', at + d(0.14), { gain: 0.8 + 0.1 * i });
    });
    var hookEnd = t + (lines.length - 1) * d(0.38) + d(0.55);
    tl.set(bar, { scaleX: 0 }, 0); tl.to(bar, { scaleX: 1, duration: d(0.5), ease: T.ease.in }, hookEnd - 0.1);
    MG.cue('tick', hookEnd);
    var hold1 = hookEnd + d(0.55);

    /* ── beat 2 (same scene): the hook leaves and the accent bar GROWS into the CTA button, so something survives the cut ── */
    var g2 = MG.box(s1, { x: 0, y: 0, w: S.w, h: S.h });   // beat-2 group: hidden until the hook has left (not hit-testable while hidden)
    tl.set(g2, { autoAlpha: 0 }, 0);
    var sup = MG.text(g2, { text: CONTENT.support, x: cx, y: S.h * 0.40, w: S.w * 0.84, size: 84 * u, weight: 700, align: 'center', lh: 1.12,
      font: 'var(--font-body)', split: 'lines', color: C.fg, valign: 'middle' });
    var pillW = 700 * u, pillH = 150 * u, pillY = S.h * 0.58;
    var pillT = MG.text(g2, { text: CONTENT.cta, x: cx, y: pillY + pillH / 2, w: pillW, size: 56 * u, weight: 800, align: 'center', valign: 'middle',
      font: 'var(--font-body)', color: '#0c0c0f' });
    lines.forEach(function (L, i) { MG.out(tl, L, { how: 'mask', at: hold1 + i * d(0.06), dur: d(0.4), ease: T.ease.out }); });
    var mEnd = MG.morph(tl, bar, { x: cx - pillW / 2, y: pillY, w: pillW, h: pillH, radius: pillH / 2 }, { at: hold1 + d(0.1), dur: d(0.7), ease: T.ease.move });
    MG.cue('whoosh', hold1 + d(0.1), { dur: d(0.55) });
    tl.set(g2, { autoAlpha: 1 }, hold1 + d(0.45) - 0.01);
    MG.in(tl, sup, { how: 'mask', at: hold1 + d(0.45), dur: d(0.6), stagger: d(0.12), ease: T.ease.in });
    var pa = mEnd;
    MG.in(tl, pillT.el, { how: 'pop', at: pa, dur: d(0.5), ease: T.ease.pop });
    MG.cue('pop', pa + d(0.08));
    MG.emph(tl, bar, { how: 'pulse', at: pa + d(0.9), scale: 1.05 });
    MG.cue('shimmer', pa + d(0.9), { gain: 0.7 });

    /* ── ambient layer + camera (slow push through the hook, settle at rest) ── */
    MG.grain(S, { opacity: 0.16 }); MG.vignette(S, { strength: 0.4 });
    MG.camera(tl, S, [{ from: { scale: 1.0 }, at: 0, dur: hold1, scale: 1 + T.camera, ease: 'sine.inOut' },
                      { at: hold1, dur: d(0.55), scale: 1, ease: 'power2.out' }]);
    return pa + d(0.9) + d(0.9) + T.hold + 0.9;
  }
};
