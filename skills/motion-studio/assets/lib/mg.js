/*
 * mg.js — deterministic motion-graphics kit (DOM + SVG + GSAP).
 *
 * Contract: every function only ADDS TWEENS to a paused GSAP timeline (or builds static DOM).
 * No clock, no Math.random, no timers, no endless repeats. Any frame is a pure function of time, so the same scene
 * renders identically here, in Remotion (`tl.time(frame/fps)`) or in a Hyperframes-style seeker.
 *
 * Design units: the stage is a fixed canvas (e.g. 1080x1920) scaled to the viewport, so a scene is written once in
 * "design pixels" and rendered at any size with the same aspect ratio.
 *
 *   MG.use(gsap)                       bind GSAP
 *   MG.tokens(json, name)              motion personality -> {ease, stagger, tempo, hold, d(), gap()}
 *   MG.ready(fonts, fn)                wait for fonts, then run fn (build the scene inside it)
 *   MG.stage({w,h,bg,host?})           -> S  (S.world, S.scene(), S.frame, S.overlay); host = container element (default <body>)
 *   MG.box / text / shape / image / icon / barChart / lineChart / ring   build elements
 *   MG.in / out / emph / counter / draw / growBars / typewriter           animate elements
 *   MG.transition / camera / cue / expose      transition types incl. zoom-through (dive into a window) and brush (painted wipe)
 *   MG.morph / carry / rectOf                  continuity: a container or element survives the boundary and becomes the next beat
 *   MG.spring({bounce,wobbles})                measured spring ease;  MG.operator(tl,S,{amp,holds,hits})  operated camera
 *   MG.inFrame(el)                             must never leave the frame (validate.py checks)
 *   MG.boil / paper / stepped(12)              hand-painted look: boiling linework, paper, animation on twos
 *   MG.three(scene,{...})              Three.js canvas redrawn from timeline state after every seek (needs vendor/three.min.js)
 *   MG.rng(seed)                       seeded PRNG for any variation
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MG = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var gsap = null, SVGNS = 'http://www.w3.org/2000/svg', cues = [], finalizers = [], uid = 0;
  var boundaries = [], CARRY_TYPES = ['zoom-through', 'morph', 'carry'], stepFps = 0, STAGE = null;
  var api = {};

  api.use = function (g) { gsap = g || window.gsap; return api; };
  /** Clear per-scene module state (cues, finalizers, boundaries, stepped fps, 3D canvases). Call before building a scene when several
   *  scenes share this module in one page (Remotion <GsapScene>); a standalone scene.html never needs it. uid keeps counting (unique SVG ids). */
  api.reset = function () { cues = []; finalizers = []; boundaries = []; stepFps = 0; threes = []; return api; };

  /* ───────────────────────── tokens ───────────────────────── */
  api.tokens = function (all, name) {
    var table = all.personalities || all.archetypes, p = table[name];
    if (!p) throw new Error('Unknown personality "' + name + '". Known: ' + Object.keys(table).join(', '));
    var t = Object.assign({}, all.defaults, p, { ease: Object.assign({}, all.defaults.ease, p.ease || {}) });
    t.name = name;
    t.d = function (s) { return s * t.tempo; };                   // seconds scaled by the personality's tempo
    t.gap = function (n) { return (n == null ? 1 : n) * t.stagger * t.tempo; };
    return t;
  };

  /* ───────────────────────── boot ───────────────────────── */
  /** Load the declared fonts (so text measures correctly), then run fn. Sets __ready only through expose(). */
  api.ready = function (fonts, fn) {
    var loads = (fonts || []).map(function (f) { return document.fonts.load(f); });
    Promise.all(loads).then(function () { return document.fonts.ready; }).then(fn);
  };

  function el(tag, css, cls) {
    var n = document.createElement(tag);
    if (css) n.style.cssText = css;
    if (cls) n.className = cls;
    return n;
  }
  function px(v) { return typeof v === 'number' ? v + 'px' : v; }

  /* ───────────────────────── stage & scenes ───────────────────────── */
  api.stage = function (o) {
    var W = o.w, H = o.h, host = o.host || document.body, vw, vh;
    if (!o.host) { host.style.cssText = 'margin:0;background:#000;overflow:hidden;width:100vw;height:100vh'; vw = innerWidth; vh = innerHeight; }
    else { host.style.position = 'relative'; host.style.overflow = 'hidden'; vw = host.clientWidth; vh = host.clientHeight; }
    var s = Math.min(vw / W, vh / H);
    var frame = el('div', 'position:absolute;left:0;top:0;width:' + W + 'px;height:' + H + 'px;overflow:hidden;' +
      'transform-origin:0 0;transform:translate(' + (vw - W * s) / 2 + 'px,' + (vh - H * s) / 2 + 'px) scale(' + s + ');' +
      'background:' + (o.bg || '#000'), 'mg-stage');
    var world = el('div', 'position:absolute;left:0;top:0;width:' + W + 'px;height:' + H + 'px;transform-origin:50% 50%', 'mg-world');
    var overlay = el('div', 'position:absolute;left:0;top:0;width:' + W + 'px;height:' + H + 'px;pointer-events:none', 'mg-overlay');
    frame.appendChild(world); frame.appendChild(overlay); host.appendChild(frame);
    var S = { w: W, h: H, frame: frame, world: world, overlay: overlay, scenes: [], bg: o.bg };
    STAGE = S;
    /** A scene is a full-size group, hidden until a transition (or `show`) brings it in. */
    S.scene = function (name, so) {
      so = so || {};
      var g = el('div', 'position:absolute;left:0;top:0;width:' + W + 'px;height:' + H + 'px;visibility:hidden;' +
        (so.bg ? 'background:' + so.bg : ''), 'mg-scene');
      g.dataset.scene = name; world.appendChild(g);
      gsap.set(g, { x: 0, y: 0 });   // constant transform from frame 0: a late 'translate(0,0)' would re-rasterise text and break random access
      var sc = { el: g, name: name, w: W, h: H };
      S.scenes.push(sc);
      return sc;
    };
    return S;
  };

  /** Show a scene at time `at` (hard cut) and optionally hide it at `until`. */
  api.show = function (tl, sc, at, until) {
    at = at || 0;
    if (at > 0) tl.set(sc.el, { autoAlpha: 0 }, 0);          // (never two sets at t=0 on the same property)
    tl.set(sc.el, { autoAlpha: 1 }, at);
    if (until != null) tl.set(sc.el, { autoAlpha: 0 }, until);
  };

  /* ───────────────────────── elements ───────────────────────── */
  function parent(p) { return p.el || p; }

  /** Generic positioned box. o: x,y,w,h,bg,radius,border,opacity,z,css */
  api.box = function (p, o) {
    var n = el('div', 'position:absolute;left:' + px(o.x || 0) + ';top:' + px(o.y || 0) + ';width:' + px(o.w == null ? 0 : o.w) +
      ';height:' + px(o.h == null ? 0 : o.h) + ';' + (o.bg ? 'background:' + o.bg + ';' : '') +
      (o.radius != null ? 'border-radius:' + px(o.radius) + ';' : '') + (o.border ? 'border:' + o.border + ';' : '') +
      (o.z != null ? 'z-index:' + o.z + ';' : '') + (o.css || ''), 'mg-box');
    parent(p).appendChild(n);
    return n;
  };

  /** Shapes are boxes; type: rect | circle | line. For a line give w (length) and h (thickness). */
  api.shape = function (p, o) {
    var n = api.box(p, Object.assign({}, o, { bg: o.fill || o.bg, radius: o.type === 'circle' ? '50%' : o.radius }));
    n.className = 'mg-shape';
    return n;
  };

  /**
   * Text block. o: text, x, y, w, size, weight, color, font, align (left|center|right), valign ('middle' centres on y),
   * lh (line-height), ls (letter-spacing), split ('words' | 'chars' | 'lines'), upper, italic, css.
   * Returns {el, words, wraps, chars, lines}. `words` are the inner spans of a masked wrapper, so a word can rise out of
   * a hard edge (the classic kinetic-type reveal) without extra markup.
   */
  api.text = function (p, o) {
    var w = o.w || 900, align = o.align || 'left';
    var left = align === 'center' ? o.x - w / 2 : align === 'right' ? o.x - w : o.x;
    var n = el('div', 'position:absolute;left:' + left + 'px;top:' + (o.y || 0) + 'px;width:' + w + 'px;text-align:' + align +
      ';font-family:' + (o.font || 'var(--font-body)') + ';font-size:' + o.size + 'px;font-weight:' + (o.weight || 600) +
      ';color:' + (o.color || '#fff') + ';line-height:' + (o.lh || 1.1) + ';letter-spacing:' + (o.ls || 0) +
      ';white-space:normal;' + (o.upper ? 'text-transform:uppercase;' : '') + (o.italic ? 'font-style:italic;' : '') +
      (o.css || ''), 'mg-text');
    var res = { el: n, words: [], wraps: [], chars: [], lines: [] };
    var raw = o.upper ? String(o.text).toUpperCase() : String(o.text);
    function word(parentEl, txt, splitChars) {
      var wrap = el('span', 'display:inline-block;overflow:hidden;vertical-align:top;padding:0.14em 0.06em 0.18em;margin:-0.14em -0.06em -0.18em', 'mg-wm');
      var inner = el('span', 'display:inline-block', 'mg-w');
      if (splitChars) {
        txt.split('').forEach(function (ch) {
          var c = el('span', 'display:inline-block', 'mg-c'); c.textContent = ch; inner.appendChild(c); res.chars.push(c);
        });
      } else inner.textContent = txt;
      wrap.appendChild(inner); parentEl.appendChild(wrap);
      res.words.push(inner); res.wraps.push(wrap);
    }
    if (o.split === 'lines') {
      raw.split('\n').forEach(function (ln) {
        var d = el('div', 'overflow:hidden;padding:0.14em 0 0.18em;margin:-0.14em 0 -0.18em', 'mg-lm');
        var i = el('div', '', 'mg-l'); i.textContent = ln; d.appendChild(i); n.appendChild(d);
        res.lines.push(i);
      });
    } else if (o.split === 'words' || o.split === 'chars') {
      raw.split('\n').forEach(function (ln, li) {
        if (li) n.appendChild(document.createElement('br'));
        ln.split(' ').forEach(function (wd, wi, arr) {
          word(n, wd, o.split === 'chars');
          if (wi < arr.length - 1) n.appendChild(document.createTextNode(' '));
        });
      });
    } else n.textContent = raw;
    parent(p).appendChild(n);
    if (o.valign === 'middle') n.style.top = (o.y - n.offsetHeight / 2) + 'px';
    res.height = n.offsetHeight;
    return res;
  };

  /** Image / screenshot. o: src, x, y, w, h, fit (cover|contain), radius, shadow */
  api.image = function (p, o) {
    var n = el('img', 'position:absolute;left:' + o.x + 'px;top:' + o.y + 'px;width:' + o.w + 'px;height:' + o.h + 'px;object-fit:' +
      (o.fit || 'cover') + ';border-radius:' + (o.radius || 0) + 'px;' + (o.shadow ? 'box-shadow:' + o.shadow + ';' : ''), 'mg-img');
    n.src = o.src; parent(p).appendChild(n); return n;
  };

  var ICONS = {   // 24x24 stroke icons: drawable with MG.draw
    check: 'M4 12.5 L9.5 18 L20 6', arrow: 'M4 12 H20 M13 5 L20 12 L13 19', plus: 'M12 4 V20 M4 12 H20',
    play: 'M7 4 L19 12 L7 20 Z', bolt: 'M13 2 L5 14 H12 L11 22 L19 9 H12 Z', star: 'M12 3 L14.6 9 L21 9.6 L16.2 13.8 L17.6 20.2 L12 17 L6.4 20.2 L7.8 13.8 L3 9.6 L9.4 9 Z',
    close: 'M5 5 L19 19 M19 5 L5 19', up: 'M12 20 V5 M5 12 L12 5 L19 12'
  };
  /** Stroke icon as <svg>. o: name | d, x, y, size, color, stroke. Returns {el, path}. */
  api.icon = function (p, o) {
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.style.cssText = 'position:absolute;left:' + o.x + 'px;top:' + o.y + 'px;width:' + o.size + 'px;height:' + o.size + 'px;overflow:visible';
    var path = document.createElementNS(SVGNS, 'path');
    path.setAttribute('d', o.d || ICONS[o.name]);
    path.setAttribute('fill', 'none'); path.setAttribute('stroke', o.color || '#fff');
    path.setAttribute('stroke-width', o.stroke || 2); path.setAttribute('stroke-linecap', 'round'); path.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(path); parent(p).appendChild(svg);
    return { el: svg, path: path };
  };

  /* ───────────────────────── charts (data must come from the brief; never invented) ───────────────────────── */
  /**
   * Bar chart. o: x,y,w,h, data:[{label,value,color}], max, gap, radius, labelSize, valueSize, color, textColor, fmt(v), font
   * Returns {bars, labels, values, axis, targets}. Animate with MG.growBars.
   */
  api.barChart = function (p, o) {
    var n = o.data.length, gap = o.gap == null ? 0.28 : o.gap, bw = o.w / (n + (n + 1) * gap);
    var max = o.max || Math.max.apply(null, o.data.map(function (d) { return d.value; }));
    var fmt = o.fmt || function (v) { return String(Math.round(v)); };
    var chart = { bars: [], labels: [], values: [], targets: [], fmt: fmt, axis: null };
    chart.axis = api.box(p, { x: o.x, y: o.y + o.h, w: o.w, h: 3, bg: o.axisColor || 'rgba(255,255,255,.35)', radius: 2 });
    o.data.forEach(function (d, i) {
      var bh = Math.max(2, o.h * d.value / max), bx = o.x + gap * bw + i * (bw + gap * bw);
      var bar = api.box(p, { x: bx, y: o.y + o.h - bh, w: bw, h: bh, bg: d.color || o.color || '#fff', radius: o.radius == null ? 10 : o.radius,
        css: 'transform-origin:50% 100%' });
      var val = api.text(p, { text: fmt(d.value), x: bx + bw / 2, y: o.y + o.h - bh - (o.valueSize || 44) * 1.35, w: bw + 40, align: 'center',
        size: o.valueSize || 44, weight: 800, color: o.textColor || '#fff', font: o.font, css: 'font-variant-numeric:tabular-nums' });
      var lab = api.text(p, { text: d.label, x: bx + bw / 2, y: o.y + o.h + 22, w: bw + 60, align: 'center', size: o.labelSize || 28, weight: 500,
        color: o.labelColor || 'rgba(255,255,255,.7)', font: o.font });
      chart.bars.push(bar); chart.values.push(val.el); chart.labels.push(lab.el); chart.targets.push(d.value);
    });
    return chart;
  };

  /** Animate a bar chart: bars grow from the baseline, value labels follow and count up. */
  api.growBars = function (tl, c, o) {
    o = o || {};
    var at = o.at || 0, dur = o.dur || 0.9, st = o.stagger == null ? 0.12 : o.stagger;
    c.bars.forEach(function (bar, i) {
      var s = at + i * st;
      tl.set(bar, { scaleY: 0 }, 0);
      tl.to(bar, { scaleY: 1, duration: dur, ease: o.ease || 'power3.out' }, s);
      var v = c.values[i];
      tl.set(v, { autoAlpha: 0 }, 0);
      tl.to(v, { autoAlpha: 1, duration: 0.25, ease: 'power1.out' }, s + dur * 0.35);
      api.counter(tl, v, { from: 0, to: c.targets[i], at: s, dur: dur, fmt: c.fmt, ease: o.ease || 'power3.out' });
    });
    c.labels.forEach(function (l, i) {
      tl.set(l, { autoAlpha: 0, y: 14 }, 0);
      tl.to(l, { autoAlpha: 1, y: 0, duration: 0.45, ease: 'power2.out' }, at + i * st);
    });
    tl.set(c.axis, { scaleX: 0, transformOrigin: '0 50%' }, 0);
    tl.to(c.axis, { scaleX: 1, duration: dur * 0.8, ease: 'power3.out' }, at);
  };

  /** Line chart (SVG). o: x,y,w,h, points:[v...], labels:[...], min,max, color, stroke, area. Returns {svg, line, area, dots, pts}. */
  api.lineChart = function (p, o) {
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + o.w + ' ' + o.h);
    svg.style.cssText = 'position:absolute;left:' + o.x + 'px;top:' + o.y + 'px;width:' + o.w + 'px;height:' + o.h + 'px;overflow:visible';
    var min = o.min == null ? Math.min.apply(null, o.points) : o.min, max = o.max == null ? Math.max.apply(null, o.points) : o.max;
    var pts = o.points.map(function (v, i) { return [i * o.w / (o.points.length - 1), o.h - (v - min) / (max - min) * o.h]; });
    var d = pts.map(function (q, i) { return (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' ');
    var area = null;
    if (o.area) {
      area = document.createElementNS(SVGNS, 'path');
      area.setAttribute('d', d + ' L' + o.w + ' ' + o.h + ' L0 ' + o.h + ' Z'); area.setAttribute('fill', o.area);
      svg.appendChild(area);
    }
    var line = document.createElementNS(SVGNS, 'path');
    line.setAttribute('d', d); line.setAttribute('fill', 'none'); line.setAttribute('stroke', o.color || '#fff');
    line.setAttribute('stroke-width', o.stroke || 6); line.setAttribute('stroke-linecap', 'round'); line.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(line);
    var dots = pts.map(function (q) {
      var c = document.createElementNS(SVGNS, 'circle');
      c.setAttribute('cx', q[0]); c.setAttribute('cy', q[1]); c.setAttribute('r', (o.stroke || 6) * 1.5); c.setAttribute('fill', o.color || '#fff');
      svg.appendChild(c); return c;
    });
    parent(p).appendChild(svg);
    return { svg: svg, line: line, area: area, dots: dots, pts: pts };
  };

  /** Draw a line chart: the line traces itself, the dots pop as the line reaches them, the area fades in. */
  api.drawLine = function (tl, c, o) {
    o = o || {};
    var at = o.at || 0, dur = o.dur || 1.6, len = c.line.getTotalLength();
    c.line.style.strokeDasharray = len; tl.set(c.line, { strokeDashoffset: len }, 0);
    tl.to(c.line, { strokeDashoffset: 0, duration: dur, ease: o.ease || 'power2.inOut' }, at);
    c.dots.forEach(function (dot, i) {
      tl.set(dot, { scale: 0, transformOrigin: '50% 50%', transformBox: 'fill-box' }, 0);
      tl.to(dot, { scale: 1, duration: 0.35, ease: o.pop || 'back.out(2)' }, at + dur * (i / (c.dots.length - 1)) - 0.1 * (i > 0 ? 1 : 0));
    });
    if (c.area) { tl.set(c.area, { opacity: 0 }, 0); tl.to(c.area, { opacity: 1, duration: dur * 0.6, ease: 'power1.out' }, at + dur * 0.4); }
  };

  /** Progress ring (SVG). o: x,y,size,stroke,color,track. value 0..1 animated with MG.draw(ring.path,{to:value}) */
  api.ring = function (p, o) {
    var svg = document.createElementNS(SVGNS, 'svg'), r = (o.size - o.stroke) / 2, c = o.size / 2;
    svg.setAttribute('viewBox', '0 0 ' + o.size + ' ' + o.size);
    svg.style.cssText = 'position:absolute;left:' + o.x + 'px;top:' + o.y + 'px;width:' + o.size + 'px;height:' + o.size + 'px;transform:rotate(-90deg)';
    function circ(col) {
      var e = document.createElementNS(SVGNS, 'circle');
      e.setAttribute('cx', c); e.setAttribute('cy', c); e.setAttribute('r', r); e.setAttribute('fill', 'none');
      e.setAttribute('stroke', col); e.setAttribute('stroke-width', o.stroke); e.setAttribute('stroke-linecap', 'round'); svg.appendChild(e); return e;
    }
    circ(o.track || 'rgba(255,255,255,.15)');
    var arc = circ(o.color || '#fff'); arc.dataset.len = String(2 * Math.PI * r);
    parent(p).appendChild(svg);
    return { el: svg, path: arc, len: 2 * Math.PI * r };
  };

  /* ───────────────────────── animation ───────────────────────── */
  function list(t) { return Array.isArray(t) ? t : [t]; }

  /**
   * Entrance. o.how: rise | fade | pop | slide-left | slide-right | scale | mask (words/lines/chars rise out of a hard edge)
   * target: element | array | text object (with o.by = 'words'|'lines'|'chars' for text).
   * o: at, dur, ease, dy, dx, stagger. All start states are set at t=0 so seeking in any order is safe.
   */
  api.in = function (tl, target, o) {
    o = o || {};
    var how = o.how || 'rise', at = o.at || 0, dur = o.dur || 0.7, ease = o.ease;
    var items = target;
    if (target && target.el && !(target instanceof Element)) {                // a text object
      var by = o.by || (target.lines.length ? 'lines' : target.chars.length && how !== 'mask' ? 'chars' : 'words');
      items = by === 'lines' ? target.lines : by === 'chars' ? target.chars : target.words;
      if (how === 'mask' && by === 'chars') items = target.chars;
    }
    items = list(items);
    var st = o.stagger == null ? 0 : o.stagger;
    var fromVars, toVars;
    if (how === 'mask') { fromVars = { yPercent: o.yp == null ? 150 : o.yp }; toVars = { yPercent: 0 }; }
    else if (how === 'fade') { fromVars = { autoAlpha: 0 }; toVars = { autoAlpha: 1 }; }
    else if (how === 'pop') { fromVars = { autoAlpha: 0, scale: o.from == null ? 0.6 : o.from }; toVars = { autoAlpha: 1, scale: 1 }; }
    else if (how === 'scale') { fromVars = { autoAlpha: 0, scale: o.from == null ? 1.25 : o.from }; toVars = { autoAlpha: 1, scale: 1 }; }
    else if (how === 'slide-left') { fromVars = { autoAlpha: 0, x: o.dx == null ? 120 : o.dx }; toVars = { autoAlpha: 1, x: 0 }; }
    else if (how === 'slide-right') { fromVars = { autoAlpha: 0, x: o.dx == null ? -120 : o.dx }; toVars = { autoAlpha: 1, x: 0 }; }
    else { fromVars = { autoAlpha: 0, y: o.dy == null ? 50 : o.dy }; toVars = { autoAlpha: 1, y: 0 }; }   // rise
    tl.set(items, fromVars, 0);
    toVars.duration = dur; toVars.ease = ease || (how === 'pop' ? 'back.out(1.7)' : 'power3.out');
    if (st) toVars.stagger = st;
    tl.to(items, toVars, at);
    return at + dur + (st ? st * (items.length - 1) : 0);          // end time, handy for chaining
  };

  /** Exit. o.how: fade | rise | sink | scale | mask. */
  api.out = function (tl, target, o) {
    o = o || {};
    var how = o.how || 'fade', at = o.at || 0, dur = o.dur || 0.45, items = target;
    if (target && target.el && !(target instanceof Element)) items = target.lines.length ? target.lines : target.words;
    items = list(items);
    var vars = { duration: dur, ease: o.ease || 'power2.in' };
    if (how === 'mask') vars.yPercent = -115;
    else if (how === 'rise') { vars.autoAlpha = 0; vars.y = o.dy == null ? -40 : o.dy; }
    else if (how === 'sink') { vars.autoAlpha = 0; vars.y = o.dy == null ? 40 : o.dy; }
    else if (how === 'scale') { vars.autoAlpha = 0; vars.scale = o.to == null ? 0.85 : o.to; }
    else vars.autoAlpha = 0;
    if (o.stagger) vars.stagger = o.stagger;
    tl.to(items, vars, at);
    return at + dur;
  };

  /** Emphasis. o.how: pulse | shake | wiggle. Returns to rest, so it never changes the resting frame. */
  api.emph = function (tl, target, o) {
    o = o || {};
    var how = o.how || 'pulse', at = o.at || 0, items = list(target);
    if (how === 'shake') {
      var a = o.amp || 14;
      tl.to(items, { keyframes: [{ x: -a }, { x: a }, { x: -a * 0.6 }, { x: a * 0.4 }, { x: 0 }], duration: o.dur || 0.4, ease: 'power1.inOut' }, at);
    } else if (how === 'wiggle') {
      tl.to(items, { keyframes: [{ rotation: -4 }, { rotation: 4 }, { rotation: -2 }, { rotation: 0 }], duration: o.dur || 0.5, ease: 'power1.inOut' }, at);
    } else {
      var s = o.scale || 1.08;
      tl.to(items, { keyframes: [{ scale: s, duration: 0.35, ease: 'power2.out' }, { scale: 1, duration: 0.55, ease: 'power2.inOut' }], duration: o.dur || 0.9 }, at);
    }
    return at + (o.dur || 0.9);
  };

  /** Count a number up/down inside a text element. Uses a proxy + onUpdate, which GSAP also fires when seeking. */
  api.counter = function (tl, node, o) {
    var fmt = o.fmt || function (v) { return String(Math.round(v)); }, proxy = { v: o.from == null ? 0 : o.from };
    node.textContent = fmt(proxy.v);
    tl.to(proxy, { v: o.to, duration: o.dur || 1, ease: o.ease || 'power3.out', onUpdate: function () { node.textContent = fmt(proxy.v); } }, o.at || 0);
    return (o.at || 0) + (o.dur || 1);
  };

  /** Typewriter: characters appear one by one at `cps` characters per second (text must be built with split:'chars'). */
  api.typewriter = function (tl, text, o) {
    o = o || {};
    var cps = o.cps || 22, at = o.at || 0;
    tl.set(text.chars, { autoAlpha: 0 }, 0);
    text.chars.forEach(function (c, i) { tl.set(c, { autoAlpha: 1 }, at + i / cps); });
    return at + text.chars.length / cps;
  };

  /** Trace an SVG path (icon, ring, line). o: at, dur, ease, from (0..1), to (0..1 of the length). */
  api.draw = function (tl, target, o) {
    o = o || {};
    var path = target.path || target, len = path.getTotalLength(), to = o.to == null ? 1 : o.to;
    path.style.strokeDasharray = len; tl.set(path, { strokeDashoffset: len }, 0);
    tl.to(path, { strokeDashoffset: len * (1 - to), duration: o.dur || 0.8, ease: o.ease || 'power2.inOut' }, o.at || 0);
    return (o.at || 0) + (o.dur || 0.8);
  };

  /* ───────────────────────── transitions, camera ───────────────────────── */
  /**
   * Move from scene A to scene B at time `at`. type: cut | fade | push-left | push-up | wipe-right | wipe-left | zoom | iris.
   * B must not be shown by anything else. Both scenes end in a defined state (A hidden, B shown, transforms reset).
   */
  api.transition = function (tl, A, B, o) {
    o = o || {};
    var at = o.at || 0, dur = o.dur || 0.6, type = o.type || 'fade', ease = o.ease || 'power3.inOut', a = A && A.el, b = B.el;
    boundaries.push({ t: at, dur: type === 'cut' ? 0 : dur, type: type, carried: CARRY_TYPES.indexOf(type) >= 0 });
    tl.set(b, { autoAlpha: 0 }, 0);
    if (type === 'zoom-through') return zoomThrough(tl, A, B, o, at, dur, o.ease || 'expo.inOut');
    if (type === 'brush') return brushWipe(tl, A, B, o, at, dur);
    if (type === 'cut') {
      tl.set(b, { autoAlpha: 1 }, at); if (a) tl.set(a, { autoAlpha: 0 }, at); return at;
    }
    tl.set(b, { autoAlpha: 1 }, at);
    if (type === 'fade') {
      tl.set(b, { autoAlpha: 0 }, 0); tl.to(b, { autoAlpha: 1, duration: dur, ease: 'power1.inOut' }, at);
      if (a) tl.set(a, { autoAlpha: 0 }, at + dur);
    } else if (type === 'push-left' || type === 'push-up') {
      var ax = type === 'push-left' ? 'x' : 'y', sz = type === 'push-left' ? B.w : B.h;
      var fb = {}, ta = {}; fb[ax] = sz; ta[ax] = -sz * 0.35;
      tl.set(b, fb, 0); var tb = { duration: dur, ease: ease }; tb[ax] = 0; tl.to(b, tb, at);
      if (a) { var tt = { duration: dur, ease: ease }; tt[ax] = -sz * 0.35; tl.to(a, tt, at); tl.set(a, { autoAlpha: 0, x: 0, y: 0 }, at + dur); }
    } else if (type === 'wipe-right' || type === 'wipe-left') {
      var from = type === 'wipe-right' ? 'inset(0 100% 0 0)' : 'inset(0 0 0 100%)';
      tl.set(b, { clipPath: from }, 0); tl.to(b, { clipPath: 'inset(0 0% 0 0%)', duration: dur, ease: ease }, at);
      if (a) tl.set(a, { autoAlpha: 0 }, at + dur);
    } else if (type === 'zoom') {
      tl.set(b, { scale: 0.88, autoAlpha: 0, transformOrigin: '50% 50%' }, 0);
      tl.to(b, { scale: 1, autoAlpha: 1, duration: dur, ease: ease }, at);
      if (a) { tl.to(a, { scale: 1.18, autoAlpha: 0, duration: dur * 0.8, ease: 'power2.in', transformOrigin: '50% 50%' }, at); tl.set(a, { scale: 1 }, at + dur); }
    } else if (type === 'iris') {
      var cx = (o.cx == null ? 50 : o.cx) + '% ' + (o.cy == null ? 50 : o.cy) + '%';
      tl.set(b, { clipPath: 'circle(0% at ' + cx + ')' }, 0); tl.to(b, { clipPath: 'circle(150% at ' + cx + ')', duration: dur, ease: ease }, at);
      if (a) tl.set(a, { autoAlpha: 0 }, at + dur);
    }
    return at + dur;
  };

  /**
   * Camera on S.world as a chain of moves. keys: [{at, dur, scale, x, y, ease}] with `from` on the first key.
   * Finish at scale 1 / x 0 / y 0 if the last frame must be the plain layout. Moves must not overlap.
   */
  api.camera = function (tl, S, keys) {
    var f = keys[0].from || {};
    tl.set(S.world, { scale: f.scale == null ? 1 : f.scale, x: f.x || 0, y: f.y || 0, transformOrigin: '50% 50%' }, 0);
    keys.forEach(function (k) {
      var v = { duration: k.dur, ease: k.ease || 'power2.inOut' };
      if (k.scale != null) v.scale = k.scale; if (k.x != null) v.x = k.x; if (k.y != null) v.y = k.y;
      tl.to(S.world, v, k.at);
    });
  };

  /* ───────────────────────── ambient layer ───────────────────────── */
  /** Film grain overlay (feTurbulence). Re-seeded 12x/s at expose() time so it shimmers without randomness. */
  api.grain = function (S, o) {
    o = o || {};
    var svg = document.createElementNS(SVGNS, 'svg'); svg.setAttribute('class', 'mg-grain');
    svg.setAttribute('width', S.w); svg.setAttribute('height', S.h);
    svg.style.cssText = 'position:absolute;left:0;top:0;mix-blend-mode:' + (o.blend || 'overlay') + ';opacity:' + (o.opacity == null ? 0.18 : o.opacity);
    var f = document.createElementNS(SVGNS, 'filter'); f.setAttribute('id', 'mg-grain-' + (++uid));
    var t = document.createElementNS(SVGNS, 'feTurbulence');
    t.setAttribute('type', 'fractalNoise'); t.setAttribute('baseFrequency', o.freq || 0.8); t.setAttribute('numOctaves', 2); t.setAttribute('seed', 1);
    f.appendChild(t);
    var r = document.createElementNS(SVGNS, 'rect');
    r.setAttribute('width', '100%'); r.setAttribute('height', '100%'); r.setAttribute('filter', 'url(#' + f.id + ')');
    svg.appendChild(f); svg.appendChild(r); S.overlay.appendChild(svg);
    if (o.animate !== false) finalizers.push(function (tl) {
      var proxy = { v: 0 }, d = tl.duration();
      t.setAttribute('seed', 1);
      tl.to(proxy, { v: d * 12, duration: d, ease: 'none', onUpdate: function () { t.setAttribute('seed', (Math.floor(proxy.v) % 40) + 1); } }, 0);
    });
    return svg;
  };

  api.vignette = function (S, o) {
    o = o || {};
    return api.box(S.overlay, { x: 0, y: 0, w: S.w, h: S.h, css: 'background:radial-gradient(ellipse at center,rgba(0,0,0,0) 55%,rgba(0,0,0,' + (o.strength || 0.45) + ') 100%)' });
  };

  /** Slow background gradient drift (ambient layer): moves a oversized gradient. Ends where it started only if `loop` is set. */
  api.bgDrift = function (tl, S, o) {
    o = o || {};
    var size = o.size || 140;
    S.frame.style.backgroundSize = size + '% ' + size + '%';
    tl.fromTo(S.frame, { backgroundPosition: '0% 0%' }, { backgroundPosition: (o.to || '100% 100%'), duration: o.dur || 8, ease: 'sine.inOut' }, o.at || 0);
  };

  /* ───────────────────────── continuity: beats that carry instead of replace ───────────────────────── */
  /*
   * A beat that replaces the previous one reads as a slide change, however good the rhythm. These moves make something
   * on screen survive the boundary and become the next beat. Carried elements live OUTSIDE the scenes they cross
   * (put them on S.world or on a shared layer), otherwise hiding the old scene hides them too.
   */

  /** Rect of an element in design px (stage coordinates), measured at build time. */
  api.rectOf = function (node) {
    var st = STAGE.frame.getBoundingClientRect(), r = node.getBoundingClientRect(), k = STAGE.w / st.width;
    return { x: (r.left - st.left) * k, y: (r.top - st.top) * k, w: r.width * k, h: r.height * k };
  };

  /**
   * Container morph: a box (card, chip, frame) grows/moves into a new rect and becomes the next beat's container.
   * Animates left/top/width/height (not scale) so borders, radius and text inside stay crisp.
   * to: {x,y,w,h,radius?,bg?} or an element (its rect is measured). o: at, dur, ease (default spring-ish expo).
   * Registers a carried boundary at `at` unless o.mark === false.
   */
  api.morph = function (tl, node, to, o) {
    o = o || {};
    var r = to instanceof Element ? api.rectOf(to) : to, at = o.at || 0, dur = o.dur || 0.9;
    var v = { left: r.x, top: r.y, width: r.w, height: r.h, duration: dur, ease: o.ease || 'expo.inOut' };
    if (r.radius != null) v.borderRadius = r.radius;
    if (r.bg) v.backgroundColor = r.bg;
    tl.to(node, v, at);
    if (o.mark !== false) boundaries.push({ t: at, dur: dur, type: 'morph', carried: true });
    return at + dur;
  };

  /**
   * Carry: move an element from where it is to a target rect/point with a FLIP transform (x, y, scale), e.g. the word
   * that becomes the title of the next beat, the dot that lands on the "i". to: {x,y} (top-left, design px) [+ w for
   * scale] or an element. o: at, dur, ease, arc (px of sideways bow on the path; 0 = straight).
   */
  api.carry = function (tl, node, to, o) {
    o = o || {};
    var from = api.rectOf(node), r = to instanceof Element ? api.rectOf(to) : to, at = o.at || 0, dur = o.dur || 0.8;
    var k = r.w ? r.w / from.w : 1, dx = r.x - from.x, dy = r.y - from.y;
    gsap.set(node, { transformOrigin: '0 0' });
    if (o.arc) {
      var px0 = { p: 0 }, ease = gsap.parseEase(o.ease || 'power3.inOut'), nx = -dy, ny = dx, nl = Math.hypot(nx, ny) || 1;
      tl.to(px0, { p: 1, duration: dur, ease: 'none', onUpdate: function () {
        var e = ease(px0.p), bow = Math.sin(Math.PI * e) * o.arc;
        gsap.set(node, { x: dx * e + nx / nl * bow, y: dy * e + ny / nl * bow, scale: 1 + (k - 1) * e });
      } }, at);
    } else tl.to(node, { x: dx, y: dy, scale: k, duration: dur, ease: o.ease || 'power3.inOut' }, at);
    if (o.mark !== false) boundaries.push({ t: at, dur: dur, type: 'carry', carried: true });
    return at + dur;
  };

  /* zoom-through: the camera dives into a window of A (o.rect {x,y,w,h} or o.el) until B, which lives inside that window, fills the frame. */
  function zoomThrough(tl, A, B, o, at, dur, ease) {
    var W = B.w, H = B.h, r = o.el ? api.rectOf(o.el) : o.rect, a = A && A.el, b = B.el;
    if (!r) throw new Error("transition 'zoom-through' needs o.rect {x,y,w,h} or o.el (the window to dive into)");
    // A and B must scale by the same factor at every instant (B/s0 == A), or the window and its content drift apart
    var cx = r.x + r.w / 2, cy = r.y + r.h / 2, s0 = Math.max(r.w / W, r.h / H), k = 1 / s0;
    var hw = r.w / (2 * s0), hh = r.h / (2 * s0), rad = (o.radius || 0) / s0;
    var clip0 = 'inset(' + (H / 2 - hh) + 'px ' + (W / 2 - hw) + 'px ' + (H / 2 - hh) + 'px ' + (W / 2 - hw) + 'px round ' + rad + 'px)';
    tl.set(b, { autoAlpha: 0, scale: s0, x: cx - W / 2, y: cy - H / 2, transformOrigin: '50% 50%', clipPath: clip0 }, at);
    tl.to(b, { autoAlpha: 1, duration: dur * 0.3, ease: 'power1.out' }, at);          // the window's content dissolves in as the dive starts
    tl.to(b, { scale: 1, x: 0, y: 0, duration: dur, ease: ease }, at);
    // the window stays the window while the camera dives; it only opens to full frame at the end (aspect mismatch)
    tl.to(b, { clipPath: 'inset(0px 0px 0px 0px round 0px)', duration: dur * 0.35, ease: 'power2.inOut' }, at + dur * 0.65);
    if (a) {
      tl.set(a, { transformOrigin: cx + 'px ' + cy + 'px' }, at);
      tl.to(a, { scale: k, x: W / 2 - cx, y: H / 2 - cy, duration: dur, ease: ease }, at);
      tl.set(a, { autoAlpha: 0, scale: 1, x: 0, y: 0 }, at + dur);
    }
    return at + dur;
  }

  /* brush: fat painted strokes cover the frame (first half), the scenes swap under full cover, the strokes drag off (second half). */
  function brushWipe(tl, A, B, o, at, dur) {
    var W = B.w, H = B.h, n = o.strokes || 6, cols = o.colors || [o.color || '#f2ead8'], rnd = api.rng(o.seed || 7);
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('width', W); svg.setAttribute('height', H); svg.setAttribute('class', 'mg-wipe');
    svg.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    var f = document.createElementNS(SVGNS, 'filter'), fid = 'mg-brush-' + (++uid);
    f.setAttribute('id', fid); f.setAttribute('x', '-10%'); f.setAttribute('y', '-10%'); f.setAttribute('width', '120%'); f.setAttribute('height', '120%');
    f.innerHTML = '<feTurbulence type="fractalNoise" baseFrequency="0.035 0.4" numOctaves="3" seed="' + (o.seed || 7) + '"/>' +
      '<feDisplacementMap in="SourceGraphic" scale="' + (o.rough == null ? 46 : o.rough) + '" xChannelSelector="R" yChannelSelector="G"/>';
    svg.appendChild(f);
    var g = document.createElementNS(SVGNS, 'g'); g.setAttribute('filter', 'url(#' + fid + ')'); svg.appendChild(g);
    var band = H / n, half = dur / 2, paths = [];
    for (var i = 0; i < n; i++) {
      var y = band * (i + 0.5), tilt = (rnd() - 0.5) * band * 0.5, p = document.createElementNS(SVGNS, 'path');
      var x0 = -0.15 * W, x1 = 1.15 * W, dir = i % 2 ? -1 : 1;
      p.setAttribute('d', dir > 0 ? 'M' + x0 + ' ' + (y - tilt) + ' L' + x1 + ' ' + (y + tilt) : 'M' + x1 + ' ' + (y + tilt) + ' L' + x0 + ' ' + (y - tilt));
      p.setAttribute('fill', 'none'); p.setAttribute('stroke', cols[i % cols.length]); p.setAttribute('stroke-linecap', 'round');
      p.setAttribute('stroke-width', band * 1.7);
      g.appendChild(p); paths.push(p);
    }
    STAGE.overlay.insertBefore(svg, STAGE.overlay.firstChild);       // under grain / vignette
    var st = half * 0.35 / n;
    paths.forEach(function (p, i) {
      var L = 1.3 * W + 10; p.style.strokeDasharray = L + ' ' + (L * 3);
      tl.set(p, { strokeDashoffset: L }, 0);
      tl.to(p, { strokeDashoffset: 0, duration: half * 0.65, ease: 'power2.in' }, at + i * st);
      tl.to(p, { strokeDashoffset: -L, duration: half * 0.65, ease: 'power2.out' }, at + half + i * st);
    });
    tl.set(B.el, { autoAlpha: 1 }, at + half);
    if (A) tl.set(A.el, { autoAlpha: 0 }, at + half);
    return at + dur;
  }

  /* ───────────────────────── measured curves ───────────────────────── */
  /**
   * Spring ease for GSAP (`ease: MG.spring({bounce: .25})`): fast start, overshoot of `bounce` (0..0.6) on the first
   * swing, `wobbles` half-swings, settles exactly on 1. Pure function: same curve every render.
   * Pick curves by how fast they reach 80 % of the move (t80): expo.out ≈ .23 (snap), power3.out ≈ .41, spring .2–.3
   * (lands), sine.inOut ≈ .70 (drift). One soft S-curve on every move makes every move look the same.
   */
  api.spring = function (o) {
    o = o || {};
    var b = Math.min(0.6, Math.max(0.02, o.bounce == null ? 0.25 : o.bounce)), n = Math.max(1, o.wobbles || 2), d = -n * Math.log(b);
    return function (p) {
      if (p <= 0) return 0; if (p >= 1) return 1;
      return 1 - Math.exp(-d * p) * Math.cos(n * Math.PI * p) * (1 - Math.pow(p, 4));
    };
  };

  /* ───────────────────────── operated camera ───────────────────────── */
  /**
   * An operator's hand on top of MG.camera: a slow two-sine float (zero inside `holds`), plus a decaying kick on each
   * landing time in `hits`. Uses xPercent/yPercent/rotation on S.world, so it composes with MG.camera's x/y/scale.
   * o: amp (design px of float, 5), freq (Hz, 0.17), rot (deg, 0.25), holds [[t0,t1]...], hits [t...], hitAmp (14), seed
   * Call it once, after the camera keys. Keep amp small: the hand should be felt, not seen.
   */
  api.operator = function (tl, S, o) {
    o = o || {};
    var amp = o.amp == null ? 5 : o.amp, fq = o.freq || 0.17, rot = o.rot == null ? 0.25 : o.rot, holds = o.holds || [], hits = o.hits || [];
    var ha = o.hitAmp == null ? 14 : o.hitAmp, R = api.rng(o.seed || 3), ph = [R() * 6.28, R() * 6.28, R() * 6.28, R() * 6.28];
    var pxW = 100 / S.w, pxH = 100 / S.h;
    function gate(t) {                         // 0 inside a hold (with 0.4 s soft edges), 1 elsewhere
      var g = 1;
      holds.forEach(function (h) { var e = 0.4, k = t < h[0] - e || t > h[1] + e ? 1 : t < h[0] ? (h[0] - t) / e : t > h[1] ? (t - h[1]) / e : 0; g = Math.min(g, k); });
      return g * g * (3 - 2 * g);
    }
    function at(t) {
      var g = gate(t), x = amp * g * (Math.sin(6.283 * fq * t + ph[0]) + 0.5 * Math.sin(6.283 * fq * 2.13 * t + ph[1]));
      var y = amp * g * (Math.sin(6.283 * fq * 0.83 * t + ph[2]) + 0.5 * Math.sin(6.283 * fq * 1.71 * t + ph[3]));
      var r = rot * g * Math.sin(6.283 * fq * 0.61 * t + ph[1]);
      hits.forEach(function (h, i) {
        var u = t - h; if (u < 0 || u > 0.6) return;
        var e = Math.exp(-u * 9) * ha, w = 6.283 * 11 * u;
        x += e * Math.sin(w + i); y += e * 0.7 * Math.cos(w * 1.3 + i);
      });
      return { xPercent: x * pxW, yPercent: y * pxH, rotation: r };
    }
    gsap.set(S.world, at(0));
    finalizers.push(function (tl2) {
      var proxy = { t: 0 }, D = tl2.duration();
      tl2.to(proxy, { t: D, duration: D, ease: 'none', onUpdate: function () { gsap.set(S.world, at(proxy.t)); } }, 0);
    });
  };

  /** Mark an element that must never leave the frame (validate.py fails any sampled frame where it does). mode 'whole' = no part may be cut. */
  api.inFrame = function (node, mode) { node.dataset.inFrame = mode || 'center'; return node; };

  /* ───────────────────────── hand-painted look ───────────────────────── */
  /**
   * Boiling linework: each drawing wobbles slightly and is redrawn `fps` times a second (12 = "on twos"), like
   * hand-drawn animation. target: element(s) (SVG strokes, shapes, text). o: amp (px, 2.2), freq (0.03), fps (12),
   * seed (give each element its own, or neighbours boil in unison). Holds still between steps, so it is deterministic.
   */
  api.boil = function (target, o) {
    o = o || {};
    var amp = o.amp == null ? 2.2 : o.amp, fps = o.fps || 12, seed0 = o.seed || (++uid * 13);
    var svg = document.createElementNS(SVGNS, 'svg'); svg.setAttribute('width', 0); svg.setAttribute('height', 0);
    svg.style.cssText = 'position:absolute;width:0;height:0';
    var f = document.createElementNS(SVGNS, 'filter'), id = 'mg-boil-' + (++uid);
    f.setAttribute('id', id); f.setAttribute('x', '-5%'); f.setAttribute('y', '-5%'); f.setAttribute('width', '110%'); f.setAttribute('height', '110%');
    var t = document.createElementNS(SVGNS, 'feTurbulence');
    t.setAttribute('type', 'fractalNoise'); t.setAttribute('baseFrequency', o.freq || 0.03); t.setAttribute('numOctaves', 2); t.setAttribute('seed', seed0);
    var d = document.createElementNS(SVGNS, 'feDisplacementMap');
    d.setAttribute('in', 'SourceGraphic'); d.setAttribute('scale', amp * 2); d.setAttribute('xChannelSelector', 'R'); d.setAttribute('yChannelSelector', 'G');
    f.appendChild(t); f.appendChild(d); svg.appendChild(f); STAGE.frame.appendChild(svg);
    list(target).forEach(function (n) { n.style.filter = 'url(#' + id + ')'; });
    finalizers.push(function (tl) {
      var proxy = { v: 0 }, D = tl.duration();
      tl.to(proxy, { v: D * fps, duration: D, ease: 'none', onUpdate: function () { t.setAttribute('seed', seed0 + (Math.floor(proxy.v) % 3)); } }, 0);
    });
    return f;
  };

  /** Paper: warm fibrous texture over the whole frame (multiply). o: color ('#efe6d2'), opacity (0.5), freq (0.9) */
  api.paper = function (S, o) {
    o = o || {};
    // an SVG *image* is rasterised once and cached; the same filter inline is recomputed every frame (10x slower captures)
    var src = '<svg xmlns="http://www.w3.org/2000/svg" width="' + S.w + '" height="' + S.h + '"><filter id="p">' +
      '<feTurbulence type="fractalNoise" baseFrequency="' + (o.freq || 0.9) + '" numOctaves="4" seed="5"/>' +
      '<feDiffuseLighting lighting-color="' + (o.color || '#efe6d2') + '" surfaceScale="1.6"><feDistantLight azimuth="45" elevation="62"/></feDiffuseLighting></filter>' +
      '<rect width="100%" height="100%" filter="url(#p)"/></svg>';
    var n = el('div', 'position:absolute;left:0;top:0;width:' + S.w + 'px;height:' + S.h + 'px;mix-blend-mode:multiply;opacity:' +
      (o.opacity == null ? 0.5 : o.opacity) + ';background:url("data:image/svg+xml;charset=utf-8,' + encodeURIComponent(src).replace(/'/g, '%27') + '")', 'mg-paper');
    S.overlay.insertBefore(n, S.overlay.firstChild);
    return n;
  };

  /** Hold every drawing for 1/fps s (12 = animation "on twos"): the whole film snaps like hand-drawn frames. Call before expose. 0 turns it off. */
  api.stepped = function (fps) { stepFps = fps || 0; };

  /* ───────────────────────── audio cues & expose ───────────────────────── */
  /** Register a sound cue at time t. names: hit | thud | whoosh | pop | tick | step | riser | sub | shimmer. Rendered by make_sfx.py. */
  api.cue = function (name, t, o) { cues.push(Object.assign({ name: name, t: t }, o || {})); };


  /* ───────────────────────── 3D layer (Three.js) ───────────────────────── */
  var threes = [];
  /** Seeded PRNG (mulberry32): the only allowed source of "randomness". */
  api.rng = function (seed) {
    var a = seed >>> 0;
    return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  };
  /**
   * A Three.js canvas inside a scene. Needs vendor/three.min.js (window.THREE). The picture is redrawn after every
   * timeline seek from the *state of the objects at that time* (GSAP tweens on position/rotation/material props),
   * so any frame can be requested in any order. Never start an animation loop.
   *   o: x,y,w,h (design px, default whole scene), fov (35), near, far, pixelRatio (1), alpha (true), exposure (1)
   * returns t3 { el, scene, camera, renderer, look (Vector3 the camera faces; tween it), pre(fn(t)), studio(), ground(), textTexture() }
   * Animate with ordinary tweens:  tl.to(t3.camera.position, {z: 4, duration: 2}, 0);  tl.to(mesh.rotation, {y: Math.PI, duration: 3}, 0);
   */
  api.three = function (p, o) {
    var TH = window.THREE; if (!TH) throw new Error('MG.three needs vendor/three.min.js');
    o = o || {};
    var W = o.w || p.w, H = o.h || p.h;
    var cv = el('canvas', 'position:absolute;left:' + px(o.x || 0) + ';top:' + px(o.y || 0) + ';width:' + W + 'px;height:' + H + 'px' + (o.z != null ? ';z-index:' + o.z : ''), 'mg-three');
    parent(p).appendChild(cv);
    var renderer = new TH.WebGLRenderer({ canvas: cv, antialias: true, alpha: o.alpha !== false, preserveDrawingBuffer: true });
    renderer.setPixelRatio(o.pixelRatio || 1); renderer.setSize(W, H, false);
    renderer.toneMapping = TH.ACESFilmicToneMapping; renderer.toneMappingExposure = o.exposure || 1;
    if (o.alpha === false && o.bg) renderer.setClearColor(o.bg, 1); else renderer.setClearColor(0x000000, 0);
    var scene = new TH.Scene(), camera = new TH.PerspectiveCamera(o.fov || 35, W / H, o.near || 0.1, o.far || 200);
    camera.position.set(0, 0, 8);
    if (o.shiftY) camera.setViewOffset(W, H, 0, o.shiftY * H, W, H);   // shifts the picture up by shiftY*H, leaving the bottom free for captions
    var t3 = { el: cv, scene: scene, camera: camera, renderer: renderer, look: new TH.Vector3(0, 0, 0), _pre: [], _post: [] };
    t3.pre = function (fn) { t3._pre.push(fn); return t3; };
    /** Soft studio: warm key (casts shadow), cool rim, dim room reflections. c: env (0.5), key, rim */
    t3.studio = function (c) {
      c = c || {};
      renderer.shadowMap.enabled = true; renderer.shadowMap.type = TH.PCFSoftShadowMap;
      var pm = new TH.PMREMGenerator(renderer);
      scene.environment = pm.fromScene(new TH.RoomEnvironment(), 0.04).texture;
      if ('environmentIntensity' in scene) scene.environmentIntensity = c.env == null ? 0.5 : c.env;
      var key = new TH.DirectionalLight(0xfff0e0, c.key == null ? 2.4 : c.key); key.position.set(3, 5, 4); key.castShadow = true;
      key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 6; key.shadow.bias = -0.0004;
      var sc = key.shadow.camera; sc.left = -6; sc.right = 6; sc.top = 6; sc.bottom = -6; sc.near = 0.5; sc.far = 20;
      var rim = new TH.DirectionalLight(0x9ec5ff, c.rim == null ? 1.8 : c.rim); rim.position.set(-4, 2, -3);
      scene.add(key, rim); t3.key = key; t3.rim = rim; return t3;
    };
    /** Transparent plane that only shows the shadow of objects above it (a contact shadow). */
    t3.ground = function (y, opacity) {
      var g = new TH.Mesh(new TH.PlaneGeometry(40, 40), new TH.ShadowMaterial({ opacity: opacity == null ? 0.35 : opacity }));
      g.rotation.x = -Math.PI / 2; g.position.y = y || 0; g.receiveShadow = true; g.userData.mgHelper = true; scene.add(g); return g;
    };
    /**
     * Calibrated material presets, so a scene never hand-tunes glass or metal again. t3.mat('metal', {color: 0xdadfe6})
     *   k: 'matte' (paper, clay) | 'soft' (sheen cloth) | 'metal' (brushed) | 'chrome' (mirror) | 'ceramic' (clearcoat)
     *      | 'glass' (transparent + clearcoat, see-through) | 'emissive' (the object is a light source)
     *   o: color, roughness, metalness, opacity, emissive, map, flat, side...  (any wins over the preset)
     *   'metal' y 'chrome' solo se ven si hay t3.env(): sin entorno no tienen qué reflejar y salen grises muertos.
     */
    t3.mat = function (k, o) {
      o = o || {};
      var phys = (k === 'glass' || k === 'ceramic' || k === 'soft' || k === 'iridescent');
      var C = phys ? TH.MeshPhysicalMaterial : TH.MeshStandardMaterial;
      var c = o.color == null ? 0xd8dde5 : o.color, P;
      if (k === 'matte') P = { roughness: 0.88, metalness: 0.0 };
      else if (k === 'soft') P = { roughness: 0.62, metalness: 0.0, sheen: 1.0, sheenRoughness: 0.7, sheenColor: c };
      else if (k === 'metal') P = { roughness: 0.26, metalness: 1.0 };
      else if (k === 'chrome') P = { roughness: 0.03, metalness: 1.0 };
      else if (k === 'ceramic') P = { roughness: 0.34, metalness: 0.0, clearcoat: 1.0, clearcoatRoughness: 0.12 };
      else if (k === 'iridescent') P = { roughness: 0.18, metalness: 0.2, iridescence: 1.0, iridescenceIOR: 1.3, clearcoat: 1.0 };
      else if (k === 'glass') P = { roughness: 0.05, metalness: 0.0, transparent: true, opacity: 0.42, clearcoat: 1.0, clearcoatRoughness: 0.05, envMapIntensity: 1.5, depthWrite: false };
      else if (k === 'emissive') P = { roughness: 0.5, metalness: 0.0, emissive: c, emissiveIntensity: 1.6 };
      else throw new Error('MG t3.mat: unknown preset "' + k + '" (matte|soft|metal|chrome|ceramic|iridescent|glass|emissive)');
      var props = { color: c };
      for (var a in P) props[a] = P[a];
      for (var b in o) if (b !== 'color') props[b] = o[b];
      return new C(props);
    };
    /**
     * Brand-coloured environment: a vertical gradient sky with an optional bright patch, baked to PMREM, so reflections
     * carry the palette instead of a grey room. c: array [top, mid, bottom] or {top, mid, bottom, glow:{color,u,v,r}, intensity, bg}
     */
    t3.env = function (c) {
      c = c || {};
      var cols = Array.isArray(c) ? c : (c.colors || [c.top || '#2a3348', c.mid || '#101722', c.bottom || '#05070a']);
      var w = 512, h = 256, k = document.createElement('canvas'); k.width = w; k.height = h;
      var g = k.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, cols[0]); gr.addColorStop(cols.length > 2 ? 0.5 : 0.45, cols[1] || cols[0]); gr.addColorStop(1, cols[cols.length - 1]);
      g.fillStyle = gr; g.fillRect(0, 0, w, h);
      if (c.glow) {                      // the only strong specular hit the objects will see
        var gu = (c.glow.u == null ? 0.72 : c.glow.u) * w, gv = (c.glow.v == null ? 0.28 : c.glow.v) * h, gra = (c.glow.r || 0.3) * w;
        var rg = g.createRadialGradient(gu, gv, 0, gu, gv, gra);
        rg.addColorStop(0, c.glow.color || '#ffffff'); rg.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = rg; g.fillRect(0, 0, w, h);
      }
      var tx = new TH.CanvasTexture(k); tx.mapping = TH.EquirectangularReflectionMapping; tx.colorSpace = TH.SRGBColorSpace;
      var pm = new TH.PMREMGenerator(renderer); pm.compileEquirectangularShader();
      var rt = pm.fromEquirectangular(tx);
      if (t3._envRT) t3._envRT.dispose();
      t3._envRT = rt; scene.environment = rt.texture;
      if ('environmentIntensity' in scene) scene.environmentIntensity = c.intensity == null ? 0.85 : c.intensity;
      if (c.bg) scene.background = rt.texture;
      tx.dispose(); pm.dispose(); return t3;
    };
    /**
     * Camera as a pure function of timeline time (no tweens needed): dolly/lerp from -> to between start and end seconds,
     * optional orbit (radians) around the look point, optional fov->fovEnd. Composes with ordinary tweens: last writer wins.
     *   o: from [x,y,z] (default [0,0,8]), to, look [x,y,z], start (0), end (start+4), orbit (0), fov, fovEnd, ease('inOut'|'out'|'linear')
     */
    t3.rig = function (o) {
      o = o || {};
      var from = o.from || [0, 0, 8], to = o.to || from, L = o.look || [0, 0, 0];
      var s = o.start || 0, e = o.end == null ? s + 4 : o.end, ea = o.ease || 'inOut';
      var f0 = o.fov, f1 = o.fovEnd == null ? o.fov : o.fovEnd;
      t3.pre(function (t) {
        var u = e > s ? Math.min(1, Math.max(0, (t - s) / (e - s))) : 1;
        var v = ea === 'linear' ? u : ea === 'out' ? 1 - (1 - u) * (1 - u) : u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
        var x = from[0] + (to[0] - from[0]) * v, y = from[1] + (to[1] - from[1]) * v, z = from[2] + (to[2] - from[2]) * v;
        if (o.orbit) {                     // swing around the look point on Y, radius preserved
          var dx = x - L[0], dz = z - L[2], a = o.orbit * v, ca = Math.cos(a), sa = Math.sin(a);
          x = L[0] + dx * ca - dz * sa; z = L[2] + dx * sa + dz * ca;
        }
        t3.camera.position.set(x, y, z); t3.look.set(L[0], L[1], L[2]);
        if (f0 != null) { var f = f0 + (f1 - f0) * v; if (Math.abs(t3.camera.fov - f) > 1e-4) { t3.camera.fov = f; t3.camera.updateProjectionMatrix(); } }
      });
      return t3;
    };
    /** Isometric look: swaps in an orthographic camera from the current pose. scale = world units visible vertically. */
    t3.ortho = function (scale) {
      scale = scale == null ? 7 : scale;
      var cam = new TH.OrthographicCamera(-scale * W / H / 2, scale * W / H / 2, scale / 2, -scale / 2, 0.1, 200);
      cam.position.copy(t3.camera.position);
      if (o.shiftY) cam.setViewOffset(W, H, 0, o.shiftY * H, W, H);
      t3.camera = cam; return t3;
    };
    /**
     * Bigger, tighter shadow map than the studio default (1024 mapped over a wide frustum). Call after t3.studio().
     *   o: res (2048), radius (8, softness), samples (16), bounds (4.5 = half-size of the frustum in world units), bias
     */
    t3.softShadow = function (o) {
      o = o || {}; if (!t3.key) throw new Error('MG t3.softShadow needs t3.studio() first');
      var sh = t3.key.shadow, res = o.res || 2048, b = o.bounds || 4.5;
      sh.mapSize.set(res, res); if (sh.map) { sh.map.dispose(); sh.map = null; }
      sh.radius = o.radius == null ? 8 : o.radius; sh.bias = o.bias == null ? -0.0003 : o.bias;
      if ('blurSamples' in sh) sh.blurSamples = o.samples || 16;
      var c = sh.camera; c.left = -b; c.right = b; c.top = b; c.bottom = -b; c.updateProjectionMatrix();
      return t3;
    };
    /**
     * Real glow with no extra WebGL pass: a second canvas over the WebGL one, carrying the same pixels isolated above
     * a highlight threshold (SVG feComponentTransfer), blurred (CSS) and summed with mix-blend-mode:screen.
     * Costs one drawImage + one compositor filter per frame. o: amount(.55), blur(10), threshold(.72), gain(1), saturate(1.15), x, y, z
     * threshold <= 0 disables the isolation (cheaper, but then everything is lifted, not just the highlights).
     */
    t3.bloom = function (o) {
      o = o || {};
      var blur = o.blur == null ? 10 : o.blur, th = o.threshold == null ? 0.72 : o.threshold, filt = '';
      if (th > 0) {                       // t(x) = slope*x + intercept, clipped: 0 below th, ramps to 1 at x = 1
        var k = 1 / Math.max(0.02, 1 - th), b = -th * k, sid = 'mg-bloomf' + (t3._bloomN = (t3._bloomN || 0) + 1);
        var NS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(NS, 'svg');
        var fl = document.createElementNS(NS, 'filter'), ct = document.createElementNS(NS, 'feComponentTransfer');
        svg.setAttribute('style', 'position:absolute;width:0;height:0;overflow:hidden');
        fl.setAttribute('id', sid); fl.setAttribute('color-interpolation-filters', 'sRGB');
        ['R', 'G', 'B'].forEach(function (ch) {        // per channel: identity only above the threshold
          var f = document.createElementNS(NS, 'feFunc' + ch);
          f.setAttribute('type', 'linear'); f.setAttribute('slope', k.toFixed(4)); f.setAttribute('intercept', b.toFixed(4));
          ct.appendChild(f);
        });
        fl.appendChild(ct); svg.appendChild(fl); document.body.appendChild(svg);   // fuera del escenario: es inerte y no debe entrar en el QA de entidades
        filt = 'url(#' + sid + ') ';
      }
      filt += 'blur(' + blur + 'px) saturate(' + (o.saturate == null ? 1.15 : o.saturate) + ')' + (o.gain && o.gain !== 1 ? ' brightness(' + o.gain + ')' : '');
      var res = o.res == null ? 0.5 : o.res;         // medio resolución: el blur se come la diferencia y el filtro cuesta 4x menos
      var st = 'position:absolute;left:' + px(o.x || 0) + ';top:' + px(o.y || 0) + ';width:' + W + 'px;height:' + H + 'px;' +
               'mix-blend-mode:screen;filter:' + filt + ';opacity:' + (o.amount == null ? 0.55 : o.amount) + ';pointer-events:none;' +
               (o.z == null ? '' : 'z-index:' + o.z);
      var c2 = el('canvas', st, 'mg-bloom'); c2.width = Math.max(16, Math.round(cv.width * res)); c2.height = Math.max(16, Math.round(cv.height * res));
      parent(p).insertBefore(c2, cv.nextSibling);          // right after the WebGL canvas: later DOM (text, anchors) stays on top
      var g2 = c2.getContext('2d');
      t3._post.push(function () { g2.clearRect(0, 0, c2.width, c2.height); g2.drawImage(cv, 0, 0, c2.width, c2.height); });   // scaled: c2 is res x the WebGL size
      t3.bloomEl = c2; return t3;
    };
    /** Fake ambient occlusion: a soft dark radial sprite lying on the ground (no light, no extra pass). radius in world units. */
    t3.ao = function (radius, opacity) {
      radius = radius == null ? 1.4 : radius;
      var k = document.createElement('canvas'); k.width = k.height = 128;
      var g = k.getContext('2d'), rg = g.createRadialGradient(64, 64, 0, 64, 64, 64);
      rg.addColorStop(0, 'rgba(0,0,0,1)'); rg.addColorStop(0.55, 'rgba(0,0,0,0.5)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = rg; g.fillRect(0, 0, 128, 128);
      var tx = new TH.CanvasTexture(k);
      var m = new TH.Mesh(new TH.PlaneGeometry(radius * 2, radius * 2),
        new TH.MeshBasicMaterial({ map: tx, transparent: true, opacity: opacity == null ? 0.5 : opacity, depthWrite: false }));
      m.rotation.x = -Math.PI / 2; m.position.y = 0.002; m.renderOrder = 1; m.userData.mgHelper = true; scene.add(m); return m;
    };
    /** Texture from text drawn on a 2D canvas (fonts must already be loaded: MG.ready does that). */
    t3.textTexture = function (text, c) {
      c = c || {}; var w = c.w || 1024, h = c.h || 512, k = document.createElement('canvas'); k.width = w; k.height = h;
      var g = k.getContext('2d'); if (c.bg) { g.fillStyle = c.bg; g.fillRect(0, 0, w, h); }
      var fam = (c.font || 'sans-serif').replace(/var\((--[\w-]+)\)/g, function (m, v) { return getComputedStyle(document.documentElement).getPropertyValue(v) || 'sans-serif'; });   // canvas cannot read CSS variables
      g.fillStyle = c.color || '#fff'; g.font = (c.weight || 700) + ' ' + (c.size || 160) + 'px ' + fam;
      g.textAlign = 'center'; g.textBaseline = 'middle';
      String(text).split('\n').forEach(function (ln, i, a) { g.fillText(ln, w / 2, h / 2 + (i - (a.length - 1) / 2) * (c.size || 160) * 1.1); });
      var tx = new TH.CanvasTexture(k); tx.colorSpace = TH.SRGBColorSpace; tx.anisotropy = 8; return tx;
    };
    /** A DOM anchor that follows a 3D object: returns a 0x0 div positioned from the projected world point (plus offset [x,y,z]
     *  in world units and dx,dy in design px). Put MG.text inside it with x:0 (align center) or x:0 (align left). Pure function of time. */
    t3.anchor = function (obj, a) {
      a = a || {};
      var d = el('div', 'position:absolute;left:0;top:0;width:0;height:0;z-index:' + (a.z == null ? 6 : a.z), 'mg-anchor');
      parent(p).appendChild(d);
      var v = new TH.Vector3(), off = a.offset || [0, 0, 0];
      t3.pre(function () {
        obj.updateWorldMatrix(true, false); v.setFromMatrixPosition(obj.matrixWorld); v.x += off[0]; v.y += off[1]; v.z += off[2];
        v.project(t3.camera);
        d.style.transform = 'translate(' + ((v.x * 0.5 + 0.5) * W + (a.dx || 0)).toFixed(2) + 'px,' + ((-v.y * 0.5 + 0.5) * H + (a.dy || 0)).toFixed(2) + 'px)';
      });
      return d;
    };
    t3.render = function (t) {
      t3.camera.lookAt(t3.look); t3.camera.updateMatrixWorld();   // camera pose first: anchors and pre() hooks project with THIS frame's camera
      t3._pre.forEach(function (f) { f(t); });
      t3.camera.lookAt(t3.look); t3.camera.updateMatrixWorld();   // a rig() inside pre() may have moved the camera
      renderer.render(scene, t3.camera);
      t3._post.forEach(function (f) { f(t); });                   // DOM passes (bloom): after the pixels exist
    };
    /** Para validate.py: rectángulo en pantalla (px de diseño) de cada malla visible, proyectando sus vértices reales (no la caja,
     *  que en un objeto rotado es más grande que la silueta). Se saltan el suelo/ao (userData.mgHelper) y lo marcado userData.crop. */
    t3.boxes = function () {
      var out = [], v = new TH.Vector3(), cx = o.x || 0, cy = o.y || 0;
      t3.camera.updateMatrixWorld(); scene.updateMatrixWorld(true);
      scene.traverseVisible(function (m) {
        if (!m.isMesh || m.userData.mgHelper || m.userData.crop || !m.geometry || !m.geometry.attributes.position) return;
        var p = m.geometry.attributes.position, n = p.count, stride = Math.max(1, Math.floor(n / 3000));
        var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, behind = false, clip = (m.material && m.material.clippingPlanes) || [];
        for (var i = 0; i < n; i += stride) {
          v.fromBufferAttribute(p, i).applyMatrix4(m.matrixWorld);
          if (clip.some(function (pl) { return pl.distanceToPoint(v) < 0; })) continue;   // lo que un plano de recorte oculta no se ve
          v.project(t3.camera);
          if (v.z > 1 || v.z < -1) { behind = true; continue; }
          var sx = cx + (v.x * 0.5 + 0.5) * W, sy = cy + (-v.y * 0.5 + 0.5) * H;
          if (sx < x0) x0 = sx; if (sx > x1) x1 = sx; if (sy < y0) y0 = sy; if (sy > y1) y1 = sy;
        }
        if (x1 > x0) out.push({ name: m.name || (m.geometry.type || 'mesh').replace('Geometry', ''), x0: x0, y0: y0, x1: x1, y1: y1, behind: behind });
      });
      return out;
    };
    threes.push(t3);
    return t3;
  };
  function renderThrees(tl, list) { var t = tl.time(); (list || threes).forEach(function (x) { x.render(t); }); }

  api.expose = function (tl, w) {
    w = w || window;
    var sf = stepFps, th = threes.slice();     // captured: a later scene's reset()/stepped() must not change this scene's seek
    finalizers.forEach(function (f) { f(tl); });
    tl.pause();
    if (th.length) tl.eventCallback('onUpdate', function () { renderThrees(tl, th); });   // after every seek, once all tweens have set their state
    w.__tl = tl;
    w.__duration = tl.duration();
    w.__size = STAGE ? [STAGE.w, STAGE.h] : null;          // tamaño real del escenario (la vista previa lo lee)
    w.__threeBoxes = th.length ? function () { var r = []; th.forEach(function (x) { r = r.concat(x.boxes()); }); return r; } : null;   // validate.py: 3D en pantalla (solo si hay 3D)
    // never seek to exactly 0: GSAP reverts zero-duration tweens positioned at 0 there and does not re-apply them going forward
    w.__seek = function (t) {
      if (sf) t = Math.floor(t * sf + 1e-6) / sf;
      tl.pause(); tl.time(Math.max(1e-4, Math.min(t, tl.duration()))); return t;
    };
    w.__boundaries = boundaries.slice().sort(function (a, b) { return a.t - b.t; });
    w.__stepped = sf;
    tl.time(1e-4);
    if (th.length) renderThrees(tl, th);
    w.__labels = tl.labels;
    w.__cues = cues.slice().sort(function (a, b) { return a.t - b.t; });
    w.__ready = true;
  };

  return api;
});
