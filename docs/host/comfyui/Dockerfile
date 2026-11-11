# syntax=docker/dockerfile:1
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

ADD --chown=1000:1000 https://github.com/comfyanonymous/ComfyUI.git#${COMFYUI_REF} /opt/ComfyUI
RUN pip install -r /opt/ComfyUI/requirements.txt \
 && install -d -o 1000 -g 1000 /home/comfy

WORKDIR /opt/ComfyUI
USER 1000:1000
EXPOSE 8188
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
