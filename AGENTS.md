# Repository operating rules

This is an Ansible **source** repository, not the active home. Read this file
completely before editing. Read README.md and docs/DEPLOYMENT.md for role,
inventory and ownership changes; docs/SECRETS.md before touching Vault,
preimages or rollback; docs/SOFTWARE.md before package/build changes; and
 docs/migration/README.md before changing baseline dispositions.

## Boundaries that matter

- Source-only work never runs `scripts/deploy`, a real-host playbook, an installer,
  Pi update, live services, or website publication. Publication and deployment
  require their own assigned scope; a PR is not permission to apply it.
- Never edit the currently active home, `/etc`, package/plugin outputs or private
  runtime trees to make a source test pass. Use explicit disposable homes with
  `dots_sandbox=true`, and leave installs/external acquisition/services disabled.
- Inventory membership is explicit. A T3 connection, tailnet peer, or requested
  component is not enrollment or permission to widen a host's eligibility.
- Manifests own file destinations/modes; role tasks own lifecycle; package/Git/Pi
  managers own their outputs. Unknown paths stay unmanaged. Do not recursively
  adopt, chown, prune, reset personal repositories, or import a live home.
- Credentials go through policy/secrets.yml and Vault. No plaintext credentials,
  keys, backup archives, logs containing private payloads, or generated stores in
  Git. Keep `no_log`/diff suppression and fail before mutation on wrong keys.
- Upstream mirrored skills retain upstream ownership. Do not copy local policy
  into them to satisfy a broad textual scan; adjust the owner/acquisition instead.

## Change checklist

For destination/template changes, update the component manifest and migration
ledger when relevant; preserve exact modes, home portability, host filtering and
literal embedded template languages. For new lifecycle behavior, inspect the
corresponding task pattern, dependency closure and service activation inputs.
Secret changes and successful binary builds must activate the affected service;
failed builds must remain retryable. Documentation must distinguish configuration
rollback from package/data/system recovery.

Add a focused regression first for logic/security failures. Use real Ansible in
disposable homes for target-file, Vault, selection, convergence or rollback
changes, not only textual assertions. Never lower a safety check because a live
side effect was deliberately not authorized. Say loudly if a rule conflicts with
the assignment rather than silently bypassing it.

## Available verification ladder

Install **project-local** development dependencies, not a host toolchain:
`uv venv .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt`.
Then `PATH="$PWD/.venv/bin:$PATH" ./scripts/check static` is the mandatory floor
(syntax/ownership/guidance checks; not falsely described as file-scoped).

Escalate only the affected surfaces:

- Ansible/plugins/wrappers/secrets/host selection: `scripts/check deployment`.
- Curated software/build privilege changes: `scripts/check software`.
- Tmux persistence helper/protocol changes: `scripts/check tmux`.
- Cross-cutting migration changes: `scripts/check all`.

Keep the virtualenv PATH prefix for these commands. `scripts/check-packages` is
an optional **read-only** official-package availability query against the current
Arch sync databases; it does not install or refresh. There is no claim of a
repo-wide live deployment/visual capture suite or hosted CI here. Handoff must
name checks actually run and explicitly mark real installs, sudo/SSH, services,
provider sign-ins and visual behavior unexercised when they were not authorized.
Run `git diff --check` before handoff and inspect the changed-path list for
unassigned files/secrets. Do not merge unless separately authorized.
