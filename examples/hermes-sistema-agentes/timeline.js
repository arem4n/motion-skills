/*
 * HERMES — el sistema de agentes de Sergio, explicado en volumen (3D).
 * Una sola cámara continua viaja entre estaciones: servidor → agentes → por dentro → cómo se habla con él → hacia afuera.
 * Datos: solo los que Sergio dio (ver SPEC.md). MetaSergius es el único perfil con nombre; los otros catorce van sin nombre.
 */
window.SCENE = {
  bg: '#dfe4ea',
  build: function (MG, T, S, tl) {
    var TH = window.THREE, u = Math.min(S.w, S.h) / 1080, d = T.d;
    var INK = '#14181d', CORAL = '#ff5a36';
    var CONTENT = {
      captions: [
        { t: 'HERMES', s: 'Un servidor · Ubuntu 26.04 · i7 · 8 GB' },
        { t: '15 PERFILES DE AGENTE', s: 'Uno de ellos: MetaSergius, copiloto de guion' },
        { t: 'POR DENTRO', s: 'Cada capa tiene un trabajo' },
        { t: 'CÓMO HABLAS CON ÉL', s: 'Telegram para pedir · SSH por Tailscale para operar' },
        { t: 'Y HACIA AFUERA', s: 'Claude Code y Antigravity operan Firebase por MCP' },
        { t: 'AREM4N OS', s: 'Tu sistema de agentes, de punta a punta' }
      ],
      layers: ['tmux · systemd', 'SQLite · sesiones', 'Docker · n8n', 'Obsidian · bóveda', 'cron · tareas']   // de abajo hacia arriba
    };

    var sc = S.scene('main', { bg: 'linear-gradient(180deg,#e9edf1 0%,#cfd6df 100%)' }); MG.show(tl, sc, 0);
    var t3 = MG.three(sc, { fov: 42, exposure: 1.05, shiftY: 0.15 }).studio({ env: 0.55 });
    t3.ground(0, 0.26);
    var cam = t3.camera, look = t3.look, scene = t3.scene;

    /* ───────── helpers ───────── */
    function mat(hex, rough, metal) { return new TH.MeshStandardMaterial({ color: hex, roughness: rough == null ? 0.55 : rough, metalness: metal || 0.05 }); }
    function rbox(w, h, dd, hex, r, rough) {
      var m = new TH.Mesh(new TH.RoundedBoxGeometry(w, h, dd, 4, r == null ? 0.08 : r), mat(hex, rough));
      m.castShadow = true; m.receiveShadow = true; return m;
    }
    function hide(o) { tl.set(o.scale, { x: 0.001, y: 0.001, z: 0.001 }, 0); }
    function pop(o, at, dur, ease) { tl.to(o.scale, { x: 1, y: 1, z: 1, duration: dur || d(0.5), ease: ease || 'back.out(1.6)' }, at); }
    function go(at, dur, pos, lk, ease) {
      tl.to(cam.position, { x: pos[0], y: pos[1], z: pos[2], duration: dur, ease: ease || 'power3.inOut' }, at);
      tl.to(look, { x: lk[0], y: lk[1], z: lk[2], duration: dur, ease: ease || 'power3.inOut' }, at);
    }
    function caption(i, at, until) {
      var c = CONTENT.captions[i], y = S.h * 0.715;
      var t = MG.text(sc, { text: c.t, x: S.w / 2, y: y, w: S.w * 0.9, size: 128 * u, weight: 400, align: 'center', lh: 1, font: 'var(--font-display)', split: 'words', color: INK, z: 8 });
      var s = MG.text(sc, { text: c.s, x: S.w / 2, y: y + 140 * u, w: S.w * 0.84, size: 44 * u, weight: 700, align: 'center', lh: 1.2, font: 'var(--font-body)', color: '#3d4753', z: 8 });
      MG.in(tl, t, { how: 'mask', at: at, dur: d(0.55), stagger: T.gap(1), ease: T.ease.in });
      MG.in(tl, s.el, { how: 'rise', at: at + d(0.2), dur: d(0.5), dy: 22 * u, ease: T.ease.in });
      if (until) MG.out(tl, [t.el, s.el], { how: 'fade', at: until, dur: d(0.4) });
    }
    function label(anchorObj, text, at, until, o) {
      o = o || {};
      var a = t3.anchor(anchorObj, { offset: o.offset, dx: o.dx, dy: o.dy });
      var tx = MG.text(a, { text: text, x: 0, y: 0, w: 640, size: (o.size || 40) * u, weight: 700, align: o.align || 'center', lh: 1.1, font: 'var(--font-body)', color: o.color || INK, css: 'white-space:pre' });
      MG.in(tl, tx.el, { how: 'rise', at: at, dur: d(0.45), dy: 16 * u, ease: T.ease.in });
      if (until) MG.out(tl, tx.el, { how: 'fade', at: until, dur: d(0.35) });
      return tx;
    }
    /* a tube that draws itself (draw range follows `k.p`) and a packet that rides a curve (position follows `k.u`) */
    function link(pts, r, hex, op) {
      var curve = new TH.CatmullRomCurve3(pts.map(function (p) { return new TH.Vector3(p[0], p[1], p[2]); }));
      var g = new TH.TubeGeometry(curve, 64, r, 8, false), total = g.index.count;
      var m = new TH.Mesh(g, new TH.MeshStandardMaterial({ color: hex, roughness: 0.4, transparent: true, opacity: op, depthWrite: false }));
      var k = { curve: curve, mesh: m, p: 0, total: total };
      t3.pre(function () { var n = Math.floor(k.p * (total / 48)) * 48; g.setDrawRange(0, n); m.visible = n > 0; });
      scene.add(m); return k;
    }
    function packet(k, at, dur, hex) {
      var m = new TH.Mesh(new TH.SphereGeometry(0.13, 20, 14), new TH.MeshBasicMaterial({ color: hex || CORAL, toneMapped: false }));
      var s = { u: 0 }; m.visible = false; scene.add(m);
      t3.pre(function () { m.visible = s.u > 0 && s.u < 1; if (m.visible) m.position.copy(k.curve.getPoint(s.u)); });
      tl.to(s, { u: 1, duration: dur, ease: 'none' }, at);
      return at + dur;
    }

    /* ───────── escenario: servidor (torre de 5 losas) ───────── */
    var LAYER_HEX = ['#5b6775', '#2a9d8f', '#3b82c4', '#8a6fd1', '#e9b44c'], SLATE = '#2b3440';
    var srv = new TH.Group(); scene.add(srv);
    var slabs = [], baseY = [];
    for (var i = 0; i < 5; i++) {
      var sl = rbox(2.8, 0.5, 2.0, SLATE, 0.09, 0.5); sl.position.y = 0.25 + i * 0.54; baseY.push(sl.position.y);
      var strip = new TH.Mesh(new TH.BoxGeometry(2.0, 0.07, 0.02), new TH.MeshStandardMaterial({ color: '#9aa6b5', roughness: 0.4 }));
      strip.position.set(0, 0, 1.01); sl.add(strip);
      srv.add(sl); slabs.push(sl);
    }
    var TOP = 0.25 + 4 * 0.54 + 0.25;                     // altura de la torre armada (2.67)

    /* tomas 1: Hermes cae, gira y aterriza */
    cam.position.set(3.8, 3.6, 9.4); look.set(0, 1.3, 0);
    var land = 0.35 + d(0.5);
    tl.set(srv.position, { y: 6 }, 0); tl.set(srv.rotation, { y: -1.6 }, 0); hide(srv);
    tl.to(srv.scale, { x: 1, y: 1, z: 1, duration: d(0.25), ease: 'power2.out' }, 0.02);
    tl.to(srv.position, { y: 0, duration: land - 0.02, ease: 'power3.in' }, 0.02);
    tl.to(srv.rotation, { y: 0, duration: land - 0.02 + d(0.45), ease: 'power3.out' }, 0.02);
    tl.to(srv.scale, { y: 0.93, x: 1.04, z: 1.04, duration: d(0.07), ease: 'power2.out' }, land);
    tl.to(srv.scale, { y: 1, x: 1, z: 1, duration: d(0.45), ease: 'elastic.out(1,0.55)' }, land + d(0.07));
    MG.cue('whoosh', land - 0.05, { dur: land - 0.02 }); MG.cue('hit', land, { gain: 1 });
    go(land + 0.1, d(2.6), [3.0, 3.4, 8.2], [0, 1.4, 0], 'sine.inOut');
    caption(0, land + 0.35, 4.6);

    /* ───────── tomas 2: once agentes salen en anillo ───────── */
    var N = 15, R = 3.7, ringG = new TH.Group(); scene.add(ringG);
    var plinth = new TH.Mesh(new TH.CylinderGeometry(R + 0.85, R + 0.85, 0.1, 72), mat('#f6f8fa', 0.9));
    plinth.position.y = 0.05; plinth.receiveShadow = true; ringG.add(plinth);
    var agents = [], lines = [], META = N - 1, a0 = 62 * Math.PI / 180;
    for (var k = 0; k < N; k++) {
      var isM = k === META, sz = isM ? 0.82 : 0.56;
      var ag = rbox(sz, sz, sz, isM ? CORAL : '#2f3b52', 0.1, 0.45);
      var ang = a0 - k * (2 * Math.PI / N);
      var tx = Math.cos(ang) * R, tz = Math.sin(ang) * R, ty = 0.1 + sz / 2;
      ag.position.set(0, TOP + 0.2, 0); ag.userData = { tx: tx, ty: ty, tz: tz };
      ag.rotation.y = -ang + Math.PI / 4;
      ringG.add(ag); agents.push(ag);
      var gl = new TH.BufferGeometry(); gl.setAttribute('position', new TH.BufferAttribute(new Float32Array(6), 3));
      var ln = new TH.Line(gl, new TH.LineBasicMaterial({ color: isM ? CORAL : INK, transparent: true, opacity: isM ? 0.8 : 0.3 }));
      ln.frustumCulled = false; scene.add(ln); lines.push({ ln: ln, ag: ag });
    }
    var wp = new TH.Vector3();
    t3.pre(function () {
      lines.forEach(function (L) {
        var a = L.ln.geometry.attributes.position; ringG.updateWorldMatrix(true, false);
        L.ag.getWorldPosition(wp);
        L.ln.visible = L.ag.scale.x > 0.05; a.setXYZ(0, 0, TOP - 0.1, 0); a.setXYZ(1, wp.x, wp.y, wp.z); a.needsUpdate = true;
      });
    });
    hide(plinth);
    var T2 = 4.1;
    go(T2 - 0.2, d(1.9), [0.5, 15.0, 18.5], [0, 0.3, 0.2]);
    tl.to(plinth.scale, { x: 1, y: 1, z: 1, duration: d(0.6), ease: 'power3.out' }, T2 + 0.3);
    agents.forEach(function (ag, k) {
      var at = T2 + 0.9 + k * 0.13, dd = ag.userData;
      hide(ag);
      tl.to(ag.scale, { x: 1, y: 1, z: 1, duration: d(0.4), ease: 'back.out(1.5)' }, at);
      tl.to(ag.position, { x: dd.tx, y: dd.ty, z: dd.tz, duration: d(0.75), ease: 'power3.out' }, at);
      MG.cue(k === META ? 'pop' : 'tick', at + d(0.28), { gain: k === META ? 0.9 : 0.45 });
    });
    var metaAt = T2 + 0.9 + META * 0.13 + d(0.5);
    tl.to(agents[META].scale, { x: 1.18, y: 1.18, z: 1.18, duration: d(0.18), ease: 'power2.out' }, metaAt);
    tl.to(agents[META].scale, { x: 1, y: 1, z: 1, duration: d(0.5), ease: 'elastic.out(1,0.5)' }, metaAt + d(0.18));
    MG.cue('shimmer', metaAt + 0.05, { gain: 0.6 });
    label(agents[META], 'MetaSergius', metaAt + 0.1, 9.9, { offset: [0, 0, 0], dy: 92 * u, size: 44 });
    caption(1, T2 + 0.9, 10.2);

    /* ───────── tomas 3: vista explotada — lo que hay dentro ───────── */
    var T3 = 10.2;
    tl.to(ringG.scale, { x: 0.001, y: 0.001, z: 0.001, duration: d(0.55), ease: 'power3.in' }, T3 - 0.15);
    go(T3 - 0.1, d(1.5), [6.2, 4.6, 13.5], [1.1, 2.8, 0]);
    slabs.forEach(function (sl, i) {
      var at = T3 + 0.55 + i * 0.16, c = new TH.Color(LAYER_HEX[i]);
      tl.to(sl.position, { y: 0.25 + i * 1.28, duration: d(0.7), ease: 'power3.out' }, at);
      tl.to(sl.material.color, { r: c.r, g: c.g, b: c.b, duration: d(0.5), ease: 'power2.out' }, at);
      MG.cue('tick', at + 0.05, { gain: 0.5 });
      label(sl, CONTENT.layers[i], at + d(0.5), 14.8, { offset: [1.8, 0.0, 0.0], align: 'left', dy: -18 * u });
    });
    tl.to(cam.position, { x: 5.6, y: 4.5, z: 12.4, duration: d(2.6), ease: 'sine.inOut' }, T3 + 2.0);
    caption(2, T3 + 0.4, 16.1);
    var T3b = 14.9;                                         // vuelven a armarse
    slabs.forEach(function (sl, i) {
      var c = new TH.Color(SLATE), at = T3b + (4 - i) * 0.07;
      tl.to(sl.position, { y: baseY[i], duration: d(0.5), ease: 'power3.inOut' }, at);
      tl.to(sl.material.color, { r: c.r, g: c.g, b: c.b, duration: d(0.4), ease: 'power2.inOut' }, at);
    });
    MG.cue('hit', T3b + 0.45, { gain: 0.7 });
    tl.to(ringG.scale, { x: 1, y: 1, z: 1, duration: d(0.7), ease: 'back.out(1.4)' }, T3b + 0.45);

    /* ───────── tomas 4: teléfono y portátil hablan con Hermes ───────── */
    var T4 = 16.3;
    var phone = new TH.Group();
    var pb = rbox(1.0, 1.9, 0.14, '#20262e', 0.12); phone.add(pb);
    var pscr = new TH.Mesh(new TH.PlaneGeometry(0.86, 1.72), new TH.MeshBasicMaterial({ color: '#eaf1f7', toneMapped: false })); pscr.position.z = 0.075; phone.add(pscr);
    var b1 = new TH.Mesh(new TH.PlaneGeometry(0.55, 0.22), new TH.MeshBasicMaterial({ color: '#cfd6df', toneMapped: false })); b1.position.set(-0.12, 0.45, 0.08); phone.add(b1);
    var b2 = new TH.Mesh(new TH.PlaneGeometry(0.5, 0.22), new TH.MeshBasicMaterial({ color: CORAL, toneMapped: false })); b2.position.set(0.14, 0.05, 0.08); phone.add(b2);
    phone.position.set(-2.5, 0.96, 9.4); phone.rotation.y = 0.32; scene.add(phone); hide(phone);
    var lap = new TH.Group();
    var lbase = rbox(2.4, 0.1, 1.6, '#3a4350', 0.04); lbase.position.y = 0.05; lap.add(lbase);
    var lid = new TH.Group(); lid.position.set(0, 0.1, -0.78); lid.rotation.x = -0.3; lap.add(lid);
    var lscr = rbox(2.4, 1.5, 0.08, '#2a313b', 0.04); lscr.position.y = 0.75; lid.add(lscr);
    var lface = new TH.Mesh(new TH.PlaneGeometry(2.2, 1.34), new TH.MeshBasicMaterial({ map: t3.textTexture('>_ ssh hermes', { w: 1024, h: 624, bg: '#11161c', color: '#7fe0c9', size: 118, weight: 700, font: 'Inter, monospace' }), toneMapped: false }));
    lface.position.set(0, 0.75, 0.045); lid.add(lface);
    lap.position.set(2.4, 0, 9.0); lap.rotation.y = -0.25; scene.add(lap); hide(lap);

    var tg = link([[-2.35, 1.7, 9.4], [-2.4, 4.8, 6.0], [-1.0, 4.2, 2.2], [-0.4, TOP + 0.05, 0.5]], 0.035, INK, 0.5);
    var ts = link([[3.5, 0.5, 8.4], [2.6, 1.0, 5.4], [1.6, 1.5, 2.8], [1.0, 1.4, 1.0]], 0.13, '#2a9d8f', 0.42);
    var gate = new TH.Mesh(new TH.TorusGeometry(0.62, 0.07, 14, 40), mat(INK, 0.4)); gate.castShadow = true;
    var gp = ts.curve.getPoint(0.5), gq = ts.curve.getPoint(0.56); gate.position.copy(gp); gate.lookAt(gq); scene.add(gate); hide(gate);

    go(T4 - 0.5, d(1.9), [0.2, 10.5, 24.0], [0.0, 0.8, 4.5]);
    pop(phone, T4 + 0.3, d(0.55)); pop(lap, T4 + 0.55, d(0.55));
    MG.cue('pop', T4 + 0.45, { gain: 0.6 }); MG.cue('pop', T4 + 0.7, { gain: 0.6 });
    tl.to(tg, { p: 1, duration: d(0.9), ease: 'power2.inOut' }, T4 + 1.1);
    tl.to(ts, { p: 1, duration: d(0.9), ease: 'power2.inOut' }, T4 + 1.4);
    pop(gate, T4 + 2.0, d(0.5));
    MG.cue('whoosh', T4 + 1.0, { dur: 0.8, gain: 0.5 });
    var pk = T4 + 2.4, pd = d(1.0);
    for (var j = 0; j < 3; j++) {
      var s1 = pk + j * 1.05, s2 = s1 + 0.45;
      packet(tg, s1, pd); packet(ts, s2, pd);
      MG.cue('tick', s1 + pd, { gain: 0.5 }); MG.cue('tick', s2 + pd, { gain: 0.5 });
      tl.to(gate.scale, { x: 1.18, y: 1.18, z: 1.18, duration: d(0.1), ease: 'power2.out' }, s2 + pd * 0.5 - 0.05);
      tl.to(gate.scale, { x: 1, y: 1, z: 1, duration: d(0.35), ease: 'power2.out' }, s2 + pd * 0.5 + d(0.05));
    }
    label(phone, 'Telegram', T4 + 0.9, 22.4, { offset: [0, -1.0, 0], dy: 34 * u });
    label(lap, 'Termius · SSH', T4 + 1.1, 22.4, { offset: [0, 0, 0.9], dy: 64 * u });
    label(gate, 'Ed25519 · fail2ban', T4 + 2.3, 22.4, { offset: [-0.5, -0.9, 0.7], align: 'right', dx: -6 * u });
    label({ matrixWorld: new TH.Matrix4().setPosition(2.3, 1.1, 5.3), updateWorldMatrix: function () {} }, 'Tailscale', T4 + 2.1, 22.4, { align: 'left', dx: 44 * u, dy: 12 * u });
    caption(3, T4 + 0.2, 22.8);

    /* ───────── tomas 5: hacia afuera — Firebase por MCP ───────── */
    var T5 = 22.9;
    var cloud = new TH.Group();
    [[-1.0, 0, 0, 0.95], [0.1, 0.35, 0, 1.3], [1.15, -0.05, 0, 0.95]].forEach(function (c) {
      var sp = new TH.Mesh(new TH.SphereGeometry(c[3], 28, 20), mat('#fbfcfd', 0.9)); sp.position.set(c[0], c[1], c[2]); cloud.add(sp);   // sin sombra: cae fuera del frustum de la luz y quedaría una astilla
    });
    cloud.position.set(0, 2.3, -8.8); scene.add(cloud); hide(cloud);
    var mcp = link([[0, TOP - 0.2, -1.0], [0.4, 3.6, -3.4], [0.2, 3.1, -6.0], [0, 2.4, -7.6]], 0.1, '#3b82c4', 0.45);
    var R5 = T5 - 0.6;                                      // lo de la toma 4 se retira para despejar la toma 5
    [phone, lap, gate].forEach(function (o) { tl.to(o.scale, { x: 0.001, y: 0.001, z: 0.001, duration: d(0.4), ease: 'power3.in' }, R5); });
    tl.to(tg, { p: 0, duration: d(0.4), ease: 'power2.in' }, R5); tl.to(ts, { p: 0, duration: d(0.4), ease: 'power2.in' }, R5);
    tl.to(ringG.scale, { x: 0.001, y: 0.001, z: 0.001, duration: d(0.5), ease: 'power3.in' }, R5);   // los agentes vuelven al servidor
    go(T5 - 0.4, d(1.9), [2.0, 15.5, 12.5], [0, 2.0, -4.4]);
    pop(cloud, T5 + 0.9, d(0.6)); MG.cue('pop', T5 + 1.05, { gain: 0.7 });
    tl.to(mcp, { p: 1, duration: d(0.9), ease: 'power2.inOut' }, T5 + 1.3);
    MG.cue('whoosh', T5 + 1.2, { dur: 0.8, gain: 0.5 });
    for (var q = 0; q < 3; q++) { var e = packet(mcp, T5 + 2.5 + q * 0.7, d(1.0)); MG.cue('tick', e, { gain: 0.5 }); }
    label(cloud, 'Firestore · tommybox', T5 + 1.5, T5 + 4.3, { offset: [0, 1.6, 0], dy: -6 * u });
    label({ matrixWorld: new TH.Matrix4().setPosition(0.3, 3.6, -3.8), updateWorldMatrix: function () {} }, 'Firebase MCP\nFirestore\nAuth · deploys', T5 + 1.9, T5 + 4.3, { align: 'left', dx: 34 * u });
    caption(4, T5 + 0.3, T5 + 6.1);

    /* ───────── tomas 6: plano general y cierre ───────── */
    var T6 = T5 + 5.0;
    go(T6 - 0.1, d(2.2), [10.0, 21.0, 29.0], [0, 0.4, -0.5]);
    tl.to(ringG.scale, { x: 1, y: 1, z: 1, duration: d(0.7), ease: 'back.out(1.4)' }, T6 + 0.2);
    pop(phone, T6 + 1.9, d(0.5)); pop(lap, T6 + 2.05, d(0.5)); pop(gate, T6 + 2.2, d(0.45));      // vuelven al plano general
    tl.to(tg, { p: 1, duration: d(0.7), ease: 'power2.inOut' }, T6 + 2.2); tl.to(ts, { p: 1, duration: d(0.7), ease: 'power2.inOut' }, T6 + 2.3);
    MG.cue('pop', T6 + 2.0, { gain: 0.5 }); MG.cue('pop', T6 + 2.15, { gain: 0.5 });
    MG.cue('riser', T6 + 1.2, { dur: 1.4, gain: 0.5 });
    caption(5, T6 + 1.5, null);
    MG.cue('hit', T6 + 1.6, { gain: 0.8 }); MG.cue('shimmer', T6 + 1.7, { gain: 0.6 });
    return T6 + 1.7 + T.hold + 1.6;
  }
};
