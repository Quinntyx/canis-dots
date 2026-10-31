# gcal-sync credentials

Holds Google Calendar OAuth material for the gcal-sync skill's bundled
`bin/gcal-sync` script. This README documents the directory structure for new
machines. Credential and token files stay outside normal Ansible manifests;
tracking this README does not adopt its neighboring runtime/auth files.

- `client_secret.json` — OAuth desktop client (Google Cloud Console download).
  Restore manually per machine. Separately approved provisioning must use Vault
  `encrypted_files/<host>/...` under `policy/secrets.yml` through edit-config,
  never a plaintext tracked copy.
- `token.json` — cached access/refresh token created by `gcal-sync --auth`.

On a new machine, run:

    ~/.config/pi/profiles/omn-assistant/skills/gcal-sync/bin/gcal-sync --auth
