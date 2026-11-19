/*
 * EXPLAINER — a process in three steps. Each step is a card: number → icon draws itself → title → one line.
 * A connector line draws from step to step, so the eye is led; the closing scene shows the outcome.
 * Replace STEPS / TITLE / OUTCOME. Keep each description to one short line (a viewer cannot read and watch more).
 */
window.SCENE = {
  bg: '#101014',
  build: function (MG, T, S, tl) {
    var u = Math.min(S.w, S.h) / 1080, d = T.d, portrait = S.h > S.w, cx = S.w / 2;
    var TITLE = 'Cómo funciona';
    var STEPS = [ { icon: 'plus', title: 'Primero', text: 'Describe el paso en una línea' },
                  { icon: 'bolt', title: 'Después', text: 'Qué ocurre a continuación' },
                  { icon: 'check', title: 'Listo', text: 'El resultado final' } ];
    var OUTCOME = 'El resultado, en una frase';
    var C = { fg: '#f4f2ee', muted: 'rgba(244,242,238,.66)', a: '#7c9cff', card: '#1a1b22' };

    var s1 = S.scene('steps'); MG.show(tl, s1, 0);
    var title = MG.text(s1, { text: TITLE, x: cx, y: S.h * (portrait ? 0.10 : 0.07), w: S.w * 0.9, size: 80 * u * (portrait ? 1 : 1.2), weight: 700, align: 'center', split: 'words',
      font: 'var(--font-display)', color: C.fg });
    MG.in(tl, title, { how: 'mask', at: 0.25, dur: d(0.6), stagger: d(0.1), ease: T.ease.in });

    var n = STEPS.length, cards = [], cardW, cardH, gx, gy;
    if (portrait) { cardW = S.w * 0.84; cardH = S.h * 0.19; gx = (S.w - cardW) / 2; gy = S.h * 0.19; }
    else { cardW = S.w * 0.27; cardH = S.h * 0.5; gx = S.w * 0.06; gy = S.h * 0.3; }
    var t0 = 0.25 + d(0.8), beat = d(1.15), centers = [], readEnd = 0;
    STEPS.forEach(function (st, i) {
      var x = portrait ? gx : gx + i * (cardW + (S.w - gx * 2 - cardW * n) / (n - 1));
      var y = portrait ? gy + i * (cardH + S.h * 0.045) : gy;
      var card = MG.box(s1, { x: x, y: y, w: cardW, h: cardH, bg: C.card, radius: 28 * u, border: '1px solid rgba(255,255,255,.07)' });
      var num = MG.text(s1, { text: String(i + 1), x: x + 34 * u, y: y + 26 * u, w: 90 * u, size: 54 * u, weight: 800, color: C.a, font: 'var(--font-display)' });
      var isz = (portrait ? 96 : 120) * u;
      var ic = MG.icon(s1, { name: st.icon, x: portrait ? x + cardW - isz - 40 * u : x + cardW / 2 - isz / 2, y: portrait ? y + cardH / 2 - isz / 2 : y + cardH * 0.2,
        size: isz, color: C.a, stroke: 1.6 });
      var tt = MG.text(s1, { text: st.title, x: x + 34 * u, y: portrait ? y + cardH * 0.34 : y + cardH * 0.52, w: cardW - (portrait ? isz + 100 * u : 68 * u), size: 52 * u, weight: 700, color: C.fg, font: 'var(--font-body)' });
      var tx = MG.text(s1, { text: st.text, x: x + 34 * u, y: portrait ? y + cardH * 0.34 + 66 * u : y + cardH * 0.52 + 70 * u, w: cardW - (portrait ? isz + 100 * u : 68 * u), size: 33 * u, weight: 500, color: C.muted, font: 'var(--font-body)' });
      var at = t0 + i * beat;
      MG.in(tl, card, { how: 'rise', at: at, dur: d(0.55), dy: 60 * u, ease: T.ease.in });
      MG.in(tl, num.el, { how: 'pop', at: at + d(0.2), dur: d(0.4), ease: T.ease.pop });
      MG.draw(tl, ic, { at: at + d(0.3), dur: d(0.6) });
      MG.in(tl, tt.el, { how: 'rise', at: at + d(0.4), dur: d(0.45), dy: 24 * u, ease: T.ease.in });
      MG.in(tl, tx.el, { how: 'fade', at: at + d(0.55), dur: d(0.45) });
      if (st.text.split(/\s+/).length >= 5) readEnd = Math.max(readEnd, at + d(0.55) + st.text.length / 15 + 1.5);   // a sentence needs chars/15 + 1.5 s on screen
      MG.cue('pop', at + d(0.25), { gain: 0.8 }); MG.cue('tick', at + d(0.6), { gain: 0.5 });
      cards.push(card); centers.push([x + cardW / 2, y + cardH / 2, x, y]);
    });
    // connectors: lines that draw from card to card (after the next card is announced)
    for (var i = 0; i < n - 1; i++) {
      var a = centers[i], b = centers[i + 1], lw = 6 * u, ln;
      if (portrait) ln = MG.box(s1, { x: a[0] - lw / 2, y: a[3] + cardH, w: lw, h: b[3] - (a[3] + cardH), bg: C.a, radius: 3 * u, css: 'transform-origin:50% 0' });
      else ln = MG.box(s1, { x: a[2] + cardW, y: a[1] - lw / 2, w: b[2] - (a[2] + cardW), h: lw, bg: C.a, radius: 3 * u, css: 'transform-origin:0 50%' });
      tl.set(ln, portrait ? { scaleY: 0 } : { scaleX: 0 }, 0);
      tl.to(ln, portrait ? { scaleY: 1, duration: d(0.4), ease: T.ease.move } : { scaleX: 1, duration: d(0.4), ease: T.ease.move }, t0 + (i + 1) * beat - d(0.1));
    }
    var stepsEnd = Math.max(t0 + (n - 1) * beat + d(1.2), readEnd);   // never leave before the longest line could be read, whatever the tempo

    var s2 = S.scene('outcome', { bg: C.a });
    var big = MG.text(s2, { text: OUTCOME, x: cx, y: S.h * 0.5, w: S.w * 0.82, size: 104 * u, weight: 800, align: 'center', valign: 'middle', split: 'words',
      font: 'var(--font-display)', color: '#0c0d12', lh: 1.05 });
    var ring = MG.ring(s2, { x: cx - 90 * u, y: S.h * 0.5 - 330 * u, size: 180 * u, stroke: 14 * u, color: '#0c0d12', track: 'rgba(12,13,18,.18)' });
    var chk = MG.icon(s2, { name: 'check', x: cx - 50 * u, y: S.h * 0.5 - 290 * u, size: 100 * u, color: '#0c0d12', stroke: 2.4 });
    MG.transition(tl, s1, s2, { type: 'zoom-through', el: cards[n - 1], radius: 28 * u, at: stepsEnd, dur: d(0.9), ease: T.ease.move });   // dive INTO the last card: it survives the cut
    MG.cue('whoosh', stepsEnd + d(0.15), { dur: d(0.6) });
    var oa = stepsEnd + d(0.75);
    MG.draw(tl, ring, { at: oa, dur: d(0.8), to: 1 }); MG.draw(tl, chk, { at: oa + d(0.45), dur: d(0.5) });
    MG.in(tl, big, { how: 'mask', at: oa + d(0.5), dur: d(0.6), stagger: d(0.1), ease: T.ease.in });
    MG.cue('hit', oa + d(0.55), { gain: 0.8 }); MG.cue('shimmer', oa + d(0.95), { gain: 0.6 });

    MG.grain(S, { opacity: 0.1 });
    return oa + d(1.5) + T.hold + 0.5;
  }
};
