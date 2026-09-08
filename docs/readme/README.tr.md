# EaglercraftX Server

Oyuncuların tarayıcıdan katılabildiği, kalıcı depolama ve oyuncuları, dünyaları, eklentileri yönetmek için bir yönetim paneli sunan Minecraft sunucusu çalıştırın. Docker imajı EaglercraftX 1.8 / 1.12 istemcilerini ve Paper 1.8.8 / 1.12.2 sunucularını içerir; oyun sürümünü başlatırken seçin.

![EaglercraftX yönetim paneli](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | **Türkçe**

<!-- README-I18N:END -->

[Hızlı başlangıç](#hızlı-başlangıç) · [Sunucuya katılma](#sunucuya-katılma) · [Panel ve eklentiler](#yönetim-paneli-ve-eklentiler) · [Yedekleme ve yükseltme](#yedekleme-yükseltme-ve-geri-alma) · [Sorun giderme](#i̇şletim-ve-sorun-giderme) · [Ortam değişkenleri](#ortam-değişkenleri) · [Yönetim API’si](#yönetim-apisi) · [Geliştirme ve yayımlama](#geliştirme-derleme-ve-yayımlama) · [Sorun bildirme](#sorun-bildirme)

## Özellikler

| Özellik | Ayrıntılar |
|------|------|
| Sunucu yönetimi | Paper hazırlık durumu, çevrimiçi oyuncular, saniyedeki tick sayısı (TPS), hava, saat, oyun kuralları, yapılandırma ve kontrollü yeniden başlatma |
| Oyuncular ve dünyalar | Operatör yetkileri (OP), beyaz listeler, oyuncu atma, yasaklama, ışınlanma, eşya komutları, dünya kaydetme ve sınırlar |
| Eklenti yönetimi | Her oyun sürümü için ayrı depolar; yükleme, etkinleştirme, devre dışı bırakma ve silme işlemleri Paper yeniden başlatıldıktan sonra uygulanır |
| Haritalar ve seed değerleri | Gömülü Dynmap, oyuncu konumları, yerel yapı araması ve harici Seed Map bağlantıları |
| Dahil edilen eklentiler | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## Hızlı başlangıç

### 1. Ana makineyi hazırlayın

- **Ana makine**: Docker’ı kurun ve kalıcı depolama hazırlayın. Örnekler Linux yollarını kullanır. Yayımlanan imajlar AMD64 içindir; ARM64 emülasyonu ve yerel kitaplık uyumluluğu ayrıca doğrulanmalıdır. [Mimari kararına](../adr/0006-publish-linux-amd64-only.md) bakın.
- **Bellek**: Paper ve Bungee ayrı ayrı `-Xms256M -Xmx256M` kullanır. JVM’nin heap dışı belleği, dünya üretimi ve eklentiler için ek bellek ayırın. Heap boyutunu değiştirmek için ilgili çalışma dizinindeki `run.sh` dosyasını düzenleyin.
- **EULA**: Başlatma betiği `eula=true` yazar. Dağıtımdan önce [Minecraft EULA](https://www.minecraft.net/en-us/eula) metnini okuyup kabul edin.

### 2. Paper 1.12.2 başlatın

Bu komutları sunucuda çalıştırın. `YOUR_SERVER` yerine oyuncuların erişebildiği bir IP adresi veya alan adı, `replace-with-a-strong-password` yerine yönetim parolanızı yazın.

Bu örnek ana makinedeki `/data/eagler-1.12` dizinini konteyner içinde `/eaglerX-1.8-server` konumuna bağlar ve **çalışma dizininin tamamını** kalıcı tutar: dünyalar, eklentiler, yapılandırma ve ön yüz dosyaları. Boş dizin ilk kullanımda otomatik hazırlanır. Var olan dizin eksikse başlatma işlemi içeriği koruyarak sonlanır. Mevcut kurulumun çalışma dosyalarını taşımak için [Yedekleme, yükseltme ve geri alma](#yedekleme-yükseltme-ve-geri-alma) adımlarını izleyin.

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

### 3. Paneli açın ve hazırlık durumunu kontrol edin

| Giriş | Adres | Kullanım |
|------|------|----------|
| Oyun | `http://YOUR_SERVER:5200/` | Oyuncularla paylaşın ve [katılma adımlarını](#sunucuya-katılma) izleyin |
| Yönetim paneli | `http://127.0.0.1:5201/admin` | Ana makineden açın ve başlangıçta belirlediğiniz parolayla giriş yapın |

İlk dünya üretimi birkaç dakika sürebilir. Panel **Paper is ready** gösterdiğinde başlangıç tamamlanmıştır. Uzun bekleme veya hata durumunda [İşletim ve sorun giderme](#i̇şletim-ve-sorun-giderme) bölümüne bakın.

### Uzaktan yönetim ve portlar

Uzak sunucuyu yönetmek için kendi bilgisayarınızdan bir SSH tüneli açın. `user@YOUR_SERVER` yerine sunucunun SSH giriş adresini yazın:

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

Tüneli açık tutup `http://127.0.0.1:5201/admin` adresini ziyaret edin. Hedefi ana makinedeki `127.0.0.1:5201` olan bir HTTPS ters proxy de kullanabilirsiniz. VPN yönetim erişimi, trafiği bu loopback adresine iletebilmelidir.

| Port | Amaç | Erişim kapsamı |
|------|------|----------|
| 5200 | HTTP oyun sayfası, herkese açık statik dosyalar ve WebSocket oyun bağlantıları | Oyunculara açılır |
| 5201 | Yönetim paneli, yedek HTTP hizmeti ve Dynmap proxy’si | Ana makinede `127.0.0.1` adresine bağlanır |
| 25565 | Paper | Konteyner içindeki localhost |
| 25575 | RCON | Konteyner içindeki localhost |

### Özel alan adları, HTTPS ve oyun URL’si

`PUBLIC_GAME_URL` değerini **oyuncuların gerçekten kullandığı HTTP(S) oyun URL’sine** ayarlayın. Panel bu değerden hızlı katılma bağlantıları ve `ws` / `wss` adresleri üretir. Boş bırakılırsa panelin mevcut ana makine adından 5200 portunda bir HTTP URL’si türetilir (`http://主机名:5200/`). SSH tüneli, ayrı yönetim alan adı veya özel oyun portu kullanırken değeri açıkça belirtin.

HTTPS oyun girişi için DNS, sertifika ve **5200** portuna HTTP ile WebSocket yönlendirmesi gerekir. Yönetim proxy’sini **5201** portuna yönlendirin. `PUBLIC_GAME_URL` yalnızca bağlantı adreslerini üretir; proxy ve sertifikayı dağıtım ortamında yapılandırın.

### 1.8 seçimi veya iki sürümü birlikte çalıştırma

`2.2.5`, imajın yayın sürümüdür. `MINECRAFT_VERSION=1.8` Paper 1.8.8’i, `1.12` Paper 1.12.2’yi seçer. Her konteyner aynı anda tek bir oyun sürümü çalıştırır ve kendi çalışma dizinini kullanır.

1.8 çalıştırmak için hızlı başlangıç komutunda şu parametreleri değiştirin:

| Parametre | Yalnızca 1.8 | 1.12 ile birlikte 1.8 |
|------|-------------|---------------------|
| Konteyner adı | `--name eaglerx-1.8` | Soldakiyle aynı |
| Oyun sürümü | `-e MINECRAFT_VERSION=1.8` | Soldakiyle aynı |
| Tam çalışma dizini bağlantısı | `-v /data/eagler-1.8:/eaglerX-1.8-server` | Soldakiyle aynı |
| Oyun portu | `-p 5200:5200` | `-p 5300:5200` |
| Yönetim portu | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| Herkese açık oyun URL’si | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

`PUBLIC_GAME_URL` değerini ilgili örneğin URL’sine ayarlayın. İkinci örneği uzaktan yönetmek için `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` kullanın ve `http://127.0.0.1:5301/admin` adresini açın.

## Sunucuya katılma

1. Oyun URL’sini veya sunucu sahibinin paneldeki Overview sayfasından paylaştığı hızlı katılma bağlantısını açın. Çok Oyunculu listesinde bu sunucu zaten yer alır: istemci `ws://` veya `wss://` adresini sayfa URL’sinden türetir, bu yüzden özel portlar ve HTTPS erişimi ek ayar gerektirmez. Hızlı katılma bağlantısı doğrudan bağlanır. Başka bir sunucuya katılmak için Çok Oyunculu bölümüne o sunucunun `ws://HOST:5200/` adresini ekleyin.
2. İlk girişte LoginSecurity yönergesini izleyip `/register <password>` yazın. Sonraki girişlerde `/login <password>` kullanın. Varsayılan olarak kayıt zorunludur, parola en az 6 karakter olmalıdır ve giriş süresi 30 saniyedir.
3. LoginSecurity oyuncu hesabı parolalarını yönetir. Panel, sunucu sahibinin `RCON_PASSWORD` değerini kullanır.

SimpleHomes `/sethome <name>`, `/home <name>` ve `/homes` komutlarını sunar. SimpleTpa `/tpa <player>`, `/tpaccept` ve `/tpdeny` komutlarını sunar. İzinler ve davranış mevcut eklenti yapılandırmasına bağlıdır.

## Yönetim paneli ve eklentiler

### Giriş ve değişikliklerin uygulanması

`RCON_PASSWORD` ayarlamak RCON’u ve yönetim API’sini etkinleştirir. Girişten sonra tarayıcı mevcut oturumda bir yönetim belirteci saklar; varsayılan geçerlilik süresi 8 saattir. Çıkış yapmak yerel belirteci temizler. Arayüz varsayılan olarak İngilizcedir, Basitleştirilmiş Çinceyi destekler ve site için seçilen dili hatırlar.

Paper başlarken giriş yapabilirsiniz. Oyun kontrolleri Paper hazır olduğunda kullanılabilir.

| İşlem | Uygulanma zamanı |
|------|----------|
| Hava, saat, oyun kuralları, oyuncu ve beyaz liste komutları | Çalışan Paper örneğine gönderilir; konsol yanıtını kontrol edin |
| MOTD, oyuncu sınırı, görüş mesafesi ve PVP gibi ayarlar | `server.properties` dosyasına yazılır ve Paper yeniden başlatılınca uygulanır |
| Eklenti yükleme, etkinleştirme, devre dışı bırakma ve silme | Depoya kaydedilir ve Paper yeniden başlatılınca uygulanır |
| Panelden Minecraft yeniden başlatma | Bungee ve panel çalışırken Paper kontrollü biçimde yeniden başlatılır |
| Panelden kapatma veya konsolda `stop` | Paper sonlanır ve tüm konteynerin kapatılmasını tetikler |

Dynmap’e panelin `/dynmap/` proxy’sinden erişilir. Yerel yapı araması, imaja dahil cubiomes bileşenini kullanır. Yapılar ve yaklaşık doğma noktaları dünya seed değerinden hesaplanır; oyuncu konumları Dynmap veya oyuncu kayıtlarından alınır. Harici Seed Map açıldığında dünya seed değeri hedef URL’ye eklenir.

### Eklenti depoları ve verileri

Etkin sürümün deposu `server-data/plugins-1.8` veya `server-data/plugins-1.12` konumundadır. `enabled/` dizini etkin paketleri ve eklenti verilerini, `disabled/` devre dışı paketleri içerir. Paper’ın `plugins` yolu etkin deponun `enabled/` dizinine işaret eder.

İlk başlangıç, dahil edilen eklenti paketlerini ve verilerini içe aktarır. Sonrakiler elle yapılan değişiklikler, devre dışı paketler ve silmeler dahil mevcut depo durumunu korur. Tam çalışma dizini bağlantısı bu verilerin tümünü kalıcı tutar.

Panel etkin oyun sürümünü, dosya boyutlarını, değişiklik zamanlarını, sonraki başlangıç durumunu ve bekleyen yeniden başlatma bilgisini gösterir:

- Yüklemeler, arşiv kökünde `plugin.yml` içeren JAR dosyaları olmalıdır. Dosya adı küçük harfli `.jar` ile bitmeli ve boyutu en fazla **64 MiB** olmalıdır. Aynı dosya adı çakışma hatası döndürür.
- Bir eklentiyi yükledikten, etkinleştirdikten, devre dışı bıraktıktan veya sildikten sonra güncel küme için panelden yeniden başlatın. Yüklenmiş kod Paper durana kadar etkin kalır.
- Eklenti silmek JAR dosyasını kaldırır, yapılandırmayı ve veritabanlarını korur. Aynı veri dizinini kullanan uyumlu eklentiyi yeniden kurmak bu verileri tekrar kullanabilir.
- JAR dosyaları Paper işleminin yetkileriyle çalışır. Güvenilir kaynaklar kullanın, kurulum öncesinde paketleri inceleyip tarayın ve yedek alın.

<details>
<summary>Mevcut dünyalar ve ayrı veri dizini (eski kurulum desteği)</summary>

`PERSISTENT_DATA_ROOT`, eklenti depoları ve eski dünya bağlantıları için ortak bir kök belirler. `SERVER_DATA_DIR` uyumluluk takma adıdır. Varsayılan dağıtım yöntemi tam çalışma dizinini bağlamaktır.

**Boş bir ayrı veri dizini yalnızca eklenti deposunu başlatır.** Dünya sembolik bağlantıları için ilgili dünyalar veri kökünde zaten bulunmalıdır. Yeni dünyalar sürüme özel `server-版本/` dizininde kalır ve tam çalışma dizini bağlantısıyla kalıcı tutulur.

Mevcut dünyaları taşımak için sunucuyu durdurup yedek alın; ardından `<level-name>`, `<level-name>_nether` ve `<level-name>_the_end` dizinlerini hazırlayın. Varsayılan adları `world`, `world_nether` ve `world_the_end` şeklindedir. Giriş noktası bu adlara geri dönebilir ve sunucu yollarındaki mevcut gerçek dünya dizinlerini korur. Her sürüm için ayrı veri kökü kullanın ve başlangıçtan sonra her bağlantının gerçek hedefini kontrol edin.

</details>

## Yedekleme, yükseltme ve geri alma

### Sunucuyu durdurup yedekleme

Bu komutlar hızlı başlangıçtaki konteyneri ve bağlantıyı kullanır. Yedekler dünyaları, oyuncu durumunu, eklenti verilerini, yapılandırmayı, kimlik doğrulama veritabanlarını ve yönetim parolasını içerir. Erişimi kısıtlı bir dizinde saklayın.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

Normal yedekleme bittikten sonra `docker start eaglerx-1.12` çalıştırın. Yükseltme sırasında eski konteyneri durmuş halde tutun. Harici `PERSISTENT_DATA_ROOT` kullanıyorsanız bu kökü de yedekleyin; tar varsayılan olarak sembolik bağlantıların kendisini korur.

Durma sinyali alındığında giriş noktası Paper’a en fazla 30 saniye, ardından Bungee’ye en fazla 10 saniye verir. Örnekteki 45 saniyelik Docker durma süresi bu sıra için zaman tanır. [Docker durdurma davranışına](https://docs.docker.com/reference/cli/docker/container/stop/) bakın.

### Yükseltmeyi yeni dizinde hazırlama

**Tam çalışma dizini yalnızca ilk başlangıçta imajdan hazırlanır.** İmaj değişince mevcut bağlantı sunucu, ön yüz ve Python arka uç dosyalarını sağlamaya devam eder. Yükseltme, çalışma dosyalarının açıkça güncellenmesini ve kalıcı durumun taşınmasını gerektirir.

**Adım 1: Durdurun ve yedekleyin.** Eski konteyneri, çalışma dizinini ve imaj sürümünü saklayın.

**Adım 2: Yeni çalışma dizini hazırlayın.** Hedef imajdan tam şablonu kopyalayın. Bu örnek `2.2.5` kullanır; kullanılmayan bir şablon konteyner adı ve dizin seçin:

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

Şablon konteyneri başlatılmamış halde bırakın. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) durmuş konteynerlerden dosya kopyalayabilir. Şablondan sonra eski dizindeki kalıcı durumu taşıyın:

| Veri | Taşıma yöntemi |
|------|----------|
| `server-1.12/<level-name>` ile Nether ve End dizinleri | Dünyaları tamamen kopyalayın ve `level-name` değerini dizin adlarıyla uyumlu tutun |
| `server-data/` | Eklenti deposunun tamamını, işaret dosyalarını ve eski dünya dizinlerini kopyalayın |
| Paper’ın `*.properties`, `*.yml` ve `*.json` dosyaları | Ayarları yeni şablonla birleştirin; operatörleri, beyaz listeleri, yasakları ve oyuncu önbelleklerini koruyun |
| Bungee ayarları, kimlik doğrulama veritabanları ve görünüm önbellekleri | Ayarları ve veritabanlarını ayrı ayrı taşıyın; kök ve eklenti dizinlerindeki özel verileri kontrol edin |
| Özel ön yüz dosyaları, eklentiler ve başlatma seçenekleri | Uyarlamaları gerektiği kadar birleştirin; sunucu JAR’larını, betikleri ve yönetim varlıklarını hedef imajdan kullanın |

Giriş noktası `server/`, `web/` ve Paper’ın `plugins` sembolik bağlantılarını yeniden oluşturur. Harici veri dizinlerini yeni bir ana makine dizinine kopyalayın ve yeni konteynere özgün konteyner yolunda bağlayın. Eski veri kökünü eski konteyner için saklayın. Diğer sürümlerin ve özel dünyaların durumunu da taşıma listesine ekleyin.

**Adım 3: Yeni konteyneri başlatın.** [Hızlı başlangıç komutunda](#2-paper-1122-başlatın) konteyner adını `eaglerx-1.12-next`, ana makine dizinini `/data/eagler-1.12-next`, imajı hedef sürüm yapın. Özgün oyun sürümünü, parolayı, genel URL’yi ve port eşlemelerini koruyun.

**Adım 4: Taşımayı doğrulayın.** Paper’ın hazır olduğunu, oyuncuların katıldığını, dünyaların sağlam kaldığını, eklentilerin yüklendiğini, beyaz listelerin ve haritaların çalıştığını kontrol edin. Ardından eski konteyner, imaj ve yedeklerin saklama süresini belirleyin.

### Geri alma ve kurtarma

Eski konteyner ve dizini duruyorsa yeni konteyneri durdurup eskisini başlatın:

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

Geri alma, eski dizinde kayıtlı durumu geri getirir. Yeni konteyner çalışırken oluşan verileri sonraki kurtarmalar için saklayın. Sıkıştırılmış yedeği yeni bir dizine çıkarın, çıkarılan `eagler-1.12` dizinini tam çalışma dizini olarak bağlayın ve yedekle eşleşen imaj sürümünü ve başlatma seçeneklerini kullanın.

## İşletim ve sorun giderme

Bu komutlar varsayılan konteyner adını kullanır:

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

Paper ve Bungee tmux içinde çalışır. Yukarıdaki Paper konsolu varsayılan `mcserver:0.1` bölmesini, Bungee ise `mcserver:0.0` bölmesini kullanır. Docker sağlık kontrolü 5200, 5201 ve 25565 portlarını sınar. Panel ayrıca Paper hazırlığını belirlemek için RCON’u kontrol eder.

| Belirti | Kontrol |
|------|------------|
| Konteyner hemen sonlanıyor | `MINECRAFT_VERSION` değerinin `1.8` veya `1.12` olduğunu doğrulayın ve günlükteki hatayı inceleyin |
| Başlangıç eksik çalışma dizini bildiriyor | Boş dizin hazırlayın veya tam yedeği geri yükleyin; mevcut dizini inceleme için saklayın |
| Panel açıkken Paper hâlâ başlıyor | Konsoldan dünya üretimi ve eklenti yükleme ilerlemesini izleyin; Paper hazır olunca panel güncellenir |
| Uzak panele erişilemiyor | SSH tüneli veya yönetim proxy’sinin ana makinedeki `127.0.0.1:5201` adresine eriştiğini kontrol edin |
| Hızlı katılma adresi yanlış veya HTTPS bağlantısı başarısız | `PUBLIC_GAME_URL`, genel port ve oyun proxy’sindeki WebSocket yönlendirmesini kontrol edin |
| `/api/status` 404 döndürüyor | `RCON_PASSWORD` ayarlayıp konteyneri yeniden oluşturun; başlangıç betiği RCON’u bununla etkinleştirir |
| Giriş 429 döndürüyor | Hata penceresinde aynı kaynaktan beş başarısız deneme 10 dakikalık kilit başlatır; tünel veya proxy arkasındaki yöneticiler kaynağı paylaşabilir |
| Değişiklikler kaydedildiği halde eski davranış sürüyor | Panelden kontrollü Paper yeniden başlatması yapıp çalışan durumu kontrol edin |
| Dynmap 502 döndürüyor | Etkin ve tamamen yüklenmiş olduğunu, ardından HTTP dinleme adresi ve portunu kontrol edin |
| Yerel yapı araması başarısız | `linux/amd64` çalışma ortamını, yerel kitaplık yükleme hatalarını ve dünya seed okumasını kontrol edin |

Giriş noktası Bungee, Paper ve HTTP’yi sırayla başlatıp sürekli izler. Ana hizmetlerden biri sonlanırsa tüm konteyneri kapatır ve hata durumu döndürür. `SIGTERM` / `SIGINT` alındığında düzenli kapatma yapar. Yeniden başlatma politikasını, panelden kapatmanın konteyneri de sonlandırdığını hesaba katarak belirleyin.

## Ortam değişkenleri

`docker run -e` ile geçirin. Konteynerin ortam değişkenlerini değiştirmek için mevcut bağlantıyla yeniden oluşturun.

| Değişken | Varsayılan | Açıklama |
|------|--------|------|
| `MINECRAFT_VERSION` | Gerekli | `1.8` Paper 1.8.8’i, `1.12` Paper 1.12.2’yi seçer |
| `RCON_PASSWORD` | Boş | Ayarlandığında RCON ve API’yi etkinleştirir; boşsa kimlik doğrulamalı yönetim uç noktaları kapalıdır |
| `PUBLIC_GAME_URL` | Boş | Hızlı katılma bağlantıları ve WebSocket adresleri için kullanılan genel HTTP(S) oyun URL’si |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | Eklenti depoları ve mevcut dünyaların eski bağlantıları için kök; boş dizin depoyu otomatik hazırlar |
| `SERVER_DATA_DIR` | Boş | `PERSISTENT_DATA_ROOT` için uyumluluk takma adı; ikinci değişkenin açık değeri önceliklidir |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | Yönetim belirtecinin saniye cinsinden geçerlilik süresi |
| `ADMIN_AUTH_SECRET` | RCON parolasından türetilir | İsteğe bağlı belirteç imzalama sırrı |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | Yönetim arka ucunun kullandığı Dynmap upstream adresi |

## Yönetim API’si

Betik entegrasyonları içindir. Tüm uç noktalar **5201** yönetim portunu kullanır. Günlük işlemler panelden yapılabilir.

<details>
<summary>Uç noktalar, kimlik doğrulama ve curl örnekleri</summary>

“Genel”, uç noktanın kendi kimlik doğrulama koşullarını anlatır. Yönetim portuna [SSH tüneli veya yönetim proxy’si](#uzaktan-yönetim-ve-portlar) üzerinden erişin.

| Uç nokta | Erişim koşulları |
|------|----------|
| `GET /api/connection-info` | Her zaman kullanılabilir; genel oyun giriş yapılandırmasını döndürür |
| `GET /api/status` | RCON etkinken kullanılabilir; Paper durumunu ve ilgili bilgileri döndürür |
| `POST /api/login` | RCON etkinken yönetim parolasını belirteçle değiştirir |
| `POST /api/rcon`, `/api/config`, `/api/system` ve `/api/plugins` gibi JSON yönetim uç noktaları | İstek gövdesi geçerli bir `token` içermelidir |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, ham JAR istek gövdesi ve `X-Plugin-Filename` başlığı |
| `GET /dynmap/` | Dynmap’e doğrudan proxy; erişimi yönetim bağlantısı korur |

JSON istek gövdesi sınırı 64 KiB, okuma süresi 10 saniyedir. Ham JAR yüklemeleri 64 MiB ile ve toplam 30 saniyelik okumayla sınırlıdır. Aynı tünel veya ters proxy kaynağını paylaşan yöneticiler aynı giriş kilidi penceresini paylaşabilir.

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

## Geliştirme, derleme ve yayımlama

### Yerel değişiklikler ve doğrulama

Python 3 ve Docker kurulu halde bu komutları depo kökünde çalıştırın. Yönetim varlıklarını `web-1.8/` içinde düzenleyip eşitleme betiğiyle `web-1.12/` dizinini güncelleyin. Taban imaj ve yerel kitaplık koşulları için [çalışma ortamı taban imajı kararına](../adr/0007-retain-the-verified-runtime-base.md) bakın.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

Yerel yayın kontrolü ayrıca Node.js, tmux, `agent-browser` ve çalışır bir Chrome kurulumu gerektirir. CI `agent-browser@0.26.0` sürümünü sabitler; kurulum adımları [yayın iş akışındadır](../../.github/workflows/release.yml).

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

Yerel kontroller Python sözdizimini, sunucu ve eklenti regresyonlarını, iki sürümün kaynaklarını, yönetim varlıklarını ve İngilizce ile Basitleştirilmiş Çince tarayıcı akışlarını kapsar. Tarayıcı kontrolleri yerel Mock Admin API kullanır. Tam yayın doğrulaması ayrıca imajı derleyip iki Paper sürümünü çalıştırır:

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

Kontrol, tüm `--live` denetimleri geçince `summary.json` içindeki `release_ready` değerini `true` yapar. Kapsam, kanıt biçimleri ve Linux geçici bağlantı izinleri için [yayın kontrolü belgelerine](../release-gate.md) bakın.

### Sürüm yayımlama

Resmî sürümler `vMAJOR.MINOR` veya `vMAJOR.MINOR.PATCH` Git etiketlerini kullanır. İş akışı aynı imajı tamamen doğrular, ardından sürüm ve commit SHA etiketleriyle ve derleme kaynağı doğrulamasıyla GHCR’a yayımlar. En yüksek sürümün otomatik yayını `latest` etiketini günceller. Elle tekrar çalıştırmalar yalnızca belirtilen sürümü ve SHA etiketlerini günceller.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` yerel derlemeleri sarmalar; `push` argümanı imajı doğrudan gönderir. Resmî dağıtım [tam live gate koşuluna](../adr/0005-require-the-live-release-gate.md) ve yukarıdaki etiket iş akışına uyar.

## Sorun bildirme

Dağıtım sorunlarını ve özellik isteklerini [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues) üzerinden iletin. İmaj etiketi, `MINECRAFT_VERSION`, ana makine mimarisi, gizli verileri çıkarılmış başlangıç seçenekleri, yeniden üretme adımları ve ilgili hata günlüklerini ekleyin. Göndermeden önce parola ve belirteçleri kaldırın.

## Teşekkürler

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Kaynak proje](https://github.com/burgerhugger/ALL-server)
