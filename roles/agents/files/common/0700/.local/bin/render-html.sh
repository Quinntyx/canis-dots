#!/bin/sh
# aerc HTML filter: render HTML to plain text NON-interactively,
# then display in the helix pager (pager-helix.sh).

if command -v w3m >/dev/null 2>&1; then
    exec w3m -dump -T text/html -I UTF-8 -cols "${COLUMNS:-100}"
fi
exec pandoc -f html -t plain
