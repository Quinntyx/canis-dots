#!/usr/bin/env bash
# Snapshot what a fresh araveia cannot rebuild from chezmoi and the package
# lists: keys, tokens, service identities, system config and app data.
#
#   sudo ~/docs/backups/araveia/backup.sh
#
# Re-run right before wiping the NVMe. OAuth refresh tokens (CLIProxyAPI,
# Pi, oama, gcal-sync) rotate, so an old snapshot can restore dead tokens.
# Close Zen, Element, PrismLauncher and REAPER first so their databases are
# consistent. Without sudo, only the home half is refreshed.
#
# Layout (mirrors the filesystem so restore.sh can copy it straight back):
#   home/       paths relative to $HOME
#   root/       absolute system paths (root-owned, restored as-is)
#   reference/  copies kept for reading only; restore.sh regenerates these
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
user=${SUDO_USER:-$(id -un)}
home=$(getent passwd "$user" | cut -d: -f6)

umask 077
mkdir -p "$here/home" "$here/root" "$here/reference"
chmod 700 "$here" "$here/home" "$here/root" "$here/reference"

missing=()

# Secrets, service identities, and app data worth keeping. Each entry is
# relative to $HOME; directories are mirrored with deletes so a re-run matches
# the live machine.
home_paths=(
	# keys and tokens
	.ssh
	.gnupg                          # also decrypts oama's mail tokens
	.git-credentials
	.config/gh/hosts.yml
	.local/share/forgejo-cli/keys.json
	.config/fish/conf.d/canvas-private.fish
	.config/mail-router              # Jev API key for mail-route-jev.py
	.config/keepassxc/keepassxc.ini  # holds the KeeShare private key
	.config/.wrangler
	.local/state/oama
	.local/share/cliproxyapi         # pooled subscription OAuth logins
	# service state
	.local/state/syncthing           # device ID; peers stay paired
	.local/state/mail-router         # gmail backlog flag, reconcile stamp
	# Pi and Claude Code, including sessions, auth and package checkouts
	.config/pi
	.pi
	.local/share/pi-buddy
	.claude
	.claude.json
	# apps
	.config/zen
	.config/Element                  # Matrix encryption keys
	.local/share/PrismLauncher/instances
	.local/share/PrismLauncher/accounts.json
	.local/share/PrismLauncher/prismlauncher.cfg
	.local/share/PrismLauncher/icons
	.local/share/PrismLauncher/themes
	.forge                           # MTG Forge decks, quests, adventure saves
	.config/r2modman
	.config/r2modmanPlus-local
	.config/REAPER
	.config/DecentSampler
	.local/bin/DecentSampler
	.local/share/applications
	.config/mimeapps.list
	.config/fish/fish_variables
	.local/share/webnovel-reader
	.config/webnovel-ai-reader
	.local/share/daily-assistant
	.local/state/cliproxyapi         # runtime config and auth snapshots
	# agent history: T3 Code, OpenCode, Codex
	.t3/userdata
	.config/t3code-v2
	.config/opencode                 # includes antigravity-accounts.json
	.local/share/opencode
	.local/state/opencode
	.codex
	# files: downloads (unsorted), ~/src checkouts with uncommitted edits and
	# the NeoForge server worlds, CAD work, Element (audio host) sessions
	downs
	src
	cad
	Music/Element
	.vst3
	# game saves without Steam Cloud
	.factorio/saves
	.factorio/config
	.factorio/mods
	.factorio/player-data.json
	.config/unity3d
	.local/share/SlayTheSpire2
	.local/share/Archipelago
	.local/share/Baba_Is_You
	.local/share/FasterThanLight
	".local/share/Space Station 14"
	.local/share/FBF                 # 100% Orange Juice
	# Lutris library and Wine runners, and the Battle.net prefix they launch
	.local/share/lutris
	Games/battlenet
	# apps installed outside pacman, and browser profiles
	Applications/gantry
	.local/share/gantry
	Videos
	.config/chromium
	.local/share/Steam/userdata
)

# Saves inside Proton prefixes and game install directories. restore.sh puts
# them back before Steam reinstalls the games, which then fills in around them.
steam=.local/share/Steam/steamapps
for d in "$home/$steam"/compatdata/*/pfx/drive_c/users/steamuser "$home/$steam"/common/Subnautica*/SNAppData; do
	[[ -d "$d" ]] && home_paths+=("${d#"$home/"}")
done

# Databases apps keep open (T3 Code is likely running during the backup).
# rsync could catch them mid-write, so they are re-copied with sqlite's
# online backup after the mirror.
live_dbs=(.t3/userdata/statev2.sqlite .local/share/opencode/opencode.db)
for f in "$home"/.codex/*_[0-9].sqlite; do
	[[ "$f" == */logs_* ]] || live_dbs+=("${f#"$home/"}")
done

home_excludes=(
	--exclude='S.*'                  # gpg-agent sockets
	--exclude='__pycache__/'
	--exclude='.local/state/syncthing/index-v2/'
	--exclude='.local/state/syncthing/syncthing.lock'
	--exclude='.config/pi/profiles/*/tmux-client-*.log'
	--exclude='.claude/cache/'
	--exclude='.claude/shell-snapshots/'
	--exclude='.claude/session-env/'
	--exclude='.claude/downloads/'
	--exclude='.local/share/applications/mimeinfo.cache'
	--exclude='.local/share/applications/wine/'
	--exclude='.config/zen/**/cache2/'
	--exclude='.t3/userdata/logs/'
	--exclude='.config/t3code-v2/*Cache/'
	--exclude='.config/t3code-v2/Crashpad/'
	--exclude='.config/t3code-v2/Singleton*'
	--exclude='.local/share/opencode/bin/'
	--exclude='.local/share/opencode/log/'
	--exclude='.codex/cache/'
	--exclude='.codex/tmp/'
	--exclude='.codex/.tmp/'
	--exclude='.codex/shell_snapshots/'
	--exclude='.config/opencode/node_modules/'
	--exclude='.local/state/cliproxyapi/cli-proxy-api*'
	--exclude='.local/state/cliproxyapi/session-quota-build/'
	--exclude='.local/share/lutris/runtime/'
	--exclude='Games/battlenet/GLCache/'
	--exclude='.config/chromium/**/*Cache/'
	--exclude='.config/chromium/Singleton*'
	--exclude='.codex/logs_*.sqlite*'
)

for app in zen-bin element-desktop prismlauncher reaper; do
	if pgrep -x "$app" >/dev/null; then
		echo "warning: $app is running; its data may be copied mid-write" >&2
	fi
done

echo "==> home ($home)"
for rel in "${home_paths[@]}"; do
	if [[ -e "$home/$rel" ]]; then
		rsync -aR --delete --delete-excluded "${home_excludes[@]}" "$home/./$rel" "$here/home/"
	else
		missing+=("~/$rel")
	fi
done

as_owner() { if [[ $EUID -eq 0 ]]; then sudo -u "$user" "$@"; else "$@"; fi; }
for rel in "${live_dbs[@]}"; do
	[[ -s "$home/$rel" ]] || continue
	# As the owner, so sqlite never leaves root-owned -wal/-shm files beside
	# the live database.
	if as_owner sqlite3 "$home/$rel" ".backup '$here/home/$rel.tmp'"; then
		mv "$here/home/$rel.tmp" "$here/home/$rel"
		rm -f "$here/home/$rel-wal" "$here/home/$rel-shm"
	else
		rm -f "$here/home/$rel.tmp"
		echo "warning: sqlite backup of ~/$rel failed; the rsync copy may be inconsistent" >&2
	fi
done


# The docs disk's fstab line, so restore.sh can mount it permanently.
awk -v m="$home/docs" '$2 == m' /etc/fstab >"$here/reference/docs-fstab-line"

if [[ $EUID -eq 0 ]]; then
	echo "==> system"
	root_paths=(
		/etc/ssh/ssh_host_ecdsa_key /etc/ssh/ssh_host_ecdsa_key.pub
		/etc/ssh/ssh_host_ed25519_key /etc/ssh/ssh_host_ed25519_key.pub
		/etc/ssh/ssh_host_rsa_key /etc/ssh/ssh_host_rsa_key.pub
		/var/lib/tailscale/tailscaled.state  # node key: keeps 100.110.255.43 and the name
		/etc/cloudflared/token
		/etc/systemd/system/cloudflared.service
		/etc/keyd/default.conf
		/etc/security/limits.d/audio.conf
		/etc/conf.d/wireless-regdom
		/etc/NetworkManager/conf.d/90-dns-systemd-resolved.conf
		/etc/cups/printers.conf
		/etc/cups/ppd
		/etc/nvidia/nvidia-application-profiles-rc.d  # niri VRAM fix for the NVIDIA driver
	)
	for p in "${root_paths[@]}"; do
		if [[ -e "$p" ]]; then
			rsync -aR --delete "$p" "$here/root/"
		else
			missing+=("$p")
		fi
	done

	echo "==> reference"
	for p in /etc/firewalld/zones /etc/fstab /etc/hosts /etc/environment \
		/etc/kernel/cmdline /etc/ssh/sshd_config /etc/pacman.conf \
		/etc/pacman.d/openai-chatgpt.conf; do
		[[ -e "$p" ]] && rsync -aR --delete "$p" "$here/reference/"
	done
	systemctl list-unit-files --state=enabled --no-legend >"$here/reference/system-enabled-units.txt"
else
	echo "note: not root, so SSH host keys, Tailscale state, the cloudflared token and /etc were skipped" >&2
fi

# Inventories for comparison after the restore.
pacman -Qqen >"$here/reference/pacman-explicit-native.txt"
pacman -Qqem >"$here/reference/pacman-explicit-foreign.txt"
if command -v tailscale >/dev/null; then
	tailscale ip -4 >"$here/reference/tailscale-ip" 2>/dev/null || true
fi
sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$(id -u "$user")" \
	systemctl --user list-unit-files --state=enabled --no-legend \
	>"$here/reference/user-enabled-units.txt" 2>/dev/null || true

date -Is >"$here/reference/snapshot-date"
# Keep the top-level files user-owned so a later run without sudo can rewrite them.
chown "$user:" "$here/reference"/*.txt "$here/reference/docs-fstab-line" \
	"$here/reference/tailscale-ip" "$here/reference/snapshot-date" 2>/dev/null || true

if ((${#missing[@]})); then
	printf 'not present (skipped): %s\n' "${missing[@]}" >&2
fi
du -sh "$here/home" "$here/root" "$here/reference" 2>/dev/null
echo "snapshot complete: $(cat "$here/reference/snapshot-date")"
