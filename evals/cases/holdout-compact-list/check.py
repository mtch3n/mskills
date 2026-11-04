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
  const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden"; };
  const textOf = (el) => (el.innerText || el.value || "").trim();
  const controls = ["button", "a", "input", "select", "textarea"];
  const boxLike = (el) => {
    if (controls.includes(el.tagName.toLowerCase()) || !visible(el)) return false;
    const r = el.getBoundingClientRect();
    if (r.height <= 64 || r.width <= 64) return false;
    const s = getComputedStyle(el);
    const sides = ["Top", "Right", "Bottom", "Left"].filter((d) => parseFloat(s[`border${d}Width`]) > 0 && s[`border${d}Style`] !== "none").length;
    return sides >= 3 || s.boxShadow !== "none";
  };
  const all = [...document.querySelectorAll("body *")].filter(visible);
  const nested = all.filter((el) => boxLike(el) && el.parentElement && (() => { for (let a = el.parentElement; a; a = a.parentElement) if (boxLike(a)) return true; return false; })());
  const shadows = all.filter((el) => { const r = el.getBoundingClientRect(); return r.width > 200 && r.height > 100 && getComputedStyle(el).boxShadow !== "none"; });
  const buttons = [...document.querySelectorAll("button, a")].filter(visible);
  const named = (name) => buttons.filter((el) => textOf(el) === name);
  const search = document.querySelector("input[type=search], input[placeholder*=Search i]");
  const toolbar = [...named("Export"), ...named("New lead"), ...(search ? [search] : [])].map((el) => Math.round(el.getBoundingClientRect().height));
  const footers = named("Call").map((button) => {
    const out = [];
    for (let a = button.parentElement; a && !/[^\\s]/.test(textOf(a).replace(/Call|Email/g, "")); a = a.parentElement) {
      const s = getComputedStyle(a);
      const painted = s.backgroundColor !== "rgba(0, 0, 0, 0)" && s.backgroundColor !== "transparent" && s.backgroundColor !== getComputedStyle(a.parentElement).backgroundColor;
      out.push(parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== "none" || painted);
    }
    return out.some(Boolean);
  });
  const h1 = document.querySelector("h1");
  const main = document.querySelector("main");
  const side = document.querySelector("aside");
  const sizes = all.filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())).map((el) => parseFloat(getComputedStyle(el).fontSize));
  return {
    text: document.body.innerText,
    scrollWidth: document.documentElement.scrollWidth,
    toolbar,
    buttonHeights: [...named("Call"), ...named("Email"), ...named("Export"), ...named("New lead")].map((el) => Math.round(el.getBoundingClientRect().height)),
    inset: h1 && main ? Math.round(h1.getBoundingClientRect().left - main.getBoundingClientRect().left) : null,
    shadows: shadows.length,
    nested: nested.length,
    painted: footers.filter(Boolean).length,
    footers: footers.length,
    sidebar: side ? Math.round(side.getBoundingClientRect().width) : null,
    smallest: Math.min(...sizes),
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
            page.goto((site / "leads.html").as_uri())
            out[width] = page.evaluate(FACTS)
            other = browser.new_page(viewport={"width": width, "height": 900})
            other.goto((site / "pipeline.html").as_uri())
            out[f"pipeline{width}"] = other.evaluate("() => ({ text: document.body.innerText, scrollWidth: document.documentElement.scrollWidth })")
        browser.close()
    return out


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1])))
