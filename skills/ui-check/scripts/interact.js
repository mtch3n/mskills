() => {
  document.getElementById('__uicheck')?.remove();
  document.activeElement?.blur();
  const fields = ['outline-style', 'outline-width', 'outline-color', 'box-shadow', 'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color', 'background-color', 'color', 'text-decoration'];
  const paint = el => [null, '::before', '::after'].map(pseudo => {
    const style = getComputedStyle(el, pseudo);
    if (pseudo && (style.content === 'none' || style.content === 'normal')) return null;
    return fields.map(field => style.getPropertyValue(field));
  });
  const baseline = new Map([...document.querySelectorAll('*')].map(el => [el, JSON.stringify(paint(el))]));
  const pinned = el => { for (let node = el; node; node = node.parentElement) if (['fixed', 'sticky'].includes(getComputedStyle(node).position)) return true; return false; };
  const box = el => {
    const r = el.getBoundingClientRect();
    if (pinned(el)) return [r.x, r.y, r.width, r.height];
    let x = r.x + scrollX, y = r.y + scrollY;
    for (let parent = el.parentElement; parent; parent = parent.parentElement) {
      if (parent !== document.body && parent !== document.documentElement) {
        x += parent.scrollLeft;
        y += parent.scrollTop;
      }
    }
    return [x, y, r.width, r.height];
  };
  const snapshot = () => new Map([...document.querySelectorAll('*')].map(el => [el, box(el)]));
  const shifted = (el, before) => [el, ...el.parentElement.children].some(node => {
    const was = before.get(node), now = box(node);
    return was && now.some((value, i) => (node === el || i < 2) && Math.abs(value - was[i]) > 1);
  });
  const groups = new Map();
  const add = (el, severity, kind, message) => {
    if (!groups.has(kind)) groups.set(kind, {severity, kind, message, nodes: new Set(), elements: [], boxes: []});
    const group = groups.get(kind);
    if (group.nodes.has(el)) return;
    group.nodes.add(el);
    if (group.elements.length < 4) {
      group.elements.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + ' ' + (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 60));
      const r = el.getBoundingClientRect();
      group.boxes.push([r.x + scrollX, r.y + scrollY, r.width, r.height]);
    }
  };
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const context = canvas.getContext('2d', {willReadFrequently: true});
  const opaque = color => {
    context.clearRect(0, 0, 1, 1);
    context.fillStyle = color;
    context.fillRect(0, 0, 1, 1);
    return context.getImageData(0, 0, 1, 1).data[3] > 0;
  };
  let first;
  return {
    snapshot,
    focus(before) {
      const el = document.activeElement;
      if (!el || el === document.body || el === document.documentElement || el === first) return false;
      first ||= el;
      const style = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (r.width * r.height <= 4 || style.opacity === '0' || /inset\((50|100)%/.test(style.clipPath)) return true;
      const outline = !['none', 'hidden'].includes(style.outlineStyle) && parseFloat(style.outlineWidth) > 0 && opaque(style.outlineColor);
      const changed = node => node && baseline.get(node) !== JSON.stringify(paint(node));
      const restyled = changed(el) && JSON.stringify(paint(el).map(p => p && p.slice(3))) !== JSON.stringify(JSON.parse(baseline.get(el)).map(p => p && p.slice(3)));
      const other = restyled || changed(el.parentElement) || changed(el.parentElement?.parentElement);
      if (!outline && !changed(el) && !other)
        add(el, 'fail', 'focus-invisible', 'No visible focus style');
      if (outline && !other) {
        const extent = parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset);
        for (let parent = el.parentElement; parent; parent = parent.parentElement) {
          const s = getComputedStyle(parent), p = parent.getBoundingClientRect();
          const left = p.left + parent.clientLeft, top = p.top + parent.clientTop;
          if ((s.overflowX !== 'visible' && (left - (r.left - extent) > 1 || r.right + extent - left - parent.clientWidth > 1)) ||
              (s.overflowY !== 'visible' && (top - (r.top - extent) > 1 || r.bottom + extent - top - parent.clientHeight > 1))) {
            add(el, 'fail', 'focus-clipped', 'Focus outline is clipped by an ancestor');
            break;
          }
        }
      }
      const points = [[.5, .5], [.1, .1], [.9, .1], [.1, .9], [.9, .9]];
      const covered = points.filter(([x, y]) => {
        const hits = document.elementsFromPoint(r.left + r.width * x, r.top + r.height * y);
        for (const hit of hits) {
          if (hit === el || el.contains(hit)) return false;
          if (hit.contains(el)) continue;
          for (let node = hit; node; node = node.parentElement) {
            if (!node.contains(el) && ['fixed', 'sticky'].includes(getComputedStyle(node).position)) return true;
          }
          return false;
        }
        return false;
      }).length;
      if (covered > 2) add(el, 'fail', 'focus-covered', 'Fixed or sticky content covers most focus points');
      if (shifted(el, before)) add(el, 'warn', 'focus-shift', 'Focus moves or resizes the control or moves its siblings');
      return true;
    },
    hover(el, before) {
      if (shifted(el, before)) add(el, 'warn', 'hover-shift', 'Hover moves or resizes the control or moves its siblings');
    },
    mark() {
      for (const el of document.querySelectorAll('*')) el.__uicheckSeen = el.getClientRects().length > 0 && getComputedStyle(el).visibility === 'visible';
    },
    popups() {
      const shown = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility === 'visible' && parseFloat(getComputedStyle(el).opacity) > 0;
      const floating = el => ['menu', 'listbox', 'dialog', 'alertdialog', 'tooltip', 'tree', 'grid'].includes(el.getAttribute('role')) || el.tagName === 'DIALOG' || ['fixed', 'absolute'].includes(getComputedStyle(el).position);
      const semantic = el => ['menu', 'listbox', 'dialog', 'alertdialog', 'tooltip', 'tree', 'grid'].includes(el.getAttribute('role')) || el.tagName === 'DIALOG';
      const painted = el => { const s = getComputedStyle(el); return opaque(s.backgroundColor) || parseFloat(s.borderTopWidth) > 0 || s.boxShadow !== 'none'; };
      const backdrop = el => { const r = el.getBoundingClientRect(); return r.width >= innerWidth * 0.9 && r.height >= innerHeight * 0.9 && !/dialog/.test(el.getAttribute('role') || '') && el.tagName !== 'DIALOG'; };
      const found = [...document.querySelectorAll('*')].filter(el => !el.__uicheckSeen && shown(el) && floating(el) && !backdrop(el) && (semantic(el) || painted(el)) && el.getBoundingClientRect().width * el.getBoundingClientRect().height >= 400);
      const popups = found.filter(el => !found.some(other => other !== el && other.contains(el)));
      for (const el of popups) {
        const r = el.getBoundingClientRect();
        let view = {left: 0, top: 0, right: innerWidth, bottom: innerHeight};
        for (let parent = el.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
          const s = getComputedStyle(parent);
          if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
          const position = getComputedStyle(el).position, block = el.offsetParent;
          if (position === 'fixed' && !block) continue;
          if (position === 'absolute' && block && parent !== block && !parent.contains(block)) continue;
          const p = parent.getBoundingClientRect();
          view = {left: Math.max(view.left, s.overflowX === 'visible' ? -1e9 : p.left), top: Math.max(view.top, s.overflowY === 'visible' ? -1e9 : p.top), right: Math.min(view.right, s.overflowX === 'visible' ? 1e9 : p.right), bottom: Math.min(view.bottom, s.overflowY === 'visible' ? 1e9 : p.bottom)};
        }
        const seen = Math.max(0, Math.min(r.right, view.right) - Math.max(r.left, view.left)) * Math.max(0, Math.min(r.bottom, view.bottom) - Math.max(r.top, view.top));
        const dialog = el.tagName === 'DIALOG' || /dialog/.test(el.getAttribute('role') || '');
        const scrolls = node => [node, ...node.querySelectorAll('*')].some(n => /auto|scroll/.test(getComputedStyle(n).overflowY) && n.scrollHeight > n.clientHeight + 1);
        if (dialog && (r.bottom > innerHeight + 1 || r.top < -1) && !scrolls(el)) add(el, 'fail', 'dialog-unreachable', 'Dialog is taller than the screen and does not scroll, so part of it cannot be reached');
        else if (seen < 0.98 * r.width * r.height) add(el, 'fail', 'popup-clipped', 'Open menu or popup is cut off by its container or the screen');
        const inset = 6;
        const points = [[r.left + r.width / 2, r.top + r.height / 2], [r.left + inset, r.top + inset], [r.right - inset, r.top + inset], [r.left + inset, r.bottom - inset], [r.right - inset, r.bottom - inset]].filter(([x, y]) => x >= 0 && y >= 0 && x < innerWidth && y < innerHeight);
        const covered = points.filter(([x, y]) => { const hit = document.elementFromPoint(x, y); return hit && !el.contains(hit) && !hit.contains(el); }).length;
        if (covered >= 2) add(el, 'fail', 'popup-covered', 'Open menu or popup is painted under other content');
      }
      return popups.length;
    },
    findings() {
      return [...groups.values()].map(({nodes, ...finding}) => ({...finding, count: nodes.size}));
    }
  };
}
