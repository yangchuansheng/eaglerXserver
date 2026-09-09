# EaglercraftX Server

Ejecuta un servidor de Minecraft al que los jugadores puedan acceder desde el navegador, con almacenamiento persistente y un panel de administración para gestionar jugadores, mundos y plugins. La imagen de Docker incluye los clientes EaglercraftX 1.8 / 1.12 y los servidores Paper 1.8.8 / 1.12.2; elige la versión del juego al iniciar.

![Panel de administración de EaglercraftX](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | **Español** | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[Inicio rápido](#inicio-rápido) · [Conectarse al servidor](#conectarse-al-servidor) · [Panel y plugins](#panel-de-administración-y-plugins) · [Copias y actualizaciones](#copias-de-seguridad-actualizaciones-y-vuelta-a-una-versión-anterior) · [Solución de problemas](#operación-y-solución-de-problemas) · [Variables de entorno](#variables-de-entorno) · [API de administración](#api-de-administración) · [Desarrollo y publicación](#desarrollo-compilación-y-publicación) · [Informar de problemas](#informar-de-problemas)

## Funciones

| Función | Detalles |
|------|------|
| Administración del servidor | Disponibilidad de Paper, jugadores conectados, ticks por segundo (TPS), clima, hora, reglas, configuración y reinicios controlados |
| Jugadores y mundos | Permisos de operador (OP), listas blancas, expulsiones, bloqueos, teletransporte, comandos de objetos, guardado de mundos y límites del mundo |
| Administración de plugins | Repositorios separados por versión; permite subir, activar, desactivar y eliminar plugins, con cambios efectivos tras reiniciar Paper |
| Mapas y semillas | Dynmap integrado, ubicación de jugadores, búsqueda nativa de estructuras y enlaces a un Seed Map externo |
| Plugins incluidos | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## Inicio rápido

### 1. Preparar el host

- **Host**: Instala Docker y prepara almacenamiento persistente. Los ejemplos usan rutas de Linux. Las imágenes publicadas están destinadas a AMD64; la emulación en ARM64 y la compatibilidad de las bibliotecas nativas requieren validación adicional. Consulta la [decisión de arquitectura](../adr/0006-publish-linux-amd64-only.md).
- **Memoria**: Paper y Bungee usan `-Xms256M -Xmx256M` cada uno. Reserva memoria adicional para la JVM fuera del heap, la generación de mundos y los plugins. Para ajustar el heap, edita `run.sh` en el directorio de ejecución correspondiente.
- **EULA**: El script de inicio escribe `eula=true`. Lee y acepta el [EULA de Minecraft](https://www.minecraft.net/en-us/eula) antes de desplegar.

### 2. Iniciar Paper 1.12.2

Ejecuta estos comandos en el servidor. Sustituye `YOUR_SERVER` por una IP o un dominio accesible para los jugadores y `replace-with-a-strong-password` por tu contraseña de administración.

Este ejemplo monta `/data/eagler-1.12` del host en `/eaglerX-1.8-server` dentro del contenedor y conserva **todo el directorio de ejecución**: mundos, plugins, configuración y archivos del frontend. Un directorio vacío se inicializa automáticamente en el primer uso. Si un directorio existente está incompleto, el inicio conserva su contenido y termina. Para un despliegue existente, sigue [Copias de seguridad, actualizaciones y vuelta a una versión anterior](#copias-de-seguridad-actualizaciones-y-vuelta-a-una-versión-anterior) para migrar los archivos de ejecución.

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5

docker run -d \
  --name eaglerx-1.12 \
  --platform linux/amd64 \
  --stop-timeout 45 \
  -p 5200:5200 \
  -p 127.0.0.1:5201:5201 \
  -v /data/eagler-1.12:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.12 \
  -e 'RCON_PASSWORD=replace-with-a-strong-password' \
  -e 'PUBLIC_GAME_URL=http://YOUR_SERVER:5200' \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
```

### 3. Abrir el panel y comprobar la disponibilidad

| Acceso | Dirección | Uso |
|------|------|----------|
| Juego | `http://YOUR_SERVER:5200/` | Compártela con los jugadores y sigue las [instrucciones de conexión](#conectarse-al-servidor) |
| Panel de administración | `http://127.0.0.1:5201/admin` | Ábrelo desde el host e inicia sesión con la contraseña configurada al arrancar |

La generación inicial del mundo puede tardar unos minutos. El inicio finaliza cuando el panel muestra **Paper is ready**. Si la espera se prolonga o aparece un error, consulta [Operación y solución de problemas](#operación-y-solución-de-problemas).

### Administración remota y puertos

Para administrar un servidor remoto, abre un túnel SSH desde tu equipo. Sustituye `user@YOUR_SERVER` por la dirección de acceso SSH del servidor:

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

Mantén abierto el túnel y accede a `http://127.0.0.1:5201/admin`. También puedes usar un proxy inverso HTTPS cuyo destino sea `127.0.0.1:5201` en el host. El acceso de administración por VPN debe poder reenviar tráfico a esa dirección de loopback.

| Puerto | Función | Exposición |
|------|------|----------|
| 5200 | Página del juego por HTTP, archivos estáticos públicos y conexiones de juego WebSocket | Accesible para los jugadores |
| 5201 | Panel, servicio HTTP de respaldo y proxy de Dynmap | Vincular a `127.0.0.1` en el host |
| 25565 | Paper | Localhost dentro del contenedor |
| 25575 | RCON | Localhost dentro del contenedor |

### Dominios propios, HTTPS y URL del juego

Establece `PUBLIC_GAME_URL` en **la URL HTTP(S) del juego que usan realmente los jugadores**. El panel genera a partir de ella enlaces de acceso rápido y direcciones `ws` / `wss`. Si queda vacía, deriva una URL HTTP a partir del nombre de host actual del panel y el puerto 5200 (`http://主机名:5200/`). Configúrala explícitamente si usas un túnel SSH, un dominio de administración separado o un puerto de juego personalizado.

Un acceso al juego por HTTPS requiere DNS, un certificado y reenvío HTTP y WebSocket a **5200**. Dirige el proxy de administración a **5201**. `PUBLIC_GAME_URL` solo genera direcciones de conexión; configura el proxy y el certificado en tu despliegue.

### Elegir 1.8 o ejecutar ambas versiones

`2.2.5` es la versión de publicación de la imagen. `MINECRAFT_VERSION=1.8` selecciona Paper 1.8.8 y `1.12` selecciona Paper 1.12.2. Cada contenedor ejecuta una versión del juego a la vez y usa su propio directorio.

Para ejecutar 1.8, ajusta estos parámetros del comando de inicio rápido:

| Parámetro | Ejecutar solo 1.8 | Ejecutar 1.8 junto con 1.12 |
|------|-------------|---------------------|
| Nombre del contenedor | `--name eaglerx-1.8` | Igual que a la izquierda |
| Versión del juego | `-e MINECRAFT_VERSION=1.8` | Igual que a la izquierda |
| Montaje del directorio completo | `-v /data/eagler-1.8:/eaglerX-1.8-server` | Igual que a la izquierda |
| Puerto del juego | `-p 5200:5200` | `-p 5300:5200` |
| Puerto de administración | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| URL pública del juego | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

Establece `PUBLIC_GAME_URL` en la URL de esa instancia. Para administrar la segunda instancia de forma remota, usa `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` y abre `http://127.0.0.1:5301/admin`.

## Conectarse al servidor

1. Abre la URL del juego o usa el enlace de acceso rápido que el administrador comparta desde la página Overview del panel. La pantalla Multijugador ya incluye este servidor: el cliente deriva la dirección `ws://` o `wss://` de la URL de la página, así que los puertos personalizados y los accesos HTTPS funcionan sin configuración adicional. El enlace de acceso rápido conecta directamente. Para unirte a otro servidor, añade su dirección `ws://HOST:5200/` en Multijugador.
2. En la primera visita, sigue las indicaciones de LoginSecurity e introduce `/register <password>`. En visitas posteriores, usa `/login <password>`. El registro es obligatorio por defecto, las contraseñas deben tener al menos 6 caracteres y el plazo para iniciar sesión es de 30 segundos.
3. LoginSecurity gestiona las contraseñas de las cuentas de jugadores. El panel usa la `RCON_PASSWORD` del administrador del servidor.

SimpleHomes proporciona `/sethome <name>`, `/home <name>` y `/homes`. SimpleTpa proporciona `/tpa <player>`, `/tpaccept` y `/tpdeny`. Los permisos y el comportamiento dependen de la configuración actual del plugin.

## Panel de administración y plugins

### Iniciar sesión y aplicar cambios

Configurar `RCON_PASSWORD` activa RCON y la API de administración. Tras iniciar sesión, el navegador conserva un token en la sesión actual; por defecto caduca a las 8 horas. Cerrar sesión elimina el token local. La interfaz está en inglés por defecto, admite chino simplificado y recuerda el idioma elegido para el sitio.

Puedes iniciar sesión mientras Paper arranca. Los controles del juego estarán disponibles cuando Paper esté listo.

| Acción | Cuándo se aplica |
|------|----------|
| Clima, hora, reglas del juego, comandos de jugadores y lista blanca | Se envían a la instancia de Paper en ejecución; revisa la respuesta de la consola |
| Configuración del servidor, incluidos MOTD, límite de jugadores, distancia de visión y PVP | Se guarda en `server.properties` y se aplica tras reiniciar Paper |
| Subir, activar, desactivar o eliminar plugins | Se guarda en el repositorio de plugins y se aplica tras reiniciar Paper |
| Reinicio de Minecraft desde el panel | Reinicia Paper de forma controlada mientras Bungee y el panel siguen funcionando |
| Apagar desde el panel o ejecutar `stop` en la consola | Paper termina y desencadena el apagado de todo el contenedor |

Dynmap está disponible mediante el proxy `/dynmap/` del panel. La búsqueda nativa de estructuras usa el componente cubiomes incluido en la imagen. Las estructuras y los puntos aproximados de aparición se calculan a partir de la semilla; las ubicaciones de los jugadores proceden de Dynmap o de sus datos guardados. Al abrir el Seed Map externo, la semilla se incluye en la URL de destino.

### Repositorios y datos de plugins

El repositorio de la versión activa está en `server-data/plugins-1.8` o `server-data/plugins-1.12`. El directorio `enabled/` contiene los paquetes activados y los datos de los plugins; `disabled/` contiene los paquetes desactivados. La ruta `plugins` de Paper apunta al directorio `enabled/` del repositorio activo.

El primer inicio importa los paquetes y datos de plugins incluidos. Los siguientes conservan el estado actual del repositorio, incluidas las ediciones manuales, desactivaciones y eliminaciones. El montaje del directorio completo conserva todos estos datos.

El panel muestra la versión activa del juego, tamaños de archivos, fechas de modificación, estado para el siguiente inicio y si hay un reinicio pendiente:

- Los archivos deben ser JAR y contener `plugin.yml` en la raíz. Los nombres deben terminar en `.jar` en minúsculas y el límite es de **64 MiB**. Los nombres duplicados generan un conflicto.
- Tras subir, activar, desactivar o eliminar un plugin, reinicia desde el panel para cargar el conjunto actualizado. El código cargado sigue activo hasta que Paper se detiene.
- Eliminar un plugin borra su JAR y conserva la configuración y las bases de datos. Un plugin compatible reinstalado que use el mismo directorio puede reutilizar esos datos.
- Los JAR se ejecutan con los permisos del proceso de Paper. Usa fuentes fiables, revisa y analiza los paquetes antes de instalarlos y realiza una copia de seguridad.

<details>
<summary>Mundos existentes y directorio de datos separado (compatibilidad heredada)</summary>

`PERSISTENT_DATA_ROOT` establece una raíz compartida para los repositorios de plugins y los montajes heredados de mundos. `SERVER_DATA_DIR` es su alias de compatibilidad. El método de despliegue predeterminado monta el directorio de ejecución completo.

**Un directorio de datos separado y vacío solo inicializa el repositorio de plugins.** Los enlaces simbólicos de mundos requieren que esos mundos ya existan en la raíz de datos. Los mundos nuevos permanecen en el directorio `server-版本/` de la versión y se conservan mediante el montaje completo.

Para migrar mundos existentes, detén el servidor y haz una copia; después prepara los directorios `<level-name>`, `<level-name>_nether` y `<level-name>_the_end`. Los nombres predeterminados son `world`, `world_nether` y `world_the_end`. El punto de entrada puede recurrir a estos nombres y conserva los directorios reales de mundos existentes en las rutas del servidor. Usa una raíz de datos por versión y comprueba el destino de cada enlace después del inicio.

</details>

## Copias de seguridad, actualizaciones y vuelta a una versión anterior

### Detener el servidor y hacer una copia

Estos comandos usan el contenedor y el montaje del inicio rápido. Las copias contienen mundos, estado de jugadores, datos de plugins, configuración, bases de datos de autenticación y la contraseña de administración. Guárdalas en un directorio con acceso restringido.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

Para una copia habitual, ejecuta `docker start eaglerx-1.12` al terminar. Durante una actualización, mantén detenido el contenedor antiguo. Si usas un `PERSISTENT_DATA_ROOT` externo, copia también esa raíz; tar conserva los enlaces simbólicos en sí por defecto.

Al recibir una señal de parada, el punto de entrada concede hasta 30 segundos a Paper para terminar y después hasta 10 segundos a Bungee. El plazo de parada de Docker de 45 segundos del ejemplo permite completar esta secuencia. Consulta el [comportamiento de parada de Docker](https://docs.docker.com/reference/cli/docker/container/stop/).

### Preparar la actualización en un directorio nuevo

**El directorio de ejecución completo se inicializa desde la imagen solo en el primer inicio.** Al cambiar la imagen, el montaje existente sigue suministrando el servidor, el frontend y el backend de Python. Actualizar requiere sustituir explícitamente los archivos de ejecución y migrar el estado persistente.

**Paso 1: Detener el servidor y hacer una copia.** Conserva el contenedor, el directorio y la versión de imagen anteriores.

**Paso 2: Preparar un directorio de ejecución nuevo.** Copia la plantilla completa de la imagen de destino. Este ejemplo usa `2.2.5`; elige un nombre de contenedor de plantilla y un directorio que estén libres:

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

Mantén el contenedor de plantilla sin iniciar. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) permite copiar archivos desde contenedores detenidos. Después de copiar la plantilla, migra el estado persistente del directorio anterior:

| Datos | Cómo migrarlos |
|------|----------|
| `server-1.12/<level-name>` y sus directorios Nether y End | Copia los mundos completos y mantén `level-name` coherente con los nombres de directorio |
| `server-data/` | Copia todo el repositorio de plugins, los archivos de marcador y los directorios heredados de mundos |
| Archivos `*.properties`, `*.yml` y `*.json` de Paper | Combina la configuración con la plantilla nueva; conserva operadores, listas blancas, bloqueos y cachés de jugadores |
| Configuración de Bungee, bases de autenticación y cachés de apariencias | Migra configuración y bases individualmente; comprueba el estado personalizado de la raíz y de los directorios de plugins |
| Frontend personalizado, plugins y opciones de inicio | Integra las personalizaciones necesarias; usa los JAR del servidor, scripts y recursos del panel de la imagen de destino |

El punto de entrada vuelve a crear los enlaces `server/`, `web/` y `plugins` de Paper. Copia los directorios de datos externos a un directorio nuevo del host y móntalos en el nuevo contenedor en su ruta original. Conserva la raíz antigua para el contenedor anterior. Incluye el estado de otras versiones y mundos personalizados en la lista de migración.

**Paso 3: Iniciar el contenedor nuevo.** Usa el [comando de inicio rápido](#2-iniciar-paper-1122), cambiando el nombre a `eaglerx-1.12-next`, el directorio del host a `/data/eagler-1.12-next` y la imagen a la versión de destino. Conserva la versión del juego, la contraseña, la URL pública y los puertos originales.

**Paso 4: Verificar la migración.** Comprueba que Paper esté listo, los jugadores puedan entrar, los mundos sigan intactos, los plugins se carguen y las listas blancas y mapas funcionen. Después, define cuánto tiempo conservar el contenedor, la imagen y las copias anteriores.

### Volver a una versión anterior y recuperar datos

Si conservas el contenedor y el directorio anteriores, detén el nuevo contenedor e inicia el antiguo:

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

Volver a la versión anterior restaura el estado guardado en el directorio antiguo. Conserva los datos generados durante la ejecución del contenedor nuevo para poder recuperarlos. Para restaurar una copia comprimida, extráela en un directorio nuevo, monta el directorio `eagler-1.12` extraído como directorio de ejecución completo y usa la imagen y las opciones de inicio correspondientes a esa copia.

## Operación y solución de problemas

Estos comandos usan el nombre de contenedor predeterminado:

```bash
# Container health and entrypoint / HTTP logs
docker inspect --format '{{.State.Status}} / {{.State.Health.Status}}' eaglerx-1.12
docker logs --tail 100 eaglerx-1.12

# Paper console output in the managed tmux session
docker exec -e TMUX_TMPDIR=/tmp/eaglerx-tmux eaglerx-1.12 \
  tmux capture-pane -p -t mcserver:0.1 -S -100

# Public status probe when RCON is enabled, via the host or SSH tunnel
curl -sS http://127.0.0.1:5201/api/status
```

Paper y Bungee se ejecutan en tmux. La consola de Paper anterior usa el panel `mcserver:0.1` por defecto; Bungee usa `mcserver:0.0`. La comprobación de salud de Docker sondea los puertos 5200, 5201 y 25565. El panel también consulta RCON para comprobar si Paper está listo.

| Síntoma | Qué comprobar |
|------|------------|
| El contenedor termina inmediatamente | Comprueba que `MINECRAFT_VERSION` sea `1.8` o `1.12` y revisa el error concreto en los registros |
| El inicio informa de un directorio incompleto | Inicializa un directorio vacío o restaura una copia completa; conserva el actual para investigar |
| El panel abre mientras Paper sigue arrancando | Revisa en la consola el progreso de generación de mundos y carga de plugins; el panel se actualiza cuando Paper está listo |
| El panel remoto es inaccesible | Comprueba que el túnel SSH o el proxy de administración llegue a `127.0.0.1:5201` en el host |
| El enlace rápido es incorrecto o falla la conexión HTTPS | Revisa `PUBLIC_GAME_URL`, el puerto público y el reenvío WebSocket del proxy del juego |
| `/api/status` devuelve 404 | Configura `RCON_PASSWORD` y vuelve a crear el contenedor; el script de inicio lo usa para activar RCON |
| El inicio de sesión devuelve 429 | Cinco intentos fallidos desde un origen dentro de la ventana de fallos activan un bloqueo de 10 minutos; los administradores tras un túnel o proxy pueden compartir origen |
| Los cambios se guardan, pero sigue el comportamiento anterior | Reinicia Paper de forma controlada desde el panel y comprueba el estado en ejecución |
| Dynmap devuelve 502 | Comprueba que esté activado y haya terminado de cargar; revisa la dirección y el puerto HTTP |
| Falla la búsqueda nativa de estructuras | Revisa el entorno `linux/amd64`, los errores de carga de bibliotecas nativas y la obtención de la semilla |

El punto de entrada inicia Bungee, Paper y HTTP en ese orden y los supervisa continuamente. Si termina un servicio principal, apaga todo el contenedor y devuelve un estado de error. Realiza una parada ordenada ante `SIGTERM` / `SIGINT`. Configura la política de reinicio teniendo en cuenta que apagar desde el panel también termina el contenedor.

## Variables de entorno

Pásalas mediante `docker run -e`. Para cambiar las variables de un contenedor, vuelve a crearlo con el montaje existente.

| Variable | Valor predeterminado | Descripción |
|------|--------|------|
| `MINECRAFT_VERSION` | Obligatoria | `1.8` selecciona Paper 1.8.8; `1.12` selecciona Paper 1.12.2 |
| `RCON_PASSWORD` | Vacía | Activa RCON y la API al establecerse; los endpoints de administración autenticados quedan desactivados si está vacía |
| `PUBLIC_GAME_URL` | Vacía | URL pública HTTP(S) del juego usada para generar enlaces rápidos y direcciones WebSocket |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | Raíz de repositorios de plugins y montajes heredados de mundos; un directorio vacío inicializa automáticamente el repositorio |
| `SERVER_DATA_DIR` | Vacía | Alias de compatibilidad de `PERSISTENT_DATA_ROOT`; un valor explícito de esta última tiene prioridad |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | Duración del token de administración en segundos |
| `ADMIN_AUTH_SECRET` | Derivada de la contraseña RCON | Secreto opcional para firmar tokens |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | Dirección de Dynmap usada por el backend de administración |

## API de administración

Para integraciones con scripts. Todos los endpoints usan el puerto de administración **5201**. El panel cubre las operaciones habituales.

<details>
<summary>Endpoints, autenticación y ejemplos con curl</summary>

«Público» describe los requisitos de autenticación del propio endpoint. Accede al puerto de administración mediante un [túnel SSH o un proxy de administración](#administración-remota-y-puertos).

| Endpoint | Requisitos de acceso |
|------|----------|
| `GET /api/connection-info` | Siempre disponible; devuelve la configuración del acceso público al juego |
| `GET /api/status` | Disponible con RCON activado; devuelve el estado de Paper e información relacionada |
| `POST /api/login` | Intercambia la contraseña de administración por un token con RCON activado |
| Endpoints JSON de administración como `POST /api/rcon`, `/api/config`, `/api/system` y `/api/plugins` | El cuerpo debe incluir un `token` válido |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, cuerpo JAR sin procesar y cabecera `X-Plugin-Filename` |
| `GET /dynmap/` | Proxy directo a Dynmap; la conexión de administración protege el acceso |

Las peticiones JSON admiten cuerpos de hasta 64 KiB y tienen un tiempo de lectura de 10 segundos. Las subidas JAR admiten hasta 64 MiB y un plazo total de lectura de 30 segundos. Los administradores que comparten origen mediante un túnel o proxy pueden compartir la misma ventana de bloqueo de inicio de sesión.

```bash
# Exchange the management password for a token
curl -sS http://127.0.0.1:5201/api/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"replace-with-a-strong-password"}'

# Use the returned token for a management command
curl -sS http://127.0.0.1:5201/api/rcon \
  -H 'Content-Type: application/json' \
  -d '{"command":"list","token":"TOKEN_FROM_LOGIN"}'
```

</details>

## Desarrollo, compilación y publicación

### Cambios locales y validación

Ejecuta estos comandos desde la raíz del repositorio con Python 3 y Docker instalados. Edita los recursos del panel en `web-1.8/` y ejecuta el script de sincronización para actualizar `web-1.12/`. Consulta la [decisión sobre la imagen base](../adr/0007-retain-the-verified-runtime-base.md) para conocer los requisitos de la imagen y las bibliotecas nativas.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

La validación local de publicación también requiere Node.js, tmux, `agent-browser` y una instalación funcional de Chrome. CI fija `agent-browser@0.26.0`; consulta los pasos de instalación en el [flujo de publicación](../../.github/workflows/release.yml).

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

Las comprobaciones locales cubren sintaxis de Python, regresiones del servidor y plugins, recursos de ambas versiones, recursos del panel y flujos de navegador en inglés y chino simplificado. El navegador usa una Mock Admin API local. La validación completa también construye la imagen y ejecuta ambas versiones de Paper:

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

La validación establece `release_ready` en `true` dentro de `summary.json` solo cuando pasan todas las comprobaciones `--live`. Consulta la [documentación de validación de publicación](../release-gate.md) para ver cobertura, formatos de evidencias y permisos de montajes temporales en Linux.

### Publicar una versión

Las publicaciones oficiales usan etiquetas Git `vMAJOR.MINOR` o `vMAJOR.MINOR.PATCH`. El flujo valida una misma imagen por completo y la publica en GHCR con etiquetas de versión y SHA del commit, y una atestación de procedencia de compilación. Las publicaciones automáticas de la versión más alta actualizan `latest`; las ejecuciones manuales solo actualizan la versión indicada y las etiquetas SHA.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` simplifica las compilaciones locales; su argumento `push` envía la imagen directamente. La distribución oficial sigue el [requisito de validación live completa](../adr/0005-require-the-live-release-gate.md) y el flujo de etiquetas anterior.

## Informar de problemas

Envía problemas de despliegue y solicitudes de funciones a [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues). Incluye la etiqueta de imagen, `MINECRAFT_VERSION`, arquitectura del host, opciones de inicio con datos sensibles ocultos, pasos de reproducción y registros relevantes. Elimina contraseñas y tokens antes de enviar.

## Créditos

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Proyecto original](https://github.com/burgerhugger/ALL-server)
