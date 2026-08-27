# gcal-sync credentials

Holds Google Calendar OAuth material for the gcal-sync skill's bundled
`bin/gcal-sync` script. This directory is tracked so its structure survives
on new machines, but every file inside it is machine-local secret or runtime
state, excluded via `.chezmoiignore`:
but every file inside it is machine-local secret or runtime state, excluded
via `.chezmoiignore`:

- `client_secret.json` — OAuth desktop client (Google Cloud Console download).
  Restore manually per machine.
- `token.json` — cached access/refresh token created by `gcal-sync --auth`.

On a new machine, run:

    ~/.config/pi/profiles/omn-assistant/skills/gcal-sync/bin/gcal-sync --auth
