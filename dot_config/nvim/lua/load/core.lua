-- Core plugins: treesitter (parser manager) + which-key (helix-style key menu)
-- + fff.vim (fff file manager as a <leader>e file picker).

local knobs = require("utils").knobs()

return {
    {
        "nvim-treesitter/nvim-treesitter",
        lazy = false, -- nvim-treesitter (main branch) does not support lazy-loading
        build = ":TSUpdate",
        enabled = knobs.treesitter.enabled,
        config = function() require("plugins.nvim-treesitter-cfg") end,
    },
    {
        "dylanaraps/fff.vim",
        cmd = { "F" }, -- lazy-load on the :F command used by the <leader>e mapping
        config = function() require("plugins.fff-cfg") end,
    },
    {
        "folke/which-key.nvim",
        enabled = knobs.whichkey.enabled,
        event = "VeryLazy",
        config = function() require("plugins.which-key-cfg") end,
    },
}
