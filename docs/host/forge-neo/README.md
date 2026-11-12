# Forge Neo on araveia

Open **http://araveia:8188/forge/** over Tailscale. SwarmUI stays at the same
address without `/forge/`; no new firewall port or LAN listener is introduced.
The existing Caddy gate in `../comfyui/gate/Caddyfile` routes the two frontends.

The container starts on demand through `forge-neo-proxy.socket`. Closing all
clients lets the relay stop it after 30 minutes, releasing GPU allocations.
Do not run concurrent Forge and Swarm generations on the same 12 GB GPU.

## Initial model selection

The `qwen21` UI preset uses the existing Qwen-Image 2.1 INT8 checkpoint,
Qwen3-VL-8B abliterated INT8 ConvRot encoder, and Qwen Image 2.1 VAE. All are
mounted read-only from `../comfyui/models`; no weights are duplicated.
The initial resolution is 1024x1024, Euler/Simple, 16 steps, CFG 2.5.

Use **ImageStitch Integrated** to add multiple reference images. Enable its
accordion, add files to the gallery, or paste an image and click
**Append Pasted Image**. The preset has Qwen 2.1 reference editing enabled.

Settings and caches persist in `data/`; generated images persist in `output/`.
These runtime directories are intentionally not tracked by chezmoi. The initial
configuration is copied once, then Forge owns subsequent changes made in its UI.
Changing `config.initial.json` does not overwrite an existing user's settings.

## Management

```sh
# Build after an intentional pinned-source update.
cd ~/docs/host/forge-neo
docker compose build forge-neo

# Systemd owns activation and shutdown; do not bypass it with `compose up`.
systemctl --user stop forge-neo-proxy.service forge-neo.service
journalctl --user -u forge-neo -f
docker compose logs --tail=50 -f forge-neo
```

The image pins Forge Neo source revision
`507e66fbbb5c42645e8b22431789da08d62949e7`; dependencies are installed at build
time. Startup does not modify the Python environment or update source.
