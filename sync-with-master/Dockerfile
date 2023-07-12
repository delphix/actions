FROM ubuntu:lunar

RUN \
  apt-get update && \
  apt-get install -y bash curl git && \
  rm -rf /var/lib/apt/lists/*

RUN \
  curl -fsSL https://github.com/github/hub/raw/master/script/get | \
  bash -s v2.14.2

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
