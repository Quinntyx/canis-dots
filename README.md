# dots — ordinary Ansible workstation configuration

Ansible Core inventory, roles, templates and handlers for **araveia** (main
workstation/controller) and **syssec-canis** (lab). No custom Ansible plugins,
manifest engine, recovery command or automatic secret enrollment.

## Deploy locally

Use your existing backup/restore procedure first after reinstalling EndeavourOS.
It restores the docs disk, personal data, credentials and network identity;
Ansible is configuration management, not a replacement for that procedure.
Install Ansible Core yourself, then from this checkout:

```sh
./scripts/deploy
# Preview; commands marked read-only may still query the machine:
./scripts/deploy --check --diff
```

The wrapper selects the **current enrolled hostname** and prompts for sudo and,
when encrypted files are present, the Vault password. It does not enroll another
host. From araveia, with ordinary SSH access to the restored targets:

```sh
./scripts/deploy --host syssec-canis
./scripts/deploy --all
```

Or use Ansible directly:

```sh
ansible-playbook playbooks/site.yml --limit araveia -c local --ask-become-pass
```

Add `--ask-vault-pass` if using encrypted host variables. No credentials or live
installation are required just to read/edit this source repository.

## Merge-to-deploy

`.forgejo/workflows/ansible.yml` checks PRs in disposable homes. A successful
check of a push to **main** then deploys over SSH to this explicit inventory,
one host at a time. Feature branches do not run the deployment job. You own merge
access; the accepted trust model allows repository workflows access to repository
secrets. No second deployment repository or webhook listener.

Configure the existing runner and repository secrets once as described in
[Deployment](docs/DEPLOYMENT.md) and [Secrets](docs/SECRETS.md). The workflow is
source only until merged and configured; developing this PR does **not** deploy.

## Source and boundaries

- `inventory/`: explicit hosts, account-independent defaults, host-specific values.
- `roles/<name>/files/{common,araveia,lab}/<mode>/`: readable destination-shaped
  file trees. `tasks/config.yml` copies each declared tree, renders named
  templates and creates named links. Nothing prunes unknown target files.
- `roles/<name>/tasks/`, `handlers/`: lifecycle using built-in Ansible modules.
- `secrets/<host>.yml`: optional ordinary host variables, encrypted with Vault
  before adding secrets; initially empty public examples.
- [Software](docs/SOFTWARE.md), [recovery boundary](docs/RECOVERY.md),
  [migration record](docs/migration/README.md), [operating rules](AGENTS.md).

Configuration rollback is a Git revert and redeploy. Database, package, service
identity and personal-data recovery remain separate backup/restore work.

## Verification

Development checks also require Node.js and tmux. The virtualenv installs
`trash-cli` for recoverable test-fixture cleanup, including inside CI; it does
not require a host-level trash utility. These are verification dependencies,
not extra prerequisites for `./scripts/deploy`.

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
PATH="$PWD/.venv/bin:$PATH" ./scripts/check all
```

Checks use temporary homes and recording package/service substitutes. They do
not prove real installs, remote SSH, provider authentication, live service or
visual behavior. Never run deployment against a real host to make a source test
pass.
