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

# Release tarball via Python: works with the legacy builder (no buildx here), needs no git/curl.
RUN python -c "import io,sys,tarfile,urllib.request as u; tarfile.open(fileobj=io.BytesIO(u.urlopen(sys.argv[1]).read())).extractall('/opt', filter='data')" \
      "https://github.com/comfyanonymous/ComfyUI/archive/refs/tags/${COMFYUI_REF}.tar.gz" \
 && mv "/opt/ComfyUI-${COMFYUI_REF#v}" /opt/ComfyUI \
 && pip install -r /opt/ComfyUI/requirements.txt \
 && install -d -o 1000 -g 1000 /home/comfy \
 && chown -R 1000:1000 /opt/ComfyUI

WORKDIR /opt/ComfyUI
USER 1000:1000
EXPOSE 8188
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
