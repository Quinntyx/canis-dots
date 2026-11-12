# Standalone Forge Neo build. The Python/CUDA toolchain layers deliberately match
# the existing ComfyUI Dockerfile so rebuilding on araveia can reuse their cache.
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/comfy
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev

ARG FORGE_REF=507e66fbbb5c42645e8b22431789da08d62949e7
LABEL org.opencontainers.image.source="https://github.com/Haoming02/sd-webui-forge-classic" \
      org.opencontainers.image.revision="${FORGE_REF}"
RUN apt-get update && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 libgomp1
ADD https://codeload.github.com/Haoming02/sd-webui-forge-classic/tar.gz/${FORGE_REF} /tmp/forge.tar.gz
RUN install -d /opt/forge-neo \
 && tar -xzf /tmp/forge.tar.gz -C /opt/forge-neo --strip-components=1 \
 && pip install gradio==4.40.0 gradio_rangeslider==0.0.8 \
 && pip install -r /opt/forge-neo/requirements.txt \
 && useradd --uid 1000 --user-group --create-home --home-dir /home/forge forge \
 && chown -R 1000:1000 /opt/forge-neo /home/forge

ENV HOME=/home/forge \
    USER=forge \
    XDG_CACHE_HOME=/data/cache \
    HF_HOME=/data/huggingface \
    TORCH_HOME=/data/torch \
    TORCHINDUCTOR_CACHE_DIR=/data/cache/torchinductor \
    GRADIO_TEMP_DIR=/data/gradio
COPY entrypoint.sh /usr/local/bin/forge-neo-entrypoint
RUN chmod 0755 /usr/local/bin/forge-neo-entrypoint
WORKDIR /opt/forge-neo
USER 1000:1000
EXPOSE 7860
ENTRYPOINT ["/usr/local/bin/forge-neo-entrypoint"]
