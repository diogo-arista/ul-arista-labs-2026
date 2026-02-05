FROM mcr.microsoft.com/devcontainers/base:ubuntu

# 1. Install system dependencies
# 2. Setup Python alias
# 3. Install gdown
# 4. Install Containerlab
# 5. Create 'clab_admins' group and add 'vscode' user to both 'docker' and 'clab_admins'
RUN apt-get update && apt-get install -y python3-pip curl \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && pip3 install gdown --break-system-packages --no-cache-dir \
    && curl -sL https://get.containerlab.dev | bash \
    && groupadd -f clab_admins \
    && usermod -aG docker,clab_admins vscode \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*