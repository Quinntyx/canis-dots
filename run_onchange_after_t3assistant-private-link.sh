#!/bin/sh
# The t3assistant private configuration lives on the docs disk, which survives a
# reinstall. The documented path under ~/.local/state is only a symlink to it, so
# recreate that link when the system disk is new and the archive file is present.
# A real file at the link path is never replaced.
set -e

archive="$HOME/docs/omn/artifacts/t3assistant-config.private.json"
link="$HOME/.local/state/t3assistant/config.private.json"

[ -f "$archive" ] || exit 0
mkdir -p "$(dirname "$link")"
if [ -L "$link" ] || [ ! -e "$link" ]; then
    ln -sfn "$archive" "$link"
fi
