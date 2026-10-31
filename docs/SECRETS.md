# Secrets: ordinary Ansible Vault and Forgejo Actions

There is no custom encrypted-file registry, automatic credential import or local
Vault store. Credentials already restored to their application's runtime paths
remain runtime state. Nothing reads the active home to manufacture Git contents.

## Optional encrypted host variables

`secrets/araveia.yml` and `secrets/syssec-canis.yml` start as public empty examples.
Before adding a real password or token, encrypt the selected file, then edit it:

```sh
ansible-vault encrypt secrets/araveia.yml
ansible-vault edit secrets/araveia.yml
# Commit the ciphertext, never the password.
git add secrets/araveia.yml
```

Host files are loaded with native `vars_files`. Run with `--ask-vault-pass`, or
set the standard `ANSIBLE_VAULT_PASSWORD_FILE` to an existing protected controller
file. The local wrapper prompts when encrypted files exist. Wrong/missing keys
fail standard Vault decryption; there is no key generator or silent enrollment.

Encrypting a host file is optional if all application credentials have already
been restored. Ansible still requires the relevant existing runtime credentials
before starting their service. Provider/OAuth refresh, SSH identity, GPG keys,
runner enrollment and missing personal data cannot be generated from Git.

## Optional encrypted files

If a particular credential should be deployed by Ansible, make a Vault-encrypted
file under `secrets/` and declare it in that host's variables:

```yaml
vault_files:
  - src: cliproxyapi.vault
    dest: .local/share/cliproxyapi/secrets.json
    services: [cliproxyapi]
```

Create it using `ansible-vault create secrets/cliproxyapi.vault`, enter the secret
in the editor, and commit only its Vault ciphertext. Native `copy` decrypts it on
deployment and writes it with mode 0600, with logging/diffs suppressed. Parent
paths and an existing destination must never be symlinks. This overwrites only
an explicitly declared regular file; it never imports or recursively adopts
private trees. List affected service role names in optional `services` (for
example `mail`, `cliproxyapi`, or `forgejo`); only those roles are restarted when
the file changes. Without that list, delivery alone does not restart a service.
A malformed application credential is still an application error: Vault protects
transport/storage but does not validate a provider's tokens or refresh them.

`vault_files` can also hold ordinary source filenames **only when their contents
are Ansible Vault ciphertext**. Do not commit `.env`, private SSH keys, plaintext
auth JSON, generated stores, logs or database backups anywhere in this repository.
`.gitignore` is defense in depth, not encryption or an authoritative allowlist.

## Forgejo Actions repository secrets

Use the same repository's Settings → Actions → Secrets. The deployment workflow
expects `ANSIBLE_VAULT_PASSWORD`, `ANSIBLE_SSH_PRIVATE_KEY`,
`ANSIBLE_KNOWN_HOSTS`, `ANSIBLE_SSH_USER`, and `ANSIBLE_BECOME_PASSWORD`.
See [Deployment](DEPLOYMENT.md) for what they contain and runner prerequisites.

The job puts the Vault password and SSH key into temporary owner-only files;
Ansible reads the sudo password from the job environment through a plain variable
expression. No password is put in Git, printed or supplied as a process argument.
The job cleans up temporary files and its container is disposable. Secrets are
only attached to the main-branch deployment step, not normal PR checks.

The owner explicitly accepts that workflow authors in this repository are trusted
with repository secrets. Updates to the owner-controlled main branch are the
operational deploy trigger, not an additional secret-isolation guarantee. This
source does not configure or assert that branch protection is already enabled.

**Keep an offline copy of the Vault password.** Forgejo lives on araveia; its
recovery cannot depend on retrieving the only password from that same Forgejo.
Forgejo repository secrets are not automatically available to a local command;
local interactive deployment and CI are separate credential delivery paths.

## Rotation and rollback

Use `ansible-vault edit` or `ansible-vault rekey`, commit the encrypted change,
update the corresponding Forgejo secret when changing the Vault password, and
redeploy. Configuration handlers activate affected services after successful
configuration/build changes. Provider-side revocation is separate.

A Git revert and redeploy restores tracked configuration, not runtime secret
history, removed files, a database, installed packages or whole-machine state.
Use the existing backups for those recovery operations. This repository no longer
captures encrypted preimages or supplies a custom rollback command.
