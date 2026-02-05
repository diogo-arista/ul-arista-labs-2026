FROM mcr.microsoft.com/devcontainers/base:ubuntu
FROM ghcr.io/aristanetworks/aclabs/host-ubuntu:rev1.0

# 1. Install system dependencies & setup python alias
# 2. Install gdown (using --break-system-packages for Ubuntu 24.04)
# 3. Install Containerlab
# 4. Create necessary groups and add 'vscode' user
RUN apt-get update && apt-get install -y python3-pip curl \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && pip3 install gdown --break-system-packages --no-cache-dir \
    && curl -sL https://get.containerlab.dev | bash \
    && groupadd -f docker \
    && groupadd -f clab_admins \
    && usermod -aG docker,clab_admins vscode \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*
