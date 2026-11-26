# vigilante-web

Vigila una página web y te avisa por **Telegram** cuando aparecen o desaparecen documentos enlazados (PDF, Word, Excel, ZIP...). Es gratis, no necesita servidor propio y se configura desde el navegador.

Pensado para seguir convocatorias, oposiciones, becas, listados de admitidos, etc., donde se publican documentos nuevos sin avisar.

## Cómo funciona

```
cron-job.org  ──(cada X minutos)──▶  GitHub Actions  ──▶  monitor.py  ──▶  Telegram
                                           │
                                           └─ guarda el estado en snapshot.txt
```

1. Un servicio gratuito (cron-job.org) lanza el workflow cada pocos minutos.
2. El workflow descarga la página y extrae los enlaces a documentos.
3. Los compara con la lista guardada en `snapshot.txt`.
4. Si hay diferencias, te envía un mensaje con lo **nuevo** y lo **eliminado**.

Tu URL y tu bot **no están en el código**: se guardan como secretos de GitHub, así que cada persona usa los suyos.

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

Si tu cuenta es gratuita y quieres que el repo sea **privado**, ten en cuenta el límite de minutos (ver [Límites y consumo](#límites-y-consumo)).

### 3. Activar GitHub Actions en tu copia

En los forks, los workflows vienen desactivados. Ve a la pestaña **Actions** y pulsa **I understand my workflows, go ahead and enable them**.

### 4. Configurar los secretos

En tu repo: **Settings → Secrets and variables → Actions → New repository secret**. Crea estos tres:

| Nombre | Valor |
|---|---|
| `MONITOR_URL` | La URL completa de la página que quieres vigilar |
| `TELEGRAM_TOKEN` | El token que te dio BotFather |
| `TELEGRAM_CHAT_ID` | Tu chat_id |

**Opcional.** En la pestaña **Variables** (justo al lado de Secrets) puedes crear:

| Nombre | Valor | Por defecto |
|---|---|---|
| `MONITOR_EXTENSIONES` | Extensiones a vigilar, separadas por comas. Ej.: `.pdf,.docx` | `.pdf,.doc,.docx,.xls,.xlsx,.zip,.odt` |

### 5. Probarlo a mano

1. Ve a **Actions → Vigilar WEB → Run workflow**.
2. Te llegará a Telegram el mensaje **"Monitorización iniciada"** con la lista de documentos actuales.
3. Para simular un cambio: edita `snapshot.txt`, borra una línea (no la primera) y vuelve a ejecutar. Recibirás un aviso con esa línea como **NUEVO**.

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
   - **Frecuencia:** la que quieras (ver recomendación abajo).
2. En **Advanced**:
   - **Request method:** `POST`
   - **Request body:** `{"ref":"main"}`
   - **Headers:**
     - `Authorization: Bearer TU_TOKEN_DE_GITHUB`
     - `Accept: application/vnd.github+json`
     - `Content-Type: application/json`
3. Pulsa **Test run**. Si devuelve **204**, funciona, y verás la ejecución en la pestaña Actions con el evento `workflow_dispatch`.

> Si renombraste el repo o el archivo del workflow, cambia la URL del paso 6.2 en consecuencia.

## Personalización

- **Otra página:** cambia el secreto `MONITOR_URL`. Al detectar una URL distinta, el estado se reinicia solo y recibirás de nuevo el mensaje de inicio.
- **Otros tipos de documento:** variable `MONITOR_EXTENSIONES`.
- **Varias páginas:** haz un fork por cada página (cada uno con sus propios secretos).
- **Otro nombre del workflow:** edita la línea `name:` de `.github/workflows/vigilar.yml`.

## Límites y consumo

- En repositorios **públicos**, los minutos de GitHub Actions son gratuitos. En repos **privados**, el plan gratuito incluye 2.000 minutos al mes y cada ejecución se redondea a 1 minuto. Consulta las cifras actuales en la [documentación oficial](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- Un disparo cada minuto son unas 43.000 ejecuciones al mes: viable solo en repos públicos. En repos privados, usa 30 minutos o más.
- Para casi cualquier convocatoria, cada 5-10 minutos es más que suficiente.

## Privacidad

- Los secretos (`MONITOR_URL`, token y chat_id) **no son visibles** en el repo ni en los logs (GitHub los enmascara).
- Pero `snapshot.txt` se guarda en el repositorio. Si tu repo es público, cualquiera puede ver la lista de **enlaces a documentos** de la página vigilada. Si eso es un problema, usa un repo privado y un intervalo mayor.
- Nadie puede lanzar tu workflow sin tener permisos de escritura en tu repo o tu token de GitHub. Mantén ese token solo en cron-job.org.

## Limitaciones

- Solo detecta **documentos enlazados** (por extensión). Un aviso solo con texto, o un enlace a otra página, no se detecta.
- No ejecuta JavaScript: si los documentos se cargan dinámicamente, no aparecerán.
- Si la web bloquea las IPs de GitHub, la ejecución fallará y GitHub te avisará por correo.
- Si el repo no tiene actividad durante 60 días, GitHub puede desactivar los workflows programados internamente (no afecta al disparo por API desde cron-job.org).

## Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| No llega nada a Telegram | No pulsaste **Iniciar** en el bot, o el token/chat_id está mal |
| Error `Faltan secretos` | Falta algún secreto o el nombre no coincide exactamente |
| `Test run` en cron-job.org da 404 | URL mal escrita, token sin permiso *Actions: Read and write* o repo renombrado |
| `Test run` da 401 o 403 | Token caducado o mal copiado (incluye la palabra `Bearer`) |
| Avisa en cada ejecución | La página tiene enlaces que cambian cada vez; restringe `MONITOR_EXTENSIONES` |
| "No he encontrado ningún documento" | La URL es incorrecta o los documentos tienen otras extensiones |

## Licencia

MIT License
