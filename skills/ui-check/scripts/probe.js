(options) => {
  const settings = options || {};
  const NEAR = 4;
  const frameMode = settings.frame || "issues";
  const root = document.documentElement;
  const viewportWidth = root.clientWidth;
  const viewportHeight = window.innerHeight;
  const offsetX = window.scrollX;
  const offsetY = window.scrollY;
  const SKIPPED = new Set(["SCRIPT", "STYLE", "LINK", "META", "HEAD", "TITLE", "NOSCRIPT", "TEMPLATE", "BR", "WBR", "SOURCE", "TRACK"]);
  const MEDIA = new Set(["IMG", "SVG", "VIDEO", "CANVAS", "IFRAME", "PICTURE", "OBJECT", "EMBED"]);
  const FIELDS = new Set(["INPUT", "SELECT", "TEXTAREA"]);
  const CONTROL_ROLES = new Set(["button", "tab", "menuitem", "option", "switch", "checkbox", "radio", "link"]);
  const CELLS = new Set(["TD", "TH", "TR", "TABLE", "THEAD", "TBODY", "TFOOT", "CAPTION", "COLGROUP", "COL"]);
  const EVERYWHERE = { x1: -1e9, y1: -1e9, x2: 1e9, y2: 1e9 };
  const NOWHERE = { x1: 0, y1: 0, x2: 0, y2: 0 };

  const px = (value) => parseFloat(value) || 0;
  const tenth = (value) => Math.round(value * 10) / 10;
  const width = (b) => b.x2 - b.x1;
  const height = (b) => b.y2 - b.y1;
  const centreX = (b) => (b.x1 + b.x2) / 2;
  const centreY = (b) => (b.y1 + b.y2) / 2;
  const toBox = (r) => ({ x1: r.left + offsetX, y1: r.top + offsetY, x2: r.right + offsetX, y2: r.bottom + offsetY });
  const union = (a, b) => (!a ? b : !b ? a : { x1: Math.min(a.x1, b.x1), y1: Math.min(a.y1, b.y1), x2: Math.max(a.x2, b.x2), y2: Math.max(a.y2, b.y2) });
  const intersect = (a, b) => {
    const r = { x1: Math.max(a.x1, b.x1), y1: Math.max(a.y1, b.y1), x2: Math.min(a.x2, b.x2), y2: Math.min(a.y2, b.y2) };
    return r.x2 > r.x1 && r.y2 > r.y1 ? r : null;
  };
  const inside = (inner, outer) => inner.x1 >= outer.x1 - 1 && inner.y1 >= outer.y1 - 1 && inner.x2 <= outer.x2 + 1 && inner.y2 <= outer.y2 + 1;
  const asList = (b) => [tenth(b.x1), tenth(b.y1), tenth(width(b)), tenth(height(b))];
  const countOf = (values) => {
    const counts = new Map();
    for (const v of values) counts.set(v, (counts.get(v) || 0) + 1);
    return counts;
  };
  const modeOf = (values) => {
    let best = null;
    let bestCount = 0;
    for (const [v, c] of countOf(values)) if (c > bestCount) { best = v; bestCount = c; }
    return best;
  };

  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  const paint = canvas.getContext("2d", { willReadFrequently: true });
  const colourCache = new Map();
  const toColour = (text) => {
    if (!text) return null;
    if (colourCache.has(text)) return colourCache.get(text);
    let colour = null;
    if (/^rgba?\(/.test(text)) {
      const parts = text.match(/[\d.]+/g).map(Number);
      colour = { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
    } else if (CSS.supports("color", text)) {
      paint.clearRect(0, 0, 1, 1);
      paint.fillStyle = text;
      paint.fillRect(0, 0, 1, 1);
      const d = paint.getImageData(0, 0, 1, 1).data;
      colour = { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
    }
    colourCache.set(text, colour);
    return colour;
  };
  const coloursIn = (text) => (text.match(/(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^()]*\)|#[0-9a-fA-F]{3,8}\b/g) || []).map(toColour).filter(Boolean);
  const hex = (c) => "#" + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("") + (c.a < 0.995 ? Math.round(c.a * 255).toString(16).padStart(2, "0") : "");
  const distance = (a, b) => Math.hypot(a.r - b.r, a.g - b.g, a.b - b.b);
  const blend = (top, bottom) => ({ r: top.r * top.a + bottom.r * (1 - top.a), g: top.g * top.a + bottom.g * (1 - top.a), b: top.b * top.a + bottom.b * (1 - top.a), a: 1 });
  const hsl = (c) => {
    const r = c.r / 255, g = c.g / 255, b = c.b / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return { h: 0, s: 0, l };
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    const h = max === r ? ((g - b) / d + (g < b ? 6 : 0)) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return { h: h * 60, s, l };
  };
  const saturated = (c, floor) => {
    if (!c || c.a < 0.2) return false;
    const v = hsl(c);
    return v.s >= floor && v.l > 0.12 && v.l < 0.92;
  };
  const luminance = (c) => {
    const ch = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  };
  const contrast = (a, b) => {
    const la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };

  const fontCache = new Map();
  const ascentRatio = (cs) => {
    const font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    if (!fontCache.has(font)) {
      paint.font = font;
      const m = paint.measureText("Hg");
      fontCache.set(font, m.fontBoundingBoxAscent / (m.fontBoundingBoxAscent + m.fontBoundingBoxDescent));
    }
    return fontCache.get(font);
  };

  const describe = (el) => {
    let name = el.tagName.toLowerCase();
    if (el.id) name += "#" + el.id;
    else {
      const classes = [...(el.classList || [])].filter((c) => c.length <= 24 && !/[:\[\]\/()]/.test(c)).slice(0, 2);
      if (classes.length) name += "." + classes.join(".");
    }
    const text = (el.getAttribute("aria-label") || el.getAttribute("alt") || el.getAttribute("placeholder") || el.textContent || "").replace(/\s+/g, " ").trim();
    if (text) name += ' "' + (text.length > 28 ? text.slice(0, 27) + "…" : text) + '"';
    return name;
  };
  const pathOf = (el) => {
    const parts = [];
    for (let e = el; e && e !== document.body && e !== root; e = e.parentElement) {
      let index = 1;
      for (let s = e.previousElementSibling; s; s = s.previousElementSibling) if (s.tagName === e.tagName) index++;
      parts.push(e.tagName.toLowerCase() + (index > 1 ? index : ""));
    }
    return parts.reverse().join(">");
  };

  const nodes = [];
  const byElement = new Map();
  const walk = (el, parent, depth, state) => {
    const tag = el.tagName.toUpperCase();
    if (SKIPPED.has(tag) || el.id === "__uicheck") return;
    const cs = getComputedStyle(el);
    if (cs.display === "none") return;
    const fixed = cs.position === "fixed";
    const node = {
      i: nodes.length, el, cs, tag, depth, parent, kids: [],
      b: toBox(el.getBoundingClientRect()),
      clip: fixed ? EVERYWHERE : state.clip,
      hard: fixed ? EVERYWHERE : state.hard,
      zero: state.zero || parseFloat(cs.opacity) === 0,
      floating: state.floating || cs.position === "absolute" || fixed,
    };
    node.hidden = node.zero || cs.visibility !== "visible";
    if (parent >= 0) nodes[parent].kids.push(node.i);
    nodes.push(node);
    byElement.set(el, node);
    const tiny = (width(node.b) <= 2 || height(node.b) <= 2) && cs.overflow !== "visible";
    const clippedAway = /rect\(0(px)?,? 0(px)?,? 0(px)?,? 0(px)?\)/.test(cs.clip) || /inset\((50%|100%)/.test(cs.clipPath);
    node.innerClip = node.clip;
    node.innerHard = node.hard;
    if (tiny || clippedAway) { node.hidden = true; return; }
    if (tag === "SVG" || MEDIA.has(tag) || FIELDS.has(tag)) return;
    let clip = node.clip;
    let hard = node.hard;
    const clipsX = cs.overflowX !== "visible";
    const clipsY = cs.overflowY !== "visible";
    if (tag === "HTML" || tag === "BODY") {
      if (clipsX || clipsY) {
        const limit = { x1: clipsX ? 0 : -1e9, x2: clipsX ? viewportWidth : 1e9, y1: -1e9, y2: 1e9 };
        clip = intersect(clip, limit) || NOWHERE;
        hard = intersect(hard, limit) || NOWHERE;
      }
    } else if (clipsX || clipsY) {
      const pad = { x1: node.b.x1 + px(cs.borderLeftWidth), y1: node.b.y1 + px(cs.borderTopWidth), x2: node.b.x2 - px(cs.borderRightWidth), y2: node.b.y2 - px(cs.borderBottomWidth) };
      const limit = { x1: clipsX ? pad.x1 : -1e9, x2: clipsX ? pad.x2 : 1e9, y1: clipsY ? pad.y1 : -1e9, y2: clipsY ? pad.y2 : 1e9 };
      clip = intersect(clip, limit) || NOWHERE;
      const scrolls = /auto|scroll/.test(cs.overflowX + cs.overflowY);
      node.scrolls = scrolls;
      if (scrolls) hard = EVERYWHERE;
      else hard = intersect(hard, limit) || NOWHERE;
      node.clipBox = limit;
    }
    node.innerClip = clip;
    node.innerHard = hard;
    if (nodes.length > 8000) return;
    for (const kid of el.children) walk(kid, node.i, depth + 1, { clip, hard, zero: node.zero, floating: node.floating });
  };
  walk(root, -1, 0, { clip: EVERYWHERE, hard: EVERYWHERE, zero: false, floating: false });

  const effectiveBackground = (node) => {
    if (node.eff !== undefined) return node.eff;
    const base = node.parent >= 0 ? effectiveBackground(nodes[node.parent]) : { r: 255, g: 255, b: 255, a: 1 };
    let result = base;
    const own = toColour(node.cs.backgroundColor);
    if (node.cs.backgroundImage !== "none") result = null;
    else if (own && own.a > 0) result = base ? blend(own, base) : own.a >= 0.99 ? own : null;
    node.eff = result;
    return result;
  };
  const sides = ["Top", "Right", "Bottom", "Left"];
  const borderWidths = (cs) => sides.map((s) => (cs[`border${s}Style`] !== "none" && (toColour(cs[`border${s}Color`]) || { a: 0 }).a > 0.05 ? px(cs[`border${s}Width`]) : 0));
  const visibleBox = (node) => {
    const { cs, tag } = node;
    if (tag === "HTML" || tag === "BODY") return null;
    if (MEDIA.has(tag)) return "media";
    if (FIELDS.has(tag)) return "field";
    if (cs.backgroundImage !== "none") return "fill";
    const own = toColour(cs.backgroundColor);
    if (own && own.a > 0.05) {
      const behind = node.parent >= 0 ? effectiveBackground(nodes[node.parent]) : null;
      if (!behind || distance(blend(own, behind), behind) > 6) return "fill";
    }
    if (borderWidths(cs).some((w) => w >= 1)) return "border";
    if (cs.boxShadow !== "none") return "shadow";
    return null;
  };
  const roleOf = (el) => (el.getAttribute("role") || "").toLowerCase();
  const isControl = (node) => node.tag === "BUTTON" || node.tag === "SUMMARY" || FIELDS.has(node.tag) || CONTROL_ROLES.has(roleOf(node.el)) || (node.tag === "A" && !!node.box);
  const inlineInText = (node) => {
    if (node.cs.display !== "inline") return false;
    const parent = nodes[node.parent];
    return !!parent && [...parent.el.childNodes].some((c) => c.nodeType === 3 && c.data.trim());
  };
  const textAlign = (node) => {
    const cs = node.cs;
    const a = cs.textAlign;
    if (a === "center") return "c";
    if (a === "right" || (a === "end" && cs.direction !== "rtl")) return "r";
    return "l";
  };

  for (const node of nodes) {
    if (node.hidden) continue;
    node.box = visibleBox(node);
    if (node.box && (width(node.b) < 2 || height(node.b) < 2 || !intersect(node.b, node.clip))) node.box = null;
    const cs = node.cs;
    const textVisible = (toColour(cs.color) || { a: 0 }).a > 0.05 || /text/.test(cs.backgroundClip + cs.webkitBackgroundClip);
    if (!textVisible) continue;
    let all = null;
    const lines = [];
    const fragments = [];
    let words = 0;
    let own = "";
    for (const t of node.el.childNodes) {
      if (t.nodeType !== 3) continue;
      const start = t.data.search(/\S/);
      if (start < 0) continue;
      const end = t.data.length - t.data.match(/\s*$/)[0].length;
      const range = document.createRange();
      range.setStart(t, start);
      range.setEnd(t, end);
      for (const r of range.getClientRects()) {
        if (r.width < 1 || r.height < 1) continue;
        const b = toBox(r);
        all = union(all, b);
        fragments.push(b);
        const line = lines.find((l) => Math.abs(l.y1 - b.y1) <= 2);
        if (line) Object.assign(line, union(line, b));
        else lines.push({ ...b });
      }
      own += t.data.slice(start, end) + " ";
      words += t.data.slice(start, end).split(/\s+/).length;
    }
    if (!all || !intersect(all, node.innerClip)) continue;
    lines.sort((a, b) => a.y1 - b.y1);
    node.text = all;
    node.lines = lines;
    node.fragments = fragments;
    node.first = lines[0];
    node.words = words;
    node.own = own.trim();
    node.baseline = node.first.y1 + height(node.first) * ascentRatio(cs);
  }
  for (const node of nodes) if (node.box && isControl(node)) node.control = true;
  const controlAround = (node) => {
    for (let n = node; n; n = nodes[n.parent]) if (n.control && height(n.b) <= 64) return n;
    return null;
  };
  const insideControl = (node) => node.parent >= 0 && !!controlAround(nodes[node.parent]);
  const inCell = (node) => {
    for (let n = node; n; n = nodes[n.parent]) if (n.tag === "TD" || n.tag === "TH") return true;
    return false;
  };

  const items = [];
  for (const node of nodes) {
    if (node.box) items.push({ node, b: node.b, kind: "box" });
    if (node.text) items.push({ node, b: node.text, kind: "text", align: textAlign(node) });
  }
  for (const item of items) {
    for (let n = item.node; n; n = nodes[n.parent]) n.ink = union(n.ink, item.b);
    for (let n = nodes[item.node.parent]; n; n = nodes[n.parent]) n.inner = union(n.inner, item.b);
  }
  for (const node of nodes) if (node.text) node.inner = union(node.inner, node.text);
  const related = (a, b) => {
    if (a.kind === "text" && b.kind === "text") return a.node === b.node;
    if (a.kind === "box" && b.kind === "box") return a.node.el.contains(b.node.el) || b.node.el.contains(a.node.el);
    const box = a.kind === "box" ? a : b;
    const text = a.kind === "box" ? b : a;
    return box.node.el.contains(text.node.el);
  };

  const findings = [];
  let refs = 0;
  const ref = (list) => {
    const el = list[0]?.el;
    if (!el?.setAttribute) return undefined;
    if (!el.hasAttribute("data-uic")) el.setAttribute("data-uic", String(++refs));
    return el.getAttribute("data-uic");
  };
  const add = (severity, kind, message, list, boxes, extra) => {
    findings.push(Object.assign({ severity, kind, message, elements: list.map((n) => describe(n.el)), boxes: boxes.map(asList), ref: ref(list) }, extra || {}));
  };

  const scrollWidth = root.scrollWidth;
  if (scrollWidth > viewportWidth + 1) {
    const culprits = nodes.filter((n) => !n.hidden && n.tag !== "HTML" && n.tag !== "BODY" && n.b.x2 > viewportWidth + 1 && n.clip.x2 > viewportWidth + 1 && width(n.b) > 0 && !(n.parent >= 0 && nodes[n.parent].tag !== "BODY" && nodes[n.parent].b.x2 > viewportWidth + 1 && nodes[n.parent].clip.x2 > viewportWidth + 1));
    add("fail", "overflow-x", `page scrolls sideways by ${scrollWidth - viewportWidth}px; ${culprits.length ? "widest cause ends at x=" + tenth(Math.max(...culprits.map((c) => c.b.x2))) : "cause not found"}`, culprits.slice(0, 3), culprits.slice(0, 3).map((c) => c.b));
  }

  const truncated = [];
  for (const node of nodes) {
    if (!node.text || node.innerHard === EVERYWHERE) continue;
    const fs = px(node.cs.fontSize);
    const h = node.innerHard;
    const outX = Math.max(node.text.x2 - h.x2, h.x1 - node.text.x1);
    const outY = Math.max(node.text.y2 - h.y2, h.y1 - node.text.y1);
    if (outX <= 2 && outY <= Math.max(2, 0.15 * fs)) continue;
    let marked = false;
    for (let n = node; n; n = nodes[n.parent]) {
      if (n.cs.textOverflow === "ellipsis" || (n.cs.webkitLineClamp && n.cs.webkitLineClamp !== "none")) { marked = true; break; }
      if (n.clipBox) break;
    }
    if (marked) truncated.push(node);
    else add("fail", "clipped", `text is cut off by ${tenth(Math.max(outX, outY))}px`, [node], [node.text, h]);
  }
  if (truncated.length) add("warn", "truncated", `${truncated.length} text(s) cut short with an ellipsis; check the full text is reachable`, truncated.slice(0, 4), truncated.slice(0, 4).map((n) => n.text));

  const overlapItems = [];
  for (const node of nodes) {
    if (node.fragments) for (const piece of node.fragments) { const shown = intersect(piece, node.innerClip); if (shown) overlapItems.push({ node, b: shown, kind: "text" }); }
    if (node.control && !node.hidden) overlapItems.push({ node, b: intersect(node.b, node.clip) || node.b, kind: "box" });
  }
  overlapItems.sort((a, b) => a.b.y1 - b.b.y1);
  const overlapSeen = new Set();
  for (let i = 0; i < overlapItems.length; i++) {
    const a = overlapItems[i];
    for (let j = i + 1; j < overlapItems.length && overlapItems[j].b.y1 < a.b.y2; j++) {
      const c = overlapItems[j];
      if (a.node === c.node || related(a, c)) continue;
      const shared = intersect(a.b, c.b);
      if (!shared || width(shared) < 2 || height(shared) < 2) continue;
      if (a.kind !== c.kind) {
        const text = a.kind === "text" ? a : c;
        const box = a.kind === "text" ? c : a;
        if (inside(text.b, box.b)) continue;
      }
      const key = [a.node.i, c.node.i].sort().join(":");
      if (overlapSeen.has(key)) continue;
      overlapSeen.add(key);
      add("fail", "overlap", `${a.kind === "text" ? "text" : "control"} overlaps ${c.kind === "text" ? "text" : "control"} by ${tenth(width(shared))}×${tenth(height(shared))}px`, [a.node, c.node], [a.b, c.b]);
    }
  }

  for (const node of nodes) {
    if (node.hidden || node.floating || !(node.box || node.text) || node.tag === "HTML" || node.tag === "BODY") continue;
    const own = node.box ? node.b : node.text;
    let holder = null;
    for (let n = nodes[node.parent]; n; n = nodes[n.parent]) if (n.box && n.tag !== "BODY" && n.tag !== "HTML") { holder = n; break; }
    if (!holder || holder.clipBox || inCell(node)) continue;
    const out = Math.max(own.x2 - holder.b.x2, holder.b.x1 - own.x1, own.y2 - holder.b.y2, holder.b.y1 - own.y1);
    if (out <= 2) continue;
    const parent = nodes[node.parent];
    const parentOut = parent !== holder && (parent.b.x2 - holder.b.x2 > 2 || holder.b.x1 - parent.b.x1 > 2 || parent.b.y2 - holder.b.y2 > 2);
    if (parentOut) continue;
    add("warn", "sticks-out", `sticks out of its box by ${tenth(out)}px`, [node, holder], [own, holder.b]);
  }

  const near = (d) => d >= 1 && d <= NEAR;
  const groups = new Map();
  const remember = (kind, key, a, c, message, extra) => {
    const id = kind + ":" + key;
    if (!groups.has(id)) groups.set(id, { kind, message, nodes: [], boxes: [], extra });
    const g = groups.get(id);
    for (const it of [a, c]) if (!g.nodes.includes(it.node) && g.nodes.length < 4) { g.nodes.push(it.node); g.boxes.push(it.b); }
  };
  const alignable = items.filter((it) => {
    const n = it.node;
    if (n.tag === "HTML" || n.tag === "BODY" || inCell(n)) return false;
    if (it.kind === "text") return !inlineInText(n) && !controlAround(n);
    return width(it.b) < viewportWidth * 0.98 && !insideControl(n);
  });
  const frameOf = (it) => {
    for (let n = it.kind === "text" ? it.node : nodes[it.node.parent]; n; n = nodes[n.parent]) if (n.box && n.tag !== "BODY" && n.tag !== "HTML") return n;
    return null;
  };
  for (const it of items) it.frame = frameOf(it);
  const sameFrame = (a, c, edge) => a.frame === c.frame || (a.kind === "text" && c.kind === "text" && !!a.frame && !!c.frame && Math.abs(edge(a.frame.b) - edge(c.frame.b)) < 1);
  const ends = (it, side) => {
    const n = it.node;
    const p = nodes[n.parent];
    if (!p) return true;
    const overlapY = (b) => Math.min(b.y2, it.b.y2) - Math.max(b.y1, it.b.y1) > 0;
    const beyond = (b) => (side === "l" ? b.x2 <= it.b.x1 + 1 : b.x1 >= it.b.x2 - 1);
    const others = p.kids.map((i) => nodes[i]).filter((k) => k !== n && !k.hidden && !k.floating).map((k) => (k.box ? k.b : k.text || k.inner)).filter(Boolean);
    if (others.some((b) => overlapY(b) && beyond(b))) return false;
    return !(it.kind !== "text" && p.lines && p.lines.some((l) => overlapY(l) && beyond(l)));
  };
  alignable.sort((a, b) => a.b.y1 - b.b.y1);
  for (let i = 0; i < alignable.length; i++) {
    const a = alignable[i];
    for (let j = i + 1; j < alignable.length && alignable[j].b.y1 <= a.b.y2 + 96; j++) {
      const c = alignable[j];
      if (c.b.y1 < a.b.y2 - 1) continue;
      if (Math.min(a.b.x2, c.b.x2) - Math.max(a.b.x1, c.b.x1) <= 0 || related(a, c)) continue;
      const sharedCentre = Math.abs(centreX(a.b) - centreX(c.b)) < 1;
      const left = (it) => !sharedCentre && (it.kind === "box" || it.align === "l") && ends(it, "l");
      const right = (it) => !sharedCentre && (it.kind === "box" || it.align === "r") && ends(it, "r");
      const centred = (it) => it.kind === "text" && it.align === "c";
      const guide = (axis, va, vc) => ({ guide: { axis, at: [tenth(va), tenth(vc)], from: tenth(a.b.y1), to: tenth(c.b.y2) } });
      if (left(a) && left(c) && sameFrame(a, c, (b) => b.x1) && near(Math.abs(a.b.x1 - c.b.x1))) remember("edge", "l" + [Math.round(a.b.x1), Math.round(c.b.x1)].sort().join("/"), a, c, `left edges at x=${tenth(a.b.x1)} and x=${tenth(c.b.x1)} are ${tenth(Math.abs(a.b.x1 - c.b.x1))}px apart`, guide("x", a.b.x1, c.b.x1));
      if (right(a) && right(c) && sameFrame(a, c, (b) => b.x2) && near(Math.abs(a.b.x2 - c.b.x2))) remember("edge", "r" + [Math.round(a.b.x2), Math.round(c.b.x2)].sort().join("/"), a, c, `right edges at x=${tenth(a.b.x2)} and x=${tenth(c.b.x2)} are ${tenth(Math.abs(a.b.x2 - c.b.x2))}px apart`, guide("x", a.b.x2, c.b.x2));
      if (centred(a) && centred(c) && sameFrame(a, c, centreX) && near(Math.abs(centreX(a.b) - centreX(c.b)))) remember("edge", "c" + [Math.round(centreX(a.b)), Math.round(centreX(c.b))].sort().join("/"), a, c, `centres at x=${tenth(centreX(a.b))} and x=${tenth(centreX(c.b))} are ${tenth(Math.abs(centreX(a.b) - centreX(c.b)))}px apart`, guide("x", centreX(a.b), centreX(c.b)));
    }
  }

  const rowable = items.filter((it) => {
    const n = it.node;
    if (n.tag === "HTML" || n.tag === "BODY") return false;
    if (it.kind === "text") return !inlineInText(n);
    return width(it.b) < viewportWidth * 0.98;
  });
  rowable.sort((a, b) => a.b.y1 - b.b.y1);
  const isIcon = (it) => it.kind === "box" && (it.node.tag === "SVG" || it.node.tag === "IMG") && width(it.b) <= 40 && height(it.b) <= 40;
  const isSmallControl = (it) => it.kind === "box" && it.node.control && height(it.b) <= 64;
  const isPanel = (it) => it.kind === "box" && !isIcon(it) && !it.node.control && height(it.b) > 64;
  for (let i = 0; i < rowable.length; i++) {
    const a = rowable[i];
    for (let j = i + 1; j < rowable.length && rowable[j].b.y1 < a.b.y2; j++) {
      const c = rowable[j];
      const [l, r] = a.b.x1 <= c.b.x1 ? [a, c] : [c, a];
      const gap = r.b.x1 - l.b.x2;
      if (gap < -1 || gap > 48 || related(a, c)) continue;
      const pair = [a, c];
      const icon = pair.find(isIcon);
      const text = pair.find((it) => it.kind === "text");
      if (icon && text) {
        const d = Math.abs(centreY(icon.b) - centreY(text.node.first));
        if (d >= 1.5 && d <= 8) remember("icon-centre", icon.node.i + "/" + text.node.i, icon, text, `icon centre is ${tenth(d)}px off its label's centre`);
        continue;
      }
      if (a.kind === "text" && c.kind === "text") {
        const d = Math.abs(a.node.baseline - c.node.baseline);
        const dc = Math.abs(centreY(a.node.first) - centreY(c.node.first));
        if (d >= 1.5 && d <= NEAR && dc >= 1.5 && Math.abs(a.node.first.y1 - c.node.first.y1) < height(a.node.first)) remember("baseline", a.node.i + "/" + c.node.i, a, c, `text baselines are ${tenth(d)}px apart`);
        continue;
      }
      if (isSmallControl(a) && isSmallControl(c)) {
        const dh = Math.abs(height(a.b) - height(c.b));
        if (dh >= 1 && dh <= 8) remember("row-height", a.node.i + "/" + c.node.i, a, c, `controls side by side are ${tenth(height(a.b))}px and ${tenth(height(c.b))}px tall`);
        else if (dh < 1 && near(Math.abs(a.b.y1 - c.b.y1))) remember("row-top", a.node.i + "/" + c.node.i, a, c, `controls side by side start ${tenth(Math.abs(a.b.y1 - c.b.y1))}px apart`);
        continue;
      }
      const control = pair.find(isSmallControl);
      if (text && control && height(control.b) <= 48) {
        const d = Math.abs(centreY(text.node.first) - centreY(control.b));
        if (d >= 1.5 && d <= NEAR) remember("row-centre", text.node.i + "/" + control.node.i, text, control, `label centre is ${tenth(d)}px off the control's centre`);
        continue;
      }
      if (isPanel(a) && isPanel(c)) {
        const dt = Math.abs(a.b.y1 - c.b.y1);
        const db = Math.abs(a.b.y2 - c.b.y2);
        if (near(dt)) remember("row-top", a.node.i + "/" + c.node.i, a, c, `boxes side by side start ${tenth(dt)}px apart`);
        else if (dt < 1 && near(db)) remember("row-bottom", a.node.i + "/" + c.node.i, a, c, `boxes side by side end ${tenth(db)}px apart`);
      }
    }
  }
  for (const g of groups.values()) add("warn", g.kind, g.message, g.nodes, g.boxes, g.extra);

  const layoutBox = (node) => {
    if (node.box) return node.b;
    const cs = node.cs;
    return {
      x1: node.b.x1 + px(cs.borderLeftWidth) + px(cs.paddingLeft),
      y1: node.b.y1 + px(cs.borderTopWidth) + px(cs.paddingTop),
      x2: node.b.x2 - px(cs.borderRightWidth) - px(cs.paddingRight),
      y2: node.b.y2 - px(cs.borderBottomWidth) - px(cs.paddingBottom),
    };
  };
  const gapValues = [];
  for (const parent of nodes) {
    if (parent.hidden || parent.kids.length < 3) continue;
    const kids = parent.kids.map((i) => nodes[i]).filter((k) => !k.hidden && !k.floating && k.cs.position !== "sticky" && k.cs.display !== "inline" && k.ink && !CELLS.has(k.tag)).map((k) => ({ node: k, b: layoutBox(k) }));
    if (kids.length < 3) continue;
    let stacked = true;
    let inRow = true;
    for (let k = 1; k < kids.length; k++) {
      const p = kids[k - 1].b, q = kids[k].b;
      if (q.y1 < p.y2 - 1) stacked = false;
      if (q.x1 < p.x2 - 1 || Math.min(p.y2, q.y2) - Math.max(p.y1, q.y1) <= 0) inRow = false;
    }
    if (!stacked && !inRow) continue;
    const gaps = [];
    for (let k = 1; k < kids.length; k++) gaps.push(Math.round(stacked ? kids[k].b.y1 - kids[k - 1].b.y2 : kids[k].b.x1 - kids[k - 1].b.x2));
    gapValues.push(...gaps);
    const counts = countOf(gaps);
    const usual = modeOf(gaps);
    if (counts.get(usual) < 2) continue;
    gaps.forEach((g, k) => {
      const d = Math.abs(g - usual);
      if (counts.get(g) === 1 && d >= 1 && d <= Math.max(NEAR, Math.round(usual * 0.34))) {
        add("warn", "gap", `${stacked ? "vertical" : "horizontal"} gap of ${g}px where the other gaps in this ${stacked ? "stack" : "row"} are ${usual}px`, [kids[k].node, kids[k + 1].node], [kids[k].b, kids[k + 1].b]);
      }
    });
  }

  const centredContent = (node) => {
    const cs = node.cs;
    if (/flex|grid/.test(cs.display)) return /center/.test(cs.justifyContent) || (/column/.test(cs.flexDirection) && /center/.test(cs.alignItems));
    return cs.textAlign === "center";
  };
  for (const node of nodes) {
    if (!node.box || node.box === "field" || node.box === "media" || !node.inner) continue;
    const small = height(node.b) <= 64 && width(node.b) <= 480;
    const pill = small && height(node.b) <= 32 && !!node.inner;
    if (!small || !(node.control || pill)) continue;
    const bw = borderWidths(node.cs);
    const space = { x1: node.b.x1 + bw[3], y1: node.b.y1 + bw[0], x2: node.b.x2 - bw[1], y2: node.b.y2 - bw[2] };
    const c = node.inner;
    const lg = c.x1 - space.x1, rg = space.x2 - c.x2, tg = c.y1 - space.y1, bg = space.y2 - c.y2;
    if (lg < 0 || rg < 0 || tg < -2 || bg < -2) continue;
    if (centredContent(node) && Math.abs(lg - rg) >= 1.5 && Math.abs(lg - rg) <= 12) add("warn", "off-centre", `content sits ${tenth(lg)}px from the left and ${tenth(rg)}px from the right`, [node], [node.b, c]);
    if (Math.abs(tg - bg) >= 1.5 && Math.abs(tg - bg) <= 8) add("warn", "off-centre", `content sits ${tenth(tg)}px from the top and ${tenth(bg)}px from the bottom`, [node], [node.b, c]);
  }

  for (const table of document.querySelectorAll("table")) {
    if (!byElement.has(table) || byElement.get(table).hidden) continue;
    const rows = [...table.rows];
    const head = rows.find((r) => [...r.cells].some((c) => c.tagName === "TH"));
    if (!head) continue;
    const body = rows.filter((r) => r !== head && [...r.cells].every((c) => c.tagName === "TD") && r.cells.length === head.cells.length);
    if (!body.length || [...head.cells].some((c) => c.colSpan > 1)) continue;
    [...head.cells].forEach((th, k) => {
      const headNode = byElement.get(th);
      const cellNodes = body.map((r) => byElement.get(r.cells[k])).filter((n) => n && n.inner);
      if (!headNode || !headNode.inner || !cellNodes.length) return;
      const placement = (n) => {
        const cs = n.cs;
        const space = { x1: n.b.x1 + px(cs.borderLeftWidth) + px(cs.paddingLeft), x2: n.b.x2 - px(cs.borderRightWidth) - px(cs.paddingRight) };
        const lg = n.inner.x1 - space.x1;
        const rg = space.x2 - n.inner.x2;
        if (lg <= 1 && rg <= 1) return "fill";
        if (lg <= 1) return "l";
        if (rg <= 1) return "r";
        if (Math.abs(lg - rg) <= 1.5) return "c";
        return textAlign(n);
      };
      const headAlign = placement(headNode);
      const cellAlign = modeOf(cellNodes.map(placement));
      if (headAlign === "fill" || cellAlign === "fill") return;
      const name = (th.textContent || "").trim().slice(0, 24) || `column ${k + 1}`;
      const words = { l: "left-aligned", c: "centred", r: "right-aligned" };
      if (headAlign !== cellAlign) {
        add("warn", "table-column", `header "${name}" is ${words[headAlign]} but its cells are ${words[cellAlign]}`, [headNode, cellNodes[0]], [headNode.inner, cellNodes[0].inner]);
        return;
      }
      const edge = (b) => (headAlign === "l" ? b.x1 : headAlign === "r" ? b.x2 : centreX(b));
      const cellEdge = modeOf(cellNodes.map((n) => tenth(edge(n.inner))));
      const d = Math.abs(edge(headNode.inner) - cellEdge);
      if (d >= 1) add("warn", "table-column", `header "${name}" text is ${tenth(d)}px off its cells (x=${tenth(edge(headNode.inner))} vs x=${cellEdge})`, [headNode, cellNodes[0]], [headNode.inner, cellNodes[0].inner]);
    });
  }

  const contrastSeen = new Map();
  for (const node of nodes) {
    if (!node.text || node.zero || /text/.test(node.cs.backgroundClip + node.cs.webkitBackgroundClip)) continue;
    if (node.el.closest("[disabled],[aria-disabled=true]")) continue;
    const fg = toColour(node.cs.color);
    const bg = effectiveBackground(node);
    if (!fg || !bg) continue;
    const shown = fg.a < 1 ? blend(fg, bg) : fg;
    const ratio = contrast(shown, bg);
    const fs = px(node.cs.fontSize);
    const large = fs >= 24 || (fs >= 18.66 && Number(node.cs.fontWeight) >= 700);
    const needed = large ? 3 : 4.5;
    if (ratio >= needed) continue;
    const key = hex(shown) + "/" + hex(bg);
    if (contrastSeen.has(key)) { contrastSeen.get(key).count++; continue; }
    const entry = { count: 1 };
    contrastSeen.set(key, entry);
    add("fail", "contrast", `text contrast ${ratio.toFixed(2)}:1, needs ${needed}:1 (${hex(shown)} on ${hex(bg)})`, [node], [node.text], { pair: key, entry });
  }
  for (const f of findings) if (f.entry) { if (f.entry.count > 1) f.message += `, ${f.entry.count} places`; delete f.entry; }

  const interactive = (n) => {
    if (n.hidden || width(n.b) < 1 || height(n.b) < 1) return false;
    if (n.tag === "INPUT") return !["hidden", "checkbox", "radio"].includes((n.el.getAttribute("type") || "").toLowerCase());
    if (n.tag === "A") return n.el.hasAttribute("href") && !inlineInText(n);
    return n.tag === "BUTTON" || n.tag === "SELECT" || n.tag === "TEXTAREA" || n.tag === "SUMMARY" || CONTROL_ROLES.has(roleOf(n.el));
  };
  const targets = nodes.filter(interactive).filter((n) => { for (let p = nodes[n.parent]; p; p = nodes[p.parent]) if (interactive(p)) return false; return true; });
  const centreOf = (b) => ({ x: (b.x1 + b.x2) / 2, y: (b.y1 + b.y2) / 2 });
  const distanceToBox = (pt, b) => Math.hypot(Math.max(b.x1 - pt.x, 0, pt.x - b.x2), Math.max(b.y1 - pt.y, 0, pt.y - b.y2));
  const undersized = targets.filter((n) => width(n.b) < 24 || height(n.b) < 24);
  const cramped = undersized.filter((n) => {
    const c = centreOf(n.b);
    return targets.some((o) => o !== n && (distanceToBox(c, o.b) < 12 || (undersized.includes(o) && Math.hypot(c.x - centreOf(o.b).x, c.y - centreOf(o.b).y) < 24)));
  });
  if (cramped.length) add("warn", "target-size", `${cramped.length} click target(s) smaller than 24×24px with a neighbour too close (WCAG 2.5.8), e.g. ${tenth(width(cramped[0].b))}×${tenth(height(cramped[0].b))}px`, cramped.slice(0, 4), cramped.slice(0, 4).map((n) => n.b));

  const area = (b) => (b ? width(b) * height(b) : 0);
  const cut = targets.filter((n) => !n.floating && area(n.b) > 0 && area(intersect(n.b, n.hard)) < 0.9 * area(n.b));
  for (const n of cut) add("fail", "control-cut", `control is cut off: ${Math.round(100 - (100 * area(intersect(n.b, n.hard))) / area(n.b))}% of it cannot be seen or clicked`, [n], [n.b]);
  const broken = nodes.filter((n) => n.tag === "IMG" && !n.hidden && n.el.complete && n.el.naturalWidth === 0);
  if (broken.length) add("fail", "broken-image", `${broken.length} image(s) did not load`, broken.slice(0, 4), broken.slice(0, 4).map((n) => n.b));

  const NUMBER = /^[\s$€£¥+\-−(]*\d[\d.,\s]*\)?\s*(%|[kmb]|kb|mb|gb|tb|ms|s)?$/i;
  const PLACEHOLDER = new Set(["", "-", "–", "—", "n/a", "na", "none", "null", "undefined", "?"]);
  for (const table of document.querySelectorAll("table")) {
    const rows = [...(table.tBodies[0] || table).rows].filter((r) => byElement.get(r) && !byElement.get(r).hidden);
    if (!rows.length) continue;
    const columns = Math.max(...rows.map((r) => r.cells.length));
    for (let k = 0; k < columns; k++) {
      const cells = rows.map((r) => r.cells[k]).filter(Boolean);
      const texts = cells.map((c) => c.innerText.trim());
      const filled = cells.filter((c, j) => !PLACEHOLDER.has(texts[j].toLowerCase()));
      const numeric = filled.filter((c) => NUMBER.test(c.innerText.trim()));
      if (filled.length >= 2 && numeric.length >= 0.8 * filled.length) {
        const left = numeric.filter((c) => ["left", "start"].includes(getComputedStyle(c).textAlign));
        if (left.length >= 0.5 * numeric.length) {
          const tabular = numeric.every((c) => /tabular-nums/.test(getComputedStyle(c).fontVariantNumeric));
          const head = table.tHead && table.tHead.rows[0] && table.tHead.rows[0].cells[k];
          const list = left.slice(0, 4).map((c) => byElement.get(c)).filter(Boolean);
          add("warn", "numeric-align", `number column ${head ? '"' + head.innerText.trim() + '" ' : ""}is left-aligned${tabular ? "" : " and has no tabular-nums"}; right-align numbers so the digits line up`, list, list.map((n) => n.b));
        }
      }
      const forms = new Set(texts.filter((t) => PLACEHOLDER.has(t.toLowerCase())).map((t) => t || "(empty)"));
      if (forms.size >= 2) {
        const list = cells.filter((c, j) => PLACEHOLDER.has(texts[j].toLowerCase())).slice(0, 4).map((c) => byElement.get(c)).filter(Boolean);
        add("warn", "empty-cell", `one column shows missing values in ${forms.size} ways: ${[...forms].join(", ")}`, list, list.map((n) => n.b));
      }
    }
    const paged = document.querySelector('[aria-label*="pagination" i], .pagination, [class*="pagination" i]') || [...document.querySelectorAll("button,a")].some((b) => /^(next|previous|prev|load more|show more|›|»|>)$/i.test((b.innerText || b.getAttribute("aria-label") || "").trim()) || /next page|previous page/i.test(b.getAttribute("aria-label") || ""));
    if (rows.length > 50 && !paged) {
      const n = byElement.get(table);
      add("warn", "long-table", `table shows ${rows.length} rows with no pagination or "load more"`, [n], [n.b]);
    }
  }

  const longLines = nodes.filter((n) => {
    if (n.hidden || !n.fragments || n.words < 15) return false;
    const lines = new Set(n.fragments.map((f) => Math.round(f.y1))).size;
    return lines >= 2 && n.own.length / lines > 90;
  });
  if (longLines.length) add("warn", "line-length", `${longLines.length} paragraph(s) with more than 90 characters per line; keep body text near 45–75`, longLines.slice(0, 4), longLines.slice(0, 4).map((n) => n.text));

  const tinyText = nodes.filter((n) => !n.hidden && n.text && n.own && px(n.cs.fontSize) < 12);
  if (tinyText.length) add("warn", "small-text", `${tinyText.length} text(s) smaller than 12px, smallest ${Math.min(...tinyText.map((n) => px(n.cs.fontSize)))}px`, tinyText.slice(0, 4), tinyText.slice(0, 4).map((n) => n.text));

  const headingTags = nodes.filter((n) => !n.hidden && /^H[1-6]$/.test(n.tag) && n.text);
  const headingProblems = [];
  if (headingTags.filter((n) => n.tag === "H1").length > 1) headingProblems.push(`${headingTags.filter((n) => n.tag === "H1").length} h1 elements`);
  headingTags.forEach((n, k) => {
    const level = Number(n.tag[1]);
    const before = k ? Number(headingTags[k - 1].tag[1]) : 0;
    if (k && level > before + 1) headingProblems.push(`h${before} then h${level}`);
  });
  const lookOf = (n) => ({ "font size": px(n.cs.fontSize), height: Math.round(height(n.b)), padding: `${px(n.cs.paddingTop)}/${px(n.cs.paddingLeft)}`, radius: px(n.cs.borderTopLeftRadius) });
  const differences = (list) => {
    const looks = list.map(lookOf);
    return Object.keys(looks[0]).filter((key) => new Set(looks.map((l) => String(l[key]))).size > 1).map((key) => `${key} ${[...new Set(looks.map((l) => l[key]))].join(" vs ")}`);
  };
  const iconButton = (n) => !!n.el.querySelector("svg,img") && Math.abs(width(n.b) - height(n.b)) <= 2;
  const touches = (group) => { const sorted = group.slice().sort((a, b) => a.b.x1 - b.b.x1); return sorted.some((k, j) => j && k.b.x1 - sorted[j - 1].b.x2 <= 1 && Math.abs(k.b.y1 - sorted[j - 1].b.y1) <= 1); };
  const componentLike = (n) => !n.hidden && !n.floating && (n.box || n.control) && n.box !== "media" && n.box !== "field" && height(n.b) <= 48 && !CELLS.has(n.tag);
  const reported = new Set();
  for (const parent of nodes) {
    const kids = parent.kids.map((i) => nodes[i]).filter(componentLike);
    const byTag = new Map();
    for (const k of kids) {
      const row = kids.find((o) => o.tag === k.tag && Math.min(o.b.y2, k.b.y2) - Math.max(o.b.y1, k.b.y1) > 0);
      const key = k.tag + ":" + row.i + ":" + iconButton(k);
      byTag.set(key, [...(byTag.get(key) || []), k]);
    }
    for (const group of byTag.values()) {
      if (group.length < 2) continue;
      const touching = touches(group);
      const diff = differences(group).filter((d) => !(touching && d.startsWith("radius")) && !(group.every(iconButton) && d.startsWith("padding")) && !(group.every((k) => k.control) && d.startsWith("height")));
      if (!diff.length) continue;
      group.forEach((k) => reported.add(k));
      add("warn", "inconsistent", `${group.length} side-by-side ${group[0].tag.toLowerCase()} items differ: ${diff.join(", ")}`, group.slice(0, 4), group.slice(0, 4).map((k) => k.b));
    }
  }
  const byClass = new Map();
  for (const n of nodes) {
    const name = typeof n.el.className === "string" ? n.el.className.trim().split(/\s+/).sort().join(" ") : "";
    if (!name || !componentLike(n) || reported.has(n)) continue;
    byClass.set(n.tag + "." + name, [...(byClass.get(n.tag + "." + name) || []), n]);
  }
  for (const group of byClass.values()) {
    if (group.length < 2) continue;
    const diff = differences(group).filter((d) => !d.startsWith("height") && !(touches(group) && d.startsWith("radius")));
    if (diff.length) add("warn", "inconsistent", `${group.length} elements with the same class differ: ${diff.join(", ")}`, group.slice(0, 4), group.slice(0, 4).map((k) => k.b));
  }

  const orphans = [];
  for (const parent of nodes) {
    if (parent.hidden || !/flex/.test(parent.cs.display) || parent.cs.flexWrap !== "wrap" || /column/.test(parent.cs.flexDirection)) continue;
    const kids = parent.kids.map((i) => nodes[i]).filter((k) => !k.hidden && !k.floating && width(k.b) > 0);
    if (kids.length < 4) continue;
    const rows = [];
    for (const k of kids.slice().sort((a, b) => a.b.y1 - b.b.y1)) {
      const row = rows.find((r) => Math.min(r.y2, k.b.y2) - Math.max(r.y1, k.b.y1) > 0);
      if (row) { row.y2 = Math.max(row.y2, k.b.y2); row.items.push(k); } else rows.push({ y1: k.b.y1, y2: k.b.y2, items: [k] });
    }
    if (rows.length >= 2 && rows[rows.length - 1].items.length === 1 && rows[0].items.length >= 3) orphans.push(rows[rows.length - 1].items[0]);
  }
  if (orphans.length) add("warn", "orphan-wrap", `${orphans.length} row(s) of items wrap and leave one item alone on the last line`, orphans.slice(0, 4), orphans.slice(0, 4).map((n) => n.b));

  if (headingProblems.length) add("warn", "headings", `heading levels skip or repeat: ${[...new Set(headingProblems)].slice(0, 4).join(", ")}`, headingTags.slice(0, 4), headingTags.slice(0, 4).map((n) => n.text));

  const census = { fontSize: [], fontFamily: [], fontWeight: [], textTransform: [], radius: [], color: [], background: [], border: [], shadow: [], iconSize: [], controlHeight: [], gap: gapValues };
  const where = new Map();
  const note = (field, value, node) => {
    census[field].push(value);
    const key = field + "=" + value;
    if (!where.has(key)) where.set(key, node);
  };
  for (const node of nodes) {
    if (node.hidden) continue;
    const cs = node.cs;
    if (node.text) {
      note("fontSize", px(cs.fontSize), node);
      note("fontFamily", cs.fontFamily.split(",")[0].replace(/["']/g, "").trim(), node);
      note("fontWeight", Number(cs.fontWeight), node);
      if (cs.textTransform !== "none") note("textTransform", cs.textTransform, node);
      const c = toColour(cs.color);
      if (c && c.a > 0.05) note("color", hex(c), node);
    }
    if (!node.box) continue;
    if (node.box !== "media") {
      const radius = px(cs.borderTopLeftRadius);
      note("radius", radius >= height(node.b) / 2 - 1 && radius > 0 ? "pill" : radius, node);
      const bg = toColour(cs.backgroundColor);
      if (bg && bg.a > 0.05) note("background", hex(bg), node);
      const bw = borderWidths(cs);
      bw.forEach((w, k) => { if (w >= 1) { const c = toColour(cs[`border${sides[k]}Color`]); if (c) note("border", hex(c), node); } });
      if (cs.boxShadow !== "none") note("shadow", cs.boxShadow, node);
    }
    if ((node.tag === "SVG" || node.tag === "IMG") && width(node.b) <= 48 && height(node.b) <= 48) note("iconSize", `${Math.round(width(node.b))}x${Math.round(height(node.b))}`, node);
    if (node.control && height(node.b) <= 64) note("controlHeight", tenth(height(node.b)), node);
  }
  const summary = {};
  for (const [field, values] of Object.entries(census)) {
    summary[field] = [...countOf(values)].sort((a, b) => b[1] - a[1]).map(([value, count]) => [value, count]);
  }

  const tokenColours = [];
  const rootStyle = getComputedStyle(root);
  for (let k = 0; k < rootStyle.length; k++) {
    const name = rootStyle[k];
    if (!name.startsWith("--")) continue;
    let value = rootStyle.getPropertyValue(name).trim();
    if (/^[\d.]+\s+[\d.]+%\s+[\d.]+%$/.test(value)) value = `hsl(${value})`;
    if (value && CSS.supports("color", value)) {
      const c = toColour(value);
      if (c && c.a > 0) tokenColours.push(c);
    }
  }
  const isToken = (c) => tokenColours.some((t) => distance(t, c) <= 2);
  const drift = (field, closeEnough, describeValue) => {
    const list = summary[field].filter(([v]) => v !== "pill");
    for (const [rare, rareCount] of list) {
      if (rareCount > 2) continue;
      const partner = list.find(([v, c]) => v !== rare && c >= 3 && c > rareCount && closeEnough(rare, v));
      if (!partner) continue;
      const node = where.get(field + "=" + rare);
      if (field === "fontSize" && node.el.closest("code,pre,kbd,samp")) continue;
      add("warn", "drift", `${field} ${describeValue(rare)} is used ${rareCount}× next to ${describeValue(partner[0])} used ${partner[1]}×`, [node], [node.text || node.b]);
    }
  };
  drift("fontSize", (a, b) => Math.abs(a - b) <= 1, (v) => v + "px");
  drift("controlHeight", (a, b) => Math.abs(a - b) <= 2, (v) => v + "px");
  const fontSizes = summary.fontSize.map(([v]) => v);
  const radii = summary.radius.map(([v]) => v).filter((v) => v !== 0 && v !== "pill");
  if (fontSizes.length > 7) add("warn", "scale", `${fontSizes.length} font sizes on one page (${fontSizes.slice().sort((a, b) => a - b).join(", ")}px); a type scale has about 5–7`, [], []);
  if (radii.length > 4) add("warn", "scale", `${radii.length} corner radii on one page (${radii.slice().sort((a, b) => a - b).join(", ")}px); a radius scale has about 3–4`, [], []);
  for (const field of ["color", "background", "border"]) drift(field,(a, b) => !isToken(toColour(a)) && distance(toColour(a), toColour(b)) <= 12, (v) => v);

  if (tokenColours.length >= 4) {
    const used = new Map();
    for (const field of ["color", "background", "border"]) for (const [value, count] of summary[field]) used.set(value, (used.get(value) || 0) + count);
    for (const [value, count] of used) {
      const c = toColour(value);
      if (isToken(c)) continue;
      const node = where.get("color=" + value) || where.get("background=" + value) || where.get("border=" + value);
      add("warn", "off-token", `colour ${value} is used ${count}× but is not a colour token`, [node], [node.text || node.b]);
    }
  }

  const smells = [];
  const smell = (kind, message, list) => {
    if (!list.length) return;
    smells.push({ kind, count: list.length, message: message(list.length), ref: ref(list), elements: list.slice(0, 4).map((n) => describe(n.el)), boxes: list.slice(0, 12).map((n) => asList(n.text && !n.box ? n.text : n.b)) });
  };
  const visible = nodes.filter((n) => !n.hidden && n.tag !== "HTML" && (n.box || n.text));
  const textClip = (n) => /text/.test(n.cs.backgroundClip + n.cs.webkitBackgroundClip);
  smell("gradient-text", (k) => `${k} text element(s) filled with a gradient`, visible.filter((n) => textClip(n) && /gradient\(/.test(n.cs.backgroundImage)));
  smell("gradient", (k) => `${k} element(s) with a gradient background`, visible.filter((n) => !textClip(n) && /gradient\(/.test(n.cs.backgroundImage) && width(n.b) * height(n.b) >= 400));
  smell("glass", (k) => `${k} element(s) with a blurred see-through background`, visible.filter((n) => /blur/.test(n.cs.backdropFilter || n.cs.webkitBackdropFilter || "") && !["sticky", "fixed"].includes(n.cs.position) && width(n.b) * height(n.b) < 0.9 * innerWidth * innerHeight));
  const glows = (shadow) => {
    if (!shadow || shadow === "none") return false;
    return shadow.split(/,(?![^()]*\))/).some((part) => {
      const colour = coloursIn(part)[0];
      const lengths = (part.replace(/(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\([^()]*\)/g, "").match(/-?[\d.]+px/g) || []).map(px);
      return colour && saturated(colour, 0.3) && (lengths[2] || 0) >= 12;
    });
  };
  smell("glow", (k) => `${k} element(s) with a coloured glow`, visible.filter((n) => glows(n.cs.boxShadow) || glows(n.cs.textShadow)));
  const purple = (c) => { if (!saturated(c, 0.4)) return false; const h = hsl(c).h; return h >= 245 && h <= 295; };
  smell("purple", (k) => `${k} element(s) use the stock violet/indigo accent`, visible.filter((n) => {
    const colours = [...coloursIn(n.cs.backgroundImage), toColour(n.cs.backgroundColor)].filter(Boolean);
    return colours.some((c) => purple(c) && !isToken(c));
  }));
  const emoji = /(?![©®™←-⇿☀-☄♠-♧])\p{Extended_Pictographic}/u;
  smell("emoji", (k) => `${k} element(s) with emoji in UI text`, visible.filter((n) => n.own && emoji.test(n.own)));
  const surface = (n) => width(n.b) >= viewportWidth * 0.95 || height(n.b) >= viewportHeight * 0.9;
  const card = (n) => n.box && n.box !== "media" && n.box !== "field" && !n.control && !CELLS.has(n.tag) && width(n.b) >= 40 && height(n.b) >= 40 && !surface(n);
  const cardInCard = visible.filter((n) => {
    if (!card(n) || n.floating) return false;
    for (let p = nodes[n.parent]; p; p = nodes[p.parent]) if (card(p)) return true;
    return false;
  });
  smell("card-in-card", (k) => `${k} box(es) drawn inside another box`, cardInCard);
  const tintedFill = (n) => {
    const bg = toColour(n.cs.backgroundColor);
    return !!bg && bg.a > 0.05 && hsl(bg).s >= 0.2 && hsl(bg).l < 0.97 && hsl(bg).l > 0.08;
  };
  const pillShaped = (n) => n.box && height(n.b) <= 32 && px(n.cs.borderTopLeftRadius) >= height(n.b) / 2 - 1 && !!n.inner;
  smell("tinted-box", (k) => `${k} box(es) with a coloured fill around content`, visible.filter((n) => card(n) && tintedFill(n) && !n.el.closest("[role=alert],[role=status],[aria-live]")));
  const stripe = (n) => {
    const bw = borderWidths(n.cs);
    const sideStripe = (bw[3] >= 2 && bw[3] >= 2 * Math.max(bw[0], bw[1], bw[2])) || (bw[1] >= 2 && bw[1] >= 2 * Math.max(bw[0], bw[2], bw[3]));
    if (sideStripe && height(n.b) >= 16) return true;
    for (const which of ["::before", "::after"]) {
      const p = getComputedStyle(n.el, which);
      if (p.content === "none" || p.content === "normal" || p.position !== "absolute" || parseFloat(p.opacity) === 0 || p.visibility !== "visible") continue;
      const w = px(p.width), h = px(p.height);
      const c = toColour(p.backgroundColor);
      if (c && c.a > 0.2 && w > 0 && w <= 6 && h >= 16) return true;
    }
    return false;
  };
  smell("accent-stripe", (k) => `${k} box(es) with a coloured stripe on one side`, visible.filter((n) => n.box && !n.control && !CELLS.has(n.tag) && stripe(n)));
  smell("pills", (k) => `${k} decorative pill/badge label(s)`, visible.filter((n) => pillShaped(n) && !n.control && !inCell(n) && !n.el.closest("button,a,[role=button],[role=tab]")));
  const headings = visible.filter((n) => n.text && (/^H[1-3]$/.test(n.tag) || (px(n.cs.fontSize) >= 24 && Number(n.cs.fontWeight) >= 600)));
  smell("eyebrow", (k) => `${k} small upper-case label(s) above a heading`, visible.filter((n) => {
    if (!n.text || px(n.cs.fontSize) > 14 || headings.includes(n)) return false;
    const caps = n.cs.textTransform === "uppercase" || (n.own.length >= 3 && n.own === n.own.toUpperCase() && /[A-Z]/.test(n.own));
    if (!caps) return false;
    return headings.some((h) => h.text.y1 >= n.text.y2 - 1 && h.text.y1 - n.text.y2 <= 24 && Math.min(h.text.x2, n.text.x2) - Math.max(h.text.x1, n.text.x1) > 0);
  }));
  const muted = (n, h) => px(n.cs.fontSize) < px(h.cs.fontSize) && (toColour(n.cs.color) && toColour(h.cs.color) ? luminance(toColour(n.cs.color)) > luminance(toColour(h.cs.color)) + 0.02 || px(n.cs.fontSize) <= px(h.cs.fontSize) * 0.8 : true);
  const explained = headings.filter((h) => visible.some((n) => n.text && n !== h && n.words >= 4 && n.words <= 30 && muted(n, h) && n.text.y1 >= h.text.y2 - 1 && n.text.y1 - h.text.y2 <= 24 && Math.abs(n.text.x1 - h.text.x1) <= 4));
  if (explained.length >= 3) smell("subtitles", (k) => `${k} headings each followed by a helper sentence`, explained);
  const blurOf = (shadow) => Math.max(0, ...(shadow === "none" ? [] : shadow.split(/,(?![^()]*\))/).map((part) => (part.replace(/(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\([^()]*\)/g, "").match(/-?[\d.]+px/g) || []).map(px)[2] || 0)));
  smell("border-shadow", (k) => `${k} box(es) with a full border and a wide shadow`, visible.filter((n) => card(n) && !n.floating && borderWidths(n.cs).every((w) => w >= 1) && blurOf(n.cs.boxShadow) >= 16));
  const iconOnly = (n) => !!n.el.querySelector("svg,img") && !n.el.textContent.trim();
  smell("icon-tile", (k) => `${k} icon tile(s) next to a heading`, visible.filter((n) => {
    if (!n.box || n.box === "media" || n.control || !iconOnly(n)) return false;
    const w = width(n.b), h = height(n.b);
    if (w < 24 || w > 64 || Math.abs(w - h) > 2) return false;
    return headings.some((hd) => {
      const below = hd.text.y1 - n.b.y2 >= 0 && hd.text.y1 - n.b.y2 <= 24 && Math.min(hd.text.x2, n.b.x2) - Math.max(hd.text.x1, n.b.x1) > 0;
      const beside = hd.text.x1 - n.b.x2 >= 0 && hd.text.x1 - n.b.x2 <= 24 && Math.abs(centreY(hd.text) - centreY(n.b)) <= h / 2;
      return below || beside;
    });
  }));
  const gridCards = [];
  for (const parent of nodes) {
    const kids = parent.kids.map((i) => nodes[i]).filter((k) => !k.hidden && card(k));
    if (kids.length < 3) continue;
    const same = kids.filter((k) => Math.abs(width(k.b) - width(kids[0].b)) <= 2 && Math.abs(height(k.b) - height(kids[0].b)) <= 2 && k.el.querySelector("svg,img") && k.el.querySelector("h2,h3,h4,strong,b"));
    if (same.length >= 3 && same.length === kids.length) gridCards.push(...same);
  }
  smell("card-grid", (k) => `${k} identical cards, each with an icon and a heading`, gridCards);
  smell("native-tooltip", (k) => `${k} element(s) use the browser's title tooltip`, nodes.filter((n) => !n.hidden && n.el.hasAttribute("title") && !["ABBR", "IFRAME", "HTML", "LINK", "STYLE"].includes(n.tag) && n.el.getAttribute("title").trim()));
  const hueFamilies = new Set();
  for (const field of ["color", "background", "border"]) for (const [value] of summary[field]) {
    const c = toColour(value);
    if (saturated(c, 0.3) && c.a >= 0.5) hueFamilies.add(Math.round(hsl(c).h / 30) % 12);
  }
  if (hueFamilies.size >= 4) smells.push({ kind: "hues", count: hueFamilies.size, message: `colours from ${hueFamilies.size} hue families on one screen`, elements: [], boxes: [] });
  const strokeRatios = new Map();
  for (const n of visible) if (n.tag === "SVG" && width(n.b) <= 32) {
    const shape = n.el.querySelector("path,circle,line,polyline,rect");
    const box = n.el.viewBox && n.el.viewBox.baseVal && n.el.viewBox.baseVal.width;
    if (!shape || !box || getComputedStyle(shape).stroke === "none") continue;
    const ratio = Math.round((px(getComputedStyle(shape).strokeWidth) / box) * 1000) / 1000;
    if (ratio > 0 && !strokeRatios.has(ratio)) strokeRatios.set(ratio, n);
  }
  if (strokeRatios.size >= 2) smell("icon-sets", (k) => `icons from ${k} line weights (stroke ÷ viewBox: ${[...strokeRatios.keys()].join(", ")}), likely mixed icon sets`, [...strokeRatios.values()]);
  const STOCK = ["unlock", "seamless", "elevate", "supercharge", "empower", "revolutioni", "next-level", "next level", "cutting-edge", "cutting edge", "game-chang", "effortless", "all-in-one", "at your fingertips", "in seconds", "say goodbye", "look no further", "harness the power", "unleash", "world-class", "best-in-class", "state-of-the-art", "lorem ipsum", "transform your", "magic"];
  const pageText = (document.body ? document.body.innerText : "").toLowerCase();
  const stock = STOCK.filter((p) => pageText.includes(p));
  if (stock.length) smells.push({ kind: "stock-copy", count: stock.length, message: `stock marketing words: ${stock.join(", ")}`, elements: [], boxes: [] });

  const wordsOf = (el) => (el.innerText || "").trim().split(/\s+/).filter(Boolean).length;
  const PROSE = new Set(["P", "DD", "BLOCKQUOTE", "FIGCAPTION"]);
  const paragraphs = visible.filter((n) => n.text && !n.floating && !n.el.closest("table,button,a,nav,label,[role=button],[role=tab],[role=menuitem]") && (PROSE.has(n.tag) || (n.tag === "LI" && !n.el.querySelector("p")) || (!PROSE.has(nodes[n.parent] && nodes[n.parent].tag) && n.words >= 12 && !n.el.querySelector("p,div,li"))));
  paragraphs.forEach((n) => { n.prose = wordsOf(n.el); });
  const totalWords = visible.reduce((sum, n) => sum + (n.text ? n.words : 0), 0);
  const proseWords = paragraphs.reduce((sum, n) => sum + n.prose, 0);
  const tall = nodes.find((n) => !n.hidden && (n.tag === "ASIDE" || n.tag === "NAV") && height(n.b) >= viewportHeight * 0.6 && width(n.b) <= viewportWidth * 0.4);
  const docs = !!document.querySelector("article,[class*=prose],[class*=markdown]") && proseWords >= 0.5 * totalWords;
  const mode = settings.mode || (docs ? "docs" : tall || document.querySelector("table") || targets.length >= 12 ? "app" : "marketing");

  if (mode !== "docs") {
    const long = paragraphs.filter((n) => n.prose > 60);
    if (long.length) add("warn", "long-paragraph", `${long.length} paragraph(s) over 60 words, longest ${Math.max(...long.map((n) => n.prose))} words; cut the text or split it`, long.slice(0, 4), long.slice(0, 4).map((n) => n.text));
    const breakers = visible.filter((n) => !n.floating && ((MEDIA.has(n.tag) && width(n.b) >= 48 && height(n.b) >= 48) || n.control || n.box === "field" || n.tag === "TABLE" || (card(n) && !n.el.querySelector("p"))));
    const ordered = paragraphs.slice().sort((a, b) => a.text.y1 - b.text.y1);
    let run = null;
    let worst = null;
    for (const n of ordered) {
      const broken = run && breakers.some((k) => k.b.y1 < n.text.y1 && k.b.y2 > run.y2 && !k.el.contains(n.el));
      if (!run || broken) run = { y1: n.text.y1, y2: n.text.y2, list: [n] };
      else { run.y2 = Math.max(run.y2, n.text.y2); run.list.push(n); }
      if (!worst || run.y2 - run.y1 > worst.y2 - worst.y1) worst = { ...run, list: run.list.slice() };
    }
    if (worst && worst.y2 - worst.y1 > viewportHeight) add("warn", "wall-of-text", `${Math.round(worst.y2 - worst.y1)}px of prose (${tenth((worst.y2 - worst.y1) / viewportHeight)} screens) with no picture, control or table between`, worst.list.slice(0, 4), [{ x1: Math.min(...worst.list.map((n) => n.text.x1)), y1: worst.y1, x2: Math.max(...worst.list.map((n) => n.text.x2)), y2: worst.y2 }].map(asList));
    const pageHeight = Math.max(root.scrollHeight, viewportHeight);
    const heavy = [];
    for (let top = 0, k = 1; top < pageHeight; top += viewportHeight, k++) {
      const band = { x1: 0, y1: top, x2: viewportWidth, y2: top + viewportHeight };
      const bandArea = viewportWidth * Math.min(viewportHeight, pageHeight - top);
      let textArea = 0, mediaArea = 0;
      for (const n of visible) {
        if (n.fragments) for (const f of n.fragments) textArea += area(intersect(f, band));
        if (MEDIA.has(n.tag) && width(n.b) >= 48 && height(n.b) >= 48) mediaArea += area(intersect(n.b, band));
      }
      const bandProse = paragraphs.filter((n) => n.text.y1 >= top && n.text.y1 < top + viewportHeight).reduce((sum, n) => sum + n.prose, 0);
      if (mode === "marketing" && textArea / bandArea > 0.2 && mediaArea / bandArea < 0.1 && bandProse > 120) heavy.push(`screen ${k}: text ${Math.round((100 * textArea) / bandArea)}%, pictures ${Math.round((100 * mediaArea) / bandArea)}%, ${bandProse} words of prose`);
      if (mode === "app" && bandProse > 60) heavy.push(`screen ${k}: ${bandProse} words of explanation`);
    }
    if (heavy.length) add("warn", mode === "app" ? "chatty" : "text-heavy", mode === "app" ? `the screen explains itself in prose; ${heavy.join("; ")}` : `the page reads like a document; ${heavy.join("; ")}`, [], []);
  }

  const labelLimits = [["button", 4, (n) => n.tag === "BUTTON" || roleOf(n.el) === "button"], ["tab or menu item", 4, (n) => ["tab", "menuitem", "option"].includes(roleOf(n.el))], ["table header", 5, (n) => n.tag === "TH"], ["heading", 10, (n) => /^H[1-6]$/.test(n.tag)]];
  if (mode !== "docs") for (const [what, limit, test] of labelLimits) {
    const long = visible.filter((n) => test(n) && wordsOf(n.el) > limit);
    if (long.length) add("warn", "long-label", `${long.length} ${what} label(s) over ${limit} words, e.g. "${(long[0].el.innerText || "").trim().slice(0, 60)}"`, long.slice(0, 4), long.slice(0, 4).map((n) => n.b));
  }

  const STOP = new Set("a an and are as at be by for from has have here how in into is it its of on or our that the their this to us we what when where which with you your can will all any each more manage view see".split(" "));
  const contentWords = (text) => new Set(text.toLowerCase().match(/[a-z][a-z'-]+/g)?.map((w) => w.replace(/s$/, "")).filter((w) => !STOP.has(w)) || []);
  const helpers = headings.map((h) => [h, visible.find((n) => n.text && n !== h && n.words >= 3 && n.words <= 30 && muted(n, h) && n.text.y1 >= h.text.y2 - 1 && n.text.y1 - h.text.y2 <= 24 && Math.abs(n.text.x1 - h.text.x1) <= 4)]).filter(([, n]) => n);
  const restating = helpers.filter(([h, n]) => { const said = contentWords(h.el.innerText || ""); const extra = [...contentWords(n.own)]; return extra.length && extra.filter((w) => said.has(w)).length / extra.length >= 0.5; });
  if (restating.length) add("warn", "restates", `${restating.length} sentence(s) repeat the heading above them, e.g. "${restating[0][1].own.slice(0, 60)}"`, restating.slice(0, 4).map(([, n]) => n), restating.slice(0, 4).map(([, n]) => n.text));
  if (mode === "app") {
    const others = helpers.filter((pair) => !restating.includes(pair));
    smell("helper-text", (k) => `${k} helper sentence(s) under a heading, e.g. "${others[0][1].own.slice(0, 60)}"; keep one only if it helps the next action or prevents a mistake`, others.map(([, n]) => n));
  }
  const FILLER = ["just to confirm", "here you can", "here's", "this section", "this page", "allows you to", "lets you", "simply", "easily", "quickly", "please note", "note that", "in one place", "at a glance", "keep track of", "stay on top of", "everything you need", "feel free to", "don't worry", "make sure to", "get started by", "welcome to", "you can now"];
  const filler = FILLER.filter((p) => new RegExp(`(^|[^a-z])${p.replace(/'/g, "['’]")}([^a-z]|$)`).test(pageText));
  if (filler.length) smells.push({ kind: "filler", count: filler.length, message: `filler phrases: ${filler.join(", ")}`, elements: [], boxes: [] });

  const boxAncestor = (n) => { for (let p = nodes[n.parent]; p; p = nodes[p.parent]) if (p.box && p.tag !== "BODY" && p.tag !== "HTML") return p; return null; };
  const doubled = [];
  for (const n of visible) {
    if (!n.box || n.floating || CELLS.has(n.tag)) continue;
    const bw = borderWidths(n.cs);
    const p = boxAncestor(n);
    if (p && !CELLS.has(p.tag)) {
      const pw = borderWidths(p.cs);
      const gaps = [n.b.y1 - (p.b.y1 + pw[0]), p.b.x2 - pw[1] - n.b.x2, p.b.y2 - pw[2] - n.b.y2, n.b.x1 - (p.b.x1 + pw[3])];
      if ([0, 1, 2, 3].some((k) => bw[k] >= 1 && pw[k] >= 1 && Math.abs(gaps[k]) <= 1)) { doubled.push(n); continue; }
    }
    const next = n.parent >= 0 && nodes[n.parent].kids.map((i) => nodes[i]).find((k) => !k.hidden && k.b.y1 >= n.b.y2 - 1 && k.b.y1 - n.b.y2 <= 1 && Math.min(k.b.x2, n.b.x2) - Math.max(k.b.x1, n.b.x1) > 0);
    if (next && bw[2] >= 1 && borderWidths(next.cs)[0] >= 1) doubled.push(n);
  }
  if (doubled.length) add("warn", "double-border", `${doubled.length} border(s) touch another border and draw a double line`, doubled.slice(0, 4), doubled.slice(0, 4).map((n) => n.b));

  const tight = visible.filter((n) => n.box && n.box !== "field" && (n.control || (height(n.b) <= 40 && px(n.cs.borderTopLeftRadius) > 0)) && !iconButton(n) && n.inner && width(n.b) - height(n.b) > 4 && !CELLS.has(n.tag) && (px(n.cs.paddingLeft) + 1 < px(n.cs.paddingTop) || n.inner.x1 - n.b.x1 < 3 || n.b.x2 - n.inner.x2 < 3));
  if (tight.length) add("warn", "cramped-padding", `${tight.length} button(s) or badge(s) with less side padding than top padding, or text touching the edge`, tight.slice(0, 4), tight.slice(0, 4).map((n) => n.b));

  const bodyFamily = document.body ? getComputedStyle(document.body).fontFamily.split(",")[0].replace(/["']/g, "").trim() : "";
  const bodySize = document.body ? px(getComputedStyle(document.body).fontSize) : 16;
  const leaked = visible.filter((n) => (FIELDS.has(n.tag) || n.tag === "BUTTON") && !/mono|code|courier/i.test(n.cs.fontFamily) && (n.cs.fontFamily.split(",")[0].replace(/["']/g, "").trim() !== bodyFamily || (Math.abs(px(n.cs.fontSize) - 13.333) < 0.01 && Math.abs(bodySize - 13.333) >= 0.01)));
  if (leaked.length) add("warn", "control-font", `${leaked.length} control(s) keep the browser's form font (${leaked[0].cs.fontFamily.split(",")[0]} ${tenth(px(leaked[0].cs.fontSize))}px) and not the page font (${bodyFamily} ${tenth(bodySize)}px); set font: inherit`, leaked.slice(0, 4), leaked.slice(0, 4).map((n) => n.b));

  const distorted = visible.filter((n) => n.tag === "IMG" && n.el.naturalWidth > 0 && n.el.naturalHeight > 0 && n.cs.objectFit === "fill" && width(n.b) >= 16 && height(n.b) >= 16 && Math.abs(width(n.b) / height(n.b) / (n.el.naturalWidth / n.el.naturalHeight) - 1) > 0.03);
  if (distorted.length) add("fail", "image-distorted", `${distorted.length} image(s) stretched out of their aspect ratio; use object-fit or the real ratio`, distorted.slice(0, 4), distorted.slice(0, 4).map((n) => n.b));

  const choices = [];
  for (const label of document.querySelectorAll("label")) {
    const input = label.control || label.querySelector("input,[role=checkbox],[role=switch],[role=radio]");
    if (!input || !/checkbox|radio|switch/.test((input.type || "") + roleOf(input))) continue;
    const text = [...label.querySelectorAll("*"), label].map((el) => byElement.get(el)).filter((n) => n && n.lines && n.lines.length >= 2).sort((a, b) => b.words - a.words)[0];
    let mark = byElement.get(input);
    if (!mark || mark.hidden || area(mark.b) <= 4) mark = [...label.querySelectorAll("*")].map((el) => byElement.get(el)).find((n) => n && n.box && width(n.b) <= 28 && height(n.b) <= 28);
    if (!text || !mark) continue;
    if (Math.abs(centreY(mark.b) - centreY(text.first)) > 2 && Math.abs(centreY(mark.b) - centreY(text.text)) <= 2) choices.push(mark);
  }
  if (choices.length) add("warn", "choice-centre", `${choices.length} checkbox(es) centred on a label of 2 or more lines; align it with the first line`, choices.slice(0, 4), choices.slice(0, 4).map((n) => n.b));

  const proximity = [];
  for (const h of visible.filter((n) => /^H[1-6]$/.test(n.tag) && !n.floating)) {
    const kids = nodes[h.parent].kids.map((i) => nodes[i]).filter((k) => !k.hidden && !k.floating && (k.box || k.text || k.inner));
    const at = kids.indexOf(h);
    const prev = kids[at - 1], next = kids[at + 1];
    if (!prev || !next || prev.b.y2 > h.b.y1 + 1 || next.b.y1 < h.b.y2 - 1) continue;
    const above = h.b.y1 - prev.b.y2, below = next.b.y1 - h.b.y2;
    if (above + 1 < below) proximity.push([h, above, below]);
  }
  if (proximity.length) add("warn", "proximity", `${proximity.length} heading(s) closer to the content above than to their own content (e.g. ${tenth(proximity[0][1])}px above, ${tenth(proximity[0][2])}px below)`, proximity.slice(0, 4).map(([h]) => h), proximity.slice(0, 4).map(([h]) => h.b));

  const early = [];
  for (const n of truncated) {
    for (let p = nodes[n.parent], depth = 0; p && depth < 3; p = nodes[p.parent], depth++) {
      if (!/flex/.test(p.cs.display) || /column/.test(p.cs.flexDirection)) continue;
      const kids = p.kids.map((i) => nodes[i]).filter((k) => !k.hidden && !k.floating);
      const used = kids.reduce((sum, k) => sum + width(k.b), 0) + px(p.cs.columnGap) * Math.max(0, kids.length - 1);
      const room = p.el.clientWidth - px(p.cs.paddingLeft) - px(p.cs.paddingRight);
      if (room - used > 24) early.push(n);
      break;
    }
  }
  if (early.length) add("warn", "early-ellipsis", `${early.length} text(s) cut short with an ellipsis while the row has free space`, early.slice(0, 4), early.slice(0, 4).map((n) => n.text));

  const docHeight = Math.max(root.scrollHeight, viewportHeight);
  for (const bar of nodes.filter((n) => !n.hidden && n.cs.position === "fixed" && n.box && width(n.b) >= viewportWidth * 0.5 && n.b.y1 - offsetY >= viewportHeight * 0.65 && n.b.y2 - offsetY >= viewportHeight - 32)) {
    const barHeight = viewportHeight - (bar.b.y1 - offsetY);
    const hidden = visible.filter((n) => !n.floating && !bar.el.contains(n.el) && (n.control || n.text) && n.b.y2 > docHeight - barHeight + 2 && Math.min(n.b.x2, bar.b.x2) - Math.max(n.b.x1, bar.b.x1) > 0);
    if (hidden.length) add("fail", "covered-end", `a fixed bar ${Math.round(barHeight)}px tall covers ${hidden.length} element(s) even at the end of the page; add bottom padding`, hidden.slice(0, 4), hidden.slice(0, 4).map((n) => n.b));
  }

  const actionable = (el) => /^(A|BUTTON|LABEL|SUMMARY|SELECT|INPUT|OPTION|TEXTAREA)$/.test(el.tagName) || el.getAttribute("role") || el.hasAttribute("onclick") || el.hasAttribute("tabindex") || el.isContentEditable;
  const liars = visible.filter((n) => n.cs.cursor === "pointer" && !(nodes[n.parent] && nodes[n.parent].cs.cursor === "pointer") && !actionable(n.el) && !n.el.closest("a,button,label,summary,[role],[onclick],[tabindex]") && !n.el.querySelector("a,button,input,select,[role],[onclick],[tabindex]"));
  if (liars.length) add("warn", "cursor-lie", `${liars.length} element(s) show the pointer cursor but are not links or buttons; give them a role and keyboard access, or remove the pointer`, liars.slice(0, 4), liars.slice(0, 4).map((n) => n.b));
  const buttons = visible.filter((n) => n.tag === "BUTTON" && !n.el.disabled && n.el.getAttribute("aria-disabled") !== "true");
  const pointing = buttons.filter((n) => n.cs.cursor === "pointer");
  if (pointing.length && pointing.length < buttons.length) add("warn", "cursor-mixed", `${pointing.length} of ${buttons.length} buttons show the pointer cursor; choose one cursor for all buttons`, buttons.filter((n) => n.cs.cursor !== "pointer").slice(0, 4), buttons.filter((n) => n.cs.cursor !== "pointer").slice(0, 4).map((n) => n.b));
  const cursors = new Set(visible.map((n) => n.cs.cursor).filter((c) => !["auto", "default", "pointer", "text"].includes(c)));
  if (cursors.size >= 3 || [...cursors].some((c) => /url\(/.test(c))) smells.push({ kind: "cursor-zoo", count: cursors.size, message: `special cursors: ${[...cursors].map((c) => (/url\(/.test(c) ? "custom image" : c)).join(", ")}`, elements: [], boxes: [] });

  const order = { fail: 0, warn: 1 };
  findings.sort((a, b) => order[a.severity] - order[b.severity]);
  let fails = 0, warns = 0;
  for (const f of findings) f.id = f.severity === "fail" ? "F" + ++fails : "W" + ++warns;
  smells.forEach((s, k) => { s.id = "S" + (k + 1); });

  const contentEdges = [];
  const rightEdges = [];
  for (const it of items) {
    if (it.frame || inCell(it.node) || controlAround(it.node) || width(it.b) >= viewportWidth * 0.95) continue;
    if (it.kind === "text" && it.align === "l" && !inlineInText(it.node)) contentEdges.push(Math.round(it.b.x1));
    if (it.kind === "box" && width(it.b) >= viewportWidth * 0.25) { contentEdges.push(Math.round(it.b.x1)); rightEdges.push(Math.round(it.b.x2)); }
  }
  const header = nodes.find((n) => !n.hidden && (n.tag === "HEADER" || roleOf(n.el) === "banner") && !n.el.closest("article,section,main"));
  const sidebar = nodes.find((n) => !n.hidden && (n.tag === "ASIDE" || n.tag === "NAV") && height(n.b) >= viewportHeight * 0.6 && width(n.b) <= viewportWidth * 0.4 && n.b.x1 <= 1);
  const h1 = nodes.find((n) => n.tag === "H1" && !n.hidden);
  const layout = {
    contentLeft: modeOf(contentEdges),
    contentRight: modeOf(rightEdges),
    headerHeight: header ? tenth(height(header.b)) : null,
    sidebarWidth: sidebar ? tenth(width(sidebar.b)) : null,
    bodyFont: document.body ? `${getComputedStyle(document.body).fontSize} ${getComputedStyle(document.body).fontFamily.split(",")[0].replace(/["']/g, "")}` : null,
    h1: h1 ? `${h1.cs.fontSize} ${h1.cs.fontWeight}` : null,
    radius: (summary.radius.find(([v]) => v !== 0 && v !== "pill") || [null])[0],
    controlHeight: (summary.controlHeight[0] || [null])[0],
    iconSize: (summary.iconSize[0] || [null])[0],
  };

  const snapshot = nodes.filter((n) => !n.hidden && (n.box || n.text) && n.tag !== "HTML").map((n) => ({
    key: pathOf(n.el),
    name: describe(n.el),
    b: asList(n.b),
    style: [n.cs.fontSize, n.cs.fontWeight, n.cs.fontFamily.split(",")[0], n.cs.color, n.cs.backgroundColor, n.cs.borderTopLeftRadius, n.cs.padding, n.cs.borderWidth, n.cs.textTransform, n.cs.boxShadow].join("|"),
  }));

  if (frameMode !== "none") {
    const old = document.getElementById("__uicheck");
    if (old) old.remove();
    const layer = document.createElement("div");
    layer.id = "__uicheck";
    layer.style.cssText = `position:absolute;left:0;top:0;width:${root.scrollWidth}px;height:${root.scrollHeight}px;pointer-events:none;z-index:2147483647;`;
    const rect = (b, colour, thickness, dashed) => {
      const d = document.createElement("div");
      d.style.cssText = `position:absolute;left:${b[0]}px;top:${b[1]}px;width:${Math.max(b[2], 1)}px;height:${Math.max(b[3], 1)}px;outline:${thickness}px ${dashed ? "dashed" : "solid"} ${colour};outline-offset:-${thickness}px;`;
      layer.appendChild(d);
    };
    const line = (x, y1, y2, colour) => {
      const d = document.createElement("div");
      d.style.cssText = `position:absolute;left:${x}px;top:${y1}px;width:0;height:${Math.max(y2 - y1, 1)}px;border-left:1px dashed ${colour};`;
      layer.appendChild(d);
    };
    const tag = (b, text, colour) => {
      const d = document.createElement("div");
      d.textContent = text;
      d.style.cssText = `position:absolute;left:${b[0]}px;top:${Math.max(b[1] - 14, 0)}px;font:bold 10px/12px monospace;color:#fff;background:${colour};padding:0 3px;white-space:nowrap;`;
      layer.appendChild(d);
    };
    if (frameMode === "all") {
      for (const n of nodes) if (!n.hidden && n.tag !== "HTML" && n.tag !== "BODY" && width(n.b) >= 1 && height(n.b) >= 1) rect(asList(n.b), `hsla(${(n.depth * 47) % 360},85%,45%,0.75)`, 1, false);
    } else {
      for (const it of items) if (it.node.tag !== "BODY") rect(asList(it.b), it.kind === "text" ? "rgba(14,165,233,0.45)" : "rgba(100,116,139,0.45)", 1, false);
    }
    const colourOf = { fail: "#e11d48", warn: "#d97706" };
    for (const f of findings) {
      const colour = colourOf[f.severity];
      f.boxes.forEach((b) => rect(b, colour, 2, false));
      if (f.guide) for (const x of f.guide.at) line(x, f.guide.from - 8, f.guide.to + 8, colour);
      if (f.boxes.length) tag(f.boxes[0], f.id, colour);
    }
    for (const s of smells) {
      s.boxes.forEach((b) => rect(b, "#a21caf", 2, true));
      if (s.boxes.length) tag(s.boxes[0], s.id, "#a21caf");
    }
    root.appendChild(layer);
  }

  return {
    url: location.href,
    title: document.title,
    mode,
    width: viewportWidth,
    height: root.scrollHeight,
    findings,
    smells,
    census: summary,
    layout,
    snapshot,
  };
}
