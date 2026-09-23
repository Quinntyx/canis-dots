#!/usr/bin/env bash
# forgejo-tailscale-setup.sh — point git at forgejo over Tailscale.
#
# On machines behind a firewall that can't reach git.quinntyx.dev, this rewrites
# all forgejo git URLs to http://araveia:3000 (MagicDNS over the tailnet) and
# stores matching credentials. Safe to re-run (idempotent).
#
# What it does:
#   1. git config --global: https://git.quinntyx.dev/... -> http://araveia:3000/...
#      (also rewrites ssh://git@git.quinntyx.dev/ and scp-style git@git.quinntyx.dev:)
#   2. scopes the `store` credential helper to http://araveia:3000
#   3. copies the existing git.quinntyx.dev credential from ~/.git-credentials
#      to a http://...@araveia:3000 entry (prompts for a token if none exists)
#   4. verifies with a git ls-remote
#
# Revert with:
#   git config --global --unset-all 'url.http://araveia:3000/.insteadOf'
#   git config --global --unset-all 'credential.http://araveia:3000.helper'
#   # and delete the http://...@araveia:3000 line from ~/.git-credentials

set -euo pipefail

PUBLIC_HOST="git.quinntyx.dev"
TS_HOST="araveia"
TS_PORT="3000"
TS_URL="http://${TS_HOST}:${TS_PORT}/"
USER_NAME="${FORGEJO_USER:-quinntyx}"
CREDS_FILE="${HOME}/.git-credentials"

# 0. sanity: forgejo must be reachable over the tailnet
if ! curl -fsS -o /dev/null --max-time 5 "${TS_URL}"; then
    echo "error: cannot reach ${TS_URL} — is Tailscale up on this machine?" >&2
    exit 1
fi

# 1. URL rewrites (transport-level; remotes in .git/config stay unchanged)
urlkey="url.${TS_URL}.insteadOf"
git config --global --unset-all "${urlkey}" 2>/dev/null || true
git config --global --add "${urlkey}" "https://${PUBLIC_HOST}/"
git config --global --add "${urlkey}" "ssh://git@${PUBLIC_HOST}/"
git config --global --add "${urlkey}" "git@${PUBLIC_HOST}:"

# 2. credential helper scoped to the tailscale URL
git config --global --replace-all "credential.http://${TS_HOST}:${TS_PORT}.helper" "store"

# 3. credentials: clone the existing forgejo token, prompt if there is none
if [[ -f "${CREDS_FILE}" ]] && rg -F -q "@${TS_HOST}:${TS_PORT}" "${CREDS_FILE}"; then
    echo "credentials for ${TS_HOST}:${TS_PORT} already present in ${CREDS_FILE}"
else
    token="$(sed -n "s#^https://${USER_NAME}:\([^@]*\)@${PUBLIC_HOST}#\1#p" "${CREDS_FILE}" 2>/dev/null | tail -n1 || true)"
    if [[ -z "${token}" ]]; then
        read -rsp "no stored ${PUBLIC_HOST} credential found; enter forgejo token for ${USER_NAME}: " token
        echo
    fi
    umask 077
    printf '%s\n' "http://${USER_NAME}:${token}@${TS_HOST}:${TS_PORT}" >> "${CREDS_FILE}"
    chmod 600 "${CREDS_FILE}"
    unset token
    echo "added http://${USER_NAME}:***@${TS_HOST}:${TS_PORT} to ${CREDS_FILE}"
fi

# 4. verify against a known repo (best effort)
if git ls-remote "${TS_URL}quinntyx/test.git" >/dev/null 2>&1; then
    echo "ok: git over ${TS_URL} works"
else
    echo "warning: ls-remote test failed (repo may be private or renamed) — try: git ls-remote ${TS_URL}quinntyx/test.git" >&2
fi
