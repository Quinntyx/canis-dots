-- Per-process editor sessions, kept out of projects and chezmoi.
-- Unsaved text is not written by :mksession; normal swap/undo recovery remains.
if not vim.env.TMUX or not vim.env.TMUX_PANE then return end

local uv = vim.uv or vim.loop
local pid = uv.os_getpid()
local stat = table.concat(vim.fn.readfile('/proc/' .. pid .. '/stat'), '')
local fields = vim.split(stat:match('.*%) (.*)$'), ' ', { plain = true })
local start = fields[20]
local state = vim.env.XDG_STATE_HOME or (vim.env.HOME .. '/.local/state')
local directory = state .. '/tmux/nvim'
vim.fn.mkdir(directory, 'p', 448) -- 0700: filenames and session contents are private.
local session = directory .. '/' .. pid .. '-' .. start .. '.vim'
local socket = vim.env.TMUX:match('^[^,]+')
local pane = vim.env.TMUX_PANE
local environment = {}
for _, key in ipairs({ 'NVIM_APPNAME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME' }) do
    if vim.env[key] then environment[key] = vim.env[key] end
end
local metadata = vim.json.encode({
    version = 1, kind = 'nvim', pid = pid, start = start,
    sessionFile = session, cwd = vim.fn.getcwd(), executable = vim.v.progpath,
    environment = environment,
})
local published = false
local stopped = false
local pending = false
local timer = uv.new_timer()

local function tmux(args)
    local command = { 'tmux', '-S', socket }
    vim.list_extend(command, args)
    local output = vim.fn.system(command)
    return vim.v.shell_error == 0, output
end

local function save()
    if stopped or vim.v.vim_did_enter == 0 then return end
    -- Exclude terminal buffers so restoring an editor never restarts arbitrary
    -- programs. Avoid writing machine/runtime configuration into Session.vim.
    local old = vim.o.sessionoptions
    vim.o.sessionoptions = 'buffers,curdir,folds,help,tabpages,winsize'
    local ok = pcall(vim.cmd, 'silent mksession! ' .. vim.fn.fnameescape(session))
    vim.o.sessionoptions = old
    if not ok then return end
    uv.fs_chmod(session, 384) -- 0600
    -- :cd and :tcd changes belong in both the session and launch metadata.
    local data = vim.json.decode(metadata)
    data.cwd = vim.fn.getcwd()
    local updated = vim.json.encode(data)
    if updated ~= metadata then published = false end
    metadata = updated
    if not published then
        published = tmux({ 'set-option', '-p', '-t', pane, '@nvim-resurrect', metadata })
    end
end

local function schedule_save()
    if pending or stopped then return end
    pending = true
    vim.defer_fn(function()
        pending = false
        save()
    end, 250)
end

local group = vim.api.nvim_create_augroup('TmuxPersistence', { clear = true })
vim.api.nvim_create_autocmd({ 'VimEnter', 'BufEnter', 'WinEnter', 'TabEnter', 'DirChanged', 'FocusLost' }, {
    group = group, callback = schedule_save,
})
vim.api.nvim_create_autocmd('VimLeavePre', {
    group = group,
    callback = function()
        save()
        stopped = true
        timer:stop()
        timer:close()
        local ok, value = tmux({ 'show-options', '-p', '-v', '-t', pane, '@nvim-resurrect' })
        local parsed, data = pcall(vim.json.decode, value)
        if ok and parsed and data.pid == pid then
            tmux({ 'set-option', '-p', '-u', '-t', pane, '@nvim-resurrect' })
        end
    end,
})
timer:start(10000, 10000, vim.schedule_wrap(save))
schedule_save()
