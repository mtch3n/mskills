() => {
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "TEXTAREA", "OPTION", "TITLE"]);
  const TOKEN = /^[\w@./:\\+-]{3,}$/;
  const NUMBER = /^[\s$€£¥+\-−(]*\d[\d.,\s]*\)?\s*%?$/;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode: (t) => {
      const el = t.parentElement;
      if (!el || SKIP.has(el.tagName) || el.closest("svg,#__uicheck") || !t.data.trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const texts = [];
  while (walker.nextNode()) texts.push(walker.currentNode);
  let changed = 0;
  const chrome = "button,nav,label,th,summary,[role=button],[role=tab],[role=menuitem],[role=option],a";
  for (const t of texts) {
    const text = t.data.trim();
    const short = text.split(/\s+/).length <= 3;
    if (short && t.parentElement.closest(chrome) && !NUMBER.test(text) && !(TOKEN.test(text) && /[@./:\\_-]|\d/.test(text))) continue;
    let longer;
    if (NUMBER.test(text)) longer = text.replace(/\d/, (d) => d + "88888");
    else if (TOKEN.test(text) && /[@./:\\_-]|\d/.test(text)) longer = (text + "-").repeat(Math.ceil(64 / (text.length + 1))).slice(0, Math.max(64, text.length));
    else {
      const words = text.split(/\s+/);
      const extra = words.slice(0, Math.max(1, Math.ceil(words.length * 0.4))).join(" ");
      longer = words.length === 1 ? text + text.slice(0, Math.ceil(text.length * 0.6)) : text + " " + extra;
    }
    t.data = t.data.replace(text, longer);
    changed++;
  }
  for (const input of document.querySelectorAll("input:not([type]),input[type=text],input[type=email],input[type=search],input[type=url]")) {
    if (input.value) input.value = input.value + input.value;
    if (input.placeholder) input.placeholder = input.placeholder + " " + input.placeholder;
  }
  const style = document.createElement("style");
  style.textContent = "*:not(svg):not(svg *){line-height:1.5!important;letter-spacing:0.12em!important;word-spacing:0.16em!important}p{margin-bottom:2em!important}";
  document.head.appendChild(style);
  return changed;
}
