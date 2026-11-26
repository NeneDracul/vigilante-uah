# vigilante-web

Vigila una página web y te avisa por **Telegram** cuando cambia: documentos nuevos (PDF, Word, Excel...), avisos, textos modificados o eliminados. Es gratis, no necesita servidor propio y se configura desde el navegador.

Pensado para seguir convocatorias, oposiciones, becas, listados de admitidos, tablones de anuncios, etc.

## Cómo funciona

```
cron-job.org  ──(cada X minutos)──▶  GitHub Actions  ──▶  monitor.py  ──▶  Telegram
                                           │
                                           └─ guarda el estado en snapshot.txt
```

1. Un servicio gratuito (cron-job.org) lanza el workflow cada pocos minutos.
2. El workflow descarga la página y extrae **el texto** y **los enlaces a documentos** de la zona de contenido, sin menús, cabecera ni pie.
3. Lo compara con lo guardado en `snapshot.txt`.
4. Si hay diferencias, te envía un mensaje con lo **nuevo** y lo **eliminado**.

Tu URL y tu bot **no están en el código**: se guardan como secretos de GitHub, así que cada persona usa los suyos.

## Estructura del repositorio

| Archivo | Para qué sirve |
|---|---|
| `monitor.py` | El script que descarga la página, compara y avisa |
| `requirements.txt` | Dependencias de Python (`beautifulsoup4`) |
| `.github/workflows/vigilar.yml` | El workflow **Vigilar WEB** de GitHub Actions |
| `snapshot.txt` | Estado guardado (lo crea y actualiza el propio workflow) |
| `LICENSE` | Licencia MIT |

## Requisitos

- Cuenta gratuita de [GitHub](https://github.com)
- Cuenta gratuita de [Telegram](https://telegram.org)
- Cuenta gratuita de [cron-job.org](https://cron-job.org)

## Instalación paso a paso

### 1. Crear tu bot de Telegram

1. En Telegram, abre un chat con **@BotFather** y envía `/newbot`.
2. Elige un nombre y un usuario (debe acabar en `bot`).
3. Guarda el **token** que te da (algo como `123456789:AAH...`).
4. Abre tu bot nuevo y pulsa **Iniciar** (o envíale cualquier mensaje). Sin esto no podrá escribirte.
5. Obtén tu **chat_id**: abre en el navegador `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` y busca `"chat":{"id":123456789`. Ese número es tu chat_id.

> No compartas el token con nadie: quien lo tenga controla tu bot.

### 2. Copiar el repositorio

Pulsa **Fork** (arriba a la derecha) para crear tu propia copia.

Si quieres que sea **privado**, ten en cuenta el límite de minutos (ver [Límites y consumo](#límites-y-consumo)).

### 3. Activar GitHub Actions en tu copia

En los forks, los workflows vienen desactivados. Ve a la pestaña **Actions** y pulsa **I understand my workflows, go ahead and enable them**.

### 4. Configurar los secretos

En tu repo: **Settings → Secrets and variables → Actions → pestaña Secrets → New repository secret**. Crea estos tres:

| Nombre | Valor |
|---|---|
| `MONITOR_URL` | La URL completa de la página que quieres vigilar |
| `TELEGRAM_TOKEN` | El token que te dio BotFather |
| `TELEGRAM_CHAT_ID` | Tu chat_id |

### 5. Probarlo a mano

1. Ve a **Actions → Vigilar WEB → Run workflow**.
2. Te llegará a Telegram el mensaje **"Monitorización iniciada"**. Incluye la **zona vigilada**, cuántos documentos y líneas de texto ha encontrado, y la lista. Revísalo: si ves menús o ruido, mira [Elegir qué vigilar](#elegir-qué-vigilar).
3. Para simular un cambio: edita `snapshot.txt`, borra una línea (no la primera) y vuelve a ejecutar. Recibirás un aviso con esa línea como **nuevo**.

Si no te llega nada, abre la ejecución en Actions y mira el error (normalmente es un secreto mal copiado o no haber pulsado **Iniciar** en el bot).

### 6. Programar la ejecución automática

El programador interno de GitHub (`schedule`) es poco fiable: no admite menos de 5 minutos y retrasa o salta ejecuciones. Por eso este proyecto usa **cron-job.org** como disparador.

**6.1. Crear un token de GitHub**

1. GitHub → tu foto → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. **Repository access:** *Only select repositories* y elige tu repo.
3. **Permissions → Repository permissions → Actions: Read and write**.
4. Genera el token y cópialo.

**6.2. Crear el cronjob en cron-job.org**

1. **Create cronjob** y rellena:
   - **URL:** `https://api.github.com/repos/TU_USUARIO/vigilante-web/actions/workflows/vigilar.yml/dispatches`
   - **Frecuencia:** la que quieras (ver [Límites y consumo](#límites-y-consumo)).
2. En **Advanced**:
   - **Request method:** `POST`
   - **Request body:** `{"ref":"main"}`
   - **Headers:**
     - `Authorization: Bearer TU_TOKEN_DE_GITHUB`
     - `Accept: application/vnd.github+json`
     - `Content-Type: application/json`
3. Pulsa **Test run**. Si devuelve **204**, funciona, y verás la ejecución en la pestaña Actions con el evento `workflow_dispatch`.

> Si renombraste el repo o el archivo del workflow, cambia la URL del paso 6.2 en consecuencia.

## Elegir qué vigilar

Por defecto (`MONITOR_MODO=todo`) se vigila el **texto** y los **enlaces a documentos** de la zona de contenido principal. Para detectar esa zona, el script prueba por orden estos selectores y usa el primero que exista: `main`, `[role=main]`, `#contenido`, `#content`, `article`. Si no hay ninguno, usa todo el `<body>` quitando `nav`, `header`, `footer`, `aside` y `form`.

Todo se ajusta con **variables** (no secretos) en **Settings → Secrets and variables → Actions → pestaña Variables → New repository variable**. Todas son opcionales:

| Variable | Qué hace | Por defecto |
|---|---|---|
| `MONITOR_MODO` | `todo` (texto + documentos), `texto` o `documentos` | `todo` |
| `MONITOR_SELECTOR` | Zona a vigilar, como selector CSS. Ej.: `#contenido` o `div.noticias` | Detección automática |
| `MONITOR_EXCLUIR` | Elementos a ignorar dentro de la página, como selector CSS. Ej.: `.contador, .fecha-actualizacion` | Ninguno |
| `MONITOR_IGNORAR` | Expresión regular: las líneas de texto que la cumplan se ignoran. Ej.: `visitas|actualizado el` | Ninguna |
| `MONITOR_EXTENSIONES` | Extensiones que cuentan como documento, separadas por comas | `.pdf,.doc,.docx,.xls,.xlsx,.zip,.odt` |
| `MONITOR_OCULTAR_SNAPSHOT` | `si` guarda solo huellas (hashes) en vez del texto. Ver [Privacidad](#privacidad) | `no` |

> Cada vez que cambias la URL o cualquiera de estos ajustes, el estado se reinicia solo y recibes de nuevo el mensaje de inicio, para no compararlo contra datos de otra configuración.

### Cómo encontrar el selector de la zona

1. Abre la página y, sobre el contenido que te interesa, clic derecho → **Inspeccionar**.
2. Sube por el árbol hasta el elemento que **contiene todo lo que quieres vigilar** y nada de menús ni pies.
3. Si tiene `id="contenido"`, el selector es `#contenido`. Si tiene `class="noticias"`, es `.noticias` (o `div.noticias`).
4. Guárdalo como variable `MONITOR_SELECTOR`, lanza el workflow a mano y comprueba el mensaje de inicio.

### Evitar falsos positivos

Si recibes avisos en cada ejecución, hay algo que cambia solo (contador de visitas, fecha de "última actualización", un reloj...). Mira en el aviso qué línea cambia y:

- **Ignórala** con `MONITOR_IGNORAR` (si es texto) o `MONITOR_EXCLUIR` (si es un elemento concreto de la página).
- O limita la zona con `MONITOR_SELECTOR`.

### Qué se detecta y qué no

| Cambio en la página | ¿Se detecta? |
|---|---|
| Documento nuevo o eliminado (PDF, Word...) | Sí, con su URL completa |
| Aviso o párrafo nuevo, modificado o eliminado | Sí, como texto |
| Enlace nuevo a otra página (no documento) | Solo su texto visible, no la URL |
| Cambios en menús, cabecera o pie | No (fuera de la zona) |
| Contenido que carga JavaScript | No |

## Límites y consumo

- En repositorios **públicos**, los minutos de GitHub Actions son gratuitos. En repos **privados**, el plan gratuito incluye 2.000 minutos al mes y cada ejecución se redondea a 1 minuto. Consulta las cifras actuales en la [documentación oficial](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- Un disparo cada minuto son unas 43.000 ejecuciones al mes: viable solo en repos públicos. En repos privados, usa 30 minutos o más.
- Para casi cualquier convocatoria, cada 5-10 minutos es más que suficiente.
- Si hay muchos cambios de golpe, el aviso se divide en varios mensajes (máximo 8, luego se recorta).

## Privacidad

- Los secretos (`MONITOR_URL`, token y chat_id) **no son visibles** en el repo ni en los logs (GitHub los enmascara). Las variables tampoco aparecen en el código, pero se muestran en los logs de ejecución.
- **`snapshot.txt` se guarda en el repositorio.** Con `MONITOR_MODO=todo` o `texto` contiene el **texto de la página vigilada** y los enlaces a sus documentos. Si tu repo es público, cualquiera puede verlo, y deducir así qué página vigilas.
- Opciones para evitarlo:
  - Usar un repo **privado** con un intervalo mayor.
  - Poner `MONITOR_OCULTAR_SNAPSHOT=si`: el repo solo guarda huellas (hashes). Los elementos **nuevos** se te muestran completos en Telegram, pero los **eliminados** solo aparecen como recuento, porque el script ya no conserva su texto. Las huellas de textos cortos o previsibles se pueden adivinar por fuerza bruta, así que no es cifrado.
- Si ya publicaste el repo con una URL o un snapshot anteriores, el **historial de Git** los conserva. Para borrarlos de verdad, crea un repositorio nuevo.
- Nadie puede lanzar tu workflow sin permisos de escritura en tu repo o sin tu token de GitHub. Mantén ese token solo en cron-job.org.

## Limitaciones

- No ejecuta JavaScript: si el contenido se carga dinámicamente, no aparecerá.
- Si la web bloquea las IPs de GitHub, la ejecución fallará y GitHub te avisará por correo.
- La detección automática de la zona es una heurística: en algunas webs necesitarás definir `MONITOR_SELECTOR`.

## Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| No llega nada a Telegram | No pulsaste **Iniciar** en el bot, o el token/chat_id está mal |
| Error `Faltan secretos` | Falta algún secreto o el nombre no coincide exactamente |
| Error `Selector CSS no válido` o `MONITOR_IGNORAR no es una expresión regular válida` | Revisa la sintaxis de esa variable |
| `Test run` en cron-job.org da 404 | URL mal escrita, token sin permiso *Actions: Read and write* o repo renombrado |
| `Test run` da 401 o 403 | Token caducado o mal copiado (incluye la palabra `Bearer`) |
| Avisa en cada ejecución | Hay algo que cambia solo; ver [Evitar falsos positivos](#evitar-falsos-positivos) |
| "No he encontrado nada que vigilar" | URL incorrecta, selector que no coincide con nada, o modo/extensiones que no encajan |
| El mensaje de inicio muestra menús y ruido | Define `MONITOR_SELECTOR` con la zona de contenido |

## Licencia

[MIT](LICENSE).
