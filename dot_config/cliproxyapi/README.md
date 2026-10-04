# CLIProxyAPI dev setup

Canonical source: https://git.quinntyx.dev/quinntyx/CLIProxyAPI
Server-side GitHub mirror: https://github.com/Quinntyx/CLIProxyAPI
Development checkout: ~/docs/src/CLIProxyAPI/dev

The user service listens at http://127.0.0.1:8317. OpenAI-compatible base URL:
http://127.0.0.1:8317/v1. The default strategy is reset-pressure; see
~/docs/src/CLIProxyAPI/dev/docs/reset-pressure-routing.md for the routing details.
Session affinity is disabled so sticky sessions do not override quota balancing.

## Private state (never version controlled)

- ~/.local/share/cliproxyapi/auths/: provider OAuth credentials, owner-only
- ~/.local/share/cliproxyapi/secrets.json: generated client_key and management_key
- ~/.local/state/cliproxyapi/: generated configuration and build artifacts
- ~/.local/lib/cliproxyapi/: compiled development binary

On a new machine, create the auth directory with mode 700. Generate local keys:

```sh
install -d -m 700 ~/.local/share/cliproxyapi/auths
(umask 077; jq -n --arg client_key "$(openssl rand -hex 32)" \
  --arg management_key "$(openssl rand -hex 32)" \
  '{client_key:$client_key, management_key:$management_key}' \
  > ~/.local/share/cliproxyapi/secrets.json)
```

Build with `cliproxyapi-update` after preparing the canonical dev worktree.
Add accounts interactively (repeat for each account):
`cliproxyapi --codex-login` or `cliproxyapi --codex-device-login`.
The initial setup imports the two distinct existing Codex accounts without
changing their source credential files. Imported token copies refresh independently;
if another client rotates a refresh token, re-login that account here if needed.

Read your client key locally with:
`jq -r .client_key ~/.local/share/cliproxyapi/secrets.json`
Use it as the Bearer/API key in clients. Do not put the literal key in tracked config.
For the management UI at http://127.0.0.1:8317/management.html, use
`jq -r .management_key ~/.local/share/cliproxyapi/secrets.json`.

## Operations

```sh
systemctl --user enable --now cliproxyapi.service
systemctl --user status cliproxyapi.service
journalctl --user -u cliproxyapi.service -n 50
cliproxyapi-update                   # fetch dev, build, install, restart if running
systemctl --user restart cliproxyapi.service  # regenerate runtime config
```

Chezmoi manages the secret-free config, service, and scripts. Commit/push source
changes before applying. The launcher assembles an owner-only runtime YAML with
the private local keys. To stop: `systemctl --user disable --now cliproxyapi.service`.
