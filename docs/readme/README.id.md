# EaglercraftX Server

Jalankan server Minecraft yang dapat diakses pemain melalui browser, dengan penyimpanan persisten dan panel admin untuk mengelola pemain, dunia, serta plugin. Image Docker mencakup klien EaglercraftX 1.8 / 1.12 dan server Paper 1.8.8 / 1.12.2; pilih versi game saat memulai.

![Panel admin EaglercraftX](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | **Bahasa Indonesia** | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[Mulai cepat](#mulai-cepat) · [Bergabung ke server](#bergabung-ke-server) · [Panel dan plugin](#panel-admin-dan-plugin) · [Cadangan dan pembaruan](#pencadangan-pembaruan-dan-rollback) · [Pemecahan masalah](#operasi-dan-pemecahan-masalah) · [Variabel lingkungan](#variabel-lingkungan) · [API admin](#api-admin) · [Pengembangan dan rilis](#pengembangan-build-dan-rilis) · [Melaporkan masalah](#melaporkan-masalah)

## Fitur

| Fitur | Rincian |
|------|------|
| Pengelolaan server | Kesiapan Paper, pemain online, tick per detik (TPS), cuaca, waktu, aturan game, konfigurasi, dan mulai ulang terkontrol |
| Pemain dan dunia | Hak operator (OP), whitelist, pengeluaran pemain, pemblokiran, teleportasi, perintah item, penyimpanan dunia, dan batas dunia |
| Pengelolaan plugin | Repositori terpisah untuk setiap versi; unggah, aktifkan, nonaktifkan, dan hapus plugin, lalu terapkan dengan memulai ulang Paper |
| Peta dan seed | Dynmap tertanam, lokasi pemain, pencarian struktur native, dan tautan ke Seed Map eksternal |
| Plugin bawaan | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## Mulai cepat

### 1. Siapkan host

- **Host**: Pasang Docker dan siapkan penyimpanan persisten. Contoh menggunakan path Linux. Image yang dirilis menargetkan AMD64; emulasi ARM64 dan kompatibilitas pustaka native perlu divalidasi secara terpisah. Lihat [keputusan arsitektur](../adr/0006-publish-linux-amd64-only.md).
- **Memori**: Paper dan Bungee masing-masing menggunakan `-Xms256M -Xmx256M`. Sediakan memori tambahan untuk JVM di luar heap, pembuatan dunia, dan plugin. Untuk mengubah ukuran heap, edit `run.sh` di direktori runtime terkait.
- **EULA**: Skrip awal menulis `eula=true`. Baca dan setujui [Minecraft EULA](https://www.minecraft.net/en-us/eula) sebelum deployment.

### 2. Mulai Paper 1.12.2

Jalankan perintah berikut di server. Ganti `YOUR_SERVER` dengan alamat IP atau domain yang dapat dijangkau pemain, dan ganti `replace-with-a-strong-password` dengan kata sandi admin.

Contoh ini memasang `/data/eagler-1.12` pada host ke `/eaglerX-1.8-server` di dalam container dan menyimpan **seluruh direktori runtime** secara persisten: dunia, plugin, konfigurasi, dan file frontend. Direktori kosong diinisialisasi otomatis saat pertama digunakan. Jika direktori yang ada tidak lengkap, proses awal mempertahankan isinya lalu berhenti. Untuk deployment yang sudah ada, ikuti [Pencadangan, pembaruan, dan rollback](#pencadangan-pembaruan-dan-rollback) untuk memigrasikan file runtime.

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

### 3. Buka panel dan periksa kesiapan

| Akses | Alamat | Cara menggunakan |
|------|------|----------|
| Game | `http://YOUR_SERVER:5200/` | Bagikan kepada pemain dan ikuti [panduan bergabung](#bergabung-ke-server) |
| Panel admin | `http://127.0.0.1:5201/admin` | Buka dari host dan masuk dengan kata sandi yang ditetapkan saat awal |

Pembuatan dunia pertama dapat memerlukan beberapa menit. Server selesai memulai ketika panel menampilkan **Paper is ready**. Jika menunggu terlalu lama atau muncul kesalahan, lihat [Operasi dan pemecahan masalah](#operasi-dan-pemecahan-masalah).

### Administrasi jarak jauh dan port

Untuk mengelola server jarak jauh, buka tunnel SSH dari komputer Anda. Ganti `user@YOUR_SERVER` dengan alamat login SSH server:

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

Biarkan tunnel tetap terbuka, lalu kunjungi `http://127.0.0.1:5201/admin`. Anda juga dapat memakai reverse proxy HTTPS dengan `127.0.0.1:5201` pada host sebagai upstream. Akses admin melalui VPN harus dapat meneruskan lalu lintas ke alamat loopback tersebut.

| Port | Kegunaan | Akses |
|------|------|----------|
| 5200 | Halaman game HTTP, file statis publik, dan koneksi game WebSocket | Buka untuk pemain |
| 5201 | Panel admin, layanan HTTP cadangan, dan proxy Dynmap | Ikat ke `127.0.0.1` pada host |
| 25565 | Paper | Localhost di dalam container |
| 25575 | RCON | Localhost di dalam container |

### Domain khusus, HTTPS, dan URL game

Isi `PUBLIC_GAME_URL` dengan **URL game HTTP(S) yang benar-benar digunakan pemain**. Panel memakainya untuk membuat tautan bergabung cepat dan alamat `ws` / `wss`. Jika kosong, panel membentuk URL HTTP dari hostname saat ini pada port 5200 (`http://主机名:5200/`). Isi secara eksplisit ketika menggunakan tunnel SSH, domain admin terpisah, atau port game khusus.

Akses game HTTPS memerlukan DNS, sertifikat, serta penerusan HTTP dan WebSocket ke **5200**. Arahkan proxy admin ke **5201**. `PUBLIC_GAME_URL` hanya digunakan untuk membuat alamat koneksi; atur proxy dan sertifikat pada deployment Anda.

### Memilih 1.8 atau menjalankan kedua versi

`2.2.5` adalah versi rilis image. `MINECRAFT_VERSION=1.8` memilih Paper 1.8.8, sedangkan `1.12` memilih Paper 1.12.2. Setiap container menjalankan satu versi game dalam satu waktu dan memiliki direktori runtime sendiri.

Untuk menjalankan 1.8, sesuaikan parameter berikut pada perintah mulai cepat:

| Parameter | Menjalankan 1.8 saja | Menjalankan 1.8 bersama 1.12 |
|------|-------------|---------------------|
| Nama container | `--name eaglerx-1.8` | Sama seperti di kiri |
| Versi game | `-e MINECRAFT_VERSION=1.8` | Sama seperti di kiri |
| Mount seluruh direktori runtime | `-v /data/eagler-1.8:/eaglerX-1.8-server` | Sama seperti di kiri |
| Port game | `-p 5200:5200` | `-p 5300:5200` |
| Port admin | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| URL game publik | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

Isi `PUBLIC_GAME_URL` dengan URL instance tersebut. Untuk mengelola instance kedua dari jarak jauh, gunakan `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` dan buka `http://127.0.0.1:5301/admin`.

## Bergabung ke server

1. Buka URL game atau tautan bergabung cepat yang dibagikan pemilik server dari halaman Overview pada panel. Klien 1.12 dimulai dengan daftar server kosong; tambahkan `ws://YOUR_SERVER:5200/` pada Multiplayer, atau gunakan alamat `wss://` yang sesuai untuk akses HTTPS.
2. Pada kunjungan pertama, ikuti petunjuk LoginSecurity dan masukkan `/register <password>`. Gunakan `/login <password>` pada kunjungan berikutnya. Pendaftaran diwajibkan secara default, kata sandi minimal 6 karakter, dan batas waktu login 30 detik.
3. LoginSecurity mengelola kata sandi akun pemain. Panel admin memakai `RCON_PASSWORD` milik pemilik server.

SimpleHomes menyediakan `/sethome <name>`, `/home <name>`, dan `/homes`. SimpleTpa menyediakan `/tpa <player>`, `/tpaccept`, dan `/tpdeny`. Izin serta perilakunya mengikuti konfigurasi plugin saat ini.

## Panel admin dan plugin

### Masuk dan menerapkan perubahan

Mengisi `RCON_PASSWORD` mengaktifkan RCON dan API admin. Setelah login, browser menyimpan token admin pada sesi saat ini; token kedaluwarsa setelah 8 jam secara default. Keluar menghapus token lokal. Antarmuka menggunakan bahasa Inggris secara default, mendukung Mandarin Sederhana, dan mengingat pilihan bahasa untuk situs saat ini.

Anda dapat masuk ketika Paper masih memulai. Kontrol game tersedia setelah Paper siap.

| Tindakan | Waktu penerapan |
|------|----------|
| Cuaca, waktu, aturan game, perintah pemain, dan whitelist | Dikirim ke Paper yang berjalan; periksa respons konsol |
| Konfigurasi seperti MOTD, batas pemain, jarak pandang, dan PVP | Ditulis ke `server.properties` dan diterapkan setelah Paper dimulai ulang |
| Mengunggah, mengaktifkan, menonaktifkan, dan menghapus plugin | Disimpan di repositori dan diterapkan setelah Paper dimulai ulang |
| Tindakan mulai ulang Minecraft di panel | Memulai ulang Paper secara terkontrol sementara Bungee dan panel tetap berjalan |
| Mematikan melalui panel atau menjalankan `stop` di konsol | Paper berhenti, lalu memicu penghentian seluruh container |

Dynmap tersedia melalui proxy `/dynmap/` pada panel. Pencarian struktur native menggunakan komponen cubiomes bawaan image. Struktur dan perkiraan titik spawn dihitung dari seed dunia; lokasi pemain berasal dari Dynmap atau data simpan pemain. Membuka Seed Map eksternal menyertakan seed dunia dalam URL tujuan.

### Repositori dan data plugin

Repositori versi aktif berada di `server-data/plugins-1.8` atau `server-data/plugins-1.12`. Direktori `enabled/` berisi paket aktif dan data plugin; `disabled/` berisi paket nonaktif. Path `plugins` milik Paper mengarah ke direktori `enabled/` pada repositori aktif.

Saat pertama dimulai, paket plugin bawaan dan datanya diimpor. Proses berikutnya mempertahankan keadaan repositori, termasuk edit manual, paket nonaktif, dan penghapusan. Mount seluruh direktori runtime menyimpan semua data ini secara persisten.

Panel menampilkan versi game aktif, ukuran dan waktu perubahan file plugin, status untuk startup berikutnya, serta penanda mulai ulang yang tertunda:

- Unggahan harus berupa JAR dengan `plugin.yml` di root arsip. Nama file harus diakhiri `.jar` dalam huruf kecil, dengan batas **64 MiB**. Nama file yang sama menghasilkan konflik.
- Setelah mengunggah, mengaktifkan, menonaktifkan, atau menghapus plugin, mulai ulang melalui panel agar kumpulan terbaru dimuat. Kode yang sudah dimuat tetap aktif sampai Paper berhenti.
- Menghapus plugin membuang JAR dan mempertahankan konfigurasi serta basis datanya. Memasang ulang plugin kompatibel yang memakai direktori data sama dapat menggunakan kembali data tersebut.
- JAR dijalankan dengan izin proses Paper. Gunakan sumber tepercaya, tinjau dan pindai paket sebelum memasang, serta buat cadangan.

<details>
<summary>Dunia yang sudah ada dan direktori data terpisah (dukungan lama)</summary>

`PERSISTENT_DATA_ROOT` menetapkan root bersama untuk repositori plugin dan mount dunia lama. `SERVER_DATA_DIR` adalah alias kompatibilitasnya. Metode deployment default memasang seluruh direktori runtime.

**Direktori data terpisah yang kosong hanya menginisialisasi repositori plugin.** Symlink dunia memerlukan dunia terkait yang sudah ada di root data tersebut. Dunia baru tetap berada pada direktori `server-版本/` khusus versi dan disimpan melalui mount runtime lengkap.

Untuk memigrasikan dunia, hentikan server dan buat cadangan, lalu siapkan direktori `<level-name>`, `<level-name>_nether`, dan `<level-name>_the_end`. Nama defaultnya adalah `world`, `world_nether`, dan `world_the_end`. Entrypoint dapat menggunakan nama default sebagai cadangan dan mempertahankan direktori dunia asli yang sudah ada pada path server. Gunakan root data terpisah per versi, lalu periksa tujuan setiap symlink setelah startup.

</details>

## Pencadangan, pembaruan, dan rollback

### Hentikan server dan buat cadangan

Perintah ini memakai container dan mount dari panduan mulai cepat. Cadangan memuat dunia, status pemain, data plugin, konfigurasi, basis data autentikasi, dan kata sandi admin. Simpan dalam direktori dengan akses terbatas.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

Untuk pencadangan rutin, jalankan `docker start eaglerx-1.12` setelah selesai. Saat memperbarui, biarkan container lama berhenti. Jika memakai `PERSISTENT_DATA_ROOT` eksternal, cadangkan root itu juga; tar mempertahankan symlink itu sendiri secara default.

Ketika menerima sinyal berhenti, entrypoint memberi Paper waktu maksimal 30 detik untuk keluar, lalu Bungee maksimal 10 detik. Batas berhenti Docker selama 45 detik pada contoh memberi waktu untuk urutan ini. Lihat [perilaku penghentian Docker](https://docs.docker.com/reference/cli/docker/container/stop/).

### Siapkan pembaruan di direktori baru

**Seluruh direktori runtime hanya diinisialisasi dari image saat startup pertama.** Setelah mengganti image, mount yang ada tetap menyediakan file server, frontend, dan backend Python. Pembaruan memerlukan penggantian file runtime secara eksplisit dan migrasi status persisten.

**Langkah 1: Hentikan dan cadangkan.** Simpan container lama, direktori runtime, dan versi imagenya.

**Langkah 2: Siapkan direktori runtime baru.** Salin template lengkap dari image tujuan. Contoh ini memakai `2.2.5`; pilih nama container template dan direktori yang belum digunakan:

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

Biarkan container template belum dijalankan. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) mendukung penyalinan dari container yang berhenti. Setelah menyalin template, migrasikan status persisten dari direktori lama:

| Data | Cara migrasi |
|------|----------|
| `server-1.12/<level-name>` beserta direktori Nether dan End | Salin dunia lengkap dan pastikan `level-name` sesuai dengan nama direktorinya |
| `server-data/` | Salin seluruh repositori plugin, file penanda, dan direktori dunia lama |
| File Paper `*.properties`, `*.yml`, dan `*.json` | Gabungkan konfigurasi dengan template baru; pertahankan operator, whitelist, pemblokiran, dan cache pemain |
| Konfigurasi Bungee, basis data autentikasi, dan cache skin | Migrasikan konfigurasi serta basis data satu per satu; periksa data khusus pada root dan direktori plugin |
| Frontend khusus, plugin, dan opsi startup | Gabungkan penyesuaian seperlunya; gunakan JAR server, skrip, dan aset admin dari image tujuan |

Entrypoint membuat ulang symlink `server/`, `web/`, dan `plugins` milik Paper. Salin direktori data eksternal ke direktori host baru, lalu pasang pada container baru dengan path container semula. Simpan root lama untuk container lama. Sertakan data versi lain dan dunia khusus dalam daftar migrasi.

**Langkah 3: Mulai container baru.** Gunakan [perintah mulai cepat](#2-mulai-paper-1122), ubah nama container menjadi `eaglerx-1.12-next`, direktori host menjadi `/data/eagler-1.12-next`, dan image ke versi tujuan. Pertahankan versi game, kata sandi, URL publik, dan pemetaan port semula.

**Langkah 4: Verifikasi migrasi.** Pastikan Paper siap, pemain dapat bergabung, dunia lama utuh, plugin termuat, serta whitelist dan peta berfungsi. Setelah itu, tentukan masa penyimpanan container lama, image, dan cadangan.

### Rollback dan pemulihan

Jika container dan direktori lama tetap disimpan, hentikan container baru lalu mulai yang lama:

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

Rollback memulihkan status yang tersimpan di direktori lama. Simpan data yang dibuat selama container baru berjalan agar dapat dipulihkan kemudian. Untuk memulihkan arsip cadangan, ekstrak ke direktori baru, pasang direktori `eagler-1.12` hasil ekstraksi sebagai direktori runtime lengkap, lalu gunakan versi image dan opsi startup yang sesuai dengan cadangan itu.

## Operasi dan pemecahan masalah

Perintah berikut memakai nama container default:

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

Paper dan Bungee berjalan di tmux. Konsol Paper di atas memakai pane default `mcserver:0.1`; Bungee memakai `mcserver:0.0`. Pemeriksaan kesehatan Docker memeriksa port 5200, 5201, dan 25565. Panel juga memeriksa RCON untuk menentukan kesiapan Paper.

| Gejala | Pemeriksaan |
|------|------------|
| Container langsung keluar | Pastikan `MINECRAFT_VERSION` berisi `1.8` atau `1.12`, lalu periksa kesalahan spesifik pada log |
| Startup melaporkan direktori runtime tidak lengkap | Inisialisasi direktori kosong atau pulihkan cadangan lengkap; simpan direktori saat ini untuk investigasi |
| Panel terbuka saat Paper masih memulai | Periksa progres pembuatan dunia dan pemuatan plugin di konsol; panel diperbarui otomatis saat Paper siap |
| Panel jarak jauh tidak dapat diakses | Pastikan tunnel SSH atau proxy admin dapat menjangkau `127.0.0.1:5201` pada host |
| Tautan cepat salah atau koneksi HTTPS gagal | Periksa `PUBLIC_GAME_URL`, port publik, dan penerusan WebSocket pada proxy game |
| `/api/status` mengembalikan 404 | Isi `RCON_PASSWORD` dan buat ulang container; skrip awal menggunakannya untuk mengaktifkan RCON |
| Login mengembalikan 429 | Lima kegagalan dari satu sumber dalam jendela kegagalan memicu penguncian 10 menit; admin di balik tunnel atau proxy dapat berbagi sumber |
| Perubahan tersimpan, tetapi perilaku lama tetap berjalan | Mulai ulang Paper secara terkontrol lewat panel, lalu periksa status runtime |
| Dynmap mengembalikan 502 | Pastikan Dynmap aktif dan selesai dimuat; periksa alamat serta port HTTP-nya |
| Pencarian struktur native gagal | Periksa lingkungan `linux/amd64`, kesalahan pemuatan pustaka native, dan pembacaan seed dunia |

Entrypoint memulai Bungee, Paper, lalu HTTP dan terus memantaunya. Jika layanan inti keluar, seluruh container dihentikan dengan status gagal. Saat menerima `SIGTERM` / `SIGINT`, penghentian dilakukan secara tertib. Atur kebijakan mulai ulang dengan mempertimbangkan bahwa mematikan lewat panel juga menghentikan container.

## Variabel lingkungan

Teruskan melalui `docker run -e`. Untuk mengubah variabel container, buat ulang container dengan mount yang sudah ada.

| Variabel | Default | Keterangan |
|------|--------|------|
| `MINECRAFT_VERSION` | Wajib | `1.8` memilih Paper 1.8.8; `1.12` memilih Paper 1.12.2 |
| `RCON_PASSWORD` | Kosong | Mengaktifkan RCON dan API jika diisi; endpoint admin yang memerlukan autentikasi dinonaktifkan jika kosong |
| `PUBLIC_GAME_URL` | Kosong | URL game HTTP(S) publik untuk membuat tautan cepat dan alamat WebSocket |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | Root repositori plugin dan mount lama dunia yang sudah ada; direktori kosong menginisialisasi repositori secara otomatis |
| `SERVER_DATA_DIR` | Kosong | Alias kompatibilitas untuk `PERSISTENT_DATA_ROOT`; nilai eksplisit variabel tersebut diprioritaskan |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | Masa berlaku token admin dalam detik |
| `ADMIN_AUTH_SECRET` | Diturunkan dari kata sandi RCON | Secret opsional untuk penandatanganan token |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | Alamat upstream Dynmap yang digunakan backend admin |

## API admin

Untuk integrasi skrip. Semua endpoint memakai port admin **5201**. Operasi sehari-hari tersedia melalui panel.

<details>
<summary>Endpoint, autentikasi, dan contoh curl</summary>

“Publik” menjelaskan persyaratan autentikasi endpoint itu sendiri. Akses port admin melalui [tunnel SSH atau proxy admin](#administrasi-jarak-jauh-dan-port).

| Endpoint | Persyaratan akses |
|------|----------|
| `GET /api/connection-info` | Selalu tersedia; mengembalikan konfigurasi akses game publik |
| `GET /api/status` | Tersedia saat RCON aktif; mengembalikan status Paper dan informasi terkait |
| `POST /api/login` | Menukar kata sandi admin dengan token saat RCON aktif |
| Endpoint JSON admin seperti `POST /api/rcon`, `/api/config`, `/api/system`, dan `/api/plugins` | Isi permintaan harus memuat `token` yang valid |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, isi permintaan JAR mentah, dan header `X-Plugin-Filename` |
| `GET /dynmap/` | Proxy langsung ke Dynmap; koneksi pengelolaan melindungi akses |

Permintaan JSON dibatasi 64 KiB dengan batas baca 10 detik. Unggahan JAR mentah dibatasi 64 MiB dengan tenggat baca total 30 detik. Admin yang berbagi sumber tunnel atau reverse proxy dapat berbagi jendela penguncian login.

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

## Pengembangan, build, dan rilis

### Perubahan lokal dan validasi

Jalankan perintah ini dari root repositori dengan Python 3 dan Docker terpasang. Edit aset admin di `web-1.8/`, lalu jalankan skrip sinkronisasi untuk memperbarui `web-1.12/`. Lihat [keputusan image dasar runtime](../adr/0007-retain-the-verified-runtime-base.md) untuk kebutuhan image dasar dan pustaka native.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

Pemeriksaan rilis lokal juga memerlukan Node.js, tmux, `agent-browser`, dan Chrome yang dapat dijalankan. CI menetapkan `agent-browser@0.26.0`; lihat langkah pemasangan pada [alur rilis](../../.github/workflows/release.yml).

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

Pemeriksaan lokal mencakup sintaks Python, regresi server dan plugin, aset kedua versi, aset admin, serta alur browser berbahasa Inggris dan Mandarin Sederhana. Browser memakai Mock Admin API lokal. Validasi rilis lengkap juga membangun image dan menjalankan kedua versi Paper:

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

Pemeriksaan menetapkan `release_ready` menjadi `true` di `summary.json` hanya setelah seluruh pemeriksaan `--live` lulus. Lihat [dokumentasi pemeriksaan rilis](../release-gate.md) untuk cakupan, format bukti, dan izin mount sementara Linux.

### Menerbitkan rilis

Rilis resmi memakai tag Git `vMAJOR.MINOR` atau `vMAJOR.MINOR.PATCH`. Alur kerja memeriksa satu image secara lengkap lalu menerbitkannya ke GHCR dengan tag versi, SHA commit, serta atestasi asal build. Rilis otomatis untuk versi tertinggi memperbarui `latest`; pengulangan manual hanya memperbarui versi yang ditentukan dan tag SHA.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` membungkus build lokal; argumen `push` mengirim image secara langsung. Distribusi resmi mengikuti [persyaratan pemeriksaan live lengkap](../adr/0005-require-the-live-release-gate.md) dan alur tag di atas.

## Melaporkan masalah

Laporkan masalah deployment dan permintaan fitur melalui [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues). Sertakan tag image, `MINECRAFT_VERSION`, arsitektur host, opsi startup yang sudah disamarkan, langkah reproduksi, dan log terkait. Hapus kata sandi serta token sebelum mengirim.

## Kredit

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Proyek asal](https://github.com/burgerhugger/ALL-server)
