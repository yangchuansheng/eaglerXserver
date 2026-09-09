# EaglercraftX Server

使用 Docker 部署可持久化的 Minecraft 瀏覽器遊戲伺服器，並透過管理介面管理玩家、世界與外掛。映像檔包含 EaglercraftX 1.8 / 1.12 用戶端及 Paper 1.8.8 / 1.12.2 伺服器，啟動時選擇遊戲版本。

![EaglercraftX 管理介面](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | **繁體中文** | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[快速開始](#快速開始) · [加入伺服器](#加入伺服器) · [管理介面與外掛](#管理介面與外掛) · [備份與升級](#備份升級與回復舊版) · [疑難排解](#日常維護與疑難排解) · [環境變數](#環境變數) · [管理 API](#管理-api) · [開發與發佈](#開發建置與發佈) · [問題回報](#問題回報)

## 功能

| 功能 | 說明 |
|------|------|
| 伺服器管理 | Paper 就緒狀態、線上玩家、每秒刻數（TPS）、天氣、時間、遊戲規則、設定與受控重新啟動 |
| 玩家與世界 | 管理員權限（OP）、白名單、踢出、封鎖、傳送、物品指令、世界儲存與邊界 |
| 外掛管理 | 各遊戲版本使用獨立儲存庫；支援上傳、啟用、停用與刪除，重新啟動 Paper 後生效 |
| 地圖與種子碼 | 內嵌 Dynmap、玩家位置、原生結構查詢與外部 Seed Map 連結 |
| 內建外掛 | LoginSecurity、SimpleHomes、SimpleTpa、WorldEdit、Dynmap |

## 快速開始

### 1. 準備主機

- **主機**：安裝 Docker 並準備持久化儲存空間。範例採用 Linux 路徑。發佈映像檔以 AMD64 為目標；ARM64 模擬執行及原生函式庫相容性需另行驗證，請參閱[架構決策](../adr/0006-publish-linux-amd64-only.md)。
- **記憶體**：Paper 與 Bungee 分別使用 `-Xms256M -Xmx256M`。請為 JVM 堆積以外的記憶體、世界生成及外掛預留空間。調整堆積大小時，編輯對應執行目錄中的 `run.sh`。
- **EULA**：啟動指令碼會寫入 `eula=true`。部署前請閱讀並接受 [Minecraft EULA](https://www.minecraft.net/en-us/eula)。

### 2. 啟動 Paper 1.12.2

在伺服器上執行下列指令。將 `YOUR_SERVER` 換成玩家可連線的 IP 位址或網域，並將 `replace-with-a-strong-password` 換成管理密碼。

此範例將主機的 `/data/eagler-1.12` 掛載至容器內的 `/eaglerX-1.8-server`，持久化**整個執行目錄**，涵蓋世界、外掛、設定與前端檔案。首次使用空目錄時會自動初始化；現有目錄結構不完整時，啟動程序會保留內容並結束。既有部署請依照[備份、升級與回復舊版](#備份升級與回復舊版)遷移執行檔案。

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

### 3. 開啟管理介面並確認就緒

| 入口 | 位址 | 使用方式 |
|------|------|----------|
| 遊戲 | `http://YOUR_SERVER:5200/` | 分享給玩家，並依照[加入步驟](#加入伺服器)連線 |
| 管理介面 | `http://127.0.0.1:5201/admin` | 從主機開啟，以啟動時設定的管理密碼登入 |

首次生成世界可能需要幾分鐘。管理介面顯示 **Paper is ready** 即表示啟動完成。等待過久或發生錯誤時，請參閱[日常維護與疑難排解](#日常維護與疑難排解)。

### 遠端管理與連接埠

遠端管理伺服器時，請在自己的電腦建立 SSH 通道，將 `user@YOUR_SERVER` 換成伺服器的 SSH 登入位址：

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

保持通道連線，再開啟 `http://127.0.0.1:5201/admin`。也可使用 HTTPS 反向代理，以上游主機的 `127.0.0.1:5201` 為目標；VPN 管理入口需能將流量轉送至該回送位址。

| 連接埠 | 用途 | 存取範圍 |
|------|------|----------|
| 5200 | HTTP 遊戲頁面、公開靜態檔案與 WebSocket 遊戲連線 | 對玩家開放 |
| 5201 | 管理介面、HTTP 備援與 Dynmap 代理 | 綁定主機的 `127.0.0.1` |
| 25565 | Paper | 容器內的 localhost |
| 25575 | RCON | 容器內的 localhost |

### 自訂網域、HTTPS 與遊戲網址

將 `PUBLIC_GAME_URL` 設為**玩家實際使用的 HTTP(S) 遊戲網址**。管理介面會據此產生快速加入連結及 `ws` / `wss` 位址。留空時，會依管理介面目前的主機名稱與連接埠 5200 推導 HTTP 網址（`http://主机名:5200/`）。使用 SSH 通道、獨立管理網域或自訂遊戲連接埠時，請明確設定此值。

HTTPS 遊戲入口需要 DNS、憑證，以及轉送至 **5200** 的 HTTP 與 WebSocket 代理；管理代理則指向 **5201**。`PUBLIC_GAME_URL` 僅用來產生連線位址，代理與憑證須在部署環境中設定。

### 選擇 1.8 或同時執行兩個版本

`2.2.5` 是映像檔發佈版本。`MINECRAFT_VERSION=1.8` 選擇 Paper 1.8.8，`1.12` 選擇 Paper 1.12.2。每個容器一次執行一個遊戲版本，並使用獨立執行目錄。

若要執行 1.8，請調整快速開始指令中的下列參數：

| 參數 | 單獨執行 1.8 | 與 1.12 同時執行 1.8 |
|------|-------------|---------------------|
| 容器名稱 | `--name eaglerx-1.8` | 同左 |
| 遊戲版本 | `-e MINECRAFT_VERSION=1.8` | 同左 |
| 完整執行目錄掛載 | `-v /data/eagler-1.8:/eaglerX-1.8-server` | 同左 |
| 遊戲連接埠 | `-p 5200:5200` | `-p 5300:5200` |
| 管理連接埠 | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| 公開遊戲網址 | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

將 `PUBLIC_GAME_URL` 設為該執行個體的網址。遠端管理第二個執行個體時，使用 `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` 並開啟 `http://127.0.0.1:5301/admin`。

## 加入伺服器

1. 開啟遊戲網址，或使用服主從管理介面 Overview 頁面分享的快速加入連結。多人遊戲清單已預設包含本伺服器：用戶端會依頁面網址推導 `ws://` 或 `wss://` 遊戲位址，因此自訂連接埠與 HTTPS 遊戲入口無需額外設定；快速加入連結會直接連線。若要加入其他伺服器，請在多人遊戲中加入其 `ws://HOST:5200/` 位址。
2. 首次進入時，依 LoginSecurity 提示輸入 `/register <password>`；之後使用 `/login <password>` 登入。預設要求註冊，密碼至少 6 個字元，登入逾時為 30 秒。
3. LoginSecurity 管理玩家帳號密碼；管理介面使用服主設定的 `RCON_PASSWORD`。

SimpleHomes 提供 `/sethome <name>`、`/home <name>` 與 `/homes`。SimpleTpa 提供 `/tpa <player>`、`/tpaccept` 與 `/tpdeny`。權限與行為依目前外掛設定而定。

## 管理介面與外掛

### 登入與變更生效時間

設定 `RCON_PASSWORD` 後會啟用 RCON 與管理 API。登入成功後，瀏覽器會在目前工作階段儲存管理權杖，預設有效 8 小時；登出會清除本機權杖。介面預設為英文，支援簡體中文，並會記住目前網站的語言選擇。

Paper 啟動期間即可登入管理介面；遊戲操作會在 Paper 就緒後開放。

| 操作 | 生效時間 |
|------|----------|
| 天氣、時間、遊戲規則、玩家與白名單指令 | 傳送至目前執行中的 Paper，請查看主控台回應 |
| MOTD、人數上限、視距與 PVP 等伺服器設定 | 寫入 `server.properties`，重新啟動 Paper 後生效 |
| 外掛上傳、啟用、停用與刪除 | 儲存至外掛儲存庫，重新啟動 Paper 後生效 |
| 管理介面的 Minecraft 重新啟動操作 | 受控重新啟動 Paper，Bungee 與管理介面持續執行 |
| 從管理介面關閉伺服器，或在主控台執行 `stop` | Paper 結束後觸發整個容器關閉 |

Dynmap 透過管理介面的 `/dynmap/` 代理存取。原生結構查詢使用映像檔內建的 cubiomes 元件；結構與近似出生點依世界種子碼計算，玩家位置來自 Dynmap 或玩家存檔。開啟外部 Seed Map 時，目標網址會包含世界種子碼。

### 外掛儲存庫與資料

目前版本的儲存庫位於 `server-data/plugins-1.8` 或 `server-data/plugins-1.12`。`enabled/` 目錄儲存啟用的外掛套件與資料，`disabled/` 儲存停用套件。Paper 的 `plugins` 路徑指向目前儲存庫的 `enabled/` 目錄。

首次啟動會匯入內建外掛套件與資料；後續啟動保留儲存庫現有狀態，包括手動編輯、停用套件與刪除結果。掛載完整執行目錄即可持久化這些資料。

管理介面會顯示目前遊戲版本、外掛檔案大小、修改時間、下次啟動狀態，以及是否等待重新啟動：

- 上傳檔案須為 JAR，且封存檔根目錄包含 `plugin.yml`。檔名須以小寫 `.jar` 結尾，大小上限為 **64 MiB**；檔名重複時會回傳衝突。
- 上傳、啟用、停用或刪除外掛後，請使用管理介面的重新啟動操作載入新組合。已載入的程式碼會持續執行至 Paper 停止。
- 刪除外掛會移除 JAR，並保留設定與資料庫。重新安裝使用相同資料目錄的相容外掛，即可沿用資料。
- JAR 以 Paper 程序的權限執行。請使用可信來源，安裝前審查及掃描套件，並完成備份。

<details>
<summary>既有世界與獨立資料目錄（舊版相容）</summary>

`PERSISTENT_DATA_ROOT` 設定外掛儲存庫與舊版世界掛載共用的根目錄，`SERVER_DATA_DIR` 為其相容別名。預設部署方式為掛載完整執行目錄。

**空的獨立資料目錄只會初始化外掛儲存庫。** 建立世界軟連結需要該資料根目錄中已存在對應世界。新生成的世界會留在各版本的 `server-版本/` 目錄，並由完整執行目錄掛載持久化。

遷移既有世界前，請先停服並備份，再準備 `<level-name>`、`<level-name>_nether` 與 `<level-name>_the_end` 目錄，其預設名稱為 `world`、`world_nether` 與 `world_the_end`。進入點可回退使用這些預設名稱，並保留伺服器路徑上已有的實體世界目錄。每個版本使用獨立資料根目錄，啟動後逐一確認世界軟連結的實際目標。

</details>

## 備份、升級與回復舊版

### 停服備份

下列指令使用快速開始範例中的容器與掛載目錄。備份包含世界、玩家狀態、外掛資料、設定、驗證資料庫及管理密碼，請存放於限制存取的目錄。

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

日常備份完成後執行 `docker start eaglerx-1.12`。升級期間保持舊容器停止。使用外部 `PERSISTENT_DATA_ROOT` 時，也需備份該根目錄；tar 預設保留軟連結本身。

進入點收到停止訊號後，先給 Paper 最多 30 秒結束，再給 Bungee 最多 10 秒。範例的 Docker 停止逾時設為 45 秒，為此流程預留時間，請參閱 [Docker 停止行為](https://docs.docker.com/reference/cli/docker/container/stop/)。

### 在新目錄準備升級

**完整執行目錄只在首次啟動時由映像檔初始化。** 更換映像檔後，現有掛載仍會提供伺服器、前端與 Python 後端檔案。升級需明確更新執行檔案，並遷移持久化狀態。

**第一步：停服備份。** 保留舊容器、執行目錄與映像檔版本。

**第二步：準備新執行目錄。** 從目標映像檔複製完整範本。此範例使用 `2.2.5`；請選擇尚未使用的範本容器名稱與目錄：

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

範本容器保持未啟動狀態。[docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) 支援從停止的容器複製檔案。複製範本後，再遷移舊目錄中的持久化狀態：

| 資料 | 遷移方式 |
|------|----------|
| `server-1.12/<level-name>` 及其 Nether 與 End 目錄 | 複製完整世界，並讓 `level-name` 與目錄名稱一致 |
| `server-data/` | 複製完整外掛儲存庫、標記檔案與舊版世界目錄 |
| Paper 的 `*.properties`、`*.yml` 與 `*.json` 檔案 | 對照新範本合併設定，保留管理員、白名單、封鎖與玩家快取 |
| Bungee 設定、驗證資料庫與外觀快取 | 逐項遷移設定與資料庫，並檢查根目錄及外掛目錄中的自訂狀態 |
| 自訂前端檔案、外掛與啟動選項 | 視需要合併客製內容；伺服器 JAR、指令碼與管理資產使用目標映像檔版本 |

進入點會重新建立 `server/`、`web/` 與 Paper `plugins` 軟連結。外部資料目錄須先複製至新的主機目錄，再由新容器掛載至原本的容器路徑；舊資料根目錄保留給舊容器。遷移清單也應涵蓋其他版本與自訂世界的狀態。

**第三步：啟動新容器。** 使用[快速開始指令](#2-啟動-paper-1122)，將容器名稱改為 `eaglerx-1.12-next`、主機目錄改為 `/data/eagler-1.12-next`，映像檔改為目標版本。保留原本的遊戲版本、密碼、公開網址與連接埠對應。

**第四步：驗證遷移結果。** 確認 Paper 就緒、玩家可加入、既有世界完整、外掛載入，以及白名單與地圖正常。驗證完成後，再設定舊容器、映像檔與備份的保留期限。

### 回復舊版與資料還原

保留舊容器與目錄的情況下，停止新容器，再啟動舊容器：

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

回復舊版會恢復舊目錄儲存的狀態。請先保留新容器執行期間產生的資料，以便後續還原。使用壓縮備份還原時，將其解壓縮至新目錄，再把解出的 `eagler-1.12` 目錄掛載為完整執行目錄，並使用該備份對應的映像檔版本與啟動選項。

## 日常維護與疑難排解

下列指令使用預設容器名稱：

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

Paper 與 Bungee 在 tmux 中執行。上述 Paper 主控台使用預設窗格 `mcserver:0.1`，Bungee 使用 `mcserver:0.0`。Docker 健康檢查探測 5200、5201 與 25565 連接埠；管理介面另外探測 RCON，以判斷 Paper 是否就緒。

| 現象 | 檢查項目 |
|------|------------|
| 容器立即結束 | 確认 `MINECRAFT_VERSION` 為 `1.8` 或 `1.12`，並查看記錄中的具體錯誤 |
| 啟動時回報執行目錄不完整 | 初始化空目錄或還原完整備份，並保留目前目錄供調查 |
| 管理介面可開啟，Paper 仍在啟動 | 查看 Paper 主控台的世界生成與外掛載入進度；Paper 就緒後介面會自動更新 |
| 遠端管理介面無法連線 | 檢查 SSH 通道或管理代理能否連至主機的 `127.0.0.1:5201` |
| 快速加入位址錯誤或 HTTPS 連線失敗 | 檢查 `PUBLIC_GAME_URL`、公開連接埠及遊戲代理的 WebSocket 轉送 |
| `/api/status` 回傳 404 | 設定 `RCON_PASSWORD` 並重新建立容器，啟動指令碼會據此啟用 RCON |
| 登入回傳 429 | 同一來源在失敗時間範圍內累積 5 次失敗，會鎖定 10 分鐘；通道或代理後的管理員可能共用來源 |
| 設定或外掛變更已儲存，仍維持舊行為 | 使用管理介面的受控 Paper 重新啟動，再檢查執行狀態 |
| Dynmap 回傳 502 | 確認 Dynmap 已啟用並完成載入，再檢查 HTTP 監聽位址與連接埠 |
| 原生結構查詢失敗 | 檢查 `linux/amd64` 執行環境、原生函式庫載入錯誤與世界種子碼讀取結果 |

進入點依序啟動 Bungee、Paper 與 HTTP，並持續監控。任一核心服務結束時，會關閉整個容器並回傳失敗狀態；收到 `SIGTERM` / `SIGINT` 時會依序正常關閉。請依部署需求設定重新啟動策略，並考量管理介面關服所觸發的容器結束。

## 環境變數

透過 `docker run -e` 傳入。修改容器環境變數時，使用既有掛載重新建立容器。

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `MINECRAFT_VERSION` | 必填 | `1.8` 選擇 Paper 1.8.8；`1.12` 選擇 Paper 1.12.2 |
| `RCON_PASSWORD` | 空 | 設定後啟用 RCON 與管理 API；留空時關閉需要驗證的管理端點 |
| `PUBLIC_GAME_URL` | 空 | 用來產生快速加入連結與 WebSocket 位址的公開 HTTP(S) 遊戲網址 |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | 外掛儲存庫與既有世界舊版掛載的根目錄；空目錄會自動初始化外掛儲存庫 |
| `SERVER_DATA_DIR` | 空 | `PERSISTENT_DATA_ROOT` 的相容別名，明確設定後者時以後者為優先 |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | 管理權杖有效期限，單位為秒 |
| `ADMIN_AUTH_SECRET` | 由 RCON 密碼衍生 | 選用的權杖簽章密鑰 |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | 管理後端使用的 Dynmap 上游位址 |

## 管理 API

供指令碼整合使用，所有端點均使用管理連接埠 **5201**。日常操作可透過管理介面完成。

<details>
<summary>端點、驗證與 curl 範例</summary>

「公開」指端點本身的驗證要求。請透過 [SSH 通道或管理代理](#遠端管理與連接埠)存取管理連接埠。

| 端點 | 存取要求 |
|------|----------|
| `GET /api/connection-info` | 隨時可用，回傳公開遊戲入口設定 |
| `GET /api/status` | RCON 啟用後可用，回傳 Paper 狀態及相關資訊 |
| `POST /api/login` | RCON 啟用後，以管理密碼換取權杖 |
| `POST /api/rcon`、`/api/config`、`/api/system` 與 `/api/plugins` 等 JSON 管理端點 | 請求本文須包含有效的 `token` |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`、原始 JAR 請求本文與 `X-Plugin-Filename` 標頭 |
| `GET /dynmap/` | 直接代理至 Dynmap，存取保護由管理連線提供 |

JSON 管理請求的本文上限為 64 KiB，讀取逾時為 10 秒；原始外掛 JAR 上傳上限為 64 MiB，總讀取期限為 30 秒。共用通道或反向代理來源的管理員，可能共用登入失敗鎖定時間範圍。

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

## 開發、建置與發佈

### 本機修改與驗證

安裝 Python 3 與 Docker 後，在儲存庫根目錄執行下列指令。於 `web-1.8/` 編輯管理資產，再執行同步指令碼更新 `web-1.12/`。基礎映像檔與原生函式庫需求請參閱[執行環境基礎映像檔決策](../adr/0007-retain-the-verified-runtime-base.md)。

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

本機發佈檢查還需要 Node.js、tmux、`agent-browser` 與可正常啟動的 Chrome。CI 固定使用 `agent-browser@0.26.0`，安裝步驟請參閱[發佈工作流程](../../.github/workflows/release.yml)。

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

本機檢查涵蓋 Python 語法、伺服器與外掛迴歸測試、雙版本資源、管理資產，以及英文與簡體中文的瀏覽器操作。瀏覽器檢查使用本機 Mock Admin API；完整發佈驗證還會建置映像檔並執行兩個 Paper 版本：

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

完整 `--live` 檢查通過後，檢查流程才會將 `summary.json` 中的 `release_ready` 設為 `true`。檢查範圍、證據格式與 Linux 暫存掛載權限，請參閱[發佈檢查文件](../release-gate.md)。

### 發佈版本

正式發佈使用 `vMAJOR.MINOR` 或 `vMAJOR.MINOR.PATCH` Git 標籤。工作流程對同一映像檔執行完整檢查，再發佈至 GHCR，附上版本與提交 SHA 標籤及建置來源證明。最高版本的自動發佈會更新 `latest`；手動重新執行只更新指定版本與 SHA 標籤。

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` 封裝本機建置流程，其 `push` 參數會直接推送映像檔。正式發佈遵循[完整 live gate 要求](../adr/0005-require-the-live-release-gate.md)及上述標籤工作流程。

## 問題回報

部署問題與功能建議請透過 [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues)提出。請附上映像檔標籤、`MINECRAFT_VERSION`、主機架構、已遮蔽敏感資訊的啟動選項、重現步驟及相關錯誤記錄；送出前請移除密碼與權杖。

## 致謝

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [上游專案](https://github.com/burgerhugger/ALL-server)
