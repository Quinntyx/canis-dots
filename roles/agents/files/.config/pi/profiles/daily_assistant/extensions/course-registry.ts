/**
 * course-registry.ts — deterministic `/register`, `/backdate`, `/archive`,
 * and `/courses` commands for the daily_assistant profile.
 *
 * These are thin TUI wrappers around the `da` CLI (bin/da, a Python script),
 * which is the single source of truth for course state. Moving the syllabus
 * file into managed storage and updating the SQLite registry is pure
 * deterministic code: there is no external data to interpret, so the model is
 * deliberately NOT involved. The model only ever READS course state (via
 * `da list` / `da path` / `da get` in bash) and never mutates it.
 *
 * /register <syllabus-path> [course-key]
 * /backdate <course-key> [--name NAME] [--term TERM]
 *           [--type course|test-credit] [--source SOURCE] [--date DATE]
 * /archive  <course-key> [completed|dropped|withdrawn]   (default: completed)
 * /courses
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const execFileAsync = promisify(execFile);

type CompletionItem = { value: string; label?: string };

interface RunResult {
	stdout: string;
	stderr: string;
	code: number;
}

/** Minimal shell-like split that respects double quotes. */
function splitArgs(s: string): string[] {
	const out: string[] = [];
	const re = /"([^"]*)"|(\S+)/g;
	let m: RegExpExecArray | null;
	while ((m = re.exec(s))) out.push(m[1] ?? m[2]);
	return out;
}

async function runDa(args: string[]): Promise<RunResult> {
	try {
		const { stdout, stderr } = await execFileAsync("da", args, {
			timeout: 20000,
		});
		return { stdout: stdout.trim(), stderr: stderr.trim(), code: 0 };
	} catch (e) {
		const err = e as { stderr?: string; message?: string; code?: number };
		return {
			stdout: "",
			stderr: (err.stderr ?? err.message ?? String(e)).trim(),
			code: typeof err.code === "number" ? err.code : 1,
		};
	}
}

async function activeCourseKeys(): Promise<CompletionItem[] | null> {
	const r = await runDa(["list", "--json"]);
	if (r.code !== 0) return null;
	try {
		const rows: Array<{ key: string; name: string; status: string }> = JSON.parse(r.stdout);
		return rows
			.filter((x) => x.status === "active")
			.map((x) => ({ value: x.key, label: `${x.key} — ${x.name}` }));
	} catch {
		return null;
	}
}

function notifyResult(ctx: { ui: { notify: (msg: string, kind: "info" | "error" | "warning") => void } }, r: RunResult) {
	if (r.code !== 0) ctx.ui.notify(r.stderr || "command failed", "error");
	else ctx.ui.notify(r.stdout || "(no output)", "info");
}

export default function (pi: ExtensionAPI) {
	pi.registerCommand("register", {
		description: "Register a course from a syllabus file. Usage: /register <syllabus-path> [course-key]",
		handler: async (args, ctx) => {
			const parts = splitArgs(args);
			if (parts.length < 1 || !parts[0]) {
				ctx.ui.notify("Usage: /register <syllabus-path> [course-key]", "warning");
				return;
			}
			notifyResult(ctx, await runDa(["register", ...parts]));
		},
	});

	pi.registerCommand("backdate", {
		description: "Add a completed historical course or test credit without a syllabus",
		handler: async (args, ctx) => {
			const parts = splitArgs(args);
			if (parts.length < 1 || !parts[0]) {
				ctx.ui.notify(
					"Usage: /backdate <course-key> [--name NAME] [--term TERM] [--type course|test-credit] [--source SOURCE] [--date DATE]",
					"warning",
				);
				return;
			}
			notifyResult(ctx, await runDa(["backdate", ...parts]));
		},
	});

	pi.registerCommand("archive", {
		description: "Archive a course. Usage: /archive <course-key> [completed|dropped|withdrawn] (default completed)",
		getArgumentCompletions: async () => activeCourseKeys(),
		handler: async (args, ctx) => {
			const parts = splitArgs(args);
			if (parts.length < 1 || !parts[0]) {
				ctx.ui.notify("Usage: /archive <course-key> [completed|dropped|withdrawn]", "warning");
				return;
			}
			notifyResult(ctx, await runDa(["archive", ...parts]));
		},
	});

	pi.registerCommand("courses", {
		description: "List registered courses and their statuses",
		handler: async (_args, ctx) => {
			notifyResult(ctx, await runDa(["list"]));
		},
	});
}
