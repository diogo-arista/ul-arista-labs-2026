FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install gdown and Containerlab during build
RUN apt-get update && apt-get install -y python3-pip python3-is-python3 curl \
    && pip3 install gdown --break-system-packages \
    && curl -sL https://get.containerlab.dev | bash \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*