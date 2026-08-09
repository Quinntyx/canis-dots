import { readdir, unlink } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const CLIPBOARD_PREFIX = "pi-clipboard-";

export default function updateCommand(pi: ExtensionAPI) {
  pi.registerCommand("update", {
    description: "Update pi and packages, and clean up clipboard temp files",
    handler: async (_args, ctx) => {
      const notify = (msg: string, type: "info" | "warning" | "error" = "info") =>
        ctx.ui.notify(msg, type);

      // 1. Update pi itself + installed packages
      notify("Updating pi and packages…");
      const upd = await pi.exec("pi", ["update", "--all"]);
      if (upd.code !== 0) {
        notify(`pi update failed: ${upd.stderr.trim() || upd.stdout.trim()}`, "error");
        return;
      }
      notify("pi and packages updated.");

      // 2. Clean up lingering clipboard temp images
      let removed = 0;
      try {
        const entries = await readdir(tmpdir());
        await Promise.all(
          entries
            .filter((name) => name.startsWith(CLIPBOARD_PREFIX))
            .map(async (name) => {
              try {
                await unlink(join(tmpdir(), name));
                removed++;
              } catch {
                /* already gone — ignore */
              }
            }),
        );
      } catch {
        /* tmpdir unreadable — non-fatal */
      }
      notify(`Update complete. Removed ${removed} clipboard temp file(s).`);
    },
  });
}
