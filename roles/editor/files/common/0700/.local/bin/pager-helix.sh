#!/bin/sh
# aerc pager: helix over the ANSI-stripped filter output.
# (aerc's colorize filter emits SGR escapes; helix renders them as garbage,
# so strip them and hand the clean text to helix as a stdin scratch buffer.)
sed 's/\x1b\[[0-9;]*m//g' | helix -
