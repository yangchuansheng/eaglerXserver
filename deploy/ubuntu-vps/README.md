# Bare-metal systemd deployment on an Ubuntu VPS

Run the released runtime bundle directly on an Ubuntu host under `systemd`,
with Caddy terminating HTTPS on 443. This directory carries the deployment
files for that path; the [Docker quick start](../../README.md#quick-start) stays
the supported route for the published Release Image.

The recorded installation, the full command sequence, and the evidence boundary
are published in the
[Sealos walkthrough](https://sealos.io/blog/eaglercraft-server-ubuntu-vps/).
The files in this directory are the ones that guide installs.

## Files

| File | Installed as | Purpose |
| --- | --- | --- |
| `eaglercraft-gateway.service` | `/etc/systemd/system/` | Runs `bungee/run.sh`, which holds the WebSocket and HTTP listener on 5200 |
| `eaglercraft-paper.service` | `/etc/systemd/system/` | Supervises the game server through `bin/paper-tmux.sh` |
| `eaglercraft-panel.service` | `/etc/systemd/system/` | Runs `script/http_server.py` for the Server Management Panel |
| `eaglercraft-backup.service` and `.timer` | `/etc/systemd/system/` | Takes one world snapshot each night |
| `paper-tmux.sh` | `/opt/eaglercraft/bin/` | Starts the tmux session that owns the game server pane |
| `backup.sh` | `/opt/eaglercraft/bin/` | Saves the world and writes a dated archive |
| `tmux.conf` | `/opt/eaglercraft/bin/` | Pins the pane shell and keeps a crashed pane addressable |
| `eaglercraft.env.example` | `/etc/eaglercraft/eaglercraft.env` | Runtime settings shared by every unit |
| `Caddyfile.example` | `/etc/caddy/Caddyfile` | HTTPS site block that forwards the client page and the WebSocket upgrade |

## Install

Unpack the Release Version tag archive into `/opt/eaglercraft`, publish the
selected Game Version through the `web` and `server` symlinks, and create the
service account first. The [walkthrough](https://sealos.io/blog/eaglercraft-server-ubuntu-vps/)
records those commands together with the observed output.

```sh
sudo useradd --system --create-home --home-dir /opt/eaglercraft \
  --shell /usr/sbin/nologin eaglercraft
sudo mkdir -p /opt/eaglercraft/bin /etc/eaglercraft /var/backups/eaglercraft
```

Copy the runtime files, keeping the executable bit on the two scripts:

```sh
sudo install -m 0755 paper-tmux.sh backup.sh /opt/eaglercraft/bin/
sudo install -m 0644 tmux.conf /opt/eaglercraft/bin/tmux.conf
sudo install -m 0640 -o root -g eaglercraft eaglercraft.env.example \
  /etc/eaglercraft/eaglercraft.env
sudo chown -R eaglercraft:eaglercraft /opt/eaglercraft /var/backups/eaglercraft
```

Edit `/etc/eaglercraft/eaglercraft.env` and set a generated `RCON_PASSWORD`
plus the public `PUBLIC_GAME_URL`. The panel builds its Overview connection card
from that value, and an empty value leaves visitors with a loopback address.

```sh
sudo install -m 0644 ./*.service ./*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now eaglercraft-gateway eaglercraft-paper eaglercraft-panel
sudo systemctl enable --now eaglercraft-backup.timer
```

Start the gateway before the game server. The paper unit declares the gateway as
an ordering dependency, and the panel probes the game server pane once it starts.

## Network and access boundary

| Port | Process | Exposure in the recorded run |
| --- | --- | --- |
| 5200 | Gateway | `127.0.0.1` from `bungee/plugins/EaglercraftXBungee/listeners.yml`; Caddy forwards 80/443 to it |
| 5201 | Server Management Panel | `0.0.0.0` from `script/http_server.py`, which reads no bind override |
| 25565 | Paper | Loopback |
| 25575 | RCON | Loopback |

The panel bind address comes from the runtime source, so the host firewall is
the control that keeps 5201 off the network. Allow SSH, HTTP, and HTTPS and let
the default policy drop the rest:

```sh
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Administration runs through an SSH tunnel as described in
[Remote management and ports](../../README.md#remote-management-and-ports):

```sh
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

The Caddy site block forwards the client page and the WebSocket upgrade to 5200
and adds the `X-Real-IP` header the gateway requires. Copy
`Caddyfile.example` to `/etc/caddy/Caddyfile`, replace the hostname, then run
`sudo caddy validate --config /etc/caddy/Caddyfile` before
`sudo systemctl reload caddy`.

## Recorded scope

The recorded run used one Ubuntu 24.04.4 LTS host with 2 vCPU, 3,911 MiB memory,
and a 51 GiB root disk on a private network. These steps were executed and
observed: the account and archive install, all four units enabled and active, the
loopback and panel listeners, Caddy returning the client page, the `ufw` ruleset,
a reboot with all four units restored, one `eaglercraft-backup.service` snapshot,
a restore into a fresh world directory, a browser join with registration, and the
panel reached through an SSH tunnel.

Public DNS resolution, certificate issuance, a browser `wss://` session, inbound
access from the public internet, a second machine joining, and a Release Upgrade
across tags stayed outside that run. Treat them as unverified until a recorded
execution covers them.
