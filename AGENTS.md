# EaglercraftX 1.8 Server — AGENTS.md

## 版本体系
- 项目名 `eaglerX-1.8-server` 的 `1.8` 是 EaglercraftX 客户端协议版本 + Docker 镜像版本号。
- 实际服务端是 Paper 1.12.2。后来从 git 历史恢复了 1.8.8，现在支持双版本。
- `MINECRAFT_VERSION` 环境变量选择版本：`1.8`（Paper 1.8.8）或 `1.12`（Paper 1.12.2）。该变量现在是**必填**，未传时容器直接报错退出。
- Docker 产物是**单镜像双版本**：同一个镜像同时包含 1.8 / 1.12 两套 `server-*` 和 `web-*` 目录。
- 单个容器实例一次只能选择一个版本；如果要同时运行 1.8 和 1.12，需要起两个容器并分开挂载宿主机数据目录。

## 目录结构
| 目录 | 作用 |
|------|------|
| `server-1.8/` | Paper 1.8.8（server.jar 19MB Paperclip） |
| `server-1.12/` | Paper 1.12.2（server.jar 40MB Paperclip） |
| `web-1.8/` | EaglercraftX 1.8 客户端（assets.epk, classes.js） |
| `web-1.12/` | EaglercraftX 1.12 客户端（assets.epw, classes.js, bootstrap.js, admin.html） |
| `bungee/` | Waterfall 代理 |
| `bungee/plugins/EaglercraftXBungee/` | WebSocket 入口 + HTTP 文件服务 |
| `script/` | start_server.sh + http_server.py |

运行时 `start_server.sh` 创建软链接 `web/ → web-${VERSION}/` 和 `server/ → server-${VERSION}/`。

## 端口
| 端口 | 用途 |
|------|------|
| 5200 | WebSocket 游戏连接 + HTTP 静态文件（EaglercraftXBungee 插件） |
| 5201 | 本机管理面 + HTTP 回退 + Dynmap 代理（http_server.py） |
| 25565 | Paper 内部端口（仅 localhost） |
| 25575 | RCON（仅 localhost，通过 `RCON_PASSWORD` 环境变量启用） |

## RCON 注意事项
- RCON 协议 packet length = `4(rid) + 4(type) + len(payload)` = `8 + len(payload)`。**不是 10**。
- Paper 1.12.2 首次 RCON 连接可能 Connection reset，需要重试 2-3 次。
- `rcon_send()` 参数 `retries=3`，内部 0.5s 间隔重试。

## 启动
1. 先 bungee，后 server（顺序不能错）。
2. Docker: `start_server.sh` 要求先显式传 `MINECRAFT_VERSION`，然后自动完成版本选择 → 软链接 → EULA → RCON → tmux 分屏。
3. 访问端口是 5200（WebSocket），不是 25565。
4. 入口脚本持续监控 Bungee、Paper、HTTP；任一核心服务退出时执行有序停服并返回失败状态。

## 运行机制

### 软链接机制

`start_server.sh` 启动时根据 `MINECRAFT_VERSION` 创建两个软链接：

```
web/    → web-1.12/  (或 web-1.8/)
server/ → server-1.12/ (或 server-1.8/)
```

bungee 插件的 `listeners.yml` 中 `root: '../../../web'` 和 server 的 `run.sh` 中 `cd server; ./server.jar` 都通过软链接访问正确版本的文件。软链接不在 git 中追踪（`.gitignore` 已排除）。

这意味着 Docker `build` 只需要构建**一个**镜像；运行时再用环境变量决定当前容器跑 1.8 还是 1.12。

### EULA 与 RCON 配置

`start_server.sh` 启动流程：
1. 读取 `MINECRAFT_VERSION` → 创建软链接
2. 写入 EULA → `server/eula.txt`
3. 如果 `RCON_PASSWORD` 有值 → 用 Python 按 key 更新 `server/server.properties` 中的 `enable-rcon=true` 和 `rcon.password=$RCON_PASSWORD`
4. 如果 `RCON_PASSWORD` 无值 → 用 Python 按 key 更新 `enable-rcon=false`

`server.properties` 中预留了 `rcon.port=25575` 和 `rcon.password=admin123`（占位），启动脚本会在运行时覆盖；这样即使密码包含 `/`、`&`、反斜杠等字符也不会把替换逻辑弄坏。

### 挂载机制

- 推荐直接把整个运行目录挂载到 `/eaglerX-1.8-server`，而不是只挂世界目录。
- 如果宿主机挂载目录是空的，`start_server.sh` 会先把镜像内置的 `/opt/eaglerX-1.8-server-image` 初始化复制到挂载目录，再继续启动。
- 如果宿主机挂载目录已有内容且结构残缺，入口脚本会保留原数据并退出。
- 旧的 `server-data/world*` 仍兼容，但只是可选兼容路径，不再是主方案。
- 如果要并行运行两个版本，请分别挂载到不同宿主机目录，例如 `/data/eagler-1.8` 和 `/data/eagler-1.12`。

### http_server.py（端口 5201）

合并了静态文件回退服务和 RCON 桥接功能：

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 静态文件服务（`web/` 目录） |
| `/api/connection-info` | GET | 公开游戏入口信息，无需 RCON 管理会话 |
| `/api/status` | GET | RCON 连接状态，`RCON_PASSWORD` 未设时 404 |
| `/api/login` | POST | 用 RCON 密码换取管理令牌 |
| `/api/rcon` | POST | RCON 命令桥接，body: `{"command":"list","token":"xxx"}` |
| `/admin` | GET | 302 重定向到 `/admin.html` |
| `/dynmap/` | GET | 反向代理到 `localhost:8123`，无需额外暴露端口 |

`RCON_PASSWORD` 环境变量留空时，需要管理权限的 API 保持关闭；`/api/connection-info` 始终公开。JSON 管理 API 请求体上限为 64 KiB，读取超时为 10 秒；原始插件 JAR 上传单独使用 64 MiB 上限和 30 秒总读取截止时间。同一来源连续 5 次登录失败后锁定 10 分钟。

### admin.html 管理面板

`web-1.8/` 是管理面资产的权威作者源，`script/sync_admin_assets.py` 将其物化到 `web-1.12/`。由 `admin.css` + `admin.js` 组成。

功能：
- 页面加载时探测 `/api/status`，RCON 启用则弹出自定义密码输入框
- 连接信息卡片展示快速加入链接、WebSocket 游戏地址和 5200/5201 端口边界
- 密码仅用于 `/api/login`，管理请求统一使用默认有效期 8 小时的令牌
- 令牌保存在 `sessionStorage`，浏览器会话结束时清理本地登录态
- 命令控制台（底部输入栏，回车发送）
- 天气/时间/难度/模式按钮组
- 游戏规则开关（13 项：昼夜循环、天气循环、火焰蔓延、怪物生成、掉落、死亡保留背包、苦力怕破坏方块、TNT 爆炸、自然回血、PVP、命令方块输出、死亡信息、自动保存）
- 白名单开关 + 增删查
- 玩家管理（在线列表/OP/踢出/封禁/解封）
- 世界 & 传送（种子/保存/出生点/TP 玩家/TP 坐标）
- 信息（TPS/版本/插件/广播/重载/关服）
- 在线玩家列表（10 秒自动刷新，彩色头像）
- TPS 实时显示（三色条形图，20 秒刷新）
- Dynmap 内嵌地图（开关 + 全屏按钮，通过 `/dynmap/` 代理）

## Docker 使用

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINECRAFT_VERSION` | (必填) | 选择服务端版本：`1.8` 或 `1.12` |
| `RCON_PASSWORD` | (空) | 设置后启用 RCON，管理面板弹窗需输入此密码 |
| `PUBLIC_GAME_URL` | (空) | 公开 HTTP(S) 游戏入口；空值时按当前管理面主机和 5200 端口推导 |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | 管理令牌有效期，单位为秒 |
| `ADMIN_AUTH_SECRET` | 从 RCON 密码派生 | 可选的令牌签名密钥 |

### 启动示例

```bash
# Paper 1.12.2，无 RCON
docker run -d -p 5200:5200 \
  -e MINECRAFT_VERSION=1.12 \
  <image>

# Paper 1.8.8 + RCON
docker run -d -p 5200:5200 -p 127.0.0.1:5201:5201 \
  -e MINECRAFT_VERSION=1.8 \
  -e RCON_PASSWORD=yourpass \
  <image>

# 推荐：完整目录挂载（1.12）
docker run -d -p 5200:5200 -p 127.0.0.1:5201:5201 \
  -v /data/eagler-1.12:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.12 \
  -e RCON_PASSWORD=yourpass \
  <image>

# 推荐：完整目录挂载（1.8）
docker run -d -p 5200:5200 -p 127.0.0.1:5201:5201 \
  -v /data/eagler-1.8:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.8 \
  -e RCON_PASSWORD=yourpass \
  <image>
```

游戏访问 `http://host:5200`，管理面板 `http://127.0.0.1:5201/admin`。远程管理使用 HTTPS 反向代理、VPN 或 SSH 隧道，5201 保持绑定宿主机回环地址。

### 构建与推送

```bash
./build.sh 2.2.3        # 构建并打标签
./build.sh 2.2.3 push   # 构建并推送
```

Dockerfile 用 `COPY .` 打包全部文件（含两个版本），运行时通过软链接选择。镜像约 1.47GB。

## 当前镜像
`ghcr.io/yangchuansheng/eaglerx1.8server:2.2.3`

## Agent skills

### Issue tracker

Issues and PRDs are tracked in this repository's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

The repository uses the default five-role triage label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

The repository uses a single-context domain layout. See `docs/agents/domain.md`.
