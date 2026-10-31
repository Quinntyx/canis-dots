# Reinstall and recovery boundary

1. Install EndeavourOS and Ansible Core yourself.
2. Use the existing trusted backup/restore procedure to restore the preserved
   docs disk, personal data and credentials, system/network identities and remote
   access. Keep an offline Vault password copy. Do not format the docs disk.
3. Obtain this checkout from Git; run `./scripts/deploy` on the restored machine.
4. After the existing Forgejo/runner and SSH access work again, normal merged
   configuration changes can deploy through Forgejo Actions.

The historical restore/backup references under `docs/backups/private_araveia/`
are preserved documentation, not a newly executable Ansible recovery subsystem.
The archived restore script already points its chezmoi step at the GitHub mirror
of this repository. **Before using that restore after the migration, remove that
legacy chezmoi step from your separate restore procedure**, then run Ansible as
step 3 above. Do not edit or execute the archived reference as a deployment tool.
This source includes a defensive `.chezmoiignore` containing `*`: even if the old
step still reaches this repository, chezmoi manages/applies no files, rather than
copying the Ansible source tree into your home. That guard is not configuration
deployment, and does not repair the rest of an outdated restore procedure.

Retain a verified copy of your existing restore scripts/source for the reinstall.
This repository does not rewrite or run that separate procedure, nor claim its
backups are complete or current. No active restore script was changed here.

Normal deployment checks araveia's declared docs filesystem UUID, installed
Forgejo data/configuration and enrolled Tailscale address. It fails instead of
initializing a blank forge or guessing a new identity. The existing firewall
zone, tunnel enrollment, provider tokens, user data and runner registration must
already be restored. Missing or expired credentials still require their owner's
normal recovery/sign-in procedure; Ansible cannot invent them.

Removed by the simplification: `--fresh`, the recovery module/policy, root disk
bootstrap, secret enrollment, automatic preimage archives and custom rollback.
Their last complete state is available at checkpoint commit **f81385a**, not
mixed into normal desired-state deployment.

A configuration Git revert is not backup recovery. Packages, databases, personal
files, network identities, root snapshots and provider accounts have independent
recovery procedures. Never test them by applying this source to the active host
without explicit deployment authorization.
