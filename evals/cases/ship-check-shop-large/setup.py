import pathlib
import uuid

site = pathlib.Path("site")
name = f"serve_{uuid.uuid4().hex[:8]}.py"
pathlib.Path("server.py").rename(name)
readme = pathlib.Path("README.md")
readme.write_text(readme.read_text().replace("server.py", name))

common = site / "common.js"
text = common.read_text()
text = text.replace(
    'en: { save: "Save changes", pay: "Pay", cardError: "Enter the full card number." },',
    'en: { save: "Save changes", pay: "Pay", cardError: "Enter the full card number.", add: "Add to cart", promo: "Free shipping over $50" },',
)
text = text.replace(
    'de: { save: "Benachrichtigungseinstellungen speichern", pay: "Bezahlen", cardError: "Geben Sie die vollständige Kartennummer ein." },',
    'de: { save: "Benachrichtigungseinstellungen speichern", pay: "Bezahlen", cardError: "Geben Sie die vollständige Kartennummer ein.", add: "In den Warenkorb legen", promo: "Kostenloser Versand für alle Bestellungen über 50 Euro bis zum Jahresende" },',
)
text += '''function promo() {
  setTimeout(() => {
    const banner = document.createElement("span");
    banner.className = "promo";
    banner.textContent = t("promo");
    document.querySelector("header").appendChild(banner);
  }, 1500);
}
document.addEventListener("DOMContentLoaded", promo);
'''
common.write_text(text)

tokens = site / "tokens.css"
tokens.write_text(tokens.read_text() + ".promo { margin-left: auto; padding: 0 var(--space-2); border-radius: var(--radius); background: #fff4d6; white-space: nowrap; }\n")

nav = '<header><a href="index.html">Shop</a><a href="settings.html">Settings</a><a href="checkout.html">Checkout</a><a href="billing.html">Billing</a><a href="account.html">Account</a></header>'
nav_new = nav.replace('<a href="account.html">Account</a>', '<a href="account.html">Account</a><a href="orders.html">Orders</a>')
for page in site.glob("*.html"):
    page.write_text(page.read_text().replace(nav, nav_new))

(site / "product.css").write_text(
    ".product { display: grid; grid-template-columns: 1fr; gap: var(--space-3); }\n"
    ".buy { width: 140px; }\n"
    ".buy .btn { width: 100%; height: auto; min-height: 32px; padding: var(--space-1) var(--space-3); }\n"
)
products = ["Kettle", "Teapot", "Mug", "Grinder", "Scale", "Filter", "Dripper", "Carafe", "Tin", "Tray", "Spoon", "Cup", "Saucer", "Whisk"]
cards = []
for index, product in enumerate(products, start=1):
    cards.append(f'<li><a href="p{index}.html">{product}</a></li>')
    (site / f"p{index}.html").write_text(
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{product}</title>\n'
        '<link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="product.css">\n'
        f'<script src="common.js"></script></head>\n<body>{nav_new}\n<main>\n'
        f'<div class="product"><h1>{product}</h1><p>{product} for the home kitchen.</p><p class="price">${10 + index * 3}.00</p>\n'
        '<div class="buy"><button class="btn" data-t="add"></button></div></div>\n'
        '</main>\n<script>localize(); consent();</script>\n</body></html>\n'
    )
index = site / "index.html"
index.write_text(index.read_text().replace("</main>", "<ul class=\"catalog\">" + "".join(cards) + "</ul>\n</main>"))

rows = [("ORD-2026-10-004812", "Oct 18, 2026", "Kettle, Mug ×2", "Delivered", "$46.00", "DHL 00340434161234567890")]
rows += [(f"ORD-2026-10-00{4700 + n}", f"Oct {n + 1}, 2026", "Filter ×4", "Delivered", "$12.00", f"DHL 0034043416123456{7800 + n}") for n in range(6)]
data = ",\n".join("  " + str(list(row)).replace("'", '"') for row in rows)
(site / "orders.html").write_text(
    '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Orders</title>\n'
    '<link rel="stylesheet" href="tokens.css">\n<style>\n.orders { border-collapse: collapse; }\n.orders td, .orders th { padding: var(--space-2); border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }\n</style>\n'
    f'<script src="common.js"></script></head>\n<body>{nav_new}\n<main>\n<script>requireSession();</script><h1>Orders</h1>\n'
    '<table class="orders"><thead><tr><th>Order</th><th>Date</th><th>Items</th><th>Status</th><th>Total</th><th>Tracking</th></tr></thead><tbody id="rows"></tbody></table>\n'
    f'<script>\nconst ORDERS = [\n{data}\n];\n'
    'setTimeout(() => {\n  document.getElementById("rows").innerHTML = ORDERS.map((row) => "<tr>" + row.map((cell) => "<td>" + cell + "</td>").join("") + "</tr>").join("");\n}, 800);\n'
    '</script>\n</main>\n<script>localize(); consent();</script>\n</body></html>\n'
)

pathlib.Path("CHANGES.md").write_text(
    "# Unreleased\n\n"
    "- Settings: new save bar and notification toggles (`site/settings.html`).\n"
    "- Checkout: new payment form (`site/checkout.html`).\n"
    "- Header: a promo banner on every page (`site/common.js`, `site/tokens.css`).\n"
    "- Orders: a new order history page (`site/orders.html`).\n"
    "- Product pages: 14 new pages with an Add to cart button (`site/p1.html` to `site/p14.html`, `site/product.css`).\n"
)
