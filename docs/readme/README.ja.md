# EaglercraftX Server

プレイヤーがブラウザーから参加できる Minecraft サーバーを、永続ストレージとプレイヤー・ワールド・プラグインを管理する管理パネル付きで運用できます。Docker イメージには EaglercraftX 1.8 / 1.12 クライアントと Paper 1.8.8 / 1.12.2 サーバーが含まれ、起動時にゲームのバージョンを選択します。

![EaglercraftX 管理パネル](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | **日本語** | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[クイックスタート](#クイックスタート) · [サーバーへの参加](#サーバーへの参加) · [管理パネルとプラグイン](#管理パネルとプラグイン) · [バックアップと更新](#バックアップ更新ロールバック) · [トラブルシューティング](#運用とトラブルシューティング) · [環境変数](#環境変数) · [管理 API](#管理-api) · [開発とリリース](#開発ビルドリリース) · [問題の報告](#問題の報告)

## 機能

| 機能 | 内容 |
|------|------|
| サーバー管理 | Paper の準備状態、オンラインプレイヤー、毎秒の tick 数（TPS）、天候、時刻、ゲームルール、設定、管理機能による再起動 |
| プレイヤーとワールド | オペレーター権限（OP）、ホワイトリスト、キック、BAN、テレポート、アイテムコマンド、ワールド保存、ワールド境界 |
| プラグイン管理 | バージョン別のリポジトリでアップロード、有効化、無効化、削除に対応。変更は Paper の再起動後に適用 |
| マップとシード | 埋め込み Dynmap、プレイヤー位置、ネイティブ構造物検索、外部 Seed Map へのリンク |
| 同梱プラグイン | LoginSecurity、SimpleHomes、SimpleTpa、WorldEdit、Dynmap |

## クイックスタート

### 1. ホストの準備

- **ホスト**：Docker をインストールし、永続ストレージを用意します。例では Linux のパスを使用します。公開イメージは AMD64 向けです。ARM64 エミュレーションとネイティブライブラリの互換性は別途検証してください。[アーキテクチャの決定](../adr/0006-publish-linux-amd64-only.md)を参照してください。
- **メモリ**：Paper と Bungee はそれぞれ `-Xms256M -Xmx256M` を使用します。JVM のヒープ外メモリ、ワールド生成、プラグイン用にも余裕を確保してください。ヒープサイズは、該当する実行ディレクトリの `run.sh` で変更します。
- **EULA**：起動スクリプトは `eula=true` を書き込みます。デプロイ前に [Minecraft EULA](https://www.minecraft.net/en-us/eula) を読み、同意してください。

### 2. Paper 1.12.2 の起動

次のコマンドをサーバーで実行します。`YOUR_SERVER` をプレイヤーが接続できる IP アドレスまたはドメインに、`replace-with-a-strong-password` を管理用パスワードに置き換えてください。

この例ではホストの `/data/eagler-1.12` をコンテナ内の `/eaglerX-1.8-server` にマウントし、ワールド、プラグイン、設定、フロントエンドを含む**実行ディレクトリ全体**を永続化します。空のディレクトリは初回利用時に自動初期化されます。既存ディレクトリが不完全な場合は、内容を保持して起動処理を終了します。既存環境の実行ファイルの移行は[バックアップ・更新・ロールバック](#バックアップ更新ロールバック)に従ってください。

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

### 3. 管理パネルを開いて準備状態を確認

| 用途 | アドレス | 使用方法 |
|------|------|----------|
| ゲーム | `http://YOUR_SERVER:5200/` | プレイヤーに共有し、[参加手順](#サーバーへの参加)に従って接続 |
| 管理パネル | `http://127.0.0.1:5201/admin` | ホストから開き、起動時に設定した管理用パスワードでログイン |

初回のワールド生成には数分かかる場合があります。管理パネルに **Paper is ready** と表示されたら起動完了です。待機が長い場合やエラーが出た場合は[運用とトラブルシューティング](#運用とトラブルシューティング)を参照してください。

### リモート管理とポート

リモートサーバーを管理するには、手元のコンピューターで SSH トンネルを開きます。`user@YOUR_SERVER` をサーバーの SSH ログイン先に置き換えてください：

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

トンネルを開いたまま `http://127.0.0.1:5201/admin` にアクセスします。ホストの `127.0.0.1:5201` を転送先とする HTTPS リバースプロキシも利用できます。VPN 経由の管理アクセスでは、このループバックアドレスに通信を転送できる必要があります。

| ポート | 用途 | 公開範囲 |
|------|------|----------|
| 5200 | HTTP ゲームページ、公開静的ファイル、WebSocket ゲーム接続 | プレイヤー向けに公開 |
| 5201 | 管理パネル、HTTP フォールバック、Dynmap プロキシ | ホストの `127.0.0.1` にバインド |
| 25565 | Paper | コンテナ内の localhost |
| 25575 | RCON | コンテナ内の localhost |

### 独自ドメイン・HTTPS・ゲーム URL

`PUBLIC_GAME_URL` には**プレイヤーが実際に使用する HTTP(S) ゲーム URL**を設定します。管理パネルはこの値からクイック参加リンクと `ws` / `wss` アドレスを生成します。空の場合は管理パネルの現在のホスト名とポート 5200 から HTTP URL（`http://主机名:5200/`）を生成します。SSH トンネル、管理専用ドメイン、独自ゲームポートを使用する場合は明示的に設定してください。

HTTPS のゲームアクセスには DNS、証明書、**5200** への HTTP・WebSocket 転送が必要です。管理プロキシは **5201** に向けます。`PUBLIC_GAME_URL` は接続アドレスの生成専用で、プロキシと証明書はデプロイ環境で設定します。

### 1.8 の選択と両バージョンの同時運用

`2.2.5` はイメージのリリースバージョンです。`MINECRAFT_VERSION=1.8` は Paper 1.8.8、`1.12` は Paper 1.12.2 を選択します。各コンテナは一度に一つのゲームバージョンを実行し、独立した実行ディレクトリを使用します。

1.8 を実行するには、クイックスタートのコマンドで次のパラメーターを変更します：

| パラメーター | 1.8 のみを実行 | 1.12 と同時に 1.8 を実行 |
|------|-------------|---------------------|
| コンテナ名 | `--name eaglerx-1.8` | 左と同じ |
| ゲームバージョン | `-e MINECRAFT_VERSION=1.8` | 左と同じ |
| 実行ディレクトリ全体のマウント | `-v /data/eagler-1.8:/eaglerX-1.8-server` | 左と同じ |
| ゲームポート | `-p 5200:5200` | `-p 5300:5200` |
| 管理ポート | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| 公開ゲーム URL | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

`PUBLIC_GAME_URL` に対象インスタンスの URL を設定します。二つ目のインスタンスをリモート管理する場合は `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` を使い、`http://127.0.0.1:5301/admin` を開きます。

## サーバーへの参加

1. ゲーム URL、またはサーバー管理者が管理パネルの Overview ページから共有したクイック参加リンクを開きます。1.12 クライアントの初期サーバー一覧は空です。マルチプレイで `ws://YOUR_SERVER:5200/` を追加するか、HTTPS の場合は対応する `wss://` アドレスを使用します。
2. 初回は LoginSecurity の案内に従って `/register <password>` を入力します。次回からは `/login <password>` を使用します。初期設定では登録が必須で、パスワードは 6 文字以上、ログイン期限は 30 秒です。
3. プレイヤーのアカウントパスワードは LoginSecurity が管理します。管理パネルにはサーバー管理者の `RCON_PASSWORD` を使用します。

SimpleHomes では `/sethome <name>`、`/home <name>`、`/homes`、SimpleTpa では `/tpa <player>`、`/tpaccept`、`/tpdeny` を使用できます。権限と動作は現在のプラグイン設定に従います。

## 管理パネルとプラグイン

### ログインと変更の適用

`RCON_PASSWORD` を設定すると RCON と管理 API が有効になります。ログイン後、ブラウザーは現在のセッションに管理トークンを保持します。既定の有効期間は 8 時間です。ログアウトするとローカルトークンを削除します。画面は既定で英語で、簡体字中国語にも対応し、サイトごとの言語選択を記憶します。

Paper の起動中でもログインできます。ゲーム操作は Paper の準備が完了すると利用できます。

| 操作 | 適用のタイミング |
|------|----------|
| 天候、時刻、ゲームルール、プレイヤー・ホワイトリストのコマンド | 稼働中の Paper に送信。コンソールの応答を確認 |
| MOTD、人数上限、描画距離、PVP などのサーバー設定 | `server.properties` に書き込み、Paper の再起動後に適用 |
| プラグインのアップロード、有効化、無効化、削除 | リポジトリに保存し、Paper の再起動後に適用 |
| 管理パネルからの Minecraft 再起動 | Paper を制御して再起動。Bungee と管理パネルは稼働を継続 |
| 管理パネルからの停止、またはコンソールの `stop` | Paper の終了を受けてコンテナ全体を停止 |

Dynmap は管理パネルの `/dynmap/` プロキシ経由で利用します。ネイティブ構造物検索はイメージ同梱の cubiomes を使用します。構造物と概算のスポーン位置はワールドシードから計算し、プレイヤー位置は Dynmap またはプレイヤーの保存データから取得します。外部 Seed Map を開くと、移動先 URL にワールドシードが含まれます。

### プラグインのリポジトリとデータ

有効なバージョンのリポジトリは `server-data/plugins-1.8` または `server-data/plugins-1.12` にあります。`enabled/` に有効なパッケージとデータ、`disabled/` に無効なパッケージを保存します。Paper の `plugins` は有効なリポジトリの `enabled/` を参照します。

初回起動時に同梱パッケージとデータを取り込みます。以降は手動編集、無効化、削除を含む現在のリポジトリ状態を保持します。実行ディレクトリ全体のマウントで、これらのデータを永続化できます。

管理パネルには現在のゲームバージョン、ファイルサイズ、更新日時、次回起動時の状態、再起動待ちの有無が表示されます：

- アップロードはアーカイブのルートに `plugin.yml` を含む JAR に限ります。ファイル名の末尾は小文字の `.jar`、上限は **64 MiB** です。同名ファイルは競合として返されます。
- アップロード、有効化、無効化、削除後は管理パネルから再起動し、新しい構成を読み込みます。読み込み済みのコードは Paper が停止するまで動作します。
- 削除すると JAR を取り除き、設定とデータベースを保持します。同じデータディレクトリを使う互換プラグインを再インストールすれば、保存データを再利用できます。
- JAR は Paper プロセスの権限で実行されます。信頼できる提供元を選び、インストール前に内容確認とスキャン、バックアップを行ってください。

<details>
<summary>既存ワールドと独立データディレクトリ（従来方式の互換性）</summary>

`PERSISTENT_DATA_ROOT` はプラグインリポジトリと従来のワールドマウントに共通のルートを設定します。`SERVER_DATA_DIR` は互換エイリアスです。既定のデプロイ方式は実行ディレクトリ全体のマウントです。

**空の独立データディレクトリでは、プラグインリポジトリだけを初期化します。** ワールドのシンボリックリンクには、対応するワールドがデータルートに存在する必要があります。新しいワールドはバージョン別の `server-版本/` に残り、実行ディレクトリ全体のマウントで永続化されます。

既存ワールドの移行前にサーバーを停止してバックアップし、`<level-name>`、`<level-name>_nether`、`<level-name>_the_end` を用意します。既定名は `world`、`world_nether`、`world_the_end` です。エントリーポイントはこれらの既定名にフォールバックでき、サーバーパスに存在する実体のワールドディレクトリを保持します。バージョンごとにデータルートを分け、起動後に各リンクの実際の参照先を確認してください。

</details>

## バックアップ・更新・ロールバック

### サーバーを停止してバックアップ

次のコマンドはクイックスタートのコンテナとマウントを使用します。バックアップにはワールド、プレイヤー状態、プラグインデータ、設定、認証データベース、管理用パスワードが含まれます。アクセスを制限したディレクトリに保管してください。

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

通常のバックアップ後は `docker start eaglerx-1.12` を実行します。更新時は旧コンテナを停止したままにします。外部の `PERSISTENT_DATA_ROOT` を使用する場合は、そのルートもバックアップしてください。tar は既定でシンボリックリンク自体を保存します。

停止シグナルを受けると、エントリーポイントは Paper に最大 30 秒、続いて Bungee に最大 10 秒の終了時間を与えます。例では Docker の停止待ちを 45 秒として、この処理時間を確保します。[Docker の停止動作](https://docs.docker.com/reference/cli/docker/container/stop/)を参照してください。

### 新しいディレクトリで更新を準備

**実行ディレクトリ全体をイメージから初期化するのは初回起動時だけです。** イメージを変更した後も、既存のマウントからサーバー、フロントエンド、Python バックエンドのファイルを使用します。更新には実行ファイルの明示的な更新と永続データの移行が必要です。

**手順 1：停止してバックアップ。** 旧コンテナ、実行ディレクトリ、イメージのバージョンを保持します。

**手順 2：新しい実行ディレクトリを用意。** 対象イメージから完全なテンプレートをコピーします。この例は `2.2.5` を使います。未使用のテンプレートコンテナ名とディレクトリを選んでください：

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

テンプレートコンテナは未起動のままにします。[docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) は停止中のコンテナからのコピーに対応します。コピー後、旧ディレクトリから永続データを移行します：

| データ | 移行方法 |
|------|----------|
| `server-1.12/<level-name>` と Nether・End ディレクトリ | ワールド全体をコピーし、`level-name` をディレクトリ名と一致させる |
| `server-data/` | プラグインリポジトリ、マーカーファイル、従来のワールドディレクトリを丸ごとコピー |
| Paper の `*.properties`、`*.yml`、`*.json` | 新テンプレートに設定を統合し、OP、ホワイトリスト、BAN、プレイヤーキャッシュを保持 |
| Bungee 設定、認証データベース、スキンキャッシュ | 個別に移行し、ルートとプラグインディレクトリ内のカスタムデータも確認 |
| 独自フロントエンド、プラグイン、起動オプション | 必要な変更を統合し、サーバー JAR、スクリプト、管理用アセットは対象イメージのものを使用 |

エントリーポイントは `server/`、`web/`、Paper の `plugins` シンボリックリンクを再作成します。外部データは新しいホストディレクトリへコピーしてから、新コンテナの元と同じパスにマウントします。旧データルートは旧コンテナ用に保持してください。他バージョンと独自ワールドの状態も移行対象に含めます。

**手順 3：新コンテナを起動。** [クイックスタートのコマンド](#2-paper-1122-の起動)で名前を `eaglerx-1.12-next`、ホストディレクトリを `/data/eagler-1.12-next`、イメージを対象バージョンに変更します。ゲームバージョン、パスワード、公開 URL、ポート割り当ては元の設定を保持します。

**手順 4：移行を検証。** Paper の準備完了、プレイヤーの参加、既存ワールドの完全性、プラグイン読み込み、ホワイトリストとマップの動作を確認します。その後、旧コンテナ、イメージ、バックアップの保管期間を決めます。

### ロールバックと復元

旧コンテナとディレクトリを保持している場合は、新コンテナを停止して旧コンテナを起動します：

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

ロールバックすると旧ディレクトリに保存された状態に戻ります。新コンテナの稼働中に作成されたデータは、後から復元できるよう保持してください。圧縮バックアップは新ディレクトリへ展開し、展開された `eagler-1.12` を実行ディレクトリ全体としてマウントして、そのバックアップに対応するイメージと起動オプションを使用します。

## 運用とトラブルシューティング

次のコマンドは既定のコンテナ名を使用します：

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

Paper と Bungee は tmux で動作します。上記の Paper コンソールは既定のペイン `mcserver:0.1`、Bungee は `mcserver:0.0` を使用します。Docker ヘルスチェックは 5200、5201、25565 を確認します。管理パネルは RCON も確認し、Paper の準備状態を判断します。

| 症状 | 確認事項 |
|------|------------|
| コンテナがすぐ終了する | `MINECRAFT_VERSION` が `1.8` または `1.12` かを確認し、ログの具体的なエラーを調べる |
| 実行ディレクトリが不完全と表示される | 空ディレクトリを初期化するか完全バックアップを復元し、現在のディレクトリは調査用に保持 |
| 管理パネルは開くが Paper は起動中 | コンソールでワールド生成とプラグイン読み込みを確認。準備が完了するとパネルは自動更新 |
| リモート管理パネルに接続できない | SSH トンネルまたは管理プロキシがホストの `127.0.0.1:5201` に到達できるか確認 |
| クイック参加先が誤っている、または HTTPS 接続に失敗 | `PUBLIC_GAME_URL`、公開ポート、ゲームプロキシの WebSocket 転送を確認 |
| `/api/status` が 404 を返す | `RCON_PASSWORD` を設定してコンテナを再作成。起動スクリプトがこの値で RCON を有効化 |
| ログインが 429 を返す | 判定期間内に同一送信元から 5 回失敗すると 10 分間ロック。トンネルやプロキシ経由の管理者は送信元を共有する場合がある |
| 変更は保存されたが動作は以前のまま | 管理パネルから Paper を制御して再起動し、稼働状態を確認 |
| Dynmap が 502 を返す | 有効化と読み込み完了を確認し、HTTP 待受アドレスとポートを調べる |
| ネイティブ構造物検索が失敗する | `linux/amd64` 環境、ネイティブライブラリの読み込みエラー、シードの取得結果を確認 |

エントリーポイントは Bungee、Paper、HTTP の順に起動して継続監視します。主要サービスが終了するとコンテナ全体を停止し、失敗ステータスを返します。`SIGTERM` / `SIGINT` では順序立てて終了します。管理パネルからの停止もコンテナ終了を伴うことを踏まえ、再起動ポリシーを設定してください。

## 環境変数

`docker run -e` で渡します。環境変数を変更する場合は、既存マウントを使ってコンテナを再作成します。

| 変数 | 既定値 | 説明 |
|------|--------|------|
| `MINECRAFT_VERSION` | 必須 | `1.8` は Paper 1.8.8、`1.12` は Paper 1.12.2 を選択 |
| `RCON_PASSWORD` | 空 | 設定すると RCON と API を有効化。空の場合は認証が必要な管理エンドポイントを無効化 |
| `PUBLIC_GAME_URL` | 空 | クイック参加リンクと WebSocket アドレスを生成する公開 HTTP(S) ゲーム URL |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | プラグインリポジトリと従来方式の既存ワールドマウントのルート。空ディレクトリではリポジトリを自動初期化 |
| `SERVER_DATA_DIR` | 空 | `PERSISTENT_DATA_ROOT` の互換エイリアス。後者に明示した値を優先 |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | 管理トークンの有効期間（秒） |
| `ADMIN_AUTH_SECRET` | RCON パスワードから生成 | 任意のトークン署名用シークレット |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | 管理バックエンドが使用する Dynmap の転送先 |

## 管理 API

スクリプトとの連携向けです。すべてのエンドポイントは管理ポート **5201** を使用します。日常操作は管理パネルで行えます。

<details>
<summary>エンドポイント・認証・curl の例</summary>

「公開」はエンドポイント自体の認証要件を示します。管理ポートには [SSH トンネルまたは管理プロキシ](#リモート管理とポート)経由でアクセスしてください。

| エンドポイント | アクセス要件 |
|------|----------|
| `GET /api/connection-info` | 常時利用可能。公開ゲーム接続先の設定を返す |
| `GET /api/status` | RCON 有効時に利用可能。Paper 状態などを返す |
| `POST /api/login` | RCON 有効時、管理用パスワードをトークンに交換 |
| `POST /api/rcon`、`/api/config`、`/api/system`、`/api/plugins` などの JSON 管理エンドポイント | 本文に有効な `token` が必要 |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`、JAR バイナリのリクエスト本文、`X-Plugin-Filename` ヘッダー |
| `GET /dynmap/` | Dynmap へ直接転送。管理接続側でアクセスを保護 |

JSON 管理リクエストは本文 64 KiB、読み取りタイムアウト 10 秒です。JAR のアップロードは 64 MiB、読み取り全体の期限は 30 秒です。同じトンネルやリバースプロキシの送信元を共有する管理者は、ログインロックの判定期間を共有する場合があります。

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

## 開発・ビルド・リリース

### ローカルでの変更と検証

Python 3 と Docker を用意し、リポジトリのルートで次のコマンドを実行します。管理用アセットは `web-1.8/` で編集し、同期スクリプトで `web-1.12/` を更新します。ベースイメージとネイティブライブラリの要件は[実行環境のベースイメージ決定](../adr/0007-retain-the-verified-runtime-base.md)を参照してください。

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

ローカルのリリース検証には Node.js、tmux、`agent-browser`、起動可能な Chrome も必要です。CI は `agent-browser@0.26.0` に固定しています。導入手順は[リリースワークフロー](../../.github/workflows/release.yml)を参照してください。

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

ローカル検証は Python 構文、サーバーとプラグインの回帰、両バージョンの資源、管理アセット、英語・簡体字中国語のブラウザー操作を確認します。ブラウザーはローカル Mock Admin API を使います。完全なリリース検証ではイメージをビルドし、両方の Paper を実行します：

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

完全な `--live` 検証に合格した場合に限り、`summary.json` の `release_ready` を `true` に設定します。検証範囲、証跡形式、Linux の一時マウント権限は[リリースゲートの文書](../release-gate.md)を参照してください。

### リリースの公開

正式リリースには `vMAJOR.MINOR` または `vMAJOR.MINOR.PATCH` の Git タグを使用します。同一イメージで完全な検証を行った後、バージョン・コミット SHA のタグとビルド来歴の証明を付けて GHCR に公開します。最も高いバージョンの自動リリースが `latest` を更新し、手動再実行は指定バージョンと SHA タグだけを更新します。

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` はローカルビルドをまとめ、`push` 引数はイメージを直接プッシュします。正式な配布は[完全な live gate の要件](../adr/0005-require-the-live-release-gate.md)と前述のタグワークフローに従います。

## 問題の報告

デプロイの問題や機能要望は [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues) に報告してください。イメージタグ、`MINECRAFT_VERSION`、ホストアーキテクチャ、機密情報を伏せた起動オプション、再現手順、関連するエラーログを添えてください。送信前にパスワードとトークンを削除してください。

## 謝辞

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [上流プロジェクト](https://github.com/burgerhugger/ALL-server)
