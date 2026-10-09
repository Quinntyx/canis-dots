# CLIProxyAPI dev setup

Canonical source: https://git.quinntyx.dev/quinntyx/CLIProxyAPI
Server-side GitHub mirror: https://github.com/Quinntyx/CLIProxyAPI
Development checkout: ~/docs/src/CLIProxyAPI/dev

## Tailnet-only access, no inference API key

CLIProxyAPI binds directly and exclusively to `100.110.255.43:8317`, araveia's
Tailscale IPv4 address. It does NOT listen on loopback, LAN, wildcard IPv4/IPv6,
or a public IP. There is no socket-proxy gateway or Funnel. If this address is
unavailable, startup fails rather than falling back to a broader listener.
The user service has `ConditionHost=araveia`; client machines must not run it.

All Pi profiles use `http://araveia.tail985727.ts.net:8317/backend-api`, including
on araveia itself. Other OpenAI-compatible clients use
`http://araveia.tail985727.ts.net:8317/v1`.

Inference and read-only `/v1/quota/remaining` need NO API key. Access is controlled
by Tailscale membership, grants/ACLs and the operating system's network controls.
Any permitted tailnet peer can spend the pooled subscriptions' quota. Tailscale
encrypts traffic between machines; this HTTP address does not expose a public
cleartext listener. Binding an IP is not per-user authorization or a replacement
for restrictive Tailscale grants/ACLs. ACL policy has not been broadened.

Pi's Codex client still expects a JWT-shaped value containing an account claim.
The shared `models.json` therefore contains a PUBLIC, unsigned format-only
placeholder. It is not a credential and provides no authorization. Real provider
credentials/account IDs replace it upstream. `cliproxyapi-key` prints the same
public placeholder for compatibility and never reads secrets. Client machines
need only synced configuration and permitted Tailscale access, not secrets.json
or any OAuth credentials.

Management endpoints and the management UI remain password-protected at
`http://araveia.tail985727.ts.net:8317/management.html`. Management is enabled over
the tailnet so server-local tooling can reach the direct Tailscale listener.
Its private management key is NOT synced to clients. Read it on araveia only:
`jq -r .management_key ~/.local/share/cliproxyapi/secrets.json`.

## Private server state (never version controlled)

- ~/.local/share/cliproxyapi/auths/: provider OAuth credentials, owner-only
- ~/.local/share/cliproxyapi/secrets.json: private management_key; legacy client_key is unused
- ~/.local/state/cliproxyapi/: generated configuration, quota history and build artifacts
- ~/.local/lib/cliproxyapi/: compiled development binary

On a fresh SERVER installation, create the auth directory with mode 700 and a
management key. Do not overwrite existing private state:

```sh
install -d -m 700 ~/.local/share/cliproxyapi/auths
(umask 077; set -o noclobber; jq -n --arg management_key "$(openssl rand -hex 32)" \
  '{management_key:$management_key}' > ~/.local/share/cliproxyapi/secrets.json)
```

Build with `cliproxyapi-update` after preparing the canonical dev worktree.
Chezmoi manages the secret-free config, service and helpers. Commit/push before
applying. The launcher assembles owner-only runtime YAML with empty inference
keys and the private management key. It no longer requires a client_key.

## Operations

```sh
systemctl --user enable --now cliproxyapi.service
systemctl --user status cliproxyapi.service
journalctl --user -u cliproxyapi.service -n 50
cliproxyapi-update                   # fetch dev, build, install, restart if running
systemctl --user restart cliproxyapi.service
```

To stop: `systemctl --user disable --now cliproxyapi.service`.
Pi uses the native Codex client with `websocket-cached`; model defaults live in
profile settings. After syncing or updating, use `/reload` and select a
CLIProxyAPI model if needed. The quota footer uses the read-only tailnet endpoint;
it never reads or sends the management key for this connection.

## Burn scheduling and the three subscription slots

`cliproxyapi-burn` (on araveia) shows weekly inefficiency, total waste, counts,
output TPS and active burn-equivalent TPS. Add `--json` for windows/history and
projections. Private history at `~/.local/state/cliproxyapi/burn.json` is not
tracked. Metrics start N/A until a weekly period completes. Only new sessions use
normal reset pressure; session/model bindings remain sticky unless a burn
deadline or availability/cap forces a turn-boundary change. See
`~/docs/src/CLIProxyAPI/dev/docs/reset-pressure-routing.md`.

Authenticate distinct Plus or Team subscriptions using device codes on araveia:

```sh
cliproxyapi-auth 1  # SHARED: 50% weekly and 50% five-hour caps; excluded from BOTH metrics
cliproxyapi-auth 2  # unrestricted Plus or Team
cliproxyapi-auth 3  # unrestricted Plus or Team
```

Log into DIFFERENT accounts using separate browser profiles/private windows.
The helper stages authentication privately, validates Plus/Team, adds WebSocket
and cap policy before publication, and disables duplicate copies. It rejects
one subscription in multiple slots. Once all three exist, old credentials outside
this rotation are disabled and excluded from tallies, not deleted.

Shared caps use total provider-reported utilization. New requests stop when
either cap reaches 50%; unknown/stale quota or failed selected-account preflight
fails closed. In-flight requests and other users can overshoot a threshold.
Quota polling observes actual weekly resets even while idle; stale/missing data
is estimated, not silently recorded as exact history. Team seats are identified
by workspace AND authenticated user, keeping their caps and tallies distinct.

Resume a completed staged device login without reauthenticating with
`cliproxyapi-auth SLOT --enroll-staged FILE`. FILE must belong to that slot under
`~/.local/state/cliproxyapi/device-SLOT.*/auths/`; all slot policies still apply.
Reports show remaining percentages, with cap-adjusted usable headroom separately.
Provider OAuth copies refresh independently; if another client rotates a refresh
token, reauthenticate that subscription here when needed.
