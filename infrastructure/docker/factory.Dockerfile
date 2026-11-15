FROM python:3.12-slim-bookworm

ARG GODOT_VERSION=4.4-stable

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    GODOT_VERSION=${GODOT_VERSION} \
    GODOT_BIN=/usr/local/bin/godot

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    libfontconfig1 \
    sqlite3 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}/Godot_v${GODOT_VERSION}_linux.x86_64.zip" -o /tmp/godot.zip \
    && unzip -q /tmp/godot.zip -d /tmp/godot \
    && mv "/tmp/godot/Godot_v${GODOT_VERSION}_linux.x86_64" /usr/local/bin/godot \
    && chmod +x /usr/local/bin/godot \
    && rm -rf /tmp/godot /tmp/godot.zip

RUN mkdir -p /workspace /root/.local/share/godot \
    && git config --global --add safe.directory /workspace

WORKDIR /workspace
