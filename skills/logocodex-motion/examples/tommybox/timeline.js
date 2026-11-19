/*
 * TommyBox — línea de tiempo del isotipo (arquetipo Héroe: ascendente, sin caídas ni rebotes).
 * buildTimeline(kit, stg, T, tl) → agrega los tweens a `tl` (en pausa) y devuelve la duración total.
 *
 * Lectura del símbolo: el círculo + la T son una figura humana (el alumno: cabeza, hombros, tronco);
 * la B es el box, el lugar. La figura se construye de abajo hacia arriba y recién entonces el box cierra
 * contra ella: la rendija entre la T y la B es el umbral que se cruza.
 *   · tronco  sube desde el suelo            (el esfuerzo es la base)
 *   · hombros entran desde la izquierda      (la barra: la carga que se levanta)
 *   · cabeza  asciende desde el borde de los hombros (se pone de pie) — nunca cae
 *   · box     entra desde la derecha y cierra  → golpe de cámara
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.buildTimeline = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  return function buildTimeline(kit, stg, T, tl) {
    var d = T.d, N = stg.nodes;
    var FLOOR = 1577, BAR_TOP = 561;

    /* 1 · tronco: sube desde el suelo */
    var t1 = d(0.30);
    kit.wipe(tl, N.stem, 'up', { at: t1, dur: d(0.70), ease: 'power3.out' });

    /* 2 · hombros: entran desde la izquierda con arranque seco; la barra se encaja sobre el tronco */
    var t2 = t1 + d(0.45);
    kit.wipe(tl, N.bar, 'right', { at: t2, dur: d(0.55), ease: 'power4.out' });
    kit.rise(tl, N.bar, { dx: -280, dy: 0, at: t2, dur: d(0.60), ease: 'power4.out' });

    /* 3 · cabeza: sube a través del borde superior de los hombros (la ventana fija es ese borde) y se detiene en su sitio */
    var t3 = t2 + d(0.50);
    kit.window(tl, N.head, { bottom: BAR_TOP });
    kit.rise(tl, N.head, { dy: 335, inner: true, at: t3, dur: d(0.75), ease: 'power3.out' });
    var land = t3 + d(0.75) * 0.55;                              // la cabeza ya está casi arriba: golpe suave

    /* 4 · box: entra desde la derecha (su borde izquierdo es plano: es el borde natural de la B) y cierra contra la figura */
    var t4 = t3 + d(0.60);
    kit.hide(tl, N.box, 'fade');
    kit.fade(tl, N.box, { at: t4, dur: d(0.08), ease: 'none' });
    kit.rise(tl, N.box, { dx: 460, dy: 0, at: t4, dur: d(0.60), ease: 'power4.out' });
    var lock = t4 + d(0.60) * 0.78;

    /* cámara: empuje de aproximación, golpe suave al ponerse de pie, golpe seco al cerrar el box */
    var rest = t4 + d(0.60) + d(0.25);
    var end = rest + T.hold + 0.7;
    kit.camera(tl, stg, [
      { from: 1.05, to: 1.0,   at: 0,    dur: land,        ease: 'sine.out' },
      { to: 1.012,             at: land, dur: d(0.08),     ease: 'expo.out' },
      { to: 1.0,               at: land + d(0.08), dur: lock - land - d(0.08), ease: 'power2.out' },
      { to: 1.03,              at: lock, dur: d(0.08),     ease: 'expo.out' },
      { to: 1.0,               at: lock + d(0.08), dur: d(1.1), ease: 'expo.out' }
    ]);
    tl.addLabel('land', land); tl.addLabel('lock', lock); tl.addLabel('rest', rest);
    tl.set({}, {}, end);
    return end;
  };
});
