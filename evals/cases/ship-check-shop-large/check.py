#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
import functools
import http.server
import json
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

BOX = """
(selector) => [...document.querySelectorAll(selector)].map((el) => {
  const r = el.getBoundingClientRect();
  const range = document.createRange();
  range.selectNodeContents(el);
  const textWidth = range.getBoundingClientRect().width;
  return {text: (el.innerText || "").trim(), left: r.left, right: r.right, height: r.height,
          clipped: textWidth > r.width + 1, hidden: el.hidden || getComputedStyle(el).display === "none" || r.height === 0,
          margin: parseFloat(getComputedStyle(el).marginBottom), hit: el.classList.contains("hit") || !!el.closest(".hit"),
          label: el.closest("label") ? el.closest("label").getBoundingClientRect().height : 0};
})
"""


def serve(root):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def measure(browser, base, path, width, wait=2200):
    context = browser.new_context(viewport={"width": width, "height": 800}, device_scale_factor=1)
    context.add_cookies([{"name": "session", "value": "1", "url": base}])
    context.add_init_script("localStorage.setItem('consent', '1')")
    page = context.new_page()
    page.goto(base + path, wait_until="load")
    page.wait_for_timeout(wait)
    return context, page


def main():
    site = pathlib.Path(sys.argv[1]).resolve()
    server = serve(site)
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()

        promo = []
        for path in ("index.html?lang=de", "settings.html?lang=de", "p1.html?lang=de", "orders.html?lang=de"):
            context, page = measure(browser, base, path, 375)
            banners = page.evaluate(BOX, ".promo")
            width = page.evaluate("document.scrollingElement.scrollWidth")
            promo.append({"path": path, "width": width, "banners": banners})
            context.close()
        out["promo"] = promo

        context, page = measure(browser, base, "orders.html", 375)
        out["orders"] = {"width": page.evaluate("document.scrollingElement.scrollWidth"), "text": page.inner_text("body")}
        context.close()

        add = []
        for width in (375, 1280):
            context, page = measure(browser, base, "p3.html?lang=de", width, 600)
            add.append({"width": width, "buttons": page.evaluate(BOX, "button[data-t=add]")})
            context.close()
        out["add"] = add

        save = []
        for width in (375, 1280):
            context, page = measure(browser, base, "settings.html?lang=de", width, 600)
            save.append({"width": width, "buttons": page.evaluate(BOX, "button[data-t=save]"), "boxes": page.evaluate(BOX, "input[type=checkbox]")})
            context.close()
        out["settings"] = save

        context, page = measure(browser, base, "checkout.html", 375, 600)
        out["card"] = page.evaluate(BOX, "#card")
        out["fields"] = page.evaluate(BOX, "#pay .field")
        out["pay"] = page.evaluate(BOX, "button[data-t=pay]")
        page.fill("#card", "123")
        page.click("button[data-t=pay]")
        page.wait_for_timeout(300)
        out["cardError"] = page.evaluate(BOX, "#card-error")
        context.close()

        browser.close()
    server.shutdown()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
