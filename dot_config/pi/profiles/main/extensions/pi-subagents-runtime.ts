import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/** Pin roots to the recursive runtime; never replace an inherited child source. */
export default function (_pi: ExtensionAPI): void {
  if (process.env.PTC_SUBAGENTS_SOURCE?.trim()) return;
  const source = join(homedir(), "docs", "src", "pi-subagents", "feat-recursive-subagents");
  if (!existsSync(join(source, "pyproject.toml")) ||
      !existsSync(join(source, "src", "pi_subagents", "__init__.py"))) {
    throw new Error(`Recursive pi-subagents checkout is missing: ${source}`);
  }
  process.env.PTC_SUBAGENTS_SOURCE = source;
}
