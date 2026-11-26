import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def env(nombre, defecto=""):
    return (os.environ.get(nombre) or defecto).strip()


# --- Configuración (viene de los secretos/variables de GitHub, nunca del código) ---
URL = env("MONITOR_URL")
TOKEN = env("TELEGRAM_TOKEN")
CHAT_ID = env("TELEGRAM_CHAT_ID")
if not (URL and TOKEN and CHAT_ID):
    sys.exit("Faltan secretos: MONITOR_URL, TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID")

MODO = env("MONITOR_MODO", "todo").lower()  # todo | texto | documentos
if MODO not in ("todo", "texto", "documentos"):
    sys.exit("MONITOR_MODO debe ser: todo, texto o documentos")

SELECTOR = env("MONITOR_SELECTOR")  # zona a vigilar (selector CSS)
EXCLUIR = env("MONITOR_EXCLUIR")  # elementos a ignorar (selector CSS)
IGNORAR_TXT = env("MONITOR_IGNORAR")  # líneas a ignorar (expresión regular)
OCULTAR = env("MONITOR_OCULTAR_SNAPSHOT", "no").lower() in ("si", "sí", "yes", "true", "1")
EXTENSIONES = tuple(
    e.strip().lower()
    for e in env("MONITOR_EXTENSIONES", ".pdf,.doc,.docx,.xls,.xlsx,.zip,.odt").split(",")
    if e.strip()
)

try:
    IGNORAR = re.compile(IGNORAR_TXT, re.IGNORECASE) if IGNORAR_TXT else None
except re.error as e:
    sys.exit(f"MONITOR_IGNORAR no es una expresión regular válida: {e}")

SNAP = "snapshot.txt"
ZONAS_POR_DEFECTO = ["main", "[role=main]", "#contenido", "#content", "article"]
BLOQUES = [
    "p", "div", "li", "ul", "ol", "dl", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "tr", "td", "th", "caption", "section", "article", "main", "header", "footer",
    "aside", "nav", "form", "fieldset", "blockquote", "pre", "figure", "figcaption",
    "details", "summary",
]
MAX_CHARS = 3500
MAX_MENSAJES = 8

# Firma de la configuración: si cambia la URL o cualquier ajuste (o el snapshot viene
# de otro usuario), el estado se reinicia en vez de comparar contra datos que no valen.
_config = json.dumps(
    [URL, MODO, SELECTOR, EXCLUIR, IGNORAR_TXT, list(EXTENSIONES), OCULTAR], ensure_ascii=False
)
FIRMA = "#cfg:" + hashlib.sha256(_config.encode()).hexdigest()[:12]


# --- Utilidades ---
def telegram(msg):
    partes, actual = [], ""
    for linea in msg.splitlines():
        linea = linea[:MAX_CHARS]
        if actual and len(actual) + len(linea) + 1 > MAX_CHARS:
            partes.append(actual)
            actual = ""
        actual += linea + "\n"
    if actual.strip():
        partes.append(actual)
    if len(partes) > MAX_MENSAJES:
        partes = partes[:MAX_MENSAJES]
        partes[-1] += "\n… (mensaje recortado)"
    for i, parte in enumerate(partes):
        if i:
            time.sleep(1)
        data = urllib.parse.urlencode({
            "chat_id": CHAT_ID,
            "text": parte,
            "disable_web_page_preview": "true",
        }).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data, timeout=30)


def es_documento(href):
    return href.lower().split("?")[0].split("#")[0].endswith(EXTENSIONES)


def clave(valor):
    if OCULTAR:
        return "#" + hashlib.sha256(valor.encode()).hexdigest()[:16]
    return valor


def quitar(elementos):
    for t in elementos:
        if not t.decomposed:
            t.decompose()


def seleccionar(soup, selector):
    try:
        return soup.select(selector)
    except Exception as e:
        sys.exit(f"Selector CSS no válido ({selector}): {e}")


def texto_de(zona):
    for br in zona.find_all("br"):
        br.replace_with("\n")
    for b in zona.find_all(BLOQUES):
        b.insert_before("\n")
        b.insert_after("\n")
    return zona.get_text()


def lineas_de(zonas):
    out = []
    for z in zonas:
        for linea in texto_de(z).splitlines():
            linea = " ".join(linea.split())
            if linea and not (IGNORAR and IGNORAR.search(linea)):
                out.append(linea)
    return list(dict.fromkeys(out))


def documentos_de(zonas):
    out = []
    for z in zonas:
        for a in z.find_all("a", href=True):
            href = a["href"].strip()
            if es_documento(href):
                texto = " ".join(a.get_text(" ").split())
                item = f"{texto} -> {urljoin(URL, href)}"
                if not (IGNORAR and IGNORAR.search(item)):
                    out.append(item)
    return list(dict.fromkeys(out))


def guardar(entradas):
    lineas = [FIRMA] + [f"{tipo}\t{k}" for (tipo, k) in entradas]
    with open(SNAP, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


# --- Descarga y análisis ---
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    html = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")

soup = BeautifulSoup(html, "html.parser")
quitar(soup(["script", "style", "noscript", "template", "svg", "iframe"]))
if EXCLUIR:
    quitar(seleccionar(soup, EXCLUIR))

aviso_zona = ""
if SELECTOR:
    zonas, zona_txt = seleccionar(soup, SELECTOR), SELECTOR
elif MODO == "documentos":
    zonas, zona_txt = [soup], "página completa"
else:
    zonas, zona_txt = [], ""
    for s in ZONAS_POR_DEFECTO:
        zonas = seleccionar(soup, s)
        if zonas:
            zona_txt = s
            break
    if not zonas:
        quitar(soup(["nav", "header", "footer", "aside", "form"]))
        zonas = [soup.body or soup]
        zona_txt = "body (sin nav, header, footer, aside ni form)"
        aviso_zona = ("\n⚠️ No he encontrado una zona de contenido principal. "
                      "Si ves ruido, define MONITOR_SELECTOR.\n")

docs = documentos_de(zonas) if MODO != "texto" else []
txt = lineas_de(zonas) if MODO != "documentos" else []
if MODO == "todo":
    # El texto de un enlace a documento ya se vigila como documento: no se duplica
    etiquetas = {d.rsplit(" -> ", 1)[0] for d in docs}
    txt = [t for t in txt if t not in etiquetas]

nuevo = {}
for d in docs:
    nuevo[("doc", clave(d))] = d
for t in txt:
    nuevo[("txt", clave(t))] = t

# --- Estado anterior ---
old = None
if os.path.exists(SNAP):
    contenido = open(SNAP, encoding="utf-8").read().splitlines()
    if contenido and contenido[0] == FIRMA:
        old = []
        for linea in contenido[1:]:
            tipo, _, k = linea.partition("\t")
            if k:
                old.append((tipo, k))

# --- Comparación y avisos ---
if old is None:
    guardar(nuevo)
    msg = (f"✅ Monitorización iniciada\n{URL}\n\n"
           f"Modo: {MODO} · Zona: {zona_txt}\n"
           f"Documentos: {len(docs)} · Líneas de texto: {len(txt)}\n")
    if OCULTAR:
        msg += "Snapshot oculto: en el repositorio solo se guardan huellas.\n"
    msg += aviso_zona
    if not nuevo:
        msg += "\n⚠️ No he encontrado nada que vigilar. Revisa la URL, el modo o el selector."
    if docs:
        msg += "\n📄 Documentos:\n" + "\n".join(docs) + "\n"
    if txt:
        msg += "\n📝 Texto (primeras 40 líneas):\n" + "\n".join(txt[:40])
        if len(txt) > 40:
            msg += f"\n… y {len(txt) - 40} más"
    telegram(msg)
else:
    old_set = set(old)
    added = [(t, v) for (t, k), v in nuevo.items() if (t, k) not in old_set]
    removed = [(t, k) for (t, k) in old if (t, k) not in nuevo]
    if added or removed:
        nuevos = {"doc": "📄 Documentos nuevos", "txt": "📝 Texto nuevo"}
        quitados = {"doc": "📄 Documentos eliminados", "txt": "📝 Texto eliminado"}
        msg = "🔔 La página ha cambiado:\n" + URL + "\n"
        for tipo in ("doc", "txt"):
            a = [v for (t, v) in added if t == tipo]
            r = [k for (t, k) in removed if t == tipo]
            if a:
                msg += f"\n➕ {nuevos[tipo]}:\n" + "\n".join(a) + "\n"
            if r:
                if OCULTAR:
                    msg += (f"\n➖ {quitados[tipo]}: {len(r)} elemento(s) "
                            "(el snapshot oculto no guarda su contenido)\n")
                else:
                    msg += f"\n➖ {quitados[tipo]}:\n" + "\n".join(r) + "\n"
        telegram(msg)
        guardar(nuevo)
