#!/bin/sh
set -eu
umask 077

# Seed new installations only. Forge owns subsequent settings/preset changes.
if [ ! -e /data/config.json ]; then
    install -m 0600 /etc/forge/config.initial.json /data/config.json
fi

exec python /opt/forge-neo/launch.py \
    --skip-prepare-environment \
    --listen --port 7860 --api --subpath forge \
    --data-dir /data \
    --ui-settings-file /data/config.json \
    --ckpt-dirs /models/diffusion_models \
    --text-encoder-dirs /models/text_encoders \
    --vae-dirs /models/vae \
    --lora-dirs /models/loras \
    --gradio-allowed-path /output \
    "$@"
