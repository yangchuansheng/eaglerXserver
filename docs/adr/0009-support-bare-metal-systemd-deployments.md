# Support bare-metal systemd deployments

The released runtime bundle runs under systemd on an Ubuntu host from the same
tag archive that builds the Release Image. `deploy/ubuntu-vps/` carries the
systemd units, the Caddy site block, the tmux configuration, the environment
template, and the backup script, so both paths share one source tree, one runtime
layout, and one Management Plane contract. The host firewall carries the
Management Plane boundary in this path, matching the loopback port mapping that
keeps the panel off the network in the image, and administration continues
through an SSH tunnel or an HTTPS reverse proxy.
