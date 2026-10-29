#!/usr/bin/env bash
# Rebuild araveia from ~/docs after a fresh EndeavourOS install.
#
#   1. Install EndeavourOS on the NVMe: hostname araveia, user zlare, NVIDIA
#      driver. The docs disk (sdb1) must not be formatted.
#   2. Mount the docs disk:  sudo mount UUID=40eda021-8152-4dab-8be2-f19307298da2 ~/docs
#   3. sudo ~/docs/backups/araveia/restore.sh
#   4. Reboot.
#
# Each step reports failure and the script carries on; the summary lists what
# needs attention. Every step is idempotent, so re-run after fixing anything.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
dotfiles=https://github.com/Quinntyx/canis-dots.git
tailnet_ip=100.110.255.43
cider_key=A0CD6B993438E22634450CDD2A236C3F42A61682

die() { echo "restore: $*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die "run with sudo"
user=${SUDO_USER:-}
[[ -n "$user" && "$user" != root ]] || die "run with sudo from your own account, not a root shell"
[[ "$user" == zlare ]] || die "dotfiles hardcode /home/zlare; expected user zlare, got $user"
home=$(getent passwd "$user" | cut -d: -f6)
uid=$(id -u "$user")
mountpoint -q "$home/docs" || die "mount the docs disk at $home/docs first"
[[ -d "$here/home" && -d "$here/root" ]] || die "no snapshot in $here; run backup.sh on the old install"

failed=()
step() {
	local name=$1
	shift
	printf '\n\033[1m==> %s\033[0m\n' "$name"
	if ! "$@"; then
		failed+=("$name")
		printf '\033[31m!! %s failed\033[0m\n' "$name" >&2
	fi
}
as_user() {
	sudo -u "$user" -H env \
		XDG_RUNTIME_DIR="/run/user/$uid" \
		DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
		PATH="$home/.local/bin:$home/.npm-global/bin:$home/.cargo/bin:/usr/local/bin:/usr/bin" \
		"$@"
}
user_ctl() { as_user systemctl --user "$@"; }
pkglist() { sed 's/#.*//; s/[[:space:]]//g; /^$/d' "$1"; }
append_once() { grep -qxF "$2" "$1" 2>/dev/null || printf '%s\n' "$2" >>"$1"; }

# --- system ---------------------------------------------------------------

hostname_and_mount() {
	[[ "$(hostnamectl hostname)" == araveia ]] || hostnamectl set-hostname araveia
	# Forgejo publishes on 127.0.1.1:3000, where the hostname resolves.
	append_once /etc/hosts "127.0.1.1  araveia"
	append_once /etc/hosts "10.176.150.107 syssec-rpi3-host"
	local line
	line=$(cat "$here/reference/docs-fstab-line")
	[[ -n "$line" ]] || return 1
	awk -v m="$home/docs" '$2 == m { found = 1 } END { exit !found }' /etc/fstab ||
		printf '%s\n' "$line" >>/etc/fstab
	systemctl daemon-reload
}

extra_repos() {
	# Cider (Apple Music), per repo.cider.sh.
	if ! grep -q '^\[cidercollective\]' /etc/pacman.conf; then
		curl -fsSL https://repo.cider.sh/ARCH-GPG-KEY | pacman-key --add - &&
			pacman-key --lsign-key "$cider_key" &&
			printf '\n[cidercollective]\nSigLevel = Required TrustedOnly\nServer = https://repo.cider.sh/arch/x64\n' >>/etc/pacman.conf ||
			return 1
	fi
}

pacman_packages() {
	pacman -Syu --noconfirm || return 1
	local -a want ok
	mapfile -t want < <(pkglist "$here/packages/pacman.txt"; echo cider)
	mapfile -t ok < <(comm -12 <(printf '%s\n' "${want[@]}" | sort -u) <(pacman -Slq | sort -u))
	local gone
	gone=$(comm -23 <(printf '%s\n' "${want[@]}" | sort -u) <(pacman -Slq | sort -u))
	[[ -z "$gone" ]] || echo "not in the repos any more (skipped): $gone" >&2
	# --ask 4 accepts replacing conflicting packages (jack2 -> pipewire-jack).
	pacman -S --needed --noconfirm --ask 4 "${ok[@]}"
}

chatgpt() {
	pacman -Q chatgpt-bin &>/dev/null && return 0
	# OpenAI's installer adds its signed repo and key, then installs the app.
	local tmp
	tmp=$(mktemp -d)
	curl --proto '=https' --tlsv1.2 -fsSL -o "$tmp/install-arch.sh" \
		https://persistent.oaistatic.com/codex-app-prod/linux/install-arch.sh &&
		bash "$tmp/install-arch.sh"
	local rc=$?
	rm -rf "$tmp"
	return $rc
}

# yay and makepkg run as the user and call sudo pacman; allow that without a
# password prompt for the rest of this run only.
sudoers_tmp=/etc/sudoers.d/90-araveia-restore
allow_pacman() {
	printf '%s ALL=(root) NOPASSWD: /usr/bin/pacman\n' "$user" >"$sudoers_tmp"
	chmod 440 "$sudoers_tmp"
	visudo -cf "$sudoers_tmp" >/dev/null || { rm -f "$sudoers_tmp"; return 1; }
}
trap 'rm -f "$sudoers_tmp"' EXIT

aur_packages() {
	local -a bad=()
	local p
	for p in $(pkglist "$here/packages/aur.txt"); do
		as_user yay -S --needed --noconfirm --answerdiff None --answerclean None \
			--removemake "$p" || bad+=("$p")
	done
	((${#bad[@]} == 0)) || { echo "AUR failures: ${bad[*]}" >&2; return 1; }
}

account() {
	usermod -aG docker,audio,uucp "$user"
	[[ "$(getent passwd "$user" | cut -d: -f7)" == /usr/bin/fish ]] || chsh -s /usr/bin/fish "$user"
	# Linger keeps user services (Forgejo, CLIProxyAPI, mail) running without a login.
	loginctl enable-linger "$user"
	local i
	for i in $(seq 30); do [[ -S "/run/user/$uid/bus" ]] && return 0; sleep 1; done
	echo "user systemd bus did not appear" >&2
	return 1
}

system_files() {
	# Tailscale must not be running while its node key is put back.
	systemctl stop tailscaled 2>/dev/null
	# File by file: copying the tree root would stamp the snapshot directory's
	# 0700 mode onto / and /etc. mkdir -p leaves existing directories alone.
	local rel rc=0
	while IFS= read -r -d '' rel; do
		rel=${rel#./}
		mkdir -p "/$(dirname "$rel")" && cp -a "$here/root/$rel" "/$rel" || rc=1
	done < <(cd "$here/root" && find . \( -type f -o -type l \) -print0)
	((rc == 0)) || return 1
	[[ -d /var/lib/tailscale ]] && chmod 700 /var/lib/tailscale
	# Drop-ins instead of the old edited sshd_config.
	printf 'X11Forwarding yes\n' >/etc/ssh/sshd_config.d/50-araveia.conf
	append_once /etc/environment "BROWSER=zen-browser"
	append_once /etc/environment "EDITOR=helix"
	# NetworkManager hands DNS to resolved (drop-in restored above); MagicDNS needs it.
	ln -sf ../run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
	archlinux-java set java-21-openjdk
	systemctl daemon-reload
}

firewall() {
	systemctl enable --now firewalld || return 1
	local fc=(firewall-cmd --permanent)
	# LAN: ssh, mosh, Syncthing GUI, dev servers. Docker-published ports
	# (Forgejo :3000) bypass firewalld, so they need no rule here.
	"${fc[@]}" --zone=public --add-service=ssh --add-service=dhcpv6-client
	local port
	for port in 60000-61000/udp 8384/tcp 5000/tcp 5173/tcp 8080/tcp; do
		"${fc[@]}" --zone=public --add-port="$port"
	done
	# Tailnet: ssh, mosh, CLIProxyAPI.
	"${fc[@]}" --get-zones | tr ' ' '\n' | grep -qx tailscale || "${fc[@]}" --new-zone=tailscale
	"${fc[@]}" --zone=tailscale --add-interface=tailscale0
	"${fc[@]}" --zone=tailscale --add-service=ssh
	for port in 60000-61000/udp 8317/tcp; do
		"${fc[@]}" --zone=tailscale --add-port="$port"
	done
	firewall-cmd --reload
}

system_services() {
	systemctl enable --now systemd-resolved && systemctl restart NetworkManager
	local s rc=0
	for s in docker tailscaled cloudflared sshd keyd avahi-daemon cups bluetooth \
		power-profiles-daemon fstrim.timer; do
		systemctl enable --now "$s" || { echo "could not start $s" >&2; rc=1; }
	done
	local i ip=
	for i in $(seq 30); do
		ip=$(tailscale ip -4 2>/dev/null) && [[ -n "$ip" ]] && break
		sleep 2
	done
	if [[ "$ip" != "$tailnet_ip" ]]; then
		echo "tailscale IPv4 is '${ip:-none}', expected $tailnet_ip. Forgejo and CLIProxyAPI bind that address." >&2
		echo "fix: sudo tailscale up, then set this node's IP to $tailnet_ip in the admin console" >&2
		rc=1
	fi
	return $rc
}

# --- home -----------------------------------------------------------------

home_layout() {
	# docs (the mount) and downs are real directories; the XDG names point at
	# them. The installer creates empty Documents/Downloads/Pictures, and
	# anything already in them moves into the target rather than being lost.
	local -A links=([Documents]=docs [Downloads]=downs [Pictures]=docs/Photos/sys)
	local name rc=0
	as_user mkdir -p "$home/downs" "$home/docs/Photos/sys" || return 1
	for name in "${!links[@]}"; do
		local path="$home/$name" target="${links[$name]}"
		if [[ -d "$path" && ! -L "$path" ]]; then
			# Name clashes stay behind, so the directory is only gone once empty.
			as_user rsync -a --ignore-existing --remove-source-files "$path/" "$home/$target/"
			as_user find "$path" -depth -type d -empty -delete
			[[ ! -e "$path" ]] ||
				{ echo "~/$name still has files that clash with ~/$target; merge by hand" >&2; rc=1; continue; }
		fi
		as_user ln -sfn "$target" "$path" || rc=1
	done
	return $rc
}

home_data() {
	rsync -a --chown="$user:$user" "$here/home/" "$home/"
}


dotfiles() {
	if [[ ! -d "$home/.local/share/chezmoi/.git" ]]; then
		as_user chezmoi init "$dotfiles" || return 1
	fi
	as_user chezmoi apply --force
}

toolchains() {
	local rc=0
	as_user rustup default stable || rc=1
	as_user npm install -g @earendil-works/pi-coding-agent pi-profiles || rc=1
	as_user cargo binstall -y mdbook-katex flamegraph || rc=1
	if [[ -d "$home/docs/src/layer-shell" ]]; then
		as_user cargo install --path "$home/docs/src/layer-shell" || rc=1
	fi
	as_user uv python install 3.14 || rc=1
	if [[ -d "$home/docs/src/astala-downloader/main" ]]; then
		as_user uv tool install --force "$home/docs/src/astala-downloader/main" || rc=1
	fi
	if [[ ! -x "$home/.local/bin/claude" ]]; then
		as_user bash -c 'curl -fsSL https://claude.ai/install.sh | bash' || rc=1
	fi
	# Pi's Programmatic Tool Calling Python env.
	as_user bash "$home/.config/pi/profiles/main/setup.sh" || rc=1
	as_user xdg-user-dirs-update
	return $rc
}

forgejo() {
	# Start once as root (the user manager predates the docker group change);
	# restart: always brings the containers back on every later boot.
	(cd "$home/docs/host/forgejo" && docker compose up -d forgejo &&
		docker compose --profile runner up -d runner) || return 1
	local i
	for i in $(seq 90); do
		curl -fsS -o /dev/null http://127.0.0.1:3000/ && break
		sleep 2
	done
	curl -fsS -o /dev/null --max-time 15 https://git.quinntyx.dev/ ||
		{ echo "git.quinntyx.dev is unreachable; check the cloudflared tunnel" >&2; return 1; }
}

local_packages() {
	local d rc=0
	for d in $(pkglist "$here/packages/local.txt"); do
		as_user bash -c "cd \"$home/docs/$d\" && makepkg -sic --needed --noconfirm" || rc=1
	done
	return $rc
}

pi_packages() {
	# Package checkouts came back with ~/.config/pi; this reinstalls node deps
	# and pulls anything newer from the forge.
	local dir rc=0
	for dir in "$home"/.config/pi/profiles/*/ "$home/.pi/agent/"; do
		[[ -f "$dir/settings.json" ]] || continue
		as_user env PI_CODING_AGENT_DIR="${dir%/}" pi update --extensions </dev/null || rc=1
	done
	return $rc
}

cliproxyapi() {
	as_user "$home/.local/bin/cliproxyapi-update"
}

user_services() {
	user_ctl daemon-reload
	local u rc=0
	for u in forgejo.service cliproxyapi.service syncthing.service goimapnotify.service \
		mail-sync.timer omn-canvas-ingest.timer sunsetr-resume.timer tmux-resurrect-save.timer; do
		user_ctl enable --now "$u" || { echo "could not start $u" >&2; rc=1; }
	done
	# Needs a Wayland session, so enable only; it starts with niri.
	user_ctl enable sunsetr.service || rc=1
	return $rc
}

step "hostname, /etc/hosts, docs fstab entry" hostname_and_mount
step "Cider pacman repo" extra_repos
step "official packages" pacman_packages
step "ChatGPT desktop" chatgpt
step "user account: groups, fish, linger" account
step "allow pacman for yay/makepkg" allow_pacman
step "AUR packages" aur_packages
step "system config, SSH host keys, Tailscale identity" system_files
step "firewalld zones" firewall
step "system services" system_services
step "home layout: Documents, Downloads, Pictures symlinks" home_layout
step "home: secrets, app data, downloads, ~/src, game saves" home_data
step "chezmoi dotfiles" dotfiles
step "toolchains: rust, npm, cargo, uv, Claude Code, Pi PTC" toolchains
step "Forgejo" forgejo
step "local PKGBUILDs (omn)" local_packages
step "Pi packages" pi_packages
step "CLIProxyAPI build" cliproxyapi
step "user services" user_services

cat <<EOF

==> manual follow-up
  - Log in again with a fresh session, or reboot, to pick up the docker group and fish.
  - Start niri from a TTY with niri-session (there is no display manager).
  - gcal-sync: run 'gcal-sync --auth' (its token had already expired before the backup).
  - Sign in again: Discord, Slack, Steam, ChatGPT, Antigravity.
  - Gantry is restored to ~/Applications/gantry; re-run its install.sh if its launcher or deps are missing.
  - T3 Code settings and thread history are back in ~/.t3/userdata; worktrees are not.
  - Check: tailscale status; curl http://$tailnet_ip:8317/v1/models
EOF

if ((${#failed[@]})); then
	printf '\n\033[31mSteps that need attention:\033[0m\n'
	printf '  - %s\n' "${failed[@]}"
	exit 1
fi
printf '\n\033[32mrestore complete\033[0m\n'
