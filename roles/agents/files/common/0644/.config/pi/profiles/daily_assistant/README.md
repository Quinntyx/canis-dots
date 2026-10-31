# daily_assistant pi profile

A minimal pi profile that scrapes your registered courses (Blackboard
eLearning, syllabi, saved source URLs) for upcoming work and cross-checks it
against your Taskwarrior to-do list.

## Philosophy

- **Deterministic code** for what is deterministic: `/register`, `/backdate`,
  and `/archive` update one SQLite database (and move syllabus files when
  present) — no model reasoning needed, no tokens wasted.
- **Model-driven** for what benefits from judgment: scraping Blackboard Ultra
  (a JS-heavy SPA) and judging whether your task plan will finish in time.
- The model never mutates course state. It reads via `da`, browses via `bb`,
  and only ever *reports*.

## Layout

```
profiles/daily_assistant/
├── settings.json               model (gpt-5.6-sol), theme, packages
├── APPEND_SYSTEM.md            profile system prompt (rules, conventions)
├── extensions/
│   ├── course-registry.ts      /register /backdate /archive /courses (wraps `da`)
│   ├── deepseek-router.ts      router provider (flash/pro/1M failover)
│   ├── undo-latest.ts          /undo (fork before last user message)
│   ├── exit-command.ts         /exit
│   └── opencode-prompt.ts      opencode-style prompt editor
├── skills/
│   ├── daily/SKILL.md          /skill:daily — scrape + consolidated report
│   └── validate/SKILL.md       /skill:validate — taskwarrior sanity check
└── bin/
    ├── da                      course registry CLI (python, sqlite3)
    └── bb                      browser surface (playwright, persistent profile)
```

Shared config is **symlinked** (never copied) from `~/.config/pi/agent/` so all
profiles use one credential/model source — keep it that way:

```
auth.json            -> ../../agent/auth.json
models.json          -> ../../agent/models.json
deepseek-router.json -> ../../agent/deepseek-router.json
```

`models-store.json` is intentionally a real per-profile file (provider catalog
cache; the other profiles do the same).

State (mutable, kept outside the profile):

```
~/.local/share/daily-assistant/
├── courses.db    registry (sqlite)
├── active/       syllabi of active courses
├── archived/     syllabi of archived courses
└── browser/      persistent browser profile (login cookies)
```

## Setup

1. The `bin/` dir is already on PATH inside the profile (same mechanism as the
   main profile). Make the scripts executable once:

   ```sh
   chmod +x ~/.config/pi/profiles/daily_assistant/bin/da \
             ~/.config/pi/profiles/daily_assistant/bin/bb
   ```

2. **Optional but recommended** — full browser surface (`bb`). One-time:

   ```sh
   python3 -m pip install --user playwright
   python3 -m playwright install chromium
   ```

   Without it, the model can still read pages via
   `chromium --headless=new --dump-dom <url>` (no login state).

3. Authenticate the model provider once: `/login` inside the profile.

## Usage

```sh
ppi use daily_assistant
```

Then, inside pi:

```
/register ~/Downloads/CS4337-syllabus.pdf      # or /register <path> CS4337
/register ~/Downloads/MATH2418-syllabus.pdf
/backdate F25_CS1200 --name "CS 1200" --term "2025 Fall"
/backdate MATH2413 --name "MATH 2413" --type test-credit --source "AP Calculus BC" --date 2025-07-01
/courses                                       # see what's registered
/skill:daily                                   # scrape everything, report upcoming work
/skill:validate                                # sanity-check taskwarrior against it
/archive CS4337                                # completed (default)
/archive MATH2418 dropped                      # or dropped/withdrawn
```

First browser session: run `bb login` (or ask the model to), authenticate
once with NetID + Duo, then return to the terminal and press Enter. The profile persists.

## tmux layout (optional)

Put this in `~/.config/fish/functions/pi-daily.fish` (created for you):

```fish
function pi-daily --description 'Open daily_assistant: pi on the left, fish on the right'
    set -gx PATH $HOME/.config/pi/profiles/daily_assistant/bin $PATH
    if not tmux has-session -t daily 2>/dev/null
        tmux new-session -d -s daily -n work
        tmux send-keys -t daily 'ppi use daily_assistant --' Enter
        tmux split-window -t daily -h
        tmux select-pane -t daily -L
    end
    tmux switch-client -t daily
end
```

Left pane: the assistant. Right pane: a fish shell where you run Taskwarrior
(`task add ...`, `task done ...`) as the assistant recommends.

## Taskwarrior convention

- Deliverable task: `task add "Submit CS 4337 Project 2" due:2026-04-12 project:school.C S4337`
- Work block: `task add "Work on CS 4337 Project 2" scheduled:2026-04-05 +workblock project:school.CS4337`

`scheduled` informally means "the day I intend to work on this". `/skill:validate`
checks that all scheduled work lands before the real deadlines and adds up.

## `da` reference

```
da register <syllabus-path> [course-key]
da backdate <course-key> [--name NAME] [--term TERM]
            [--type course|test-credit] [--source SOURCE] [--date DATE]
            [--status completed|dropped|withdrawn]
da archive  <course-key> [completed|dropped|withdrawn]
da list [--json]
da get <course-key>
da path <course-key>
da name <course-key> [new-name]
da source <course-key> add <url> | list | clear
da note  <course-key> set <key> <value> | get | del <key>
```

## `bb` reference

```
bb login [url]       # visible browser; authenticate, then press Enter in the terminal
bb open <url>        # goto + wait; prints title/url/network state
bb text | bb html | bb title | bb shot [path]
bb eval '<js>' | bb click <css> | bb scroll [px]
bb session           # print profile dir
```
