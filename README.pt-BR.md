# EaglercraftX Server

Execute um servidor de Minecraft que os jogadores acessam pelo navegador, com armazenamento persistente e um painel de administração para gerenciar jogadores, mundos e plugins. A imagem Docker inclui os clientes EaglercraftX 1.8 / 1.12 e os servidores Paper 1.8.8 / 1.12.2; escolha a versão do jogo na inicialização.

![Painel de administração do EaglercraftX](./docs/images/admin-panel.png)

<!-- README-I18N:START -->

[English](./README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | **Português (Brasil)** | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[Início rápido](#início-rápido) · [Entrar no servidor](#entrar-no-servidor) · [Painel e plugins](#painel-de-administração-e-plugins) · [Backups e atualizações](#backups-atualizações-e-reversão-de-versão) · [Solução de problemas](#operação-e-solução-de-problemas) · [Variáveis de ambiente](#variáveis-de-ambiente) · [API de administração](#api-de-administração) · [Desenvolvimento e publicação](#desenvolvimento-build-e-publicação) · [Relatar problemas](#relatar-problemas)

## Recursos

| Recurso | Detalhes |
|------|------|
| Gerenciamento do servidor | Prontidão do Paper, jogadores online, ticks por segundo (TPS), clima, horário, regras, configuração e reinicializações controladas |
| Jogadores e mundos | Permissões de operador (OP), listas de permissões, expulsões, banimentos, teletransporte, comandos de itens, salvamento e limites dos mundos |
| Gerenciamento de plugins | Repositórios separados por versão; envie, ative, desative e exclua plugins, com aplicação após reiniciar o Paper |
| Mapas e seeds | Dynmap integrado, localização de jogadores, busca nativa de estruturas e links para um Seed Map externo |
| Plugins incluídos | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## Início rápido

### 1. Preparar o host

- **Host**: Instale o Docker e prepare armazenamento persistente. Os exemplos usam caminhos Linux. As imagens publicadas são para AMD64; a emulação em ARM64 e a compatibilidade das bibliotecas nativas exigem validação separada. Consulte a [decisão de arquitetura](docs/adr/0006-publish-linux-amd64-only.md).
- **Memória**: Paper e Bungee usam `-Xms256M -Xmx256M` cada um. Reserve memória adicional para a JVM fora do heap, geração de mundos e plugins. Para ajustar o heap, edite `run.sh` no diretório de execução correspondente.
- **EULA**: O script de inicialização grava `eula=true`. Leia e aceite o [EULA do Minecraft](https://www.minecraft.net/en-us/eula) antes de implantar.

### 2. Iniciar o Paper 1.12.2

Execute estes comandos no servidor. Substitua `YOUR_SERVER` por um IP ou domínio acessível aos jogadores e `replace-with-a-strong-password` pela sua senha de administração.

Este exemplo monta `/data/eagler-1.12` do host em `/eaglerX-1.8-server` dentro do contêiner e mantém **todo o diretório de execução** persistente: mundos, plugins, configuração e arquivos do frontend. Um diretório vazio é inicializado automaticamente no primeiro uso. Se um diretório existente estiver incompleto, a inicialização preserva seu conteúdo e encerra. Para uma implantação existente, siga [Backups, atualizações e reversão de versão](#backups-atualizações-e-reversão-de-versão) para migrar os arquivos de execução.

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

### 3. Abrir o painel e verificar a prontidão

| Acesso | Endereço | Como usar |
|------|------|----------|
| Jogo | `http://YOUR_SERVER:5200/` | Compartilhe com os jogadores e siga as [instruções de entrada](#entrar-no-servidor) |
| Painel de administração | `http://127.0.0.1:5201/admin` | Abra pelo host e entre com a senha definida na inicialização |

A geração inicial do mundo pode levar alguns minutos. A inicialização termina quando o painel mostra **Paper is ready**. Se a espera se prolongar ou ocorrer um erro, consulte [Operação e solução de problemas](#operação-e-solução-de-problemas).

### Administração remota e portas

Para administrar um servidor remoto, abra um túnel SSH no seu computador. Substitua `user@YOUR_SERVER` pelo endereço de login SSH do servidor:

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

Mantenha o túnel aberto e acesse `http://127.0.0.1:5201/admin`. Você também pode usar um proxy reverso HTTPS com `127.0.0.1:5201` no host como destino. O acesso de administração por VPN precisa encaminhar o tráfego para esse endereço de loopback.

| Porta | Finalidade | Exposição |
|------|------|----------|
| 5200 | Página HTTP do jogo, arquivos estáticos públicos e conexões WebSocket do jogo | Disponibilizar aos jogadores |
| 5201 | Painel, serviço HTTP alternativo e proxy do Dynmap | Vincular a `127.0.0.1` no host |
| 25565 | Paper | Localhost dentro do contêiner |
| 25575 | RCON | Localhost dentro do contêiner |

### Domínios personalizados, HTTPS e URL do jogo

Defina `PUBLIC_GAME_URL` como **a URL HTTP(S) do jogo que os jogadores realmente usam**. O painel gera a partir dela links de entrada rápida e endereços `ws` / `wss`. Se estiver vazia, deriva uma URL HTTP do hostname atual do painel na porta 5200 (`http://主机名:5200/`). Defina o valor explicitamente ao usar túnel SSH, domínio de administração separado ou porta de jogo personalizada.

Um acesso HTTPS ao jogo exige DNS, certificado e encaminhamento HTTP e WebSocket para **5200**. Aponte o proxy de administração para **5201**. `PUBLIC_GAME_URL` serve apenas para gerar endereços de conexão; configure o proxy e o certificado na implantação.

### Escolher 1.8 ou executar as duas versões

`2.2.5` é a versão de lançamento da imagem. `MINECRAFT_VERSION=1.8` seleciona Paper 1.8.8, e `1.12` seleciona Paper 1.12.2. Cada contêiner executa uma versão do jogo por vez e usa seu próprio diretório.

Para executar 1.8, ajuste estes parâmetros no comando de início rápido:

| Parâmetro | Executar apenas 1.8 | Executar 1.8 junto com 1.12 |
|------|-------------|---------------------|
| Nome do contêiner | `--name eaglerx-1.8` | Igual à esquerda |
| Versão do jogo | `-e MINECRAFT_VERSION=1.8` | Igual à esquerda |
| Montagem do diretório completo | `-v /data/eagler-1.8:/eaglerX-1.8-server` | Igual à esquerda |
| Porta do jogo | `-p 5200:5200` | `-p 5300:5200` |
| Porta de administração | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| URL pública do jogo | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

Defina `PUBLIC_GAME_URL` com a URL dessa instância. Para administrar a segunda instância remotamente, use `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` e abra `http://127.0.0.1:5301/admin`.

## Entrar no servidor

1. Abra a URL do jogo ou use o link de entrada rápida que o dono do servidor compartilhar pela página Overview do painel. O cliente 1.12 inicia com uma lista de servidores vazia; adicione `ws://YOUR_SERVER:5200/` em Multijogador ou use o endereço `wss://` correspondente para acesso HTTPS.
2. Na primeira visita, siga a instrução do LoginSecurity e digite `/register <password>`. Nas próximas visitas, use `/login <password>`. O cadastro é obrigatório por padrão, a senha precisa ter pelo menos 6 caracteres e o prazo para login é de 30 segundos.
3. O LoginSecurity gerencia as senhas das contas dos jogadores. O painel usa a `RCON_PASSWORD` do administrador do servidor.

O SimpleHomes oferece `/sethome <name>`, `/home <name>` e `/homes`. O SimpleTpa oferece `/tpa <player>`, `/tpaccept` e `/tpdeny`. Permissões e comportamento dependem da configuração atual do plugin.

## Painel de administração e plugins

### Entrar e aplicar alterações

Definir `RCON_PASSWORD` ativa o RCON e a API de administração. Após o login, o navegador mantém um token na sessão atual; por padrão, ele expira após 8 horas. Sair da conta limpa o token local. A interface usa inglês por padrão, oferece chinês simplificado e lembra o idioma escolhido para o site.

Você pode entrar enquanto o Paper inicia. Os controles do jogo ficam disponíveis quando ele está pronto.

| Ação | Quando entra em vigor |
|------|----------|
| Clima, horário, regras, comandos de jogadores e lista de permissões | Enviados ao Paper em execução; confira a resposta do console |
| Configurações como MOTD, limite de jogadores, distância de visão e PVP | Gravadas em `server.properties` e aplicadas após reiniciar o Paper |
| Enviar, ativar, desativar ou excluir plugins | Salvo no repositório e aplicado após reiniciar o Paper |
| Reiniciar Minecraft pelo painel | Reinicia o Paper de forma controlada, mantendo Bungee e painel em execução |
| Desligar pelo painel ou executar `stop` no console | O Paper encerra e aciona o desligamento de todo o contêiner |

O Dynmap é acessível pelo proxy `/dynmap/` do painel. A busca nativa de estruturas usa o componente cubiomes incluído na imagem. Estruturas e pontos aproximados de nascimento são calculados pela seed do mundo; as posições dos jogadores vêm do Dynmap ou dos dados salvos. Ao abrir o Seed Map externo, a seed é incluída na URL de destino.

### Repositórios e dados de plugins

O repositório da versão ativa fica em `server-data/plugins-1.8` ou `server-data/plugins-1.12`. O diretório `enabled/` contém pacotes ativados e dados dos plugins; `disabled/` contém os pacotes desativados. O caminho `plugins` do Paper aponta para `enabled/` no repositório ativo.

A primeira inicialização importa os pacotes e dados incluídos. As seguintes preservam o estado atual do repositório, inclusive edições manuais, desativações e exclusões. A montagem do diretório completo mantém todos esses dados persistentes.

O painel mostra a versão ativa do jogo, tamanhos e datas de modificação dos arquivos, estado para a próxima inicialização e se há reinicialização pendente:

- Os envios precisam ser JARs com `plugin.yml` na raiz do arquivo. O nome deve terminar em `.jar` em letras minúsculas, e o limite é de **64 MiB**. Nomes duplicados retornam conflito.
- Após enviar, ativar, desativar ou excluir um plugin, reinicie pelo painel para carregar o conjunto atualizado. O código carregado continua ativo até o Paper parar.
- Excluir um plugin remove o JAR e preserva a configuração e os bancos de dados. Reinstalar um plugin compatível que use o mesmo diretório permite reutilizar esses dados.
- JARs executam com as permissões do processo do Paper. Use fontes confiáveis, revise e faça uma varredura nos pacotes antes de instalar e realize um backup.

<details>
<summary>Mundos existentes e diretório de dados separado (compatibilidade legada)</summary>

`PERSISTENT_DATA_ROOT` define uma raiz compartilhada para repositórios de plugins e montagens legadas de mundos. `SERVER_DATA_DIR` é seu alias de compatibilidade. O método padrão monta o diretório de execução completo.

**Um diretório de dados separado e vazio inicializa apenas o repositório de plugins.** Os links simbólicos exigem que os mundos correspondentes já existam nessa raiz. Novos mundos ficam no diretório `server-版本/` da versão e são preservados pela montagem completa.

Para migrar mundos existentes, pare o servidor e faça um backup; depois prepare os diretórios `<level-name>`, `<level-name>_nether` e `<level-name>_the_end`. Os nomes padrão são `world`, `world_nether` e `world_the_end`. O ponto de entrada pode recorrer a esses nomes e preserva diretórios reais de mundos já existentes nos caminhos do servidor. Use uma raiz por versão e verifique o destino de cada link após iniciar.

</details>

## Backups, atualizações e reversão de versão

### Parar o servidor e fazer backup

Estes comandos usam o contêiner e a montagem do início rápido. Os backups incluem mundos, estado dos jogadores, dados de plugins, configuração, bancos de autenticação e a senha de administração. Armazene-os em um diretório com acesso restrito.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

Após um backup de rotina, execute `docker start eaglerx-1.12`. Durante uma atualização, mantenha o contêiner antigo parado. Se usar um `PERSISTENT_DATA_ROOT` externo, faça backup dessa raiz também; por padrão, tar preserva os próprios links simbólicos.

Ao receber um sinal de parada, o ponto de entrada dá até 30 segundos para o Paper encerrar e depois até 10 segundos para o Bungee. O tempo limite de parada do Docker de 45 segundos permite concluir essa sequência. Consulte o [comportamento de parada do Docker](https://docs.docker.com/reference/cli/docker/container/stop/).

### Preparar a atualização em um novo diretório

**O diretório de execução completo só é inicializado a partir da imagem na primeira inicialização.** Após trocar a imagem, a montagem existente continua fornecendo os arquivos do servidor, frontend e backend Python. Atualizar exige substituir explicitamente os arquivos de execução e migrar o estado persistente.

**Etapa 1: Parar e fazer backup.** Preserve o contêiner, o diretório e a versão da imagem antigos.

**Etapa 2: Preparar um novo diretório de execução.** Copie o modelo completo da imagem de destino. Este exemplo usa `2.2.5`; escolha um nome de contêiner de modelo e um diretório ainda livres:

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

Mantenha o contêiner de modelo sem iniciar. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) permite copiar arquivos de contêineres parados. Depois de copiar o modelo, migre o estado persistente do diretório antigo:

| Dados | Como migrar |
|------|----------|
| `server-1.12/<level-name>` e seus diretórios Nether e End | Copie os mundos completos e mantenha `level-name` coerente com os nomes dos diretórios |
| `server-data/` | Copie o repositório completo de plugins, os arquivos de marcação e os diretórios legados de mundos |
| Arquivos `*.properties`, `*.yml` e `*.json` do Paper | Mescle a configuração com o novo modelo; preserve operadores, listas de permissões, banimentos e caches de jogadores |
| Configuração do Bungee, bancos de autenticação e caches de skins | Migre configurações e bancos individualmente; confira estados personalizados na raiz e nos diretórios de plugins |
| Frontend personalizado, plugins e opções de inicialização | Integre as personalizações necessárias; use os JARs do servidor, scripts e recursos administrativos da imagem de destino |

O ponto de entrada recria os links `server/`, `web/` e `plugins` do Paper. Copie os diretórios externos de dados para um novo diretório do host e monte-o no novo contêiner no caminho original. Mantenha a raiz antiga para o contêiner anterior. Inclua dados de outras versões e mundos personalizados na lista de migração.

**Etapa 3: Iniciar o novo contêiner.** Use o [comando de início rápido](#2-iniciar-o-paper-1122), mudando o nome para `eaglerx-1.12-next`, o diretório do host para `/data/eagler-1.12-next` e a imagem para a versão desejada. Preserve a versão do jogo, senha, URL pública e mapeamentos de portas originais.

**Etapa 4: Verificar a migração.** Confirme que o Paper está pronto, jogadores entram, mundos permanecem íntegros, plugins carregam e listas de permissões e mapas funcionam. Depois, defina o prazo de retenção do contêiner, imagem e backups antigos.

### Reverter a versão e restaurar dados

Com o contêiner e o diretório antigos preservados, pare o novo e inicie o antigo:

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

A reversão restaura o estado salvo no diretório antigo. Preserve os dados criados enquanto o novo contêiner estava ativo para recuperá-los depois. Para restaurar um backup compactado, extraia-o em um novo diretório, monte o diretório `eagler-1.12` extraído como diretório de execução completo e use a imagem e as opções de inicialização associadas ao backup.

## Operação e solução de problemas

Estes comandos usam o nome padrão do contêiner:

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

Paper e Bungee executam no tmux. O console do Paper acima usa o painel padrão `mcserver:0.1`; o Bungee usa `mcserver:0.0`. A verificação de integridade do Docker consulta as portas 5200, 5201 e 25565. O painel também consulta o RCON para determinar se o Paper está pronto.

| Sintoma | O que verificar |
|------|------------|
| O contêiner encerra imediatamente | Confira se `MINECRAFT_VERSION` é `1.8` ou `1.12` e procure o erro específico nos logs |
| A inicialização informa um diretório incompleto | Inicialize um diretório vazio ou restaure um backup completo; preserve o atual para investigação |
| O painel abre enquanto o Paper ainda inicia | Confira a geração de mundos e o carregamento de plugins no console; o painel atualiza quando o Paper fica pronto |
| O painel remoto está inacessível | Confira se o túnel SSH ou proxy de administração alcança `127.0.0.1:5201` no host |
| O link rápido está errado ou a conexão HTTPS falha | Confira `PUBLIC_GAME_URL`, a porta pública e o encaminhamento WebSocket do proxy do jogo |
| `/api/status` retorna 404 | Defina `RCON_PASSWORD` e recrie o contêiner; o script de inicialização usa o valor para ativar o RCON |
| O login retorna 429 | Cinco falhas da mesma origem na janela de falhas causam bloqueio de 10 minutos; administradores atrás de um túnel ou proxy podem compartilhar a origem |
| Alterações foram salvas, mas o comportamento antigo continua | Reinicie o Paper de forma controlada pelo painel e confira o estado em execução |
| Dynmap retorna 502 | Confira se está ativado e terminou de carregar; verifique endereço e porta HTTP |
| A busca nativa de estruturas falha | Confira o ambiente `linux/amd64`, erros ao carregar bibliotecas nativas e a leitura da seed |

O ponto de entrada inicia Bungee, Paper e HTTP nessa ordem e os monitora continuamente. Se um serviço principal encerrar, ele desliga todo o contêiner e retorna falha. Ao receber `SIGTERM` / `SIGINT`, realiza um desligamento ordenado. Configure a política de reinicialização considerando que desligar pelo painel também encerra o contêiner.

## Variáveis de ambiente

Passe-as com `docker run -e`. Para alterar as variáveis de um contêiner, recrie-o com a montagem existente.

| Variável | Padrão | Descrição |
|------|--------|------|
| `MINECRAFT_VERSION` | Obrigatória | `1.8` seleciona Paper 1.8.8; `1.12` seleciona Paper 1.12.2 |
| `RCON_PASSWORD` | Vazia | Ativa RCON e API quando definida; endpoints administrativos autenticados ficam desativados quando vazia |
| `PUBLIC_GAME_URL` | Vazia | URL pública HTTP(S) usada para gerar links rápidos e endereços WebSocket |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | Raiz dos repositórios de plugins e montagens legadas de mundos; um diretório vazio inicializa o repositório automaticamente |
| `SERVER_DATA_DIR` | Vazia | Alias de compatibilidade de `PERSISTENT_DATA_ROOT`; um valor explícito desta última tem prioridade |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | Validade do token de administração, em segundos |
| `ADMIN_AUTH_SECRET` | Derivada da senha RCON | Segredo opcional para assinatura dos tokens |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | Endereço upstream do Dynmap usado pelo backend de administração |

## API de administração

Para integrações por scripts. Todos os endpoints usam a porta administrativa **5201**. O painel atende às operações do dia a dia.

<details>
<summary>Endpoints, autenticação e exemplos com curl</summary>

“Público” descreve os requisitos de autenticação do próprio endpoint. Acesse a porta administrativa por um [túnel SSH ou proxy de administração](#administração-remota-e-portas).

| Endpoint | Requisitos de acesso |
|------|----------|
| `GET /api/connection-info` | Sempre disponível; retorna a configuração do acesso público ao jogo |
| `GET /api/status` | Disponível com RCON ativado; retorna o estado do Paper e informações relacionadas |
| `POST /api/login` | Troca a senha de administração por um token quando o RCON está ativado |
| Endpoints JSON administrativos como `POST /api/rcon`, `/api/config`, `/api/system` e `/api/plugins` | O corpo precisa incluir um `token` válido |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, corpo JAR bruto e cabeçalho `X-Plugin-Filename` |
| `GET /dynmap/` | Proxy direto para o Dynmap; a conexão de administração protege o acesso |

Requisições JSON aceitam corpos de até 64 KiB e têm tempo de leitura de 10 segundos. Uploads de JAR bruto aceitam até 64 MiB e têm prazo total de leitura de 30 segundos. Administradores que compartilham a origem de um túnel ou proxy reverso podem compartilhar a mesma janela de bloqueio.

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

## Desenvolvimento, build e publicação

### Alterações locais e validação

Execute estes comandos na raiz do repositório com Python 3 e Docker instalados. Edite os recursos administrativos em `web-1.8/` e rode o script de sincronização para atualizar `web-1.12/`. Consulte a [decisão sobre a imagem base](docs/adr/0007-retain-the-verified-runtime-base.md) para os requisitos da imagem e das bibliotecas nativas.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

A validação local de publicação também exige Node.js, tmux, `agent-browser` e uma instalação funcional do Chrome. A CI fixa `agent-browser@0.26.0`; veja a instalação no [fluxo de publicação](.github/workflows/release.yml).

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

As verificações locais cobrem sintaxe Python, regressões do servidor e plugins, recursos das duas versões, recursos administrativos e fluxos de navegador em inglês e chinês simplificado. O navegador usa uma Mock Admin API local. A validação completa também constrói a imagem e executa ambas as versões do Paper:

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

A validação define `release_ready` como `true` em `summary.json` somente após todos os testes `--live` passarem. Veja a [documentação da validação de publicação](docs/release-gate.md) para cobertura, formatos de evidências e permissões de montagens temporárias no Linux.

### Publicar uma versão

Publicações oficiais usam as tags Git `vMAJOR.MINOR` ou `vMAJOR.MINOR.PATCH`. O fluxo valida uma única imagem por completo e a publica no GHCR com tags de versão e SHA do commit e uma atestação de procedência do build. Publicações automáticas da versão mais alta atualizam `latest`; execuções manuais atualizam apenas a versão indicada e as tags SHA.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` simplifica os builds locais; seu argumento `push` envia a imagem diretamente. A distribuição oficial segue o [requisito de validação live completa](docs/adr/0005-require-the-live-release-gate.md) e o fluxo de tags acima.

## Relatar problemas

Relate problemas de implantação e pedidos de recursos em [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues). Inclua a tag da imagem, `MINECRAFT_VERSION`, arquitetura do host, opções de inicialização com dados sensíveis ocultos, passos de reprodução e logs relevantes. Remova senhas e tokens antes de enviar.

## Créditos

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Projeto de origem](https://github.com/burgerhugger/ALL-server)
