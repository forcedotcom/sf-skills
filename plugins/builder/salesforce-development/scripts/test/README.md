# salesforce-development runtime tests

Offline regression guards for the plugin's ported runtime (`../sf-deploy-gate`
and `../sf_context.py`, dispatched through `../sf-context`). No live org
required — each suite stubs `sf` output, mocks `subprocess`, or runs in a
throwaway cwd, so they all run locally without a connected org.

Run the whole set the way CI does:

```bash
npm run test:gates
```

`test:gates` globs every `*.test.sh` (bash) and `test_*.py` (Python `unittest`)
in this directory, so a new suite is picked up automatically once its filename
matches — no package.json edit needed. `python3` is a hard requirement of the
bash suites too (each one's `parse()` shells out to it), so the Python runner
adds no new dependency.

Run an individual suite:

```bash
DIR=plugins/builder/salesforce-development/scripts/test
bash    "$DIR/classify.test.sh"             # org-bucket classification
bash    "$DIR/gate-decision.test.sh"        # full allow/deny decision (stubbed sf)
bash    "$DIR/win-shim-guard.test.sh"       # Windows batch-shim metacharacter guard
bash    "$DIR/detect-compact.test.sh"       # SessionStart(compact) re-inject
bash    "$DIR/feedback-nudge.test.sh"       # feedback gate + one-nudge-per-session
bash    "$DIR/post-deploy-failure.test.sh"  # failed-deploy → owning-skill routing
bash    "$DIR/skills-first-advisory.test.sh" # bypass-prone-op → owning-skill nudge
python3 "$DIR/test_sf_context.py"           # cross-platform exec resolver + reporting
```

## Layout

Two suites live here: the deploy-gate tests and the org-context tests. In this
repo the runtime lives directly under `scripts/` (a sibling of this `test/`
dir), not under `bin/`, because this repo's `.gitignore` blocks `bin/`. There is
no LSP test suite here — this repo vendors the prebuilt LSP bundles rather than
the TypeScript source that such tests would exercise.

## Deploy gate — `sf-deploy-gate` (issue #259)

**`classify.test.sh`** — feeds `sf org display --json` fixtures into
`sf-deploy-gate classify` and asserts the bucket
(`production|sandbox|scratch|trial|devhub|unknown`). The headline cases are the
trial/dev orgs that were previously mis-classified as production:

- OrgFarm trials (`orgfarm-*`, `*.develop.my.salesforce.com`) with `isSandbox`/
  `isScratch` returning `null`
- internal `*.pc-rnd.*` dev hosts
- any org carrying a `trialExpirationDate`

and the guard that genuine production (`*.my.salesforce.com`, classic
`*.salesforce.com`, no sandbox/scratch/trial markers) still classifies as
`production`.

**`gate-decision.test.sh`** — stubs `sf` on `PATH` and runs the full
`prod-check` path, asserting the hook's allow/deny JSON. Proves the #259 fix
end-to-end: a trial org **allows** the deploy, genuine production **denies** it,
the `CONFIRM_PROD=1` override still works, and destructive-changes deploys
(#407) are gated on prod even with the override.

**`win-shim-guard.test.sh`** — sources the gate (which defines its functions
without dispatching) and asserts the Windows batch-shim metacharacter guard:
`_has_cmd_metachars` flags every cmd.exe metacharacter, and `sf_cli` refuses a
metacharacter arg on a `.cmd` shim without invoking COMSPEC.

## Org-context runtime — `sf_context.py` / `sf-context`

**`test_sf_context.py`** (Python `unittest`, WIN-026/WIN-027) — the evidence for
the cross-platform executable resolver: `resolve_executable`/`build_command`/`run`
build a COMSPEC-wrapped **argv array** (never a shell string) for a Windows
`.cmd`/`.bat` shim, refuse metacharacter args on that reparse-prone path, and
spawn POSIX paths directly. Also covers deterministic setup/org reporting (a
missing tool is reported FAILED, never silently green) and secret-free
diagnostics. Stdlib-only (no pytest/PyYAML), mocks `subprocess`/`shutil.which`,
so it runs offline on the Python 3.9 baseline.

**`detect-compact.test.sh`** (#406) — asserts the SessionStart hook's
`source="compact"` re-fire re-injects **only** the lean skills-first reminder
(not the full catalog), shows no banner, stays silent outside a Salesforce
project, and never blocks.

**`feedback-nudge.test.sh`** (#277) — the feedback loop is default-**OFF** and
self-limiting: gate off → always silent; gate on + substantive work → exactly
one nudge per session; `record-feedback-decision` persists the opt-in. Every
response is non-blocking.

**`post-deploy-failure.test.sh`** (#405) — a failed `sf project deploy
start`/`validate`/`quick` routes to its owning skill
(`platform-metadata-deploy` / `platform-deploy-validate` / `platform-quick-deploy`);
non-deploy or garbled payloads stay silent (fail-open); never blocks. This suite
guards the skill-name references that a skill rename must keep in lockstep.

**`skills-first-advisory.test.sh`** (#286/#413/#415/#445) — a PreToolUse
skills-first check that routes bypass-prone ops to the owning skill. The 4
allow-listed 1:1 ops (query, retrieve, apex-test-run, manifest) are BLOCKED with
a `deny` + redirect; every other match (raw `.cls`/`-meta.xml` edits, `sf apex
run` anon, the generic metadata fallback) is WARN-ONLY (`continue: true`). Stays
silent on owner-less metadata and unrelated ops, and applies turn-aware
suppression once the owning skill has dispatched — including the no-deadlock
invariant that an allow-listed op is allowed through (not denied) after its
owning skill runs.

## Plugin recommendation — project-scoped surfaces (W-23856691)

The three automatic/reactive surfaces that can propose an **uninstalled** plugin are scoped to a
Salesforce project — outside one (`sfdx-project.json` absent in cwd) the plugin is
global and must not presume, matching the `cmd_detect` banner gate. Only the explicit
`plugin-match` query (an on-demand user command) is un-gated.

**`prompt-plugin-recommendation.test.sh`** — the proactive UserPromptSubmit surface:
the two exact CMS prompts from a hesitant live session recommend `experience-cms` before
the model answers; strong LWC and React prompts retain their established singular routes;
medium/generic, out-of-project, and already-enabled cases stay quiet. Prompt paint is
high-confidence-only and includes curated capability text plus the confirm-gated install command.

**`skills-first-advisory.test.sh`** (tier-2 section) — when no installed skill owns a
bypass-prone op, the captured prompt is scored against the uninstalled-plugin catalog:
high-confidence + first-occurrence can **deny** when no earlier surface proposed it;
medium or repeat **warns**, generic stays silent. In a current host, UserPromptSubmit
normally consumes the first occurrence for a high match, so the later bypass gate warns
instead of interrupting the user twice. The suite also guards the project gate directly.

**`plugin-match.test.sh`** — the explicit `sf-context plugin-match <text>`
(discovery-command) surface: renders ranked uninstalled candidates, never denies, and
uses Claude Code's `CLAUDE_CODE_SESSION_ID` subprocess environment (or an explicit
`--session-id` outside the host) to write the shared proposal marker. A later same-session
bypass-gate hit warns instead of re-denying, and a later explicit decline is accepted only
for a candidate this or another user-visible surface recorded. Not project-gated.

**`session-plugin-hint-gate.test.sh`** — the SessionStart nudge
(`session_plugin_hint.py`): concrete Agentforce, CMS, LWC, and React project-file signals
stay **silent outside a project** and route only to their high-confidence owning plugin
inside one. It also proves the SessionStart proposal marker suppresses a duplicate CMS
recommendation on the next exact task prompt.

All recommendation suites pin a **hermetic** `CLAUDE_CONFIG_DIR`, independent of the
developer's real `~/.claude` state. The tier-2/explicit-query suites mark LWC and React
enabled to isolate Agentforce/CMS behavior; the prompt and SessionStart routing suites
leave every add-on uninstalled so CMS, LWC, React, and Agentforce compete in the real
stable scoring corpus.

## Port adaptations (source ⇄ this repo)

These suites were translated from the source repo, not copied verbatim. Two
kinds of change were required, both mechanical:

1. **Path:** the runtime lives at `../sf-deploy-gate` / `../sf_context.py`
   (sibling of `test/`), so `$ROOT/bin/…` references became `$ROOT/…` and the
   Python test's `_MODULE_PATH` drops the `bin/` segment.
2. **Skill names + markers:** the advisory/routing suites assert the owning skill
   by name, and this repo renamed the source's gerund skills to the
   `<domain>-<verb>` taxonomy (e.g. `generating-apex` → `platform-apex-generate`,
   `deploying-metadata` → `platform-metadata-deploy`, `quick-deploying-to-prod`
   → `platform-quick-deploy`). Compaction re-inject markers were rebranded
   `sfdx-core` → `salesforce-development`. Expected values track the strings
   `sf_context.py` actually emits in this repo.

## Hook matcher note

Unlike the source suite — which relied on prefix-anchored `matcher` strings like
`Bash(sf project deploy start*)` — the `salesforce-development` plugin wires the
gate through the **`if` field** on each hook entry (`if: "Bash(sf project deploy
start *)"`). Claude Code's PreToolUse/PostToolUse `matcher` filters on the tool
*name* only; command-content matching belongs in `if` (permission-rule syntax).
See the plugin's `.claude-plugin/plugin.json`.
