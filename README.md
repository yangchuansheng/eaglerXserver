# EaglercraftX Server

单镜像包含 EaglercraftX 1.8 / 1.12 客户端与 Paper 1.8.8 / 1.12.2 服务端。启动时通过 `MINECRAFT_VERSION` 选择一套运行资源。

## 端口

| 端口 | 用途 | 部署边界 |
|------|------|----------|
| 5200 | WebSocket 游戏连接与公开静态文件 | 对玩家发布 |
| 5201 | 管理面、HTTP 回退与 Dynmap 代理 | 绑定宿主机 `127.0.0.1` |
| 25565 | Paper | 容器内 localhost |
| 25575 | RCON | 容器内 localhost |

## 快速启动

```bash
docker pull registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1

# Paper 1.12.2
docker run -d -p 5200:5200 \
  -e MINECRAFT_VERSION=1.12 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1

# Paper 1.8.8
docker run -d -p 5200:5200 \
  -e MINECRAFT_VERSION=1.8 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

游戏入口为 `http://<host>:5200`。启动必须显式提供 `MINECRAFT_VERSION=1.8` 或 `MINECRAFT_VERSION=1.12`。

## 本机管理面

设置 `RCON_PASSWORD` 后启用管理 API，并把 5201 发布到宿主机回环地址：

```bash
docker run -d \
  -p 5200:5200 \
  -p 127.0.0.1:5201:5201 \
  -e MINECRAFT_VERSION=1.12 \
  -e RCON_PASSWORD=你的密码 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

管理面板地址为 `http://127.0.0.1:5201/admin`。管理员密码仅发送到 `/api/login`；登录成功后，浏览器把令牌保存在 `sessionStorage`，管理请求统一使用令牌。令牌默认有效 8 小时，关闭浏览器会话会清理本地登录态。

远程管理采用以下任一受信任通道：

- HTTPS 反向代理，上游指向 `127.0.0.1:5201`
- VPN 访问宿主机管理网络
- SSH 隧道：`ssh -L 5201:127.0.0.1:5201 <host>`

## 持久化运行目录

推荐把整个运行目录挂载到 `/eaglerX-1.8-server`。首次使用空目录时，入口脚本从镜像模板初始化完整资源；已有内容且结构残缺时，入口脚本保留原数据并退出。

```bash
# 1.12
docker run -d \
  -p 5200:5200 \
  -p 127.0.0.1:5201:5201 \
  -v /data/eagler-1.12:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.12 \
  -e RCON_PASSWORD=你的密码 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1

# 1.8
docker run -d \
  -p 5200:5200 \
  -p 127.0.0.1:5201:5201 \
  -v /data/eagler-1.8:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.8 \
  -e RCON_PASSWORD=你的密码 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

并行运行两个版本时，为每个容器配置独立挂载目录和宿主机端口，例如第二个容器使用 `-p 5300:5200 -p 127.0.0.1:5301:5201`。

## 管理 API

请求体上限为 64 KiB，读取超时为 10 秒。
登录失败按来源地址累计；共享本机回环、SSH 隧道或反向代理来源时，管理员共享同一个 10 分钟锁定窗口。

```bash
# 1. 登录并取得令牌
curl -s http://127.0.0.1:5201/api/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"你的密码"}'

# 2. 使用返回的 token 调用管理 API
curl -s http://127.0.0.1:5201/api/rcon \
  -H 'Content-Type: application/json' \
  -d '{"command":"list","token":"登录返回的令牌"}'
```

同一来源连续 5 次登录失败后锁定 10 分钟。

## 生命周期

入口脚本按 Bungee、Paper、HTTP 的顺序启动服务并持续监控。任一核心服务退出时，容器依次停止其余服务并返回失败状态；收到 `SIGTERM` 或 `SIGINT` 时执行有序停服。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINECRAFT_VERSION` | 必填 | `1.8` 或 `1.12` |
| `RCON_PASSWORD` | 空 | 设置后启用 RCON 与管理 API |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | 管理令牌有效期，单位为秒 |
| `ADMIN_AUTH_SECRET` | 从 RCON 密码派生 | 可选的令牌签名密钥 |

## 构建

```bash
docker build -t eaglerx1.8server .
./build.sh 2.1
./build.sh 2.1 push
```

## Credits

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- Upstream: https://github.com/burgerhugger/ALL-server
