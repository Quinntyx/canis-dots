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


## Pi, burn scheduling and the three Plus slots

Pi main defaults to `cliproxyapi/gpt-5.5`, via the native Codex WebSocket client with `websocket-cached`. The proxy model provider lives in shared `~/.config/pi/agent/models.json`; API keys are read with `!cliproxyapi-key`, never embedded in the new provider configuration. Existing Pi sessions keep their selected model until `/model cliproxyapi/gpt-5.5` (reload model configuration first if necessary); new main-profile sessions use the proxy by default.

`cliproxyapi-burn` shows weekly inefficiency, total waste, counts, output TPS and active burn-equivalent TPS. Add `--json` for full windows/history/projections. State stays private at `~/.local/state/cliproxyapi/burn.json`; it is not tracked by chezmoi. Both metrics start N/A until a weekly period is completed. Only new sessions use normal reset pressure; existing session/model bindings remain sticky unless a burn deadline or availability/cap forces a turn-boundary change.

Authenticate distinct Plus subscriptions with device codes:

```sh
cliproxyapi-auth 1  # SHARED: 50% weekly and 50% five-hour caps; excluded from BOTH metrics
cliproxyapi-auth 2  # personal Plus
cliproxyapi-auth 3  # personal Plus
```

Log in to the correct DIFFERENT account for each code, using separate browser profiles/private windows. The helper authenticates into a private staging directory, validates a Plus plan, adds WebSocket/cap policy before publishing the credential, and disables duplicate copies so shared caps cannot be bypassed. It rejects using the same subscription for different slots. Once all three slots exist, old Codex credentials outside this rotation are disabled and excluded from the tallies; they are not deleted.

Shared caps use total provider-reported utilization. New requests stop when either reaches 50%; unknown/stale quota or a failed selected-account preflight check fails closed. Already accepted requests and another user's activity can overshoot a threshold; this cannot reserve an exact provider-side token budget. Quota polling continues while you are idle to observe actual weekly resets. Missing/stale data is reported as estimated, not reconstructed as precise history.

The local Pi-compatible opaque key is prepared by `cliproxyapi-prepare-pi`; it contains the account claim Pi requires, but only the proxy authenticates it. Real subscription tokens/account IDs replace it upstream. The previous private key remains in an untracked local backup. Use `cliproxyapi-update` to rebuild the committed dev branch and restart the service.
