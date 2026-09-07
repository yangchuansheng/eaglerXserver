# EaglercraftX Server

Hébergez un serveur Minecraft accessible depuis le navigateur, avec un stockage persistant et un panneau d’administration pour gérer les joueurs, les mondes et les plugins. L’image Docker inclut les clients EaglercraftX 1.8 / 1.12 et les serveurs Paper 1.8.8 / 1.12.2 ; choisissez la version du jeu au démarrage.

![Panneau d’administration EaglercraftX](../images/admin-panel.png)

<!-- README-I18N:START -->

[English](../../README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | **Français** | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[Démarrage rapide](#démarrage-rapide) · [Rejoindre le serveur](#rejoindre-le-serveur) · [Administration et plugins](#panneau-dadministration-et-plugins) · [Sauvegardes et mises à jour](#sauvegardes-mises-à-jour-et-retours-arrière) · [Dépannage](#exploitation-et-dépannage) · [Variables d’environnement](#variables-denvironnement) · [API d’administration](#api-dadministration) · [Développement et publication](#développement-compilation-et-publication) · [Signaler un problème](#signaler-un-problème)

## Fonctionnalités

| Fonctionnalité | Détails |
|------|------|
| Gestion du serveur | État de disponibilité de Paper, joueurs connectés, ticks par seconde (TPS), météo, heure, règles du jeu, configuration et redémarrages contrôlés |
| Joueurs et mondes | Droits d’opérateur (OP), listes blanches, expulsions, bannissements, téléportation, commandes d’objets, sauvegarde et bordures des mondes |
| Gestion des plugins | Dépôts distincts par version du jeu ; ajout, activation, désactivation et suppression, avec application après redémarrage de Paper |
| Cartes et graines | Dynmap intégré, position des joueurs, recherche native de structures et liens vers un Seed Map externe |
| Plugins inclus | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## Démarrage rapide

### 1. Préparer la machine hôte

- **Hôte** : installez Docker et prévoyez un stockage persistant. Les exemples utilisent des chemins Linux. Les images publiées ciblent AMD64 ; l’émulation ARM64 et la compatibilité des bibliothèques natives nécessitent une validation distincte. Consultez la [décision d’architecture](../adr/0006-publish-linux-amd64-only.md).
- **Mémoire** : Paper et Bungee utilisent chacun `-Xms256M -Xmx256M`. Prévoyez de la mémoire supplémentaire pour la JVM hors du tas, la génération des mondes et les plugins. Pour ajuster la taille du tas, modifiez `run.sh` dans le répertoire d’exécution concerné.
- **EULA** : le script de démarrage écrit `eula=true`. Lisez et acceptez le [contrat EULA de Minecraft](https://www.minecraft.net/en-us/eula) avant le déploiement.

### 2. Démarrer Paper 1.12.2

Exécutez ces commandes sur le serveur. Remplacez `YOUR_SERVER` par une adresse IP ou un domaine accessible aux joueurs, et `replace-with-a-strong-password` par votre mot de passe d’administration.

Cet exemple monte `/data/eagler-1.12` sur l’hôte dans `/eaglerX-1.8-server` à l’intérieur du conteneur et conserve **l’ensemble du répertoire d’exécution** : mondes, plugins, configuration et fichiers du frontend. Un répertoire vide est initialisé automatiquement à la première utilisation. Si un répertoire existant est incomplet, le démarrage préserve son contenu puis s’arrête. Pour un déploiement existant, suivez [Sauvegardes, mises à jour et retours arrière](#sauvegardes-mises-à-jour-et-retours-arrière) pour migrer les fichiers d’exécution.

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

### 3. Ouvrir le panneau et vérifier la disponibilité

| Accès | Adresse | Utilisation |
|------|------|----------|
| Jeu | `http://YOUR_SERVER:5200/` | Partagez cette adresse et suivez les [instructions de connexion](#rejoindre-le-serveur) |
| Administration | `http://127.0.0.1:5201/admin` | Ouvrez depuis l’hôte et connectez-vous avec le mot de passe défini au démarrage |

La génération initiale du monde peut prendre quelques minutes. Le démarrage est terminé lorsque le panneau affiche **Paper is ready**. En cas d’attente prolongée ou d’erreur, consultez [Exploitation et dépannage](#exploitation-et-dépannage).

### Administration à distance et ports

Pour administrer un serveur distant, ouvrez un tunnel SSH depuis votre ordinateur. Remplacez `user@YOUR_SERVER` par l’adresse de connexion SSH du serveur :

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

Gardez le tunnel ouvert, puis accédez à `http://127.0.0.1:5201/admin`. Vous pouvez aussi utiliser un proxy inverse HTTPS dont le serveur amont est `127.0.0.1:5201` sur l’hôte. Un accès d’administration par VPN doit pouvoir acheminer le trafic vers cette adresse de bouclage.

| Port | Usage | Exposition |
|------|------|----------|
| 5200 | Page de jeu HTTP, fichiers statiques publics et connexions de jeu WebSocket | Accessible aux joueurs |
| 5201 | Administration, service HTTP de secours et proxy Dynmap | Lier à `127.0.0.1` sur l’hôte |
| 25565 | Paper | Localhost dans le conteneur |
| 25575 | RCON | Localhost dans le conteneur |

### Domaines personnalisés, HTTPS et URL du jeu

Définissez `PUBLIC_GAME_URL` sur **l’URL HTTP(S) du jeu réellement utilisée par les joueurs**. Le panneau s’en sert pour générer les liens de connexion rapide et les adresses `ws` / `wss`. Si elle reste vide, une URL HTTP est déduite du nom d’hôte du panneau et du port 5200 (`http://主机名:5200/`). Renseignez-la explicitement avec un tunnel SSH, un domaine d’administration distinct ou un port de jeu personnalisé.

Un accès au jeu en HTTPS nécessite DNS, un certificat et le transfert HTTP et WebSocket vers **5200**. Faites pointer le proxy d’administration vers **5201**. `PUBLIC_GAME_URL` sert uniquement à générer les adresses de connexion ; configurez le proxy et le certificat dans votre déploiement.

### Choisir 1.8 ou exécuter les deux versions

`2.2.5` est la version de publication de l’image. `MINECRAFT_VERSION=1.8` sélectionne Paper 1.8.8 et `1.12` sélectionne Paper 1.12.2. Chaque conteneur exécute une seule version du jeu à la fois et utilise son propre répertoire.

Pour exécuter 1.8, adaptez ces paramètres dans la commande de démarrage rapide :

| Paramètre | Exécuter 1.8 seule | Exécuter 1.8 avec 1.12 |
|------|-------------|---------------------|
| Nom du conteneur | `--name eaglerx-1.8` | Identique à gauche |
| Version du jeu | `-e MINECRAFT_VERSION=1.8` | Identique à gauche |
| Montage du répertoire complet | `-v /data/eagler-1.8:/eaglerX-1.8-server` | Identique à gauche |
| Port du jeu | `-p 5200:5200` | `-p 5300:5200` |
| Port d’administration | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| URL publique du jeu | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

Définissez `PUBLIC_GAME_URL` sur l’URL de cette instance. Pour administrer la seconde instance à distance, utilisez `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` et ouvrez `http://127.0.0.1:5301/admin`.

## Rejoindre le serveur

1. Ouvrez l’URL du jeu ou utilisez le lien rapide partagé par le propriétaire du serveur depuis la page Overview du panneau. Le client 1.12 démarre avec une liste de serveurs vide ; ajoutez `ws://YOUR_SERVER:5200/` dans Multijoueur ou utilisez l’adresse `wss://` correspondante pour un accès HTTPS.
2. Lors de votre première visite, suivez les indications de LoginSecurity et saisissez `/register <password>`. Utilisez `/login <password>` lors des visites suivantes. L’inscription est obligatoire par défaut, le mot de passe doit compter au moins 6 caractères et le délai de connexion est de 30 secondes.
3. LoginSecurity gère les mots de passe des comptes joueurs. Le panneau utilise le `RCON_PASSWORD` du propriétaire du serveur.

SimpleHomes fournit `/sethome <name>`, `/home <name>` et `/homes`. SimpleTpa fournit `/tpa <player>`, `/tpaccept` et `/tpdeny`. Les permissions et le comportement dépendent de la configuration actuelle du plugin.

## Panneau d’administration et plugins

### Se connecter et appliquer les changements

Définir `RCON_PASSWORD` active RCON et l’API d’administration. Après connexion, le navigateur conserve un jeton dans la session en cours ; il expire après 8 heures par défaut. La déconnexion efface le jeton local. L’interface est en anglais par défaut, prend en charge le chinois simplifié et mémorise le choix de langue pour le site.

Vous pouvez vous connecter pendant le démarrage de Paper. Les commandes de jeu deviennent disponibles lorsque Paper est prêt.

| Action | Prise d’effet |
|------|----------|
| Météo, heure, règles du jeu, commandes joueurs et liste blanche | Envoyées à l’instance Paper en cours ; consultez la réponse de la console |
| Configuration du serveur : MOTD, limite de joueurs, distance de vue et PVP | Écrite dans `server.properties` et appliquée après redémarrage de Paper |
| Ajout, activation, désactivation et suppression de plugins | Enregistrés dans le dépôt et appliqués après redémarrage de Paper |
| Redémarrage de Minecraft depuis le panneau | Redémarre Paper de façon contrôlée ; Bungee et le panneau restent actifs |
| Arrêt depuis le panneau ou `stop` dans la console | Paper s’arrête, ce qui déclenche l’arrêt du conteneur entier |

Dynmap est accessible via le proxy `/dynmap/` du panneau. La recherche native de structures utilise le composant cubiomes intégré à l’image. Les structures et les points d’apparition approximatifs sont calculés à partir de la graine du monde ; les positions des joueurs proviennent de Dynmap ou de leurs sauvegardes. Ouvrir le Seed Map externe inclut la graine dans l’URL de destination.

### Dépôts et données des plugins

Le dépôt de la version active se trouve dans `server-data/plugins-1.8` ou `server-data/plugins-1.12`. Le répertoire `enabled/` contient les plugins activés et leurs données ; `disabled/` contient les paquets désactivés. Le chemin `plugins` de Paper pointe vers le répertoire `enabled/` du dépôt actif.

Le premier démarrage importe les plugins et données fournis. Les suivants conservent l’état actuel du dépôt, y compris les modifications manuelles, désactivations et suppressions. Le montage du répertoire complet conserve toutes ces données.

Le panneau affiche la version active du jeu, la taille et la date de modification des fichiers, l’état prévu au prochain démarrage et les redémarrages en attente :

- Les fichiers envoyés doivent être des JAR contenant `plugin.yml` à la racine de l’archive. Le nom doit se terminer par `.jar` en minuscules et la taille maximale est de **64 MiB**. Un nom déjà présent entraîne un conflit.
- Après ajout, activation, désactivation ou suppression d’un plugin, utilisez le redémarrage du panneau pour charger le nouvel ensemble. Le code chargé reste actif jusqu’à l’arrêt de Paper.
- La suppression enlève le JAR et conserve la configuration et les bases de données. Réinstaller un plugin compatible utilisant le même répertoire permet de réutiliser ces données.
- Les JAR s’exécutent avec les permissions du processus Paper. Utilisez des sources fiables, examinez et analysez les paquets avant installation, puis effectuez une sauvegarde.

<details>
<summary>Mondes existants et répertoire de données distinct (compatibilité historique)</summary>

`PERSISTENT_DATA_ROOT` définit une racine commune pour les dépôts de plugins et les anciens montages de mondes. `SERVER_DATA_DIR` est son alias de compatibilité. Le montage du répertoire d’exécution complet est la méthode de déploiement par défaut.

**Un répertoire de données distinct et vide initialise uniquement le dépôt de plugins.** Les liens symboliques exigent que les mondes correspondants existent déjà dans cette racine. Les nouveaux mondes restent dans le répertoire `server-版本/` de la version et sont conservés par le montage complet.

Pour migrer des mondes existants, arrêtez le serveur et sauvegardez-le, puis préparez les répertoires `<level-name>`, `<level-name>_nether` et `<level-name>_the_end`. Leurs noms par défaut sont `world`, `world_nether` et `world_the_end`. Le point d’entrée peut utiliser ces noms de repli et préserve les répertoires réels de mondes déjà présents aux chemins du serveur. Utilisez une racine par version et vérifiez la cible de chaque lien après démarrage.

</details>

## Sauvegardes, mises à jour et retours arrière

### Arrêter le serveur et sauvegarder

Ces commandes utilisent le conteneur et le montage du démarrage rapide. Les sauvegardes contiennent les mondes, l’état des joueurs, les données des plugins, la configuration, les bases d’authentification et le mot de passe d’administration. Stockez-les dans un répertoire à accès restreint.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

Pour une sauvegarde courante, exécutez `docker start eaglerx-1.12` une fois terminé. Pendant une mise à jour, gardez l’ancien conteneur arrêté. Si vous utilisez une racine `PERSISTENT_DATA_ROOT` externe, sauvegardez-la également ; tar conserve les liens symboliques eux-mêmes par défaut.

À réception d’un signal d’arrêt, le point d’entrée laisse jusqu’à 30 secondes à Paper pour se terminer, puis jusqu’à 10 secondes à Bungee. Le délai Docker de 45 secondes utilisé dans l’exemple laisse le temps à cette séquence. Consultez le [comportement d’arrêt de Docker](https://docs.docker.com/reference/cli/docker/container/stop/).

### Préparer la mise à jour dans un nouveau répertoire

**Le répertoire d’exécution complet est initialisé depuis l’image uniquement au premier démarrage.** Après un changement d’image, le montage existant continue de fournir les fichiers du serveur, du frontend et du backend Python. La mise à jour exige de remplacer explicitement les fichiers d’exécution et de migrer l’état persistant.

**Étape 1 : arrêter et sauvegarder.** Conservez l’ancien conteneur, son répertoire et sa version d’image.

**Étape 2 : préparer un nouveau répertoire d’exécution.** Copiez le modèle complet depuis l’image cible. Cet exemple utilise `2.2.5` ; choisissez un nom de conteneur modèle et un répertoire encore libres :

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

Laissez le conteneur modèle à l’arrêt, sans le démarrer. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) peut copier des fichiers depuis des conteneurs arrêtés. Après la copie du modèle, migrez l’état persistant de l’ancien répertoire :

| Données | Migration |
|------|----------|
| `server-1.12/<level-name>` et ses répertoires Nether et End | Copiez les mondes complets et gardez `level-name` cohérent avec les noms des répertoires |
| `server-data/` | Copiez tout le dépôt de plugins, les fichiers marqueurs et les anciens répertoires de mondes |
| Fichiers Paper `*.properties`, `*.yml` et `*.json` | Fusionnez la configuration avec le nouveau modèle ; conservez opérateurs, listes blanches, bannissements et caches des joueurs |
| Configuration Bungee, bases d’authentification et caches d’apparences | Migrez configuration et bases individuellement ; recherchez les données personnalisées dans la racine et les répertoires de plugins |
| Frontend personnalisé, plugins et options de lancement | Fusionnez les personnalisations utiles ; utilisez les JAR serveur, scripts et ressources d’administration de l’image cible |

Le point d’entrée recrée les liens symboliques `server/`, `web/` et `plugins` de Paper. Copiez les données externes dans un nouveau répertoire hôte, puis montez-le dans le nouveau conteneur à son chemin d’origine. Gardez l’ancienne racine pour l’ancien conteneur. Incluez aussi les données des autres versions et des mondes personnalisés dans votre liste de migration.

**Étape 3 : démarrer le nouveau conteneur.** Utilisez la [commande de démarrage rapide](#2-démarrer-paper-1122), avec `eaglerx-1.12-next` comme nom, `/data/eagler-1.12-next` comme répertoire hôte et la version cible de l’image. Conservez la version du jeu, le mot de passe, l’URL publique et les ports d’origine.

**Étape 4 : vérifier la migration.** Confirmez que Paper est prêt, que les joueurs se connectent, que les mondes sont intacts, que les plugins se chargent et que listes blanches et cartes fonctionnent. Définissez ensuite la durée de conservation de l’ancien conteneur, de l’image et des sauvegardes.

### Retour arrière et restauration

Si vous avez conservé l’ancien conteneur et son répertoire, arrêtez le nouveau et démarrez l’ancien :

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

Un retour arrière rétablit l’état enregistré dans l’ancien répertoire. Préservez les données créées pendant l’exécution du nouveau conteneur pour permettre leur récupération. Pour restaurer une archive, extrayez-la dans un nouveau répertoire, montez le répertoire `eagler-1.12` extrait comme répertoire d’exécution complet et utilisez la version d’image et les options de lancement associées à la sauvegarde.

## Exploitation et dépannage

Ces commandes utilisent le nom de conteneur par défaut :

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

Paper et Bungee s’exécutent dans tmux. La console Paper ci-dessus utilise le volet `mcserver:0.1` par défaut ; Bungee utilise `mcserver:0.0`. Le contrôle de santé Docker sonde les ports 5200, 5201 et 25565. Le panneau interroge aussi RCON pour déterminer si Paper est prêt.

| Symptôme | Vérification |
|------|------------|
| Le conteneur se termine immédiatement | Vérifiez que `MINECRAFT_VERSION` vaut `1.8` ou `1.12`, puis recherchez l’erreur précise dans les journaux |
| Le démarrage signale un répertoire incomplet | Initialisez un répertoire vide ou restaurez une sauvegarde complète ; conservez le répertoire actuel pour l’analyse |
| Le panneau s’ouvre alors que Paper démarre encore | Consultez la progression de génération des mondes et de chargement des plugins ; le panneau se met à jour quand Paper est prêt |
| Le panneau distant est inaccessible | Vérifiez que le tunnel SSH ou le proxy atteint `127.0.0.1:5201` sur l’hôte |
| Le lien rapide est incorrect ou HTTPS échoue | Vérifiez `PUBLIC_GAME_URL`, le port public et le transfert WebSocket du proxy du jeu |
| `/api/status` renvoie 404 | Définissez `RCON_PASSWORD` et recréez le conteneur ; le script de démarrage l’utilise pour activer RCON |
| La connexion renvoie 429 | Cinq échecs d’une même source pendant la fenêtre d’échecs entraînent un blocage de 10 minutes ; les administrateurs derrière un tunnel ou proxy peuvent partager la source |
| Les changements sont enregistrés, mais l’ancien comportement persiste | Effectuez un redémarrage contrôlé de Paper depuis le panneau, puis vérifiez l’état en cours |
| Dynmap renvoie 502 | Vérifiez son activation et la fin de son chargement, puis son adresse et son port HTTP |
| La recherche native de structures échoue | Vérifiez l’environnement `linux/amd64`, les erreurs de chargement des bibliothèques natives et la lecture de la graine |

Le point d’entrée démarre Bungee, Paper et HTTP dans cet ordre, puis les surveille. L’arrêt d’un service principal entraîne celui du conteneur entier avec un statut d’échec. À réception de `SIGTERM` / `SIGINT`, il effectue un arrêt ordonné. Configurez la politique de redémarrage en tenant compte de la sortie du conteneur déclenchée depuis le panneau.

## Variables d’environnement

Transmettez-les avec `docker run -e`. Pour modifier les variables d’un conteneur, recréez-le avec le montage existant.

| Variable | Valeur par défaut | Description |
|------|--------|------|
| `MINECRAFT_VERSION` | Obligatoire | `1.8` sélectionne Paper 1.8.8 ; `1.12` sélectionne Paper 1.12.2 |
| `RCON_PASSWORD` | Vide | Active RCON et l’API lorsqu’elle est définie ; les endpoints authentifiés sont désactivés lorsqu’elle est vide |
| `PUBLIC_GAME_URL` | Vide | URL HTTP(S) publique du jeu servant à générer les liens rapides et adresses WebSocket |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | Racine des dépôts de plugins et des anciens montages de mondes ; un répertoire vide initialise automatiquement le dépôt |
| `SERVER_DATA_DIR` | Vide | Alias de compatibilité de `PERSISTENT_DATA_ROOT` ; une valeur explicite de cette dernière est prioritaire |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | Durée de validité du jeton d’administration, en secondes |
| `ADMIN_AUTH_SECRET` | Dérivée du mot de passe RCON | Secret facultatif pour signer les jetons |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | Adresse amont Dynmap utilisée par le backend d’administration |

## API d’administration

Pour les intégrations par scripts. Tous les endpoints utilisent le port d’administration **5201**. Le panneau couvre les opérations courantes.

<details>
<summary>Endpoints, authentification et exemples curl</summary>

« Public » décrit les exigences d’authentification de l’endpoint lui-même. Accédez au port d’administration par un [tunnel SSH ou un proxy d’administration](#administration-à-distance-et-ports).

| Endpoint | Conditions d’accès |
|------|----------|
| `GET /api/connection-info` | Toujours disponible ; renvoie la configuration de l’accès public au jeu |
| `GET /api/status` | Disponible avec RCON activé ; renvoie l’état de Paper et les informations associées |
| `POST /api/login` | Échange le mot de passe d’administration contre un jeton lorsque RCON est activé |
| Endpoints JSON d’administration tels que `POST /api/rcon`, `/api/config`, `/api/system` et `/api/plugins` | Le corps doit inclure un `token` valide |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, un corps JAR brut et l’en-tête `X-Plugin-Filename` |
| `GET /dynmap/` | Proxy direct vers Dynmap ; la connexion d’administration protège l’accès |

Les requêtes JSON sont limitées à 64 KiB avec un délai de lecture de 10 secondes. Les envois de JAR bruts sont limités à 64 MiB et à 30 secondes de lecture totale. Les administrateurs partageant la source d’un tunnel ou proxy inverse peuvent partager la même fenêtre de blocage.

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

## Développement, compilation et publication

### Modifications locales et validation

Exécutez ces commandes à la racine du dépôt, avec Python 3 et Docker installés. Modifiez les ressources d’administration dans `web-1.8/`, puis lancez le script de synchronisation pour actualiser `web-1.12/`. Consultez la [décision sur l’image de base](../adr/0007-retain-the-verified-runtime-base.md) pour les exigences concernant l’image et les bibliothèques natives.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

La validation locale de publication exige aussi Node.js, tmux, `agent-browser` et une installation fonctionnelle de Chrome. La CI fixe `agent-browser@0.26.0` ; les étapes d’installation figurent dans le [workflow de publication](../../.github/workflows/release.yml).

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

Les contrôles locaux couvrent la syntaxe Python, les régressions serveur et plugins, les ressources des deux versions, les ressources d’administration et les parcours navigateur en anglais et chinois simplifié. Les tests navigateur utilisent une Mock Admin API locale. La validation complète construit aussi l’image et exécute les deux versions de Paper :

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

Le contrôle définit `release_ready` à `true` dans `summary.json` uniquement après réussite de tous les tests `--live`. Consultez la [documentation de validation de publication](../release-gate.md) pour la couverture, les formats de preuves et les permissions des montages temporaires Linux.

### Publier une version

Les versions officielles utilisent les tags Git `vMAJOR.MINOR` ou `vMAJOR.MINOR.PATCH`. Le workflow valide intégralement une même image, puis la publie dans GHCR avec des tags de version et de SHA du commit, ainsi qu’une attestation de provenance. La publication automatique de la version la plus élevée actualise `latest`. Les relances manuelles actualisent uniquement la version indiquée et les tags SHA.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` simplifie les constructions locales ; son argument `push` envoie directement l’image. La distribution officielle suit l’[exigence de validation live complète](../adr/0005-require-the-live-release-gate.md) et le workflow de tags ci-dessus.

## Signaler un problème

Signalez les problèmes de déploiement et les demandes de fonctionnalités dans [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues). Indiquez le tag de l’image, `MINECRAFT_VERSION`, l’architecture de l’hôte, les options de lancement expurgées des données sensibles, les étapes de reproduction et les journaux pertinents. Retirez mots de passe et jetons avant l’envoi.

## Crédits

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Projet amont](https://github.com/burgerhugger/ALL-server)
