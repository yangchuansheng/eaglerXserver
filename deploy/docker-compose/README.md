# Docker Compose deployment path

Run the published Release Image under Compose v2 with one bind-mounted data
directory. The base file publishes the browser client and game WebSocket on
5200, binds the Server Management Panel to the host loopback on 127.0.0.1:5201,
and stores the world, plugins, and server config in ./data.

MINECRAFT_VERSION in .env selects Paper 1.8.8 or Paper 1.12.2; the container
exits when it is missing. A first start on an empty data directory initializes
the server tree from the image, and an incomplete directory makes the server
exit with a visible error instead of silently replacing it. Container recreation
and upgrades keep reading the same directory.

The overlay adds Caddy on public ports 80 and 443 for a domain entry point such
as play.example.com; the gateway requires the X-Real-IP header that the
Caddyfile supplies.

The recorded walkthrough, including first start, browser join, recreation, and
the backup and restore drill, is published at
https://sealos.io/blog/eaglercraft-server-docker/.
