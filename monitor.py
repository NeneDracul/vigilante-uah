import os, urllib.request, urllib.parse, difflib
from html.parser import HTMLParser

URL = "https://www.uah.es/es/empleo-publico/PAS/convocatoria/CONVOCATORIA-DE-PRUEBAS-SELECTIVAS-PARA-EL-INGRESO-EN-LA-ESCALA-DE-TECNICOS-AUXILIARES-DE-INFORMATICA-GRUPO-C-SUBGRUPO-C1/"
SNAP = "snapshot.txt"

class Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.out = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.out.append(f"[enlace] {href}")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            t = " ".join(data.split())
            if t:
                self.out.append(t)

def telegram(msg):
    data = urllib.parse.urlencode({
        "chat_id": os.environ["TELEGRAM_CHAT_ID"],
        "text": msg[:4000],
        "disable_web_page_preview": "true",
    }).encode()
    urllib.request.urlopen(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage", data, timeout=30)

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
p = Extractor()
p.feed(html)
new = p.out

if not os.path.exists(SNAP):
    open(SNAP, "w", encoding="utf-8").write("\n".join(new))
    telegram("✅ Monitorización iniciada. Estado actual guardado.")
else:
    old = open(SNAP, encoding="utf-8").read().splitlines()
    if old != new:
        diff = [l for l in difflib.unified_diff(old, new, lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        telegram("🔔 La página de la UAH ha cambiado:\n" + URL + "\n\n" + "\n".join(diff))
        open(SNAP, "w", encoding="utf-8").write("\n".join(new))
