/*
 * AreMan v2 — línea de tiempo del escudo (arquetipo Ancestro).
 * Una sola fuente para todos los destinos de render (scene.html / Hyperframes y la composición de Remotion).
 *   buildTimeline(kit, stg, T, tl)  → agrega los tweens a `tl` (en pausa) y devuelve la duración total.
 *
 * La tipomorfía NO se muestra: dirige el movimiento (el espectador la siente, no se la explicamos).
 *   · A  → la montaña se ESCRIBE como la letra A: dos trazos que bajan desde el vértice, siguiendo sus pendientes.
 *   · M  → las alas se abren y pasan por su pose más alta (la M) justo en el golpe; en ese mismo fotograma
 *          caen la A y la M del nombre, y el resto del nombre se arma alrededor de ellas.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.buildTimeline = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  return function buildTimeline(kit, stg, T, tl) {
    var d = T.d;                                            // segundos × tempo del arquetipo
    var N = stg.nodes, letters = stg.parts.text;            // letters: A r e M a n
    var APEX = [948, 497], BASE_L = [532, 1213], BASE_R = [1454, 1213];
    var SHOULDER_L = [830, 520], SHOULDER_R = [1180, 520];

    /* ── 1 · La A se escribe: pata izquierda y pata derecha bajan desde el vértice (ritmo de trazo: arranque seco, frena) ── */
    kit.sweep(tl, N.mountainL, { from: APEX, to: BASE_L, at: d(0.30), dur: d(0.85), ease: 'expo.out' });
    kit.sweep(tl, N.mountainR, { from: APEX, to: BASE_R, at: d(0.42), dur: d(0.85), ease: 'expo.out' });

    /* ── 2 · El árbol brota dentro de la A (el linaje vive en el hueco de la letra): crece desde la raíz con un leve pasarse ── */
    var treeAt = d(1.05);
    kit.wipe(tl, N.tree, 'up', { at: treeAt, dur: d(0.75), ease: 'power2.out' });
    kit.grow(tl, N.tree, { sx: 0.9, sy: 0.78, origin: [985, 1158], at: treeAt, dur: d(1.0), ease: 'back.out(1.4)' });

    /* ── 3 · El cóndor sale del vértice: primero la cabeza (sube desde la A), luego las alas se abren desde los hombros ── */
    var headAt = d(1.85);
    kit.wipe(tl, N.head, 'up', { at: headAt, dur: d(0.85), ease: 'power3.out' });
    kit.rise(tl, N.head, { dy: 26, at: headAt, dur: d(1.0), ease: 'power3.out' });   // leve asentamiento, sin arrastrar la losa del torso

    var wingAt = headAt + d(0.12), wingDur = d(1.05);
    // sin máscara: un borde recto sobre una masa negra se lee como bloque; el propio despliegue construye el ala
    kit.fade(tl, N.wingL, { at: wingAt,        dur: d(0.12), ease: 'power1.out' });
    kit.fade(tl, N.wingR, { at: wingAt + 0.03, dur: d(0.12), ease: 'power1.out' });
    // empiezan caídas (±26°) y recogidas; back.out las lleva ~5° por encima de su reposo: esa es la M, un instante
    kit.unfold(tl, N.wingL, { origin: SHOULDER_L, rot: -26, sx: 0.72, at: wingAt,        dur: wingDur, easeRot: 'back.out(3.2)' });
    kit.unfold(tl, N.wingR, { origin: SHOULDER_R, rot:  26, sx: 0.72, at: wingAt + 0.03, dur: wingDur, easeRot: 'back.out(3.2)' });

    /* ── 4 · Golpe: pico de la M = caen la A y la M del nombre; el resto se arma alrededor ── */
    var hit = wingAt + wingDur * 0.60;
    var order = [[0, 0], [3, 0], [1, 0.11], [2, 0.11], [4, 0.22], [5, 0.22]];   // [índice de letra, retraso]
    order.forEach(function (o) {
      var n = letters[o[0]], at = hit + d(o[1]);
      kit.wipe(tl, n, 'up', { at: at, dur: d(0.5), ease: 'expo.out' });
      kit.rise(tl, n, { dy: 90, at: at, dur: d(0.6), ease: 'expo.out' });
    });

    /* ── cámara: empuje lento hacia el encuadre, golpe seco en el hit, asentamiento a escala 1 exacta ── */
    var rest = hit + d(1.5);
    var end = rest + T.hold;
    kit.camera(tl, stg, [
      { from: 1.06, to: 1.0,   at: 0,   dur: hit,     ease: 'sine.out' },
      { to: 1.022,             at: hit, dur: d(0.10), ease: 'expo.out' },
      { to: 1.0,               at: hit + d(0.10), dur: d(1.3), ease: 'expo.out' }
    ]);
    tl.addLabel('hit', hit);
    tl.addLabel('rest', rest);                              // logo completo, quieto, en su color canónico
    tl.set({}, {}, end);
    return end;
  };
});
