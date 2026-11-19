/* Blank scene. window.SCENE.build(MG, T, S, tl) must add its tweens to `tl` (paused) and return the total duration.
 *   MG = kit (see assets/lib/mg.js header)   T = motion tokens (T.d(sec), T.gap(n), T.ease.in/out/move/pop, T.hold)
 *   S  = stage (S.w, S.h, S.scene(name), S.overlay)   tl = paused GSAP timeline
 * Write in design pixels (the stage scales to the render size). Nothing may depend on the clock or on randomness. */
window.SCENE = {
  bg: '#0c0c0f',
  build: function (MG, T, S, tl) {
    var sc = S.scene('main'); MG.show(tl, sc, 0);
    var title = MG.text(sc, { text: 'Tu mensaje\naquí', x: S.w / 2, y: S.h / 2, w: S.w * 0.8, size: 120, weight: 700, align: 'center', valign: 'middle',
      font: 'var(--font-display)', split: 'words', color: '#f4f1ea' });
    var end = MG.in(tl, title, { how: 'mask', at: 0.3, dur: T.d(0.8), stagger: T.gap(1), ease: T.ease.in });
    MG.cue('whoosh', 0.3 + 0.1);
    return end + T.hold + 0.4;
  }
};
