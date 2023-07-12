FROM ubuntu:lunar

RUN \
  apt-get update && \
  apt-get install -y shellcheck wget && \
  rm -rf /var/lib/apt/lists/*

RUN \
  wget -nv -O /usr/local/bin/shfmt \
    https://github.com/mvdan/sh/releases/download/v3.0.2/shfmt_v3.0.2_linux_amd64 && \
  chmod +x /usr/local/bin/shfmt

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
