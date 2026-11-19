/*
 * HERO OBJECT IN 3D — one object earns the whole film: it arrives, lands with a hit, the camera pushes in, a caption names it.
 * Everything is drawn by MG.three from timeline state; tween object properties, never run a loop. Randomness: MG.rng(seed) only.
 * Rules that make 3D read as design: ONE hero (>= 40 % of the frame), warm key + cool rim + dim room reflections, contact shadow,
 * a camera move that goes somewhere (dolly/dive), no idle wobble after the landing. Replace the label, colours and geometry.
 */
window.SCENE = {
  bg: '#dfe4ea',
  build: function (MG, T, S, tl) {
    var TH = window.THREE, u = Math.min(S.w, S.h) / 1080, d = T.d, portrait = S.h > S.w;
    // encuadre por proporción: en cuadros angostos la cámara se aleja para que el objeto quepa a lo ANCHO (9x16 ≈ 1,4; 4x5 ≈ 1,1; 1x1 y 16x9 = 1)
    var fit = Math.max(1, 1.4 / (S.w / S.h + 0.45));
    var CONTENT = { label: 'MARCA', caption: 'Un objeto.\nUna idea.' };
    var C = { hero: '#ff5a36', ink: '#14181d' };

    var sc = S.scene('main', { bg: 'linear-gradient(180deg,#e9edf1 0%,#cfd6df 100%)' }); MG.show(tl, sc, 0);
    var t3 = MG.three(sc, { fov: 32, exposure: 1.05, pixelRatio: 1 }).studio({ env: 0.5 })
      .env({ colors: ['#f4f7fb', '#c6d0dc', '#7d8899'], glow: { color: '#ffffff', u: 0.66, v: 0.3, r: 0.3 }, intensity: 1.0 })  // light studio sky: the page is light, reflections must be too
      .softShadow({ res: 2048, bounds: 4.2, radius: 9 })                                                                                // tight frustum: more texels per object
      .bloom({ amount: 0.85, blur: 14, threshold: 0.7 });                                                                                // DOM glow on the highlights only, zero extra GL passes
    t3.ground(-1.05, 0.28);
    t3.ao(1.9, 0.4).position.y = -1.04;                   // contact darkening: the object sits, it does not float

    /* hero: rounded cube with a clear-coated ceramic body, a chrome ring and a text face */
    var body = new TH.Mesh(new TH.RoundedBoxGeometry(2, 2, 2, 6, 0.22), t3.mat('ceramic', { color: C.hero, roughness: 0.3 }));
    body.castShadow = true;
    var ring = new TH.Mesh(new TH.TorusGeometry(1.5, 0.045, 16, 96), t3.mat('chrome', { color: 0xdfe6ee }));
    ring.rotation.x = Math.PI / 2; ring.castShadow = true; body.add(ring);   // chrome is where the env shows off
    var spark = new TH.Mesh(new TH.SphereGeometry(0.12, 24, 16), t3.mat('emissive', { color: 0xffd9a4, emissiveIntensity: 3.4 }));
    spark.position.set(1.28, 1.18, 0.86); body.add(spark);                  // a small hot point: the thing bloom() isolates
    var face = new TH.Mesh(new TH.PlaneGeometry(1.7, 0.85),
      new TH.MeshBasicMaterial({ map: t3.textTexture(CONTENT.label, { w: 1024, h: 512, size: 230, weight: 800, color: '#ffffff', font: 'var(--font-display), sans-serif' }), transparent: true, toneMapped: false }));
    face.position.z = 1.012; body.add(face);
    var pivot = new TH.Group(); pivot.add(body); t3.scene.add(pivot);

    /* camera: starts far and slightly high, dives in to a 3/4 view; the look target drifts to keep the object in the upper two thirds */
    var cam = t3.camera;
    cam.position.set(0, 2.4, 15 * fit); t3.look.set(0, portrait ? -1.1 : -0.1, 0);   // looking below the object lifts it into the upper part of the frame, leaving room for the caption

    /* beat 1 — arrival: the cube falls in from above, turning, and lands (hit) */
    var land = 0.55 + d(0.5);
    tl.set(pivot.position, { y: 3.4 }, 0); tl.set(pivot.rotation, { y: -2.4, x: 0.5 }, 0); tl.set(pivot.scale, { x: 0.001, y: 0.001, z: 0.001 }, 0);
    tl.to(pivot.scale, { x: 1, y: 1, z: 1, duration: d(0.25), ease: 'power2.out' }, 0.02);
    tl.to(pivot.position, { y: 0, duration: land - 0.02, ease: 'power3.in' }, 0.02);
    tl.to(pivot.rotation, { y: 0, x: 0, duration: land - 0.02 + d(0.5), ease: 'power3.out' }, 0.02);
    // squash on impact, released with an overshoot (mass: heavier = slower rebound)
    tl.to(pivot.scale, { y: 0.84, x: 1.1, z: 1.1, duration: d(0.08), ease: 'power2.out' }, land);
    tl.to(pivot.scale, { y: 1, x: 1, z: 1, duration: d(0.5), ease: 'elastic.out(1,0.5)' }, land + d(0.08));
    MG.cue('whoosh', land - 0.05, { dur: land - 0.02 });
    MG.cue('hit', land, { gain: 0.95 });

    /* beat 2 — the camera goes somewhere: a single dive to a close 3/4 view that arrives as the caption lands.
       rig() derives the pose from timeline time (no tween state to desync), so any frame can be re-rendered alone. */
    var dive = land + d(0.25);
    t3.rig({ from: [0, 2.4, 15 * fit], to: [(portrait ? 2.6 : 3.4) * fit, 1.9, (portrait ? 9.6 : 8.2) * fit], start: dive, end: dive + d(1.5),
             look: [0, portrait ? -1.1 : -0.1, 0], fov: 32, fovEnd: 30, ease: 'inOut' });

    /* beat 3 — caption (DOM over the canvas): mask-in, one line at a time */
    var cap = MG.text(sc, { text: CONTENT.caption, x: S.w / 2, y: S.h * (portrait ? 0.70 : 0.76), w: S.w * 0.84, size: (portrait ? 92 : 80) * u, weight: 800, align: 'center', lh: 1.05,
      font: 'var(--font-display)', split: 'words', color: C.ink, z: 5 });
    var e = MG.in(tl, cap, { how: 'mask', at: dive + d(0.7), dur: d(0.6), stagger: T.gap(1), ease: T.ease.in });
    MG.cue('pop', dive + d(0.75), { gain: 0.6 });
    MG.cue('shimmer', e, { gain: 0.5 });
    return e + T.hold + 0.8;
  }
};
