/*
 * DATA STORY — one number that matters. Title → bars grow and count up → the standout bar is highlighted → takeaway + source.
 * RULE: every figure comes from the brief. The values below are PLACEHOLDERS: replace DATA, TITLE, UNIT and SOURCE
 * with the real ones (an invented statistic in a chart is the worst kind of motion-graphics slop).
 */
window.SCENE = {
  bg: '#0e1117',
  build: function (MG, T, S, tl) {
    var u = Math.min(S.w, S.h) / 1080, d = T.d, portrait = S.h > S.w, wide = S.w > S.h * 1.2;   // wide = landscape; a square keeps the portrait type scale
    var TITLE = 'Título que dice la conclusión', SUB = 'Qué se mide, en qué periodo', UNIT = '', SOURCE = 'Fuente: (indicar)';
    var DATA = [ { label: 'A', value: 38 }, { label: 'B', value: 52 }, { label: 'C', value: 47 }, { label: 'D', value: 81 }, { label: 'E', value: 64 } ];
    var C = { fg: '#f2f4f8', muted: 'rgba(242,244,248,.62)', bar: '#3b4559', hi: '#4dd2a1' };
    var best = DATA.reduce(function (m, x, i) { return x.value > DATA[m].value ? i : m; }, 0);
    DATA.forEach(function (x, i) { x.color = i === best ? C.hi : C.bar; });

    var sc = S.scene('data'); MG.show(tl, sc, 0);
    var padX = S.w * (portrait ? 0.09 : 0.08);
    var titleY = S.h * (portrait ? 0.125 : 0.08);   // clears the 10 % top margin even at the start of the camera push (up to 4 % in 'impact')
    var title = MG.text(sc, { text: TITLE, x: padX, y: titleY, w: S.w - padX * 2, size: (portrait ? 78 : 70) * u * (wide ? 1.3 : 1), weight: 800, lh: 1.08,
      font: 'var(--font-body)', split: 'lines', color: C.fg });
    var sub = MG.text(sc, { text: SUB, x: padX, y: titleY + title.height + 18 * u, w: S.w - padX * 2, size: 38 * u * (wide ? 1.3 : 1), weight: 500,
      font: 'var(--font-body)', color: C.muted });
    var tall = S.h / S.w > 1.5;                       // 9x16 vs 4x5: un vertical poco alto no tiene sitio para un gráfico tan alto
    var cy = S.h * (portrait ? 0.38 : 0.36), ch = S.h * (portrait ? (tall ? 0.32 : 0.27) : 0.34);
    var chart = MG.barChart(sc, { x: padX, y: cy, w: S.w - padX * 2, h: ch, data: DATA, radius: 12 * u, valueSize: 46 * u * (wide ? 1.2 : 1),
      labelSize: 32 * u * (wide ? 1.2 : 1), textColor: C.fg, labelColor: C.muted, font: 'var(--font-body)',
      fmt: function (v) { return Math.round(v) + UNIT; } });
    var src = MG.text(sc, { text: SOURCE, x: padX, y: S.h * (portrait ? 0.83 : 0.88), w: S.w - padX * 2, size: 32 * u * (wide ? 1.2 : 1), weight: 500, color: C.muted, font: 'var(--font-body)' });

    var a = 0.3;
    MG.in(tl, title, { how: 'mask', at: a, dur: d(0.6), ease: T.ease.in });
    MG.in(tl, sub.el, { how: 'rise', at: a + d(0.25), dur: d(0.5), dy: 24 * u, ease: T.ease.in });
    var g = a + d(0.8);
    MG.growBars(tl, chart, { at: g, dur: d(0.9), stagger: d(0.14), ease: T.ease.in });
    DATA.forEach(function (x, i) { MG.cue('tick', g + i * d(0.14) + d(0.1), { gain: 0.6 }); });
    var grown = g + (DATA.length - 1) * d(0.14) + d(0.9);

    // highlight: everything else dims (to 0.55, not lower: below ~0.5 the validator reads dimmed items as gone), the standout bar pulses and a callout names it
    var hl = grown + d(0.35);
    chart.bars.forEach(function (b, i) { if (i !== best) tl.to([b, chart.values[i], chart.labels[i]], { opacity: 0.55, duration: d(0.45), ease: 'power2.out' }, hl); });
    MG.emph(tl, chart.bars[best], { how: 'pulse', at: hl, scale: 1.06 });
    MG.cue('hit', hl + 0.05, { gain: 0.85 });
    // la conclusión se centra en el hueco REAL entre las etiquetas del gráfico y la fuente (sirve en cualquier formato)
    var srcY = S.h * (portrait ? 0.83 : 0.88), below = cy + ch + 70 * u, callH = 64 * u * (wide ? 1.15 : 1) * 1.1;
    var call = MG.text(sc, { text: DATA[best].label + ' lidera', x: padX, y: below + Math.max(0, (srcY - below - callH) / 2), w: S.w - padX * 2, size: 64 * u * (wide ? 1.15 : 1), weight: 800,
      color: C.hi, font: 'var(--font-body)' });
    MG.in(tl, call.el, { how: 'rise', at: hl + d(0.2), dur: d(0.5), dy: 30 * u, ease: T.ease.in });
    MG.in(tl, src.el, { how: 'fade', at: hl + d(0.3), dur: d(0.5) });

    MG.grain(S, { opacity: 0.1 }); MG.vignette(S, { strength: 0.3 });
    MG.camera(tl, S, [{ from: { scale: 1 + T.camera / 2 }, at: 0, dur: hl, scale: 1, ease: 'sine.out' }]);
    return hl + d(0.7) + T.hold + 0.8;
  }
};
