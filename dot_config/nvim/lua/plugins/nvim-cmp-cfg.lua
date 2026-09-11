-- nvim-cmp, configured to feel like helix's bundled completion:
-- menu pops automatically with the first item preselected, Enter accepts,
-- Esc aborts. Flat menu (no border) like helix.
--
-- Tab gives the cmp/LSP menu first priority, then accepts one cached Harmonize
-- chunk, then falls back to a literal tab or indentation. M-A remains a direct
-- Harmonize accept binding.

local cmp = require("cmp")

local function harmonize()
    local ok, module = pcall(require, "harmonize")
    return ok and module or nil
end

cmp.setup({
    completion = {
        completeopt = "menu,menuone,noselect",
    },
    preselect = cmp.PreselectMode.Item,
    snippet = {
        expand = function(args)
            require("luasnip").lsp_expand(args.body)
        end,
    },
    mapping = cmp.mapping.preset.insert({
        ["<Tab>"] = cmp.mapping(function(fallback)
            if cmp.visible() then
                cmp.select_next_item()
                return
            end

            local h = harmonize()
            if h and h.is_visible() then
                h.accept()
            else
                fallback()
            end
        end, { "i", "s" }),
        ["<S-Tab>"] = cmp.mapping(function(fallback)
            if cmp.visible() then
                cmp.select_prev_item()
            else
                fallback()
            end
        end, { "i", "s" }),
        ["<CR>"] = cmp.mapping.confirm({ select = true }),
    }),
    sources = cmp.config.sources({
        { name = "nvim_lsp" },
        { name = "luasnip" },
    }, {
        { name = "buffer" },
        { name = "path" },
    }),
})

-- Helix `:` command mode shows completion as well
cmp.setup.cmdline(":", {
    mapping = cmp.mapping.preset.cmdline(),
    sources = cmp.config.sources({
        { name = "path" },
    }, {
        { name = "cmdline" },
    }),
})
