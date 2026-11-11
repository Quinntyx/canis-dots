# ComfyUI pinned to a release tag. v0.45.0 includes FLUX 3 Image Klein support
# (comfyanonymous/ComfyUI#17064, merged 2026-10-15). Bump COMFYUI_REF deliberately.
FROM python:3.13-slim

ARG COMFYUI_REF=v0.45.0
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/comfy

# CUDA 13 wheels bundle their own CUDA runtime; the host driver comes in via nvidia-container-toolkit.
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# Triton compiles the INT8 (convrot) kernels at runtime and needs a C toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev

# Release tarball via Python: works with the legacy builder (no buildx here), needs no git/curl.
RUN python -c "import io,sys,tarfile,urllib.request as u; tarfile.open(fileobj=io.BytesIO(u.urlopen(sys.argv[1]).read())).extractall('/opt', filter='data')" \
      "https://github.com/comfyanonymous/ComfyUI/archive/refs/tags/${COMFYUI_REF}.tar.gz" \
 && mv "/opt/ComfyUI-${COMFYUI_REF#v}" /opt/ComfyUI \
 && pip install -r /opt/ComfyUI/requirements.txt \
 && install -d -o 1000 -g 1000 /home/comfy \
 && chown -R 1000:1000 /opt/ComfyUI

# Match SwarmUI's frontend revision. Its base64 image / websocket output nodes let
# the Generate tab build multi-reference workflows without editing the node graph.
ARG SWARM_REF=f86858dfe53f8c6138481f4ceae7e4ce9fa71d20
ADD https://codeload.github.com/mcmonkeyprojects/SwarmUI/tar.gz/${SWARM_REF} /tmp/swarm.tar.gz
RUN install -d /opt/swarm-nodes \
 && tar -xzf /tmp/swarm.tar.gz -C /opt/swarm-nodes --strip-components=5 \
      "SwarmUI-${SWARM_REF}/src/BuiltinExtensions/ComfyUIBackend/ExtraNodes/SwarmComfyCommon" \
 && pip install opencv-python-headless
COPY swarm/comfy-paths.yaml /opt/swarm-paths.yaml

WORKDIR /opt/ComfyUI
USER 1000:1000
EXPOSE 8188
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--extra-model-paths-config", "/opt/swarm-paths.yaml"]
