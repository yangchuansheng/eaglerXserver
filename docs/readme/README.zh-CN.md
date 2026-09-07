# EaglercraftX Server

通过 Docker 部署可持久化的 Minecraft 浏览器游戏服务器，并用管理面维护玩家、世界和插件。一个镜像包含 EaglercraftX 1.8 / 1.12 客户端与 Paper 1.8.8 / 1.12.2 服务端，启动时选择游戏版本。

![EaglercraftX 管理面板](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | **简体中文** | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[快速启动](#快速启动) · [玩家加入](#玩家首次加入) · [管理与插件](#管理面与插件) · [备份与升级](#备份升级与回滚) · [运维排错](#常用运维与排错) · [环境变量](#环境变量) · [管理 API](#管理-api) · [开发与发布](#开发构建与发布) · [问题反馈](#问题反馈)

## 功能

| 功能 | 内容 |
|------|------|
| 服务器管理 | Paper 就绪状态、在线玩家、TPS、天气、时间、游戏规则、配置与受控重启 |
| 玩家与世界 | OP、白名单、踢出、封禁、传送、物品命令、世界保存与边界设置 |
| 插件管理 | 按版本隔离的插件仓库，支持上传、启用、停用、删除，变更在 Paper 重启后生效 |
| 地图与种子 | Dynmap 内嵌地图、玩家定位、原生结构查找，以及打开外部 Seed Map |
| 内置插件 | LoginSecurity、SimpleHomes、SimpleTpa、WorldEdit、Dynmap |

## 快速启动

### 1. 准备运行环境

- **主机**：安装 Docker，准备持久化磁盘。示例使用 Linux 路径；发布镜像面向 AMD64，ARM64 模拟运行与原生库兼容性需单独验证，见 [架构约定](../adr/0006-publish-linux-amd64-only.md)。
- **内存**：Paper 与 Bungee 各设置 `-Xms256M -Xmx256M`，还需为 JVM 堆外内存、世界生成和插件留出资源。调整堆大小时修改对应运行目录中的 `run.sh`。
- **EULA**：启动脚本会写入 `eula=true`，部署前请阅读并接受 [Minecraft EULA](https://www.minecraft.net/en-us/eula)。

### 2. 启动 Paper 1.12.2

在服务器上执行以下命令。将 `YOUR_SERVER` 换成玩家可访问的 IP 或域名，将 `replace-with-a-strong-password` 换成管理密码。

示例将宿主机的 `/data/eagler-1.12` 挂载为容器内的 `/eaglerX-1.8-server`，持久化**整个运行目录**，一起保存世界、插件、配置和前端文件。首次使用空目录会自动初始化；目录结构残缺时保留原数据并退出。已有实例请按 [备份、升级与回滚](#备份升级与回滚) 迁移运行文件。

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

### 3. 打开管理面并确认就绪

| 入口 | 地址 | 使用方式 |
|------|------|----------|
| 游戏 | `http://YOUR_SERVER:5200/` | 分享给玩家，按 [首次加入](#玩家首次加入) 步骤连接 |
| 管理面 | `http://127.0.0.1:5201/admin` | 从宿主机访问，输入启动时设置的管理密码 |

首次生成世界可能需要几分钟。以管理面显示 **Paper 已就绪** 为启动完成标志；持续等待或报错时查看 [运维与排错](#常用运维与排错)。

### 远程管理与端口

从自己的电脑管理远程服务器时，在自己的电脑建立 SSH 隧道，将 `user@YOUR_SERVER` 换成服务器的 SSH 登录地址：

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

保持隧道连接，再打开 `http://127.0.0.1:5201/admin`。也可使用 HTTPS 反向代理，上游指向宿主机 `127.0.0.1:5201`；VPN 入口需能转发到该回环地址。

| 端口 | 用途 | 部署边界 |
|------|------|----------|
| 5200 | HTTP 游戏页面、公开静态文件与 WebSocket 游戏连接 | 对玩家发布 |
| 5201 | 管理面、HTTP 回退与 Dynmap 代理 | 绑定宿主机 `127.0.0.1` |
| 25565 | Paper | 容器内 localhost |
| 25575 | RCON | 容器内 localhost |

### 自定义域名、HTTPS 与游戏地址

`PUBLIC_GAME_URL` 应填写**玩家实际访问的 HTTP(S) 游戏入口**。管理面据此生成快速加入链接和 `ws` / `wss` 地址。留空时会按管理面当前主机名推导 `http://主机名:5200/`；SSH 隧道、独立管理域名和自定义游戏端口部署应显式填写。

HTTPS 游戏入口需要配置 DNS、证书，以及指向 **5200** 的 HTTP 和 WebSocket 转发；管理面代理指向 **5201**。`PUBLIC_GAME_URL` 只用于生成连接地址，代理与证书由部署层提供。

### 选择 1.8 或同时运行两个版本

`2.2.5` 是镜像发布版本；`MINECRAFT_VERSION=1.8` 选择 Paper 1.8.8，`1.12` 选择 Paper 1.12.2。每个容器一次运行一个游戏版本，并使用独立运行目录。

在快速启动命令中调整以下参数即可运行 1.8：

| 参数 | 单独运行 1.8 | 与 1.12 并行运行 1.8 |
|------|-------------|---------------------|
| 容器名 | `--name eaglerx-1.8` | 同左 |
| 游戏版本 | `-e MINECRAFT_VERSION=1.8` | 同左 |
| 完整目录挂载 | `-v /data/eagler-1.8:/eaglerX-1.8-server` | 同左 |
| 游戏端口 | `-p 5200:5200` | `-p 5300:5200` |
| 管理端口 | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| 公开游戏地址 | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

将对应的公开游戏地址填入 `PUBLIC_GAME_URL`。并行实例的远程管理使用 `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER`，浏览器访问 `http://127.0.0.1:5301/admin`。

## 玩家首次加入

1. 打开游戏入口，或使用服主分享的管理面 Overview 快速加入链接。1.12 客户端的初始服务器列表为空，可在多人游戏中添加 `ws://YOUR_SERVER:5200/`；HTTPS 游戏入口使用对应的 `wss://` 地址。
2. 首次进入服务器后，按 LoginSecurity 提示输入 `/register <password>`；以后使用 `/login <password>`。默认要求注册，密码至少 6 个字符，登录等待时间为 30 秒。
3. 游戏账号密码由 LoginSecurity 管理；管理面使用服主配置的 `RCON_PASSWORD`。

SimpleHomes 提供 `/sethome <name>`、`/home <name>`、`/homes`；SimpleTpa 提供 `/tpa <player>`、`/tpaccept` 和 `/tpdeny`。具体权限和行为以当前插件配置为准。

## 管理面与插件

### 登录与操作生效时间

设置 `RCON_PASSWORD` 后启用 RCON 和管理 API。登录成功后，浏览器在当前会话中保存管理令牌，默认有效 8 小时；退出登录会清除本地令牌。界面默认英文，可切换为简体中文并记住当前站点的语言选择。

Paper 启动期间可以先登录管理面，游戏操作会在 Paper 就绪后恢复。

| 操作 | 生效方式 |
|------|----------|
| 天气、时间、游戏规则、玩家与白名单命令 | 发往当前 Paper，查看控制台返回结果 |
| MOTD、人数上限、视距、PVP 等服务器配置 | 写入 `server.properties`，重启 Paper 后生效 |
| 插件上传、启用、停用、删除 | 保存到插件仓库，重启 Paper 后生效 |
| 管理面的“重启 Minecraft 服务” | 受控重启当前 Paper，Bungee 和管理面继续运行 |
| 管理面的关服或控制台 `stop` | Paper 退出后触发容器整体停服 |

Dynmap 通过管理面的 `/dynmap/` 代理访问。原生结构查找依赖镜像内的 cubiomes 组件；结构和近似出生点由种子计算，玩家定位会使用 Dynmap 或玩家存档。打开外部 Seed Map 时，会将世界种子放入目标网站 URL。

### 插件仓库与数据

当前版本的仓库位于 `server-data/plugins-1.8` 或 `server-data/plugins-1.12`。其中 `enabled/` 保存启用插件包和插件数据，`disabled/` 保存停用插件包；Paper 的 `plugins` 路径指向当前仓库的 `enabled/`。

首次启动会导入内置插件包与数据，后续启动保留仓库现有状态，包括手动修改、停用和删除的结果。完整运行目录挂载会一起持久化这些内容。

管理面展示当前版本、插件文件大小、修改时间、下次启动状态和待重启标记：

- 上传接受包含根目录 `plugin.yml` 的 JAR，文件名须以小写 `.jar` 结尾，上限 **64 MiB**；重名包返回冲突。
- 上传、启用、停用、删除后，使用管理面的重启按钮加载新集合。已加载代码会持续到 Paper 停止。
- 删除操作移除 JAR，保留插件配置和数据库；重新安装使用相同数据目录的兼容插件可继续读取这些数据。
- JAR 会以 Paper 进程权限执行代码。使用可信来源，并在安装前审查、扫描和备份。

<details>
<summary>已有世界与独立数据目录（兼容用法）</summary>

`PERSISTENT_DATA_ROOT` 可指定插件仓库与旧版世界挂载的共同根目录，`SERVER_DATA_DIR` 是兼容别名。完整运行目录挂载是默认部署方式。

**空的独立数据目录只会自动初始化插件仓库。** 世界链接要求数据根目录中已存在对应世界；新生成的世界会留在 `server-版本/`，其持久化由完整运行目录挂载保证。

迁移已有世界时，先停服并备份，再准备 `<level-name>`、`<level-name>_nether`、`<level-name>_the_end` 目录，默认名称为 `world`、`world_nether`、`world_the_end`。入口脚本也兼容回退到这些默认名称，并保留服务端路径上已有的真实世界目录。每个版本使用独立数据根目录，启动后逐项确认世界链接的实际目标。

</details>

## 备份、升级与回滚

### 停服备份

以下命令对应快速启动中的容器与挂载目录。备份包含世界、玩家状态、插件数据、配置、认证数据库和管理密码，应保存在受限目录。

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

日常备份完成后执行 `docker start eaglerx-1.12`。升级时保持旧容器停止。配置了外部 `PERSISTENT_DATA_ROOT` 的部署，还需备份该根目录；tar 默认保存软链接本身。

容器入口收到停止信号后，依次给 Paper 最多 30 秒、Bungee 最多 10 秒退出。示例的 45 秒 Docker 停止窗口为该过程留出时间，见 [Docker 停止行为](https://docs.docker.com/reference/cli/docker/container/stop/)。

### 在新目录准备升级

**完整运行目录只在首次启动时从镜像初始化。** 更换镜像后，已有挂载中的服务端、前端和 Python 后端文件会继续使用。升级需要显式更新运行文件，并迁移持久化状态。

**第一步：停服备份。** 保留旧容器、旧运行目录和旧镜像版本。

**第二步：准备新运行目录。** 从目标镜像复制完整模板。下面以 `2.2.5` 为目标；选择尚未使用的模板容器名和目录名：

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

模板容器保持未启动状态；[docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) 支持从停止的容器复制文件。复制完成后，再迁移旧目录中的持久化状态：

| 内容 | 迁移方式 |
|------|----------|
| `server-1.12/<level-name>` 及下界、末地目录 | 复制完整世界，保持 `level-name` 与实际目录对应 |
| `server-data/` | 复制完整插件仓库、标记文件和兼容世界目录 |
| Paper 的 `*.properties`、`*.yml`、`*.json` | 对照新模板合并配置，保留 OP、白名单、封禁和玩家缓存 |
| Bungee 配置、认证数据库与皮肤缓存 | 逐项迁移配置和数据库，检查根目录及插件目录中的自定义状态 |
| 自定义前端、插件与启动参数 | 按需合并定制；服务端 JAR、脚本和管理资产使用目标镜像版本 |

`server/`、`web/` 和 Paper 的 `plugins` 软链接由入口脚本重新建立。外部数据目录应先复制到新的宿主机目录，再由新容器按原容器内路径挂载；旧数据根目录保留给旧容器使用。其他版本或自定义世界的状态也应纳入迁移清单。

**第三步：启动新容器。** 使用 [快速启动命令](#2-启动-paper-1122)，将容器名改为 `eaglerx-1.12-next`、宿主机目录改为 `/data/eagler-1.12-next`，镜像改为目标版本。保持原来的游戏版本、密码、公开地址和端口映射。

**第四步：验证迁移结果。** 确认 Paper 就绪、玩家加入、原世界、插件加载、白名单和地图状态。通过后再安排旧容器、旧镜像与备份的保留周期。

### 回滚与恢复

旧容器和目录仍保留时，停止新容器，再启动旧容器：

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

回滚恢复到旧目录保存的状态；先保留新容器期间产生的数据，便于后续恢复。使用压缩备份恢复时，将其解压到一个新目录，再把解出的 `eagler-1.12` 作为完整运行目录挂载，并使用备份对应的镜像版本和启动参数。

## 常用运维与排错

以下命令对应默认容器名：

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

Paper 与 Bungee 运行在 tmux 中。上面的 Paper 控制台窗口为默认 `mcserver:0.1`，Bungee 使用 `mcserver:0.0`。Docker 健康检查探测 5200、5201、25565 三个端口；管理面的 Paper 就绪状态还会探测 RCON。

| 现象 | 检查与处理 |
|------|------------|
| 容器立即退出 | 检查 `MINECRAFT_VERSION` 是否为 `1.8` 或 `1.12`，以及日志中的具体错误 |
| 提示运行目录残缺 | 使用空目录初始化，或从完整备份恢复；保留当前目录供排查 |
| 管理面可打开，Paper 仍在启动 | 查看 Paper 控制台中的世界生成、插件加载进度；就绪后页面自动恢复 |
| 远程管理面打不开 | 检查 SSH 隧道或管理代理能否到达宿主机 `127.0.0.1:5201` |
| 快速加入地址错误或 HTTPS 下连接失败 | 核对 `PUBLIC_GAME_URL`、公开端口，以及游戏代理的 WebSocket 转发 |
| `/api/status` 返回 404 | 为容器设置 `RCON_PASSWORD` 并重新创建，启动脚本会据此启用 RCON |
| 登录返回 429 | 同一来源在失败窗口内累计 5 次失败会锁定 10 分钟；隧道或代理后的管理员可能共享来源 |
| 配置或插件显示已保存，运行效果仍旧 | 使用管理面的受控 Paper 重启，再核对运行状态 |
| Dynmap 返回 502 | 检查 Dynmap 插件是否启用、完成加载，以及其 HTTP 监听地址和端口 |
| 原生结构查找失败 | 核对 `linux/amd64` 运行环境、原生库加载错误和世界种子读取结果 |

入口脚本按 Bungee、Paper、HTTP 的顺序启动并持续监控。任一核心服务退出会触发整体停服并返回失败状态；收到 `SIGTERM` / `SIGINT` 时执行有序停服。重启策略由部署者配置，配置自动重启时应同时考虑管理面关服触发的容器退出。

## 环境变量

通过 `docker run -e` 传入。修改容器环境变量时，使用原挂载目录重新创建容器。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINECRAFT_VERSION` | 必填 | `1.8` 对应 Paper 1.8.8；`1.12` 对应 Paper 1.12.2 |
| `RCON_PASSWORD` | 空 | 设置后启用 RCON 与管理 API；留空时鉴权管理接口关闭 |
| `PUBLIC_GAME_URL` | 空 | 玩家可访问的 HTTP(S) 游戏入口，用于生成快速加入链接与 WebSocket 地址 |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | 插件仓库与已有世界兼容挂载的根目录；空目录自动初始化插件仓库 |
| `SERVER_DATA_DIR` | 空 | `PERSISTENT_DATA_ROOT` 的兼容别名；显式设置后者时优先使用后者 |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | 管理令牌有效期，单位为秒 |
| `ADMIN_AUTH_SECRET` | 从 RCON 密码派生 | 可选的令牌签名密钥 |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | 管理后端访问 Dynmap 的上游地址 |

## 管理 API

供脚本集成使用，所有路径位于管理端口 **5201**。日常操作可直接使用管理面。

<details>
<summary>查看接口、鉴权规则与 curl 示例</summary>

“公开”表示接口本身的鉴权规则，管理端口仍通过 [SSH 隧道或管理代理](#远程管理与端口) 访问。

| 接口 | 访问条件 |
|------|----------|
| `GET /api/connection-info` | 始终开放，返回公开游戏入口配置 |
| `GET /api/status` | RCON 启用后开放，返回 Paper 状态等信息 |
| `POST /api/login` | RCON 启用后使用管理密码换取令牌 |
| `POST /api/rcon`、`/api/config`、`/api/system`、`/api/plugins` 等 JSON 管理接口 | 请求体包含有效的 `token` |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`，原始 JAR 请求体与 `X-Plugin-Filename` 请求头 |
| `GET /dynmap/` | 直接代理到 Dynmap，访问保护由管理通道提供 |

JSON 管理 API 请求体上限为 64 KiB，读取超时为 10 秒；原始插件 JAR 上传上限为 64 MiB，总读取截止时间为 30 秒。共享隧道或反向代理来源的管理员可能共享登录失败锁定窗口。

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

## 开发、构建与发布

### 本地修改与验证

以下命令在仓库根目录执行，需要 Python 3 和 Docker。修改管理面时，以 `web-1.8/` 为源目录，运行同步脚本更新 `web-1.12/`。基础镜像与原生库约定见 [运行时基础镜像约定](../adr/0007-retain-the-verified-runtime-base.md)。

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

本地发布检查还需要 Node.js、tmux、`agent-browser` 和可启动的 Chrome。CI 固定使用 `agent-browser@0.26.0`，安装方式见 [发布工作流](../../.github/workflows/release.yml)。

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

本地检查覆盖 Python 语法、服务端与插件回归、双版本资源、管理资产和中英双语浏览器操作；浏览器使用本地 Mock Admin API。完整发布验证还需构建镜像并运行双版本 Paper：

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

`summary.json` 仅在完整 `--live` 检查通过时将 `release_ready` 设为 `true`。检查范围、证据格式和 Linux 临时挂载权限要求见 [发布闸门文档](../release-gate.md)。

### 正式发布

正式发布使用 `vMAJOR.MINOR` 或 `vMAJOR.MINOR.PATCH` Git 标签：工作流对同一份镜像完成完整闸门后发布到 GHCR，并生成版本标签、提交 SHA 标签和构建来源证明。最高版本的自动发布更新 `latest`；手动重跑只更新指定版本与 SHA 标签。

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` 提供本地构建封装，其 `push` 参数直接执行镜像推送。正式分发遵循 [完整 live gate 约定](../adr/0005-require-the-live-release-gate.md) 和上述标签工作流。

## 问题反馈

部署问题和功能建议请提交到 [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues)。问题报告请附镜像标签、`MINECRAFT_VERSION`、宿主机架构、脱敏后的启动参数、复现步骤和相关错误日志；密码与令牌应在提交前移除。

## 致谢

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Upstream](https://github.com/burgerhugger/ALL-server)
