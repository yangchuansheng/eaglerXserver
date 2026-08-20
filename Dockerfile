FROM registry.cn-hangzhou.aliyuncs.com/chenxuan/java:0.0.1
COPY . /opt/eaglerX-1.8-server-image
COPY script/libcubiomes_shim.so /usr/local/lib/libcubiomes_shim.so
RUN rm -rf /eaglerX-1.8-server \
    && mkdir -p /eaglerX-1.8-server \
    && cp /opt/eaglerX-1.8-server-image/script/start_server.sh /usr/local/bin/eaglerx-start \
    && chmod +x /usr/local/bin/eaglerx-start /opt/eaglerX-1.8-server-image/script/start_server.sh /opt/eaglerX-1.8-server-image/script/http_server.py
WORKDIR /eaglerX-1.8-server

ENV TERM xterm-256color
ENV APP_DIR=/eaglerX-1.8-server
ENV IMAGE_APP_DIR=/opt/eaglerX-1.8-server-image
ENV CUBIOMES_SHIM_PATH=/usr/local/lib/libcubiomes_shim.so
# 必须在 docker run 时显式传入：-e MINECRAFT_VERSION=1.8 或 1.12
# RCON_PASSWORD 可选，设置后启用 RCON 远程管理
# ENV RCON_PASSWORD=yourpassword

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python3 -c "import socket; [socket.create_connection(('127.0.0.1', port), 3).close() for port in (5200, 5201, 25565)]"

ENTRYPOINT ["/usr/local/bin/eaglerx-start"]
