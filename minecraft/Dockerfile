FROM itzg/minecraft-server:latest

USER root

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

RUN /opt/venv/bin/pip install --upgrade pip

RUN /opt/venv/bin/pip install pyyaml

ENV PATH="/opt/venv/bin:${PATH}"

USER minecraft
