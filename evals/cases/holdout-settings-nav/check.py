#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

TITLES = ["Account", "Workspace", "Developer"]

FACTS = """
(titles) => {
  const side = document.querySelector("aside, nav");
  const box = (el) => { const node = [...el.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim()) || el; const range = document.createRange(); range.selectNodeContents(node); const r = range.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; };
  const look = (el) => { const s = getComputedStyle(el); return { weight: s.fontWeight, color: s.color, size: s.fontSize, transform: s.textTransform, cursor: s.cursor, background: s.backgroundColor }; };
  const own = (el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
  const heads = titles.map((t) => [...side.querySelectorAll("*")].filter((el) => own(el) === t || (el.innerText || "").trim() === t).pop() || null);
  const links = [...side.querySelectorAll("a")].filter((a) => a.getBoundingClientRect().height > 0);
  const hints = [...side.querySelectorAll("*")].filter((el) => /^⌘[A-Z]$/.test((el.innerText || "").trim()) && !el.querySelector("*")).map((el) => {
    const a = el.closest("a");
    const label = document.createRange();
    const text = a ? [...a.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim()) || a.firstElementChild : null;
    if (text) label.selectNodeContents(text);
    return { right: Math.round(el.getBoundingClientRect().right), left: Math.round(el.getBoundingClientRect().left), offset: text ? Math.round(el.getBoundingClientRect().left - label.getBoundingClientRect().right) : null };
  });
  const main = document.querySelector("main");
  return {
    titles: heads.map((el) => el && { ...box(el), ...look(el), clickable: !!el.closest("a, button, [role=button], summary"), text: (el.innerText || "").trim() }),
    links: links.map((a) => ({ ...box(a), ...look(a), text: (a.innerText || "").trim().split(/\\s+/).filter((w) => !/^⌘/.test(w)).join(" "), href: a.getAttribute("href") })),
    hints,
    scrollWidth: document.documentElement.scrollWidth,
    mainLook: main ? [...main.querySelectorAll("*")].map((el) => { const s = getComputedStyle(el); return [el.tagName, s.color, s.backgroundColor, s.fontSize, s.borderTopLeftRadius]; }) : [],
    mainText: main ? main.innerText : "",
  };
}
"""


def measure(site):
    site = pathlib.Path(site).resolve()
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (390, 1280):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto((site / "settings.html").as_uri())
            facts = page.evaluate(FACTS, TITLES)
            page.mouse.move(0, 0)
            hover = []
            for name in TITLES:
                target = page.locator("aside, nav").first.get_by_text(name, exact=True).last
                if not target.count():
                    continue
                before = target.evaluate("(el) => getComputedStyle(el).backgroundColor")
                target.hover()
                page.wait_for_timeout(250)
                hover.append(target.evaluate("(el) => getComputedStyle(el).backgroundColor") != before)
                page.mouse.move(0, 0)
                page.wait_for_timeout(250)
            facts["titleHover"] = hover
            out[width] = facts
        browser.close()
    return out


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1])))
