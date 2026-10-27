---
name: github-mirror
description: "Use when creating or repairing server-side GitHub mirrors of personal Forgejo
  repositories, migrating GitHub-only repos, or consolidating local mirror remotes."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Named personal repositories, requested creation/migration/repair scope, and visibility.
- Git, authenticated `fj` on `git.quinntyx.dev` as `quinntyx`, and `gh` as `Quinntyx`.
- Forgejo API credentials in `~/.local/share/forgejo-cli/keys.json` at
  `hosts["git.quinntyx.dev"].token`, read into memory and sent through the authorization header.
- Server-credential repairs additionally require explicit repair scope and access to the `forgejo`
  container in `~/docs/host/forgejo`, whose persistent server data is mounted at `/data`.

## Output Contract

- Forgejo is canonical and mirrors to `ssh://github.com/Quinntyx/<repo>.git` server-side, using
  interval `8h0m0s` and `sync_on_commit: true`.
- Verified completed synchronization with empty `last_error` and matching branch/tag heads.
- Personal local clones use one canonical Forgejo `origin`; genuine foreign-fork upstreams retain
  their role. Report transport rewrites separately from canonical hosting.
- A per-repository outcome identifying retained partial state and any required repair approval.

# Entrypoint

## Stage 1: Inventory and authorize

1. Resolve owner, repository, visibility, local checkout, and requested operations. This procedure
   applies to named personal repositories actually in use. Foreign upstream contribution hosting
   remains on its actual host; an upstream URL is distinct from a personal GitHub mirror.
2. Verify tools, identities, and API access. Use `https://git.quinntyx.dev/api/v1` and in-memory
   `Authorization: token ...` headers. Redact credentials from commands, files, and reports.
3. Read both repositories, all pages of existing push mirrors, and branch/tag refs from both
   hosts. Use `GET /repos/quinntyx/{repo}`, `GET /repos/quinntyx/{repo}/push_mirrors`,
   `gh repo view "Quinntyx/$repo"`, and `git ls-remote --heads --tags` for each host.
4. A definite absence selects Stage 2: Establish both repositories. Both existing selects
   Stage 3: Reconcile refs. Authentication, network, or authorization failures end with an access
   report, preserving current state; resume Stage 1 after resolution.

## Stage 2: Establish both repositories

1. For an explicitly requested GitHub-only migration, run
   `fj repo migrate "https://github.com/Quinntyx/$repo" "quinntyx/$repo" -s github`
   with `-H https://git.quinntyx.dev`. Verify the imported Git refs and visibility. This migrates
   Git data; issue, PR, release, and settings migration requires its own scope.
2. For a forge-only repository, create the empty GitHub destination using
   `gh repo create "Quinntyx/$repo"` with `--private` or `--public` matching Forgejo.
3. For two absent repositories or migration outside the authorized scope, end with the required
   creation decision. A successful creation or migration proceeds to Stage 3: Reconcile refs.
   A failed write ends with its retained partial state. Honor rate-limit retry guidance before
   retrying the same operation, using bounded backoff rather than bypassing host limits.

## Stage 3: Reconcile refs

1. Compare every branch and tag, not just the default branch. Forgejo push mirroring can force
   updates and prune the destination, so establish preservation before the first sync.
2. Matching refs or Forgejo heads proven to contain GitHub history proceed to Stage 4: Configure
   the mirror. Missing GitHub-side refs may be imported to Forgejo only within authorized
   reconciliation scope: fetch to isolated temporary refs, verify objects and ancestry, then push
   explicit refspecs to the forge URL. Re-run Stage 3 after import.
3. Divergent branch histories, conflicting tags, ambiguous refs, or insufficient scope end with
   the exact reconciliation decision. Retain both histories and destination refs pending that
   decision. A same-SHA check alone is insufficient when branch histories differ.

## Stage 4: Configure the mirror

1. Re-read push mirrors. Reuse an exact matching destination and options; authorized repairs may
   update options through the installed API. A conflicting or duplicate destination ends with a
   consolidation decision. An absent destination continues at step 2; a matching one uses step 3.
2. Use `POST /repos/quinntyx/{repo}/push_mirrors` with `remote_address` equal to
   `ssh://github.com/Quinntyx/{repo}.git`, `interval: 8h0m0s`, and `sync_on_commit: true`.
   Retain the server's established GitHub account key. A successful write continues at step 3;
   a failure ends with the API error and retained state.
3. Queue `POST /repos/quinntyx/{repo}/push_mirrors-sync`, then poll mirror status with bounded
   waits. A completed sync with empty `last_error` proceeds to Stage 6: Verify local state.
   A completed error proceeds to Stage 5: Resolve the sync failure. A pending timeout ends with
   synchronization accurately reported as pending; queue acceptance is not completion.

## Stage 5: Resolve the sync failure

1. A missing-ref or refused-default-branch-deletion error returns to Stage 3: Reconcile refs.
   Credential or host-key errors continue at step 2. Other errors end with the server's message.
2. Confirm server repair scope and container access. Authorized access continues at step 3;
   otherwise end with the required repair decision and preserve running services.
3. For host-key verification, compare GitHub's published SSH fingerprints through an authenticated
   primary source before updating `/data/git/.ssh/known_hosts` as the container's Git user.
   Retain correct ownership and restrictive permissions; unverified scan output is discovery only.
4. For public-key or deploy-key authorization errors, inspect the effective SSH identity and its
   GitHub scope. Use an established account-level key for shared personal mirrors. Inspect
   `/data/git/.ssh/config` for conflicting identity selection and reconcile only the proven cause.
   Adding or generating an account key requires that security-sensitive change to be authorized.
5. Record the exact repair and re-run Stage 4: Configure the mirror. Preserve unrelated server
   credentials, mirror identities, active services, and global client configuration.

## Stage 6: Verify local state

1. Compare all branch/tag refs after synchronization and verify mirror address, interval,
   sync-on-commit, completion timestamp, and empty error. A mismatch returns to Stage 3:
   Reconcile refs; verified parity continues at step 2.
2. Inspect local remotes, branch upstreams, and `git config --show-origin --get-regexp` for active
   URL rewrites. On ordinary machines, canonical `origin` is
   `https://git.quinntyx.dev/quinntyx/{repo}.git`. A restricted machine may intentionally resolve
   this through GitHub transport; retain its rewrite and distinguish stored from effective URLs.
3. Within authorized local-remote consolidation, inventory every affected branch's upstream and
   prove the forge has its commits. Set the canonical origin and matching tracking refs, then
   remove obsolete personal `github` or mirror-only `upstream` remotes. Shared worktrees use the
   primary clone's common remote configuration. Retain genuine foreign upstreams.
4. Durable Pi package-source configuration remains canonical to Forgejo. Any requested source
   setting change is authored in chezmoi source state and follows its separately assigned
   commit/push/apply lifecycle. Package caches remain runtime state.
5. Report mirror destination, completion time, last error, ref parity, local remotes/tracking, and
   any pending operation. A missing mirror/HEAD on a restricted machine is repaired at the mirror
   source, preserving canonical package source declarations and existing global rewrites.

# Execution conventions

- Bind all command variables and route segments to validated identifiers. Use explicit workdirs.
- Preserve histories and partial state on failure. Approved filesystem cleanup uses `trash`.
- Use dedicated detached tmux jobs for operations expected to exceed 10–15 seconds, retaining
  native progress and exit status with bounded monitoring and active user panes preserved.
