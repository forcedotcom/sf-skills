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

**`skills-first-advisory.test.sh`** (#286/#413/#415/#445) — a PreToolUse advisory
nudges toward the owning skill on bypass-prone ops (raw `.cls`/`-meta.xml` edits,
raw `sf apex/retrieve/data` calls), stays silent on owner-less metadata and
unrelated ops, and applies turn-aware suppression once the owning skill has
dispatched. WARN-ONLY — every response carries `continue: true`.

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
