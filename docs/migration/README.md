# Migration record

## Current decision

The owner selected **normal Ansible + Ansible Vault + same-repository Forgejo
Actions**, with their merge to main as the operational deployment approval. The
existing restore procedure runs first after a reinstall; recovery is not part of
Ansible desired state. Repository workflow authors are trusted with repository
secrets under the explicitly accepted small-instance trust model.

Checkpoint **f81385a** (`chore: checkpoint Ansible implementation before
simplification`) preserves the previous complete implementation and its forensic
ledger, custom plugins, encrypted preimages and fresh-recovery path. It was made
before this rebuild so that design can be inspected without reintroducing it.

## Dispositions

- Desired configuration remains source-owned role files/templates, explicit YAML
  tasks and native handlers. Static source bytes/destination/mode/host-scope are
  preserved by the conversion; the small role-level digest regression fixture is
  test evidence, not a runtime manifest.
- Explicit inventory membership remains araveia and syssec-canis only. Main-only
  components do not deploy to the lab, whose personal SSH config remains intact.
- Package/Git/Pi managers own their acquired outputs. Upstream skill bytes stay
  upstream-owned. Personal repositories are never reset or recursively adopted.
- Credentials are existing restored runtime files or deliberately committed
  standard Vault ciphertext. No active-home import, generated key, custom secret
  registry or automatic enrollment. CI secrets live in Forgejo repository settings.
- Personal data, databases, identities and private backups remain outside Git and
  outside normal deployment. Unknown paths remain unmanaged; no remove-list sweep
  or recursive prune replaces the former manager.
- Website source remains a separate repository; this machine role does not publish
  it. OS updates and full data/system recovery remain separate operations.
- Removed: per-component JSON manifests, migration classifier/filter, custom
  action/modules, controller marker/source resolver, local `.vault` protocol,
  import/rollback wrappers, root-bridge/request machinery and `--fresh`.

## Evidence and limits

The changed checks test native Ansible in disposable homes, file/symlink safety,
convergence, host isolation, standard Vault delivery, workflow gating, AUR/tool
control flow and unchanged configuration content. No live deployment or active
configuration edit is authorized by rebuilding source. Checks do not prove OS
installation, remote sudo/SSH, current backup completeness, provider credentials,
live services or visual behavior. See AGENTS.md for the mandatory verification
ladder and docs/DEPLOYMENT.md for operational prerequisites.
