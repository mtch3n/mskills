function requireSession() {
  if (!document.cookie.includes("session=")) {
    location.replace("login.html?next=" + encodeURIComponent(location.pathname));
  }
}
function consent() {
  if (localStorage.getItem("consent")) return;
  setTimeout(showConsent, 1200);
}
function showConsent() {
  const box = document.createElement("div");
  box.id = "consent";
  box.innerHTML = '<div><p>We use cookies to run the shop.</p><button class="btn" id="consent-ok">OK</button></div>';
  document.body.appendChild(box);
  document.getElementById("consent-ok").onclick = () => { localStorage.setItem("consent", "1"); box.remove(); };
}
const STRINGS = {
  en: { save: "Save changes", pay: "Pay", cardError: "Enter the full card number." },
  de: { save: "Benachrichtigungseinstellungen speichern", pay: "Bezahlen", cardError: "Geben Sie die vollständige Kartennummer ein." },
};
function t(key) {
  const lang = new URLSearchParams(location.search).get("lang") === "de" ? "de" : "en";
  return STRINGS[lang][key];
}
function localize() {
  document.querySelectorAll("[data-t]").forEach((node) => { node.textContent = t(node.dataset.t); });
}
const FORM = { cardDigits: 19, charWidth: 22 };
