# Compose deployment directory

The Release Image runs under Docker Compose v2 from deploy/docker-compose/,
with the pinned image, the bind-mounted data directory, the environment file,
and the Caddy overlay carried as runnable files next to the systemd path in
deploy/. Compose owns the file split so one scenario stays one directory: the
base file runs the game stack, and the overlay adds the public entry point for
readers who publish it beyond the home network. The published walkthrough
embeds these files and links the directory for the full set.
