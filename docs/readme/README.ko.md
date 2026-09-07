# EaglercraftX Server

플레이어가 브라우저에서 접속할 수 있는 Minecraft 서버를 운영하세요. 영구 저장소와 플레이어, 월드, 플러그인을 관리하는 관리자 패널을 제공합니다. Docker 이미지에는 EaglercraftX 1.8 / 1.12 클라이언트와 Paper 1.8.8 / 1.12.2 서버가 포함되며, 시작할 때 게임 버전을 선택합니다.

![EaglercraftX 관리자 패널](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | **한국어** | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[빠른 시작](#빠른-시작) · [서버 접속](#서버-접속) · [관리자 패널과 플러그인](#관리자-패널과-플러그인) · [백업과 업그레이드](#백업-업그레이드-및-롤백) · [문제 해결](#운영-및-문제-해결) · [환경 변수](#환경-변수) · [관리 API](#관리-api) · [개발과 릴리스](#개발-빌드-및-릴리스) · [문제 보고](#문제-보고)

## 기능

| 기능 | 설명 |
|------|------|
| 서버 관리 | Paper 준비 상태, 온라인 플레이어, 초당 틱 수(TPS), 날씨, 시간, 게임 규칙, 설정, 제어된 재시작 |
| 플레이어와 월드 | 운영자 권한(OP), 화이트리스트, 추방, 차단, 순간이동, 아이템 명령, 월드 저장과 경계 |
| 플러그인 관리 | 게임 버전별 저장소에서 업로드, 활성화, 비활성화, 삭제 지원. 변경 사항은 Paper 재시작 후 적용 |
| 지도와 시드 | 내장 Dynmap, 플레이어 위치, 네이티브 구조물 검색, 외부 Seed Map 링크 |
| 기본 제공 플러그인 | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## 빠른 시작

### 1. 호스트 준비

- **호스트**: Docker를 설치하고 영구 저장소를 준비하세요. 예제는 Linux 경로를 사용합니다. 배포 이미지는 AMD64를 대상으로 하며, ARM64 에뮬레이션과 네이티브 라이브러리 호환성은 별도로 검증해야 합니다. [아키텍처 결정](../adr/0006-publish-linux-amd64-only.md)을 참고하세요.
- **메모리**: Paper와 Bungee는 각각 `-Xms256M -Xmx256M`을 사용합니다. JVM의 힙 외 메모리, 월드 생성, 플러그인을 위한 여유 메모리도 확보하세요. 힙 크기는 해당 실행 디렉터리의 `run.sh`에서 조정합니다.
- **EULA**: 시작 스크립트는 `eula=true`를 기록합니다. 배포 전에 [Minecraft EULA](https://www.minecraft.net/en-us/eula)를 읽고 동의하세요.

### 2. Paper 1.12.2 시작

다음 명령을 서버에서 실행하세요. `YOUR_SERVER`를 플레이어가 접속할 수 있는 IP 주소나 도메인으로, `replace-with-a-strong-password`를 관리자 비밀번호로 바꾸세요.

이 예제는 호스트의 `/data/eagler-1.12`를 컨테이너 내부의 `/eaglerX-1.8-server`에 마운트하여 월드, 플러그인, 설정, 프런트엔드 파일을 포함한 **전체 실행 디렉터리**를 영구 보관합니다. 빈 디렉터리는 처음 사용할 때 자동으로 초기화됩니다. 기존 디렉터리가 불완전하면 내용을 보존한 채 시작을 종료합니다. 기존 배포의 실행 파일을 옮길 때는 [백업, 업그레이드 및 롤백](#백업-업그레이드-및-롤백)을 따르세요.

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

### 3. 관리자 패널을 열고 준비 상태 확인

| 용도 | 주소 | 사용 방법 |
|------|------|----------|
| 게임 | `http://YOUR_SERVER:5200/` | 플레이어에게 공유하고 [접속 안내](#서버-접속)를 따르세요 |
| 관리자 패널 | `http://127.0.0.1:5201/admin` | 호스트에서 열고 시작 시 설정한 관리자 비밀번호로 로그인하세요 |

첫 월드 생성에는 몇 분이 걸릴 수 있습니다. 패널에 **Paper is ready**가 표시되면 시작이 완료된 것입니다. 대기가 길어지거나 오류가 발생하면 [운영 및 문제 해결](#운영-및-문제-해결)을 확인하세요.

### 원격 관리와 포트

원격 서버를 관리하려면 자신의 컴퓨터에서 SSH 터널을 여세요. `user@YOUR_SERVER`를 서버의 SSH 로그인 주소로 바꾸세요:

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

터널을 열어 둔 채 `http://127.0.0.1:5201/admin`에 접속하세요. 호스트의 `127.0.0.1:5201`을 업스트림으로 사용하는 HTTPS 리버스 프록시도 가능합니다. VPN 관리 진입점은 해당 루프백 주소로 트래픽을 전달할 수 있어야 합니다.

| 포트 | 용도 | 공개 범위 |
|------|------|----------|
| 5200 | HTTP 게임 페이지, 공개 정적 파일, WebSocket 게임 연결 | 플레이어에게 공개 |
| 5201 | 관리자 패널, HTTP 대체 서비스, Dynmap 프록시 | 호스트의 `127.0.0.1`에 바인딩 |
| 25565 | Paper | 컨테이너 내부 localhost |
| 25575 | RCON | 컨테이너 내부 localhost |

### 사용자 도메인, HTTPS 및 게임 URL

`PUBLIC_GAME_URL`에는 **플레이어가 실제 사용하는 HTTP(S) 게임 URL**을 설정하세요. 패널은 이 값으로 빠른 접속 링크와 `ws` / `wss` 주소를 만듭니다. 비워 두면 현재 패널 호스트 이름과 5200 포트로 HTTP URL을 생성합니다(`http://主机名:5200/`). SSH 터널, 별도 관리자 도메인, 사용자 지정 게임 포트를 사용하면 명시적으로 설정하세요.

HTTPS 게임 접속에는 DNS, 인증서, **5200**으로 전달하는 HTTP 및 WebSocket 설정이 필요합니다. 관리 프록시는 **5201**로 연결하세요. `PUBLIC_GAME_URL`는 연결 주소 생성에만 쓰이며, 프록시와 인증서는 배포 환경에서 설정합니다.

### 1.8 선택 또는 두 버전 동시 실행

`2.2.5`는 이미지 릴리스 버전입니다. `MINECRAFT_VERSION=1.8`은 Paper 1.8.8을, `1.12`는 Paper 1.12.2를 선택합니다. 각 컨테이너는 한 번에 하나의 게임 버전을 실행하며 독립된 실행 디렉터리를 사용합니다.

1.8을 실행하려면 빠른 시작 명령에서 다음 매개변수를 변경하세요:

| 매개변수 | 1.8만 실행 | 1.12와 함께 1.8 실행 |
|------|-------------|---------------------|
| 컨테이너 이름 | `--name eaglerx-1.8` | 왼쪽과 같음 |
| 게임 버전 | `-e MINECRAFT_VERSION=1.8` | 왼쪽과 같음 |
| 전체 실행 디렉터리 마운트 | `-v /data/eagler-1.8:/eaglerX-1.8-server` | 왼쪽과 같음 |
| 게임 포트 | `-p 5200:5200` | `-p 5300:5200` |
| 관리 포트 | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| 공개 게임 URL | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

`PUBLIC_GAME_URL`를 해당 인스턴스의 URL로 설정하세요. 두 번째 인스턴스의 원격 관리는 `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER`을 사용하고 `http://127.0.0.1:5301/admin`를 여세요.

## 서버 접속

1. 게임 URL이나 서버 운영자가 관리자 패널의 Overview에서 공유한 빠른 접속 링크를 여세요. 1.12 클라이언트의 초기 서버 목록은 비어 있습니다. 멀티플레이에서 `ws://YOUR_SERVER:5200/`를 추가하거나 HTTPS 게임 접속에 맞는 `wss://` 주소를 사용하세요.
2. 처음 접속하면 LoginSecurity 안내에 따라 `/register <password>`를 입력하세요. 다음부터는 `/login <password>`을 사용합니다. 기본적으로 가입이 필수이며, 비밀번호는 6자 이상이고 로그인 제한 시간은 30초입니다.
3. 플레이어 계정 비밀번호는 LoginSecurity가 관리합니다. 관리자 패널은 서버 운영자의 `RCON_PASSWORD`를 사용합니다.

SimpleHomes는 `/sethome <name>`, `/home <name>`, `/homes`를 제공하고, SimpleTpa는 `/tpa <player>`, `/tpaccept`, `/tpdeny`를 제공합니다. 권한과 동작은 현재 플러그인 설정을 따릅니다.

## 관리자 패널과 플러그인

### 로그인 및 변경 사항 적용

`RCON_PASSWORD`를 설정하면 RCON과 관리 API가 활성화됩니다. 로그인 후 브라우저는 현재 세션에 관리 토큰을 저장하며, 기본 유효 기간은 8시간입니다. 로그아웃하면 로컬 토큰이 삭제됩니다. 인터페이스는 기본적으로 영어이며 중국어 간체를 지원하고 사이트별 언어 선택을 기억합니다.

Paper가 시작되는 동안에도 로그인할 수 있습니다. 게임 조작은 Paper가 준비되면 사용할 수 있습니다.

| 작업 | 적용 시점 |
|------|----------|
| 날씨, 시간, 게임 규칙, 플레이어 및 화이트리스트 명령 | 실행 중인 Paper로 전송됩니다. 콘솔 응답을 확인하세요 |
| MOTD, 플레이어 제한, 시야 거리, PVP 등 서버 설정 | `server.properties`에 기록되며 Paper 재시작 후 적용됩니다 |
| 플러그인 업로드, 활성화, 비활성화, 삭제 | 저장소에 보관되며 Paper 재시작 후 적용됩니다 |
| 패널에서 Minecraft 재시작 | Paper를 제어하여 재시작하며 Bungee와 패널은 계속 실행됩니다 |
| 패널에서 종료하거나 콘솔에서 `stop` 실행 | Paper가 종료되면 전체 컨테이너 종료가 시작됩니다 |

Dynmap은 패널의 `/dynmap/` 프록시로 접근합니다. 네이티브 구조물 검색은 이미지에 포함된 cubiomes를 사용합니다. 구조물과 대략적인 스폰 지점은 월드 시드로 계산하며, 플레이어 위치는 Dynmap 또는 플레이어 저장 데이터에서 가져옵니다. 외부 Seed Map을 열면 대상 URL에 월드 시드가 포함됩니다.

### 플러그인 저장소와 데이터

활성 버전의 저장소는 `server-data/plugins-1.8` 또는 `server-data/plugins-1.12`에 있습니다. `enabled/` 디렉터리는 활성 패키지와 데이터를, `disabled/`는 비활성 패키지를 보관합니다. Paper의 `plugins` 경로는 활성 저장소의 `enabled/` 디렉터리를 가리킵니다.

첫 시작에 기본 플러그인 패키지와 데이터를 가져옵니다. 이후 시작은 수동 수정, 비활성화, 삭제를 포함한 저장소의 현재 상태를 유지합니다. 전체 실행 디렉터리를 마운트하면 이 데이터를 모두 영구 보관합니다.

패널에는 활성 게임 버전, 파일 크기, 수정 시각, 다음 시작 상태, 재시작 대기 여부가 표시됩니다:

- 업로드 파일은 압축 루트에 `plugin.yml`가 있는 JAR이어야 합니다. 이름은 소문자 `.jar`로 끝나야 하며 최대 크기는 **64 MiB**입니다. 이름이 중복되면 충돌을 반환합니다.
- 플러그인을 업로드, 활성화, 비활성화 또는 삭제한 뒤 패널에서 재시작하여 새 구성을 불러오세요. 이미 로드된 코드는 Paper가 멈출 때까지 활성 상태입니다.
- 플러그인을 삭제하면 JAR이 제거되고 설정과 데이터베이스는 유지됩니다. 같은 데이터 디렉터리를 쓰는 호환 플러그인을 재설치하면 기존 데이터를 다시 사용할 수 있습니다.
- JAR은 Paper 프로세스 권한으로 실행됩니다. 신뢰할 수 있는 출처를 사용하고 설치 전에 패키지를 검토·검사하고 백업하세요.

<details>
<summary>기존 월드와 별도 데이터 디렉터리(이전 방식 지원)</summary>

`PERSISTENT_DATA_ROOT`는 플러그인 저장소와 이전 방식의 월드 마운트에 사용할 공통 루트를 설정합니다. `SERVER_DATA_DIR`는 호환 별칭입니다. 기본 배포 방식은 전체 실행 디렉터리 마운트입니다.

**빈 별도 데이터 디렉터리는 플러그인 저장소만 초기화합니다.** 월드 심볼릭 링크를 만들려면 해당 월드가 데이터 루트에 이미 있어야 합니다. 새 월드는 버전별 `server-版本/` 디렉터리에 남으며 전체 실행 디렉터리 마운트로 보존됩니다.

기존 월드를 옮기려면 서버를 정지하고 백업한 뒤 `<level-name>`, `<level-name>_nether`, `<level-name>_the_end` 디렉터리를 준비하세요. 기본 이름은 `world`, `world_nether`, `world_the_end`입니다. 진입점은 이 기본 이름으로 대체할 수 있고 서버 경로의 실제 월드 디렉터리를 유지합니다. 버전마다 별도 데이터 루트를 사용하고 시작 후 각 링크의 실제 대상을 확인하세요.

</details>

## 백업, 업그레이드 및 롤백

### 서버를 정지하고 백업

다음 명령은 빠른 시작의 컨테이너와 마운트를 사용합니다. 백업에는 월드, 플레이어 상태, 플러그인 데이터, 설정, 인증 데이터베이스와 관리 비밀번호가 포함됩니다. 접근을 제한한 디렉터리에 보관하세요.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

정기 백업 후에는 `docker start eaglerx-1.12`을 실행하세요. 업그레이드 중에는 이전 컨테이너를 정지 상태로 유지합니다. 외부 `PERSISTENT_DATA_ROOT`를 사용하면 그 루트도 백업하세요. tar는 기본적으로 심볼릭 링크 자체를 보관합니다.

종료 신호를 받으면 진입점은 Paper에 최대 30초, 이어서 Bungee에 최대 10초의 종료 시간을 줍니다. 예제의 Docker 종료 제한 45초는 이 절차를 위한 시간입니다. [Docker 종료 동작](https://docs.docker.com/reference/cli/docker/container/stop/)을 참고하세요.

### 새 디렉터리에서 업그레이드 준비

**전체 실행 디렉터리는 첫 시작에만 이미지에서 초기화됩니다.** 이미지를 바꾼 뒤에도 기존 마운트가 서버, 프런트엔드, Python 백엔드 파일을 계속 제공합니다. 업그레이드는 실행 파일을 명시적으로 갱신하고 영구 상태를 옮겨야 합니다.

**1단계: 정지하고 백업하세요.** 이전 컨테이너, 실행 디렉터리, 이미지 버전을 보관합니다.

**2단계: 새 실행 디렉터리를 준비하세요.** 대상 이미지에서 전체 템플릿을 복사합니다. 이 예제는 `2.2.5`를 사용합니다. 사용하지 않는 템플릿 컨테이너 이름과 디렉터리를 선택하세요:

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

템플릿 컨테이너는 시작하지 않은 상태로 둡니다. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/)는 정지된 컨테이너에서 파일을 복사할 수 있습니다. 템플릿 복사 후 이전 디렉터리의 영구 상태를 옮기세요:

| 데이터 | 이전 방법 |
|------|----------|
| `server-1.12/<level-name>`와 Nether 및 End 디렉터리 | 월드를 통째로 복사하고 `level-name`를 디렉터리 이름과 맞추세요 |
| `server-data/` | 전체 플러그인 저장소, 마커 파일, 이전 방식의 월드 디렉터리를 복사하세요 |
| Paper의 `*.properties`, `*.yml`, `*.json` 파일 | 새 템플릿과 설정을 병합하고 운영자, 화이트리스트, 차단, 플레이어 캐시를 보존하세요 |
| Bungee 설정, 인증 데이터베이스, 스킨 캐시 | 설정과 데이터베이스를 개별 이전하고 루트와 플러그인 디렉터리의 사용자 데이터를 확인하세요 |
| 사용자 프런트엔드, 플러그인, 시작 옵션 | 필요한 변경을 병합하고 서버 JAR, 스크립트, 관리 자산은 대상 이미지의 것을 사용하세요 |

진입점은 `server/`, `web/`, Paper의 `plugins` 심볼릭 링크를 다시 만듭니다. 외부 데이터 디렉터리를 새 호스트 디렉터리로 복사한 뒤 새 컨테이너의 원래 내부 경로에 마운트하세요. 이전 데이터 루트는 이전 컨테이너용으로 보관합니다. 다른 버전과 사용자 월드의 상태도 이전 목록에 포함하세요.

**3단계: 새 컨테이너를 시작하세요.** [빠른 시작 명령](#2-paper-1122-시작)에서 이름을 `eaglerx-1.12-next`, 호스트 디렉터리를 `/data/eagler-1.12-next`, 이미지를 대상 버전으로 바꿉니다. 원래 게임 버전, 비밀번호, 공개 URL, 포트 매핑을 유지하세요.

**4단계: 이전 결과를 검증하세요.** Paper 준비 상태, 플레이어 접속, 기존 월드 무결성, 플러그인 로드, 화이트리스트와 지도 동작을 확인합니다. 이후 이전 컨테이너, 이미지, 백업의 보관 기간을 정하세요.

### 롤백과 복구

이전 컨테이너와 디렉터리가 남아 있으면 새 컨테이너를 정지하고 이전 컨테이너를 시작하세요:

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

롤백은 이전 디렉터리에 저장된 상태를 복원합니다. 새 컨테이너 실행 중 생성된 데이터는 나중에 복구할 수 있도록 보관하세요. 압축 백업을 새 디렉터리에 풀고 추출된 `eagler-1.12`를 전체 실행 디렉터리로 마운트한 뒤 해당 백업의 이미지 버전과 시작 옵션을 사용합니다.

## 운영 및 문제 해결

다음 명령은 기본 컨테이너 이름을 사용합니다:

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

Paper와 Bungee는 tmux에서 실행됩니다. 위 Paper 콘솔의 기본 창은 `mcserver:0.1`, Bungee는 `mcserver:0.0`입니다. Docker 상태 검사는 5200, 5201, 25565 포트를 확인합니다. 관리자 패널은 RCON도 확인해 Paper 준비 상태를 판단합니다.

| 증상 | 확인 사항 |
|------|------------|
| 컨테이너가 즉시 종료됨 | `MINECRAFT_VERSION`가 `1.8` 또는 `1.12`인지 확인하고 로그에서 구체적인 오류를 찾으세요 |
| 실행 디렉터리가 불완전하다고 표시됨 | 빈 디렉터리를 초기화하거나 전체 백업을 복원하고 현재 디렉터리는 조사용으로 보관하세요 |
| 패널은 열리지만 Paper가 시작 중임 | 콘솔의 월드 생성과 플러그인 로드 진행을 확인하세요. 준비되면 패널이 자동 갱신됩니다 |
| 원격 관리 패널에 접근할 수 없음 | SSH 터널이나 관리 프록시가 호스트의 `127.0.0.1:5201`에 연결되는지 확인하세요 |
| 빠른 접속 주소가 틀리거나 HTTPS 연결 실패 | `PUBLIC_GAME_URL`, 공개 포트, 게임 프록시의 WebSocket 전달을 확인하세요 |
| `/api/status`가 404 반환 | `RCON_PASSWORD`를 설정하고 컨테이너를 다시 만드세요. 시작 스크립트가 이 값으로 RCON을 켭니다 |
| 로그인이 429 반환 | 실패 집계 기간에 같은 출처에서 5회 실패하면 10분 동안 잠깁니다. 터널·프록시 뒤 관리자는 출처를 공유할 수 있습니다 |
| 변경이 저장됐지만 이전 동작이 유지됨 | 패널에서 제어된 Paper 재시작을 실행하고 동작 상태를 확인하세요 |
| Dynmap이 502 반환 | 활성화와 로드 완료 여부, HTTP 수신 주소와 포트를 확인하세요 |
| 네이티브 구조물 검색 실패 | `linux/amd64` 실행 환경, 네이티브 라이브러리 로드 오류, 월드 시드 조회를 확인하세요 |

진입점은 Bungee, Paper, HTTP 순으로 시작하고 계속 감시합니다. 핵심 서비스가 종료되면 전체 컨테이너를 종료하고 실패 상태를 반환합니다. `SIGTERM` / `SIGINT`에서는 순서대로 정상 종료합니다. 패널에서 종료해도 컨테이너가 끝나는 점을 고려해 재시작 정책을 설정하세요.

## 환경 변수

`docker run -e`로 전달합니다. 컨테이너 환경 변수를 바꾸려면 기존 마운트를 사용해 다시 만드세요.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MINECRAFT_VERSION` | 필수 | `1.8`은 Paper 1.8.8, `1.12`는 Paper 1.12.2 선택 |
| `RCON_PASSWORD` | 비어 있음 | 설정하면 RCON과 API가 활성화되며, 비어 있으면 인증이 필요한 관리 엔드포인트가 비활성화됩니다 |
| `PUBLIC_GAME_URL` | 비어 있음 | 빠른 접속 링크와 WebSocket 주소를 생성하는 공개 HTTP(S) 게임 URL |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | 플러그인 저장소와 기존 월드의 이전 방식 마운트 루트. 빈 디렉터리는 저장소를 자동 초기화 |
| `SERVER_DATA_DIR` | 비어 있음 | `PERSISTENT_DATA_ROOT`의 호환 별칭. 후자를 명시하면 그 값이 우선합니다 |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | 관리 토큰 유효 기간(초) |
| `ADMIN_AUTH_SECRET` | RCON 비밀번호에서 파생 | 선택적 토큰 서명 비밀 키 |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | 관리 백엔드가 사용하는 Dynmap 업스트림 주소 |

## 관리 API

스크립트 연동용입니다. 모든 엔드포인트는 관리 포트 **5201**을 사용합니다. 일상적인 작업은 관리자 패널에서 처리할 수 있습니다.

<details>
<summary>엔드포인트, 인증 및 curl 예제</summary>

“공개”는 엔드포인트 자체의 인증 조건을 의미합니다. 관리 포트는 [SSH 터널이나 관리 프록시](#원격-관리와-포트)를 통해 접근하세요.

| 엔드포인트 | 접근 조건 |
|------|----------|
| `GET /api/connection-info` | 항상 사용 가능. 공개 게임 진입점 설정을 반환합니다 |
| `GET /api/status` | RCON 활성 시 사용 가능. Paper 상태와 관련 정보를 반환합니다 |
| `POST /api/login` | RCON 활성 시 관리 비밀번호를 토큰으로 교환합니다 |
| `POST /api/rcon`, `/api/config`, `/api/system`, `/api/plugins` 등의 JSON 관리 엔드포인트 | 본문에 유효한 `token`이 필요합니다 |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, 원시 JAR 요청 본문 및 `X-Plugin-Filename` 헤더 |
| `GET /dynmap/` | Dynmap으로 직접 프록시하며 관리 연결에서 접근을 보호합니다 |

JSON 요청 본문은 최대 64 KiB, 읽기 제한 시간은 10초입니다. 원시 JAR 업로드는 최대 64 MiB, 전체 읽기 기한은 30초입니다. 같은 터널·리버스 프록시 출처를 쓰는 관리자는 로그인 잠금 집계 기간을 공유할 수 있습니다.

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

## 개발, 빌드 및 릴리스

### 로컬 변경과 검증

Python 3와 Docker를 설치한 후 저장소 루트에서 다음 명령을 실행하세요. `web-1.8/`의 관리 자산을 편집하고 동기화 스크립트로 `web-1.12/`를 갱신합니다. 기본 이미지와 네이티브 라이브러리 요구 사항은 [실행 환경 기본 이미지 결정](../adr/0007-retain-the-verified-runtime-base.md)을 참고하세요.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

로컬 릴리스 검증에는 Node.js, tmux, `agent-browser`, 정상 실행되는 Chrome도 필요합니다. CI는 `agent-browser@0.26.0`로 고정되어 있습니다. 설치 절차는 [릴리스 워크플로](../../.github/workflows/release.yml)를 참고하세요.

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

로컬 검사는 Python 구문, 서버·플러그인 회귀, 두 버전의 리소스, 관리 자산, 영어·중국어 간체 브라우저 동작을 확인합니다. 브라우저 검사는 로컬 Mock Admin API를 사용합니다. 전체 릴리스 검증은 이미지를 빌드하고 두 Paper 버전을 실행합니다:

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

모든 `--live` 검사를 통과해야 `summary.json`의 `release_ready`를 `true`로 설정합니다. 검사 범위, 증거 형식, Linux 임시 마운트 권한은 [릴리스 검증 문서](../release-gate.md)를 참고하세요.

### 릴리스 게시

공식 릴리스는 `vMAJOR.MINOR` 또는 `vMAJOR.MINOR.PATCH` Git 태그를 사용합니다. 워크플로는 같은 이미지에 전체 검증을 수행한 후 버전 태그, 커밋 SHA 태그, 빌드 출처 증명과 함께 GHCR에 게시합니다. 가장 높은 버전의 자동 릴리스가 `latest`를 갱신합니다. 수동 재실행은 지정 버전과 SHA 태그만 갱신합니다.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh`는 로컬 빌드를 묶어 제공하며 `push` 인자는 이미지를 바로 푸시합니다. 공식 배포는 [전체 live gate 요구 사항](../adr/0005-require-the-live-release-gate.md)과 위 태그 워크플로를 따릅니다.

## 문제 보고

배포 문제와 기능 요청은 [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues)로 보내세요. 이미지 태그, `MINECRAFT_VERSION`, 호스트 아키텍처, 민감 정보를 가린 시작 옵션, 재현 단계, 관련 오류 로그를 포함하세요. 제출 전에 비밀번호와 토큰을 제거하세요.

## 감사의 말

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [원본 프로젝트](https://github.com/burgerhugger/ALL-server)
