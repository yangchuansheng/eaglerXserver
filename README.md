# EaglercraftX Server
- fork from https://github.com/burgerhugger/ALL-server
## Credits
eaglercraft and eaglercraftx: lax1dude (calder young)
<br>
eaglercraft server: ayunami2000
<br>
## Setup Guide
Welcome to the EaglercraftX server project! Here is how you can setup your very own eaglercraft server:
<br>
<br>
First, go to the top of the repo and click on code > codespaces > create codespace
<br>
now you have your own free server instance to host eaglercraft. Next you need to run the setup commands:
<br>
<br>
create 2 terminal tabs and paste in the following snipits:
<br>
<br>
first tab: `cd server && sudo java -jar server.jar`
<br>
<br>
second tab: `cd bungee && sudo java -jar bungee.jar`
<br>
<br>
Now go to the ports area and forward (and make public) ports `25565` and `8081`
<br>
Your eaglercraft server is setup!
---
# 教程参考 https://www.cnblogs.com/chenxuan520/p/18212461 重要
# 视频教程 [最简单的MC我的世界网页版联机服务器搭建\_我的世界](https://www.bilibili.com/video/BV1ey411q7mf/)
# 注意点
1. server文件夹的plugins目录可以直接删除,避免登录需要密码的问题
2. 最好用tmux进行分屏处理,服务端用的是paper,部署的时候先启动 bungee 再启动 server,顺序不能错
---
# 我修改的特性
1. 默认5200端口
2. Docker 直接部署
3. 双版本支持：Paper 1.8.8 + Paper 1.12.2，通过 `MINECRAFT_VERSION` 环境变量切换

---

# Docker 部署

## 双版本镜像说明

- 当前 Docker 镜像是**单镜像双版本**设计：同一个镜像同时包含 `server-1.8/`、`server-1.12/`、`web-1.8/`、`web-1.12/` 四套资源。
- 启动容器时必须**显式传入** `MINECRAFT_VERSION` 选择版本，入口脚本会把统一入口目录切到对应版本：
  - `web/ -> web-1.8/` 或 `web-1.12/`
  - `server/ -> server-1.8/` 或 `server-1.12/`
- 因此：**同一个镜像可以跑 1.8，也可以跑 1.12；但单个容器实例一次只能选择一个版本。**
- 如果你要同时运行 1.8 和 1.12，请起两个容器，并把宿主机数据目录分开挂载，避免世界数据和插件配置互相污染。
- 如果未传 `-e MINECRAFT_VERSION=1.8` 或 `-e MINECRAFT_VERSION=1.12`，容器会直接报错退出。

## 拉取镜像
```bash
docker pull registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

## 启动

### Paper 1.12.2
```bash
docker run -d -p 5200:5200 \
  -e MINECRAFT_VERSION=1.12 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

### Paper 1.8.8
```bash
docker run -d -p 5200:5200 -e MINECRAFT_VERSION=1.8 registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

### 开启 RCON
```bash
docker run -d -p 5200:5200 -p 5201:5201 \
  -e MINECRAFT_VERSION=1.12 \
  -e RCON_PASSWORD=你的密码 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

管理面板: `http://<host>:5201/admin`

### 推荐：挂载完整数据目录

当前镜像支持把整个运行目录挂载出来。第一次挂载空目录时，容器会自动初始化完整文件；后续世界、插件、配置和前端文件都会保存在宿主机。

```bash
# 1.12
docker run -d \
  -p 5200:5200 -p 5201:5201 \
  -v /data/eagler-1.12:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.12 \
  -e RCON_PASSWORD=你的密码 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1

# 1.8
docker run -d \
  -p 5200:5200 -p 5201:5201 \
  -v /data/eagler-1.8:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.8 \
  -e RCON_PASSWORD=你的密码 \
  registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

如果要同时开两个版本，请把端口错开，例如把第二个容器改成 `-p 5300:5200 -p 5301:5201`。

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `MINECRAFT_VERSION` | 无默认值，必填 | 服务端版本: `1.8` 或 `1.12` |
| `RCON_PASSWORD` | 无 | 设置后启用 RCON |

## 构建
```bash
docker build -t eaglerx1.8server .
./build.sh 2.1 push
```

构建出来的是**双版本通用镜像**，不是分别构建两个镜像。
