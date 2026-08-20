# Keep the management plane local

The management plane is published only on the host loopback interface. Remote administration uses an external HTTPS reverse proxy, VPN, or SSH tunnel so the container stays certificate-agnostic while credentials remain inside a trusted transport boundary. The RCON password is exchanged only at login; every privileged API call uses an eight-hour token stored for the current browser session.
