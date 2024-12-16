FROM ubuntu:noble

RUN \
  apt-get update && \
  apt-get install -y bash curl git python3 && \
  rm -rf /var/lib/apt/lists/*

RUN \
  curl -fsSL https://github.com/github/hub/raw/master/script/get | \
    bash -s v2.14.2

COPY delete_old_branches.py /delete_old_branches.py
ENTRYPOINT ["/delete_old_branches.py"]
