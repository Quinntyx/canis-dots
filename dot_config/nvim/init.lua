-- Data Lifecycle: Stage setup...
require("setup")

-- Data Lifecycle: Stage setup-updates...
require("setup-updates")

-- Data Lifecycle: Stage setup-final-fixes...
require("setup-final-fixes")

-- Persist this pane's editor layout for named-session tmux restoration.
require("tmux-persistence")
