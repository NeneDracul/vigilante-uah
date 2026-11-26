import os, urllib.request, urllib.parse
from html.parser import HTMLParser
from urllib.parse import urljoin

URL = "https://www.uah.es/es/empleo-publico/PAS/convocatoria/CONVOCATORIA-DE-PRUEBAS-SELECTIVAS-PARA-EL-INGRESO-EN-LA-ESCALA-DE-TECNICOS-AUXILIARES-DE-INFORMATICA-GRUPO-C-SUBGRUPO-C1/"
SNAP = "snapshot.txt"
EXTENSIONES = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".odt")

def es_documento(href):
    h = href.lower().split("?")[0]
    return h.endswith(EXTENSIONES) or "/.galleries/" in h

class Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.href = None
        self.text = []
        self.out = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
        elif tag == "a" and self.href:
            if es_documento(self.href):
                texto = " ".join(" ".join(self.text).split())
                self.out.append(f"{texto} -> {urljoin(URL, self.href)}")
            self.href = None
    def handle_data(self, data):
        if not self.skip and self.href is not None:
            self.text.append(data)

def telegram(msg):
    # Envía en varios mensajes si es largo
    for i in range(0, len(msg), 3500):
        data = urllib.parse.urlencode({
            "chat_id": os.environ["TELEGRAM_CHAT_ID"],
            "text": msg[i:i+3500],
            "disable_web_page_preview": "true",
        }).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage",
            data, timeout=30)

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
p = Extractor()
p.feed(html)
new = list(dict.fromkeys(p.out))  # sin duplicados, conserva orden

if not new:
    telegram("⚠️ No he encontrado ningún documento en la página. ¿Ha cambiado la estructura?\n" + URL)
elif not os.path.exists(SNAP):
    open(SNAP, "w", encoding="utf-8").write("\n".join(new))
    telegram(f"✅ Monitorización iniciada. {len(new)} documentos guardados:\n\n" + "\n".join(new))
else:
    old = open(SNAP, encoding="utf-8").read().splitlines()
    added = [l for l in new if l not in old]
    removed = [l for l in old if l not in new]
    if added or removed:
        msg = "🔔 La página de la UAH ha cambiado:\n" + URL + "\n"
        if added:
            msg += "\n➕ NUEVO:\n" + "\n".join(added)
        if removed:
            msg += "\n\n➖ ELIMINADO:\n" + "\n".join(removed)
        telegram(msg)
        open(SNAP, "w", encoding="utf-8").write("\n".join(new))
