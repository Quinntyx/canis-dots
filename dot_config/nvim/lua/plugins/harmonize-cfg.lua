-- harmonize.nvim: AI tab-completion (ghost text) backed by local llama.cpp.
--
-- Backend: llama-server serving ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF
-- (FIM-capable), reached through llama.cpp's native /infill endpoint — the
-- server constructs the FIM prompt from the model's own tokens, so no
-- template is configured here.
--
-- The below-line display overlays same-line completions beneath the cursor.
-- Newline-leading completions use their actual next-line position and shift
-- following screen text down. Later chunks fade by 25 percentage points.
--
-- The cmp menu gets Tab first. When no menu is visible, Tab accepts Harmonize's
-- next cached chunk; M-A remains a direct backup binding.

require("harmonize").setup({
    provider = "llama_cpp",
    context_window = 512, -- conservative for local inference; raise if the machine keeps up
    throttle = 0, -- no request limit: every pause fires immediately
    debounce = 50, -- fire almost as soon as typing pauses (ms)
    auto_trigger_ft = { "*" }, -- suggest in every filetype; narrow to e.g. { "rust", "lua" } to limit
    keymap = {
        -- Tab accepts one chunk; nvim-cmp-cfg.lua binds Tab itself,
        -- and its mapping replaces the default acceptance key below.
        accept = "<M-A>", -- accept one chunk
        accept_line = "<M-a>", -- accept one line
        dismiss = "<M-e>",
        trigger = "<M-]>", -- manually request a completion
        toggle = "<M-c>", -- toggle auto-completion on and off
    },
    -- Overlay same-line text below the cursor; newline-leading text uses an
    -- in-place virtual line at its actual insertion position.
    display = "below",
    -- Keep the LSP/cmp menu visible above the Harmonize preview.
    show_with_completion_menu = true,
    -- Fade later chunks linearly while keeping long suggestions readable.
    chunk_fade = {
        enabled = true,
        opacity_step = 0.25,
        minimum_opacity = 0.1,
    },
    -- harmonize starts the server when nothing answers on 127.0.0.1:8012
    -- (the running one is detected and left alone) and leaves it running
    -- when nvim exits; nil by default, so this table opts in.
    auto_start = {
        model = "ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF",
        host = "127.0.0.1",
        port = 8012,
    },
    provider_options = {
        llama_cpp = {
            end_point = "http://127.0.0.1:8012/infill",
            optional = {
                -- streamed: the first chunk appears fast even with a large cap
                n_predict = 256,
                top_p = 0.9,
            },
        },
    },
    -- auto_start defaults apply: when nothing answers on 127.0.0.1:8012,
    -- harmonize starts `llama serve` with the Qwen model (reused from PATH
    -- or downloaded) and leaves it running when nvim exits. The server
    -- already running here is detected and left alone.
})
