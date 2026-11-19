/*
 * motion-kit.js — deterministic building blocks for LogocodeX motion scenes.
 *
 * Contract (this is what makes the same scene render identically in Hyperframes-style HTML,
 * Remotion, or a plain browser): every function only *adds tweens to a paused GSAP timeline*.
 * Nothing here reads the clock, calls Math.random, uses callbacks, or repeats forever, so any
 * frame is a pure function of time and can be rendered in any order.
 *
 * Works as a <script> (window.MotionKit) or as a CommonJS/ESM-interop import.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MotionKit = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var SVGNS = 'http://www.w3.org/2000/svg';
  var gsap = null;

  function use(g) { gsap = g || (typeof window !== 'undefined' ? window.gsap : null); return api; }
  function el(name, attrs) {
    var n = document.createElementNS(SVGNS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  /** Merge defaults + archetype into one token object and add the helpers `t.d()` and `t.gap()`. */
  function tokens(all, name) {
    var d = all.defaults, a = all.archetypes[name];
    if (!a) throw new Error('Unknown archetype "' + name + '". Known: ' + Object.keys(all.archetypes).join(', '));
    var t = Object.assign({}, d, a, { ease: Object.assign({}, d.ease, a.ease || {}) });
    t.name = name;
    t.d = function (seconds) { return seconds * t.tempo; };      // scale a duration by the archetype's tempo
    t.gap = function (n) { return (n || 1) * t.stagger * t.tempo; }; // n-th stagger step
    return t;
  }

  /**
   * Build the SVG stage from the JSON that split_logo_layers.py wrote.
   * Each layer (and each `part` of a split layer, e.g. every letter) becomes a node:
   *   { g, path, clip, box:[x0,y0,x1,y1] }  — `clip` is a <rect> you animate to wipe the shape in.
   * Returns { svg, root, nodes: {layerName: node}, parts: {layerName: [node...]} }.
   */
  function stage(container, data, opts) {
    opts = opts || {};
    var vb = data.viewBox, ink = opts.ink || '#0a0a0b', pad = 12, uid = 0;
    var svg = el('svg', { viewBox: vb.join(' '), xmlns: SVGNS, preserveAspectRatio: 'xMidYMid meet' });
    svg.style.cssText = 'width:100%;height:100%;display:block;overflow:visible';
    var defs = el('defs', {}); svg.appendChild(defs);
    var rootG = el('g', { id: 'root' }); svg.appendChild(rootG);
    var nodes = {}, parts = {};

    function make(id, d, bb) {
      var cid = 'clip-' + id + '-' + (uid++);
      var box = [bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad];
      var cp = el('clipPath', { id: cid });
      var rect = el('rect', { x: box[0], y: box[1], width: box[2] - box[0], height: box[3] - box[1] });
      cp.appendChild(rect); defs.appendChild(cp);
      // g  : clip + opacity + translation (rise / fade / wipe)
      // gs : scale about a point. Kept on its own group because GSAP shifts svgOrigin when x/y and svgOrigin
      //      are tweened on the same element, which leaves the shape displaced at the end (found by validate_motion.py).
      var g = el('g', { id: 'L-' + id, 'clip-path': 'url(#' + cid + ')' });
      var gs = el('g', { id: 'S-' + id });
      var path = el('path', { d: d, fill: ink, 'fill-rule': 'evenodd' });
      gs.appendChild(path); g.appendChild(gs); rootG.appendChild(g);
      return { g: g, gs: gs, path: path, clip: rect, box: box, id: id };
    }
    // keep the author's layer order = paint order (first layer is the back-most)
    Object.keys(data.layers).forEach(function (name) {
      var L = data.layers[name];
      if (L.parts) {
        parts[name] = L.parts.map(function (p, i) { return make(name + '-' + i, p.d, p.bbox); });
      } else {
        nodes[name] = make(name, L.d, L.bbox);
      }
    });
    container.appendChild(svg);
    return { svg: svg, root: rootG, nodes: nodes, parts: parts };
  }

  /* ---------- tweens (all positioned explicitly with `at`, in seconds on the timeline) ---------- */

  /** Hide a node completely until `at` (opacity 0 + clip closed). Call once per node at the start. */
  function hide(tl, node, how) {
    how = how || 'fade';
    if (how === 'fade') tl.set(node.g, { opacity: 0 }, 0);
    else wipeStart(tl, node, how);
  }

  function wipeStart(tl, n, dir) {
    var b = n.box, w = b[2] - b[0], h = b[3] - b[1], cx = b[0] + w / 2, cy = b[1] + h / 2, a;
    if (dir === 'up') a = { y: b[3], height: 0 };           // grows upward from the bottom edge
    else if (dir === 'down') a = { y: b[1], height: 0 };    // grows downward from the top edge
    else if (dir === 'right') a = { x: b[0], width: 0 };    // grows rightward from the left edge
    else if (dir === 'left') a = { x: b[2], width: 0 };     // grows leftward from the right edge
    else if (dir === 'out-x') a = { x: cx, width: 0 };      // opens from the vertical axis outward (heraldic symmetry)
    else if (dir === 'out-y') a = { y: cy, height: 0 };
    else throw new Error('unknown wipe dir ' + dir);
    tl.set(n.clip, { attr: a }, 0);
  }

  /** Reveal a node by opening its clip rectangle. dir: up | down | left | right | out-x | out-y. */
  function wipe(tl, n, dir, o) {
    o = o || {};
    var b = n.box, w = b[2] - b[0], h = b[3] - b[1], to;
    if (dir === 'up' || dir === 'down' || dir === 'out-y') to = { y: b[1], height: h };
    else to = { x: b[0], width: w };
    wipeStart(tl, n, dir);
    tl.to(n.clip, { attr: to, duration: o.dur || 1, ease: o.ease || 'power2.out' }, o.at || 0);
  }

  /** Opacity 0 -> 1 (or any from/to). The "from" state is set at t=0 so seeking in any order is safe. */
  function fade(tl, n, o) {
    o = o || {};
    tl.set(n.g, { opacity: o.from == null ? 0 : o.from }, 0);
    tl.to(n.g, { opacity: o.to == null ? 1 : o.to, duration: o.dur || 0.8, ease: o.ease || 'sine.out' }, o.at || 0);
  }

  /** Move a node from an offset (dx, dy in SVG units) back to its resting place. */
  function rise(tl, n, o) {
    o = o || {};
    // inner:true moves the shape inside its clip (use it with `window` so the mask stays put while the shape slides through it)
    var target = o.inner ? n.gs : n.g;
    tl.set(target, { x: o.dx || 0, y: o.dy == null ? 40 : o.dy }, 0);
    tl.to(target, { x: 0, y: 0, duration: o.dur || 1, ease: o.ease || 'power2.out' }, o.at || 0);
  }

  /**
   * Static clip window in SVG units (any of top/bottom/left/right; omitted sides keep the node's box). Combine with
   * rise({inner:true}) so a shape emerges from behind an edge, e.g. a head rising out of the top of a bar.
   * The window must contain the shape's final position, or the last frame loses ink.
   */
  function window_(tl, n, o) {
    var b = n.box, x0 = o.left == null ? b[0] : o.left, x1 = o.right == null ? b[2] : o.right,
        y0 = o.top == null ? b[1] : o.top, y1 = o.bottom == null ? b[3] : o.bottom;
    tl.set(n.clip, { attr: { x: x0, y: y0, width: x1 - x0, height: y1 - y0 } }, 0);
  }

  /** Scale a node up to its true size around a point given in SVG user units (tree base, wing-span centre...). Tweens the inner `gs` group. */
  function grow(tl, n, o) {
    o = o || {};
    var origin = o.origin || [(n.box[0] + n.box[2]) / 2, n.box[3]];
    var so = origin[0] + ' ' + origin[1];
    tl.set(n.gs, { scaleX: o.sx == null ? 1 : o.sx, scaleY: o.sy == null ? 1 : o.sy, svgOrigin: so }, 0);
    tl.to(n.gs, { scaleX: 1, scaleY: 1, svgOrigin: so, duration: o.dur || 1, ease: o.ease || 'power2.out' }, o.at || 0);
  }

  /** Tween the fill of one or more nodes to `color`, hold, then back to their original ink. */
  function tint(tl, list, color, o) {
    o = o || {};
    var paths = list.map(function (n) { return n.path; });
    var at = o.at || 0, dur = o.dur || 0.5, hold = o.hold == null ? 0.4 : o.hold;
    tl.to(paths, { fill: color, duration: dur, ease: o.ease || 'sine.inOut' }, at);
    tl.to(paths, { fill: o.back || '#0a0a0b', duration: o.backDur || dur, ease: o.ease || 'sine.inOut' }, at + dur + hold);
  }

  /** Slow camera settle: starts slightly zoomed in and ends at exactly scale 1, so the last frame is the true logo. */
  function drift(tl, stg, o) {
    o = o || {};
    var vb = stg.svg.viewBox.baseVal;
    var origin = (vb.x + vb.width / 2) + ' ' + (vb.y + vb.height / 2);
    tl.set(stg.root, { scale: o.from || 1.02, svgOrigin: origin }, 0);
    tl.to(stg.root, { scale: 1, svgOrigin: origin, duration: o.dur || 4, ease: o.ease || 'sine.inOut' }, o.at || 0);
  }


  /**
   * Reveal a node with a straight edge that travels ALONG a vector, like a pen stroke: `from` -> `to` in SVG units.
   * The clip is a rotated rectangle whose length grows; `width` must exceed the shape's extent across the stroke.
   * Use it when the form itself dictates the direction (the legs of the letter A in a mountain, a blade, a river).
   */
  function sweep(tl, n, o) {
    var f = o.from, t = o.to, dx = t[0] - f[0], dy = t[1] - f[1];
    var len = Math.sqrt(dx * dx + dy * dy) + (o.extra == null ? 40 : o.extra), W = o.width || 1400;
    var ang = Math.atan2(dy, dx) * 180 / Math.PI;
    tl.set(n.clip, { attr: { x: 0, y: -W / 2, width: 0, height: W,
      transform: 'translate(' + f[0] + ' ' + f[1] + ') rotate(' + ang.toFixed(3) + ')' } }, 0);
    tl.to(n.clip, { attr: { width: len }, duration: o.dur || 1, ease: o.ease || 'expo.out' }, o.at || 0);
  }

  /**
   * Articulated opening about a joint (a wing from the shoulder): rotation and X/Y scale tween together around
   * `origin`. Give the rotation ease an overshoot (back.out) to get a pose that goes past the rest position and settles.
   * o: {origin:[x,y], rot (start angle, deg), sx, sy (start scales), at, dur, easeRot, easeScale}
   */
  function unfold(tl, n, o) {
    var so = o.origin[0] + ' ' + o.origin[1], sx = o.sx == null ? 1 : o.sx, sy = o.sy == null ? 1 : o.sy;
    tl.set(n.gs, { rotation: o.rot || 0, scaleX: sx, scaleY: sy, svgOrigin: so }, 0);
    tl.to(n.gs, { rotation: 0, svgOrigin: so, duration: o.dur || 1, ease: o.easeRot || 'back.out(2)' }, o.at || 0);
    tl.to(n.gs, { scaleX: 1, scaleY: 1, svgOrigin: so, duration: (o.dur || 1) * (o.scaleDur == null ? 0.85 : o.scaleDur), ease: o.easeScale || 'expo.out' }, o.at || 0);
  }

  /**
   * Camera as a chain of scale moves on the whole stage, about the frame centre. keys: [{at, dur, from?, to, ease}].
   * Chain them without gaps and finish at scale 1 so the last frame is the true logo (a punch-in at a hit, a settle).
   */
  function camera(tl, stg, keys) {
    var vb = stg.svg.viewBox.baseVal, so = (vb.x + vb.width / 2) + ' ' + (vb.y + vb.height / 2);
    tl.set(stg.root, { scale: keys[0].from == null ? 1 : keys[0].from, svgOrigin: so }, 0);
    keys.forEach(function (k) {
      tl.to(stg.root, { scale: k.to, svgOrigin: so, duration: k.dur, ease: k.ease || 'sine.inOut' }, k.at);
    });
  }

  /** Expose the timeline to whoever renders it (the render script, a preview page, Hyperframes-style seekers). */
  function expose(tl, w) {
    w = w || window;
    tl.pause(0);
    w.__tl = tl;
    w.__duration = tl.duration();
    w.__seek = function (t) { tl.pause(); tl.time(Math.max(0, Math.min(t, tl.duration()))); return t; };
    w.__labels = tl.labels;
    w.__ready = true;
  }

  var api = { use: use, tokens: tokens, stage: stage, hide: hide, wipe: wipe, fade: fade, rise: rise, grow: grow, tint: tint, drift: drift, window: window_, sweep: sweep, unfold: unfold, camera: camera, expose: expose };
  return api;
});
