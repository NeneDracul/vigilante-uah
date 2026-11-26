import hashlib
import os
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

# --- Configuración (viene de los secretos/variables de GitHub, nunca del código) ---
URL = os.environ.get("MONITOR_URL", "").strip()
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
if not (URL and TOKEN and CHAT_ID):
    sys.exit("Faltan secretos: MONITOR_URL, TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID")

EXTENSIONES = tuple(
    e.strip().lower()
    for e in (os.environ.get("MONITOR_EXTENSIONES") or ".pdf,.doc,.docx,.xls,.xlsx,.zip,.odt").split(",")
    if e.strip()
)

SNAP = "snapshot.txt"
# Firma de la URL: si cambia la URL (o el snapshot viene de otro usuario), se reinicia el estado
FIRMA = "#url:" + hashlib.sha256(URL.encode()).hexdigest()[:12]


def es_documento(href):
    return href.lower().split("?")[0].split("#")[0].endswith(EXTENSIONES)


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
    # Si el mensaje es largo, se envía en varios
    for i in range(0, len(msg), 3500):
        data = urllib.parse.urlencode({
            "chat_id": CHAT_ID,
            "text": msg[i:i + 3500],
            "disable_web_page_preview": "true",
        }).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data, timeout=30)


def guardar(lineas):
    with open(SNAP, "w", encoding="utf-8") as f:
        f.write("\n".join([FIRMA] + lineas))


req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
p = Extractor()
p.feed(html)
new = list(dict.fromkeys(p.out))  # sin duplicados, conserva el orden

old = None
if os.path.exists(SNAP):
    contenido = open(SNAP, encoding="utf-8").read().splitlines()
    if contenido and contenido[0] == FIRMA:
        old = contenido[1:]

if old is None:
    # Primera ejecución (o URL distinta): se guarda el estado actual
    guardar(new)
    msg = f"✅ Monitorización iniciada. {len(new)} documentos guardados."
    if new:
        msg += "\n\n" + "\n".join(new)
    else:
        msg += "\n\n⚠️ No he encontrado ningún documento. Revisa la URL o las extensiones."
    telegram(msg)
else:
    added = [l for l in new if l not in old]
    removed = [l for l in old if l not in new]
    if added or removed:
        msg = "🔔 La página ha cambiado:\n" + URL + "\n"
        if added:
            msg += "\n➕ NUEVO:\n" + "\n".join(added)
        if removed:
            msg += "\n\n➖ ELIMINADO:\n" + "\n".join(removed)
        telegram(msg)
        guardar(new)
