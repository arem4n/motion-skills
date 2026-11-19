/*
 * Línea de tiempo de la escena. Una sola fuente para todos los destinos de render (scene.html, Remotion, Hyperframes).
 *   buildTimeline(kit, stg, T, tl)  → agrega tweens a `tl` (en pausa) y devuelve la duración total.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.buildTimeline = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  return function buildTimeline(kit, stg, T, tl) {
    var d = T.d;

    /* STARTER — secuencia genérica que funciona con cualquier logo separado en capas.
       Reemplázala por la historia real de la marca (ver references/storyboard-from-semiotics.md):
         DENOTACIÓN  → qué se ve primero (lo icónico / literal)
         CONNOTACIÓN → qué significa para quien conoce los códigos (índice / símbolo)
         MITO        → el remate: nombre, tipomorfía, promesa */
    var c = 0.5;
    var names = Object.keys(stg.nodes);
    names.forEach(function (name, i) {
      kit.wipe(tl, stg.nodes[name], 'up', { at: c + i * T.gap(2), dur: d(1.4), ease: T.ease.move });
    });
    c += (names.length - 1) * T.gap(2) + d(1.4) + T.hold;
    Object.keys(stg.parts).forEach(function (name) {
      stg.parts[name].forEach(function (n, i) {
        kit.rise(tl, n, { dy: 40, at: c + i * T.gap(0.8), dur: d(0.9), ease: T.ease.in });
        kit.fade(tl, n, { at: c + i * T.gap(0.8), dur: d(0.7) });
      });
      c += (stg.parts[name].length - 1) * T.gap(0.8) + d(0.9);
    });
    tl.addLabel('rest', c);                                    // logo completo y quieto: el validador compara este frame con el original
    var end = c + T.hold + 0.6;
    kit.drift(tl, stg, { from: T.drift, at: 0, dur: end });
    tl.set({}, {}, end);
    return end;
  };
});
