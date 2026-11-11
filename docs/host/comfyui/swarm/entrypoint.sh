#!/bin/sh
set -eu
mkdir -p /SwarmUI/Data/home
# Backends and user preferences are runtime state. Seed the known backend only once.
if [ ! -e /SwarmUI/Data/Backends.fds ]; then
    cp /etc/swarm/Backends.fds /SwarmUI/Data/Backends.fds
fi
exec dotnet /SwarmUI/src/bin/live_release/SwarmUI.dll \
    --host 0.0.0.0 --port 7801 --launch_mode none \
    --settings_file /etc/swarm/Settings.fds --lock_settings true
