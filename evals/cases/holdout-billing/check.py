#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

FACTS = """
() => {
  const lum = (c) => {
    const [r, g, b] = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const background = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const bg = getComputedStyle(e).backgroundColor;
      const alpha = bg.match(/[\\d.]+/g)?.[3];
      if (bg !== "transparent" && alpha !== "0") return bg;
    }
    return "rgb(255, 255, 255)";
  };
  const ratio = (el) => { const a = lum(getComputedStyle(el).color), b = lum(background(el)); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
  const clippedBy = (el) => {
    const r = el.getBoundingClientRect();
    for (let a = el.parentElement; a; a = a.parentElement) {
      const o = getComputedStyle(a);
      if (/(auto|scroll)/.test(o.overflowX + o.overflowY)) return null;
      if (/(hidden|clip)/.test(o.overflowX + o.overflowY)) {
        const b = a.getBoundingClientRect();
        if (r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1) return a.tagName;
      }
    }
    return null;
  };
  const textOf = (el) => (el.innerText || "").trim();
  const invoices = [...document.querySelectorAll("td, th, a, span, div, p")].filter((el) => /^INV-\\d{4}-\\d{6}-NORTHWIND-EU$/.test(textOf(el)) && !el.querySelector("*"));
  const cells = [...document.querySelectorAll("td, th")].filter((el) => textOf(el) && el.getClientRects().length);
  const planButtons = [...document.querySelectorAll("button, a")].filter((el) => /^(Choose plan|Current plan)$/.test(textOf(el)));
  const dueCells = [...document.querySelectorAll("tbody tr")].map((tr) => [...tr.children].filter((td) => /^[A-Z][a-z]{2} \\d{1,2}, 2026$/.test(textOf(td)))[1]).filter(Boolean);
  return {
    scrollWidth: document.documentElement.scrollWidth,
    cells: cells.filter((el) => el.scrollWidth > el.clientWidth + 1 || clippedBy(el)).map((el) => textOf(el)),
    invoices: invoices.map((el) => ({ text: textOf(el), cut: el.scrollWidth > el.clientWidth + 1, clippedBy: clippedBy(el), right: el.getBoundingClientRect().right })),
    planButtons: planButtons.map((el) => { const r = el.getBoundingClientRect(); return { text: textOf(el), bottom: Math.round(r.bottom), top: Math.round(r.top), radius: getComputedStyle(el).borderTopLeftRadius, height: Math.round(r.height) }; }),
    dueContrast: dueCells.map((el) => Math.round(ratio(el) * 100) / 100),
    pageText: document.body.innerText,
    amounts: (document.body.innerText.match(/\\$24\\.00/g) || []).length,
  };
}
"""

MENU = """
() => {
  const items = [...document.querySelectorAll("[role=menuitem]")].filter((el) => el.getClientRects().length && getComputedStyle(el).visibility !== "hidden");
  return items.map((el) => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    const inside = x >= 0 && y >= 0 && x <= innerWidth && y <= innerHeight;
    const hit = inside ? document.elementFromPoint(x, y) : null;
    return { text: (el.innerText || "").trim(), reachable: !!hit && (hit === el || el.contains(hit)) };
  });
}
"""

GEOMETRY = """
() => [...document.querySelectorAll("main *, header *")].map((el) => {
  const r = el.getBoundingClientRect();
  const s = getComputedStyle(el);
  return [el.tagName, Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height), s.color, s.backgroundColor, s.borderTopLeftRadius, s.fontSize];
})
"""


def measure(site):
    site = pathlib.Path(site).resolve()
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (390, 1280):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto((site / "billing.html").as_uri())
            facts = page.evaluate(FACTS)
            triggers = page.locator("[aria-haspopup=menu]")
            menus = []
            if triggers.count():
                last = triggers.nth(triggers.count() - 1)
                last.scroll_into_view_if_needed()
                last.click()
                page.wait_for_timeout(200)
                menus = page.evaluate(MENU)
            facts["menu"] = menus
            page.goto((site / "billing.html").as_uri())
            facts["header"] = page.evaluate("() => [...document.querySelectorAll('header, header *')].map((el) => { const r = el.getBoundingClientRect(); return [el.tagName, Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; })")
            account = browser.new_page(viewport={"width": width, "height": 900})
            account.goto((site / "account.html").as_uri())
            facts["account"] = account.evaluate(GEOMETRY)
            out[width] = facts
        browser.close()
    return out


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1])))
