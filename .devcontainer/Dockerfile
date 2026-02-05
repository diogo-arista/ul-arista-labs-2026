FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install dependencies, setup python alias, and install tools
RUN apt-get update && apt-get install -y python3-pip curl \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && pip3 install gdown --break-system-packages --no-cache-dir \
    && curl -sL https://get.containerlab.dev | bash \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*
