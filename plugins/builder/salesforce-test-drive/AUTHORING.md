# Authoring a Test Drive

This plugin is a **framework**. The engine, the authoring contract, the `presetInputs` mechanism, the
instrumentation harness, and these conventions are owned by the framework team. **The individual test
drives are owned by product teams** — you bring a steel-thread prompt and a requirements manifest, and
it's on you to make your prompt sing.

You author a test drive as **two files**:

1. **A catalog entry** in [`catalog/test-drives.json`](catalog/test-drives.json) — the menu label,
   the requirements manifest, ownership, `presetInputs`, and the handoff. Validated against
   [`catalog/test-drive.schema.json`](catalog/test-drive.schema.json).
2. **A prompt file** in [`prompts/`](prompts/) — the steel-thread prose that gets injected and run.

Everything else is framework machinery you don't hand-write: the drive runs on the shared engine in
[`references/engine.md`](references/engine.md), and is exposed through the single
`/salesforce-test-drive:start` command — it appears in that command's menu and can be launched directly
with `/salesforce-test-drive:start <id>` (see **Command surface** below).

## The ownership split

| Framework owns | You (the product team) own |
|---|---|
| The engine (`references/engine.md`) and the single `/salesforce-test-drive:start` command | Your prompt (`prompts/<id>.md`) |
| Readiness gate, provisioning tiers, picklist | Your catalog entry + requirements manifest |
| `presetInputs` injection mechanism | Which inputs to pre-answer vs. leave live |
| Instrumentation (`--instrument`) harness | Keeping your prompt current as the product changes |
| These conventions + the schema | A durable owner contact |

## Add a drive

1. Pick a stable kebab-case `id` (e.g. `service-help-agent`).
2. Add a catalog entry with the required fields (`id`, `title`, `description`, `owner`, `requires`,
   `promptPath`, `handoff`). Set `owner.contact` to a **durable** channel/alias, not a person.
3. Write `prompts/<id>.md` as a natural, user's-voice prompt — as if a real user pasted it into the
   CLI. It is injected and run verbatim, so keep engine/meta commentary out of it (a top HTML comment
   for maintainers is fine). **Do not path to plugin-bundled files with `${CLAUDE_PLUGIN_ROOT}` in your
   prompt or catalog entry.** That token only resolves inside a *command body* — not in prompt/reference
   content and not in a Bash shell — so it silently expands to nothing and breaks the path. Anything your
   drive must read from the plugin goes through the engine's `PLUGIN_ROOT` convention (the engine
   receives the resolved absolute path from the command and reads bundled files via the Read tool). If
   your drive needs a bundled file the engine doesn't already load, raise it with the framework team
   rather than reaching for it from the prompt.
4. Fill `requires` so the engine can gate the org: `minApiVersion`, `licenses`, `userPerms`/`orgPerms`,
   and a `provisioningTier` (optional — omit it and the engine treats the drive as `any`). The engine
   uses `provisioningTier` to route the user to a matching free
   trial org in **two** places — when they have no org at all (Step 2), and when their connected org
   can't be made to satisfy this drive (Step 4) — so set it to the smallest tier that actually works
   (`any` / `developer-edition` / `agentforce`). **Don't put signup URLs in your entry:** routing is
   centralized in the engine against this closed enum precisely so no unverified deep-link can ship. If
   your drive needs a trial edition/template the engine doesn't route to yet, raise it with the framework
   team rather than pasting a link. List `orderedSkills` (the `salesforce-development` skills your drive
   choreographs) — advisory, but it documents intent.
5. That's it — **no command to add.** The drive appears in the `/salesforce-test-drive:start` menu
   automatically (the menu is built from the catalog) and is launchable directly with
   `/salesforce-test-drive:start <id>`. See **Command surface**.

## Command surface

The plugin exposes a **single command** — [`/salesforce-test-drive:start`](commands/start.md) — which
runs the shared engine ([`references/engine.md`](references/engine.md)) two ways:

- **`/salesforce-test-drive:start`** (no argument) — presents the catalog menu so the user picks a
  drive. Good for "show me what's available."
- **`/salesforce-test-drive:start <id>`** — launches that drive directly, skipping the menu
  (`SELECTED_DRIVE = <id>`).

Both paths run the same engine, which owns readiness, provisioning, the requirements gate, launch, and
handoff. **Adding a drive does not add a command** — the menu is built from
`catalog/test-drives.json`, so a new catalog entry shows up automatically and is launchable by its `id`.
That's what keeps authoring a **two-file job** (catalog entry + prompt): there is no per-drive command
stub to write or to keep in sync with the catalog.

## The interactivity contract

The run should feel like a user pasted an expert prompt and watched the agent build the real thing.
So:

- **Pre-answer plumbing, via `presetInputs`.** Output paths, naming defaults — mechanical choices that
  would only interrupt the demo. These go in the catalog entry's `presetInputs`. **Don't pre-answer the
  target org.** The engine always targets the org it settled on during readiness — the user's default
  org (under whatever alias *they* use), or one it provisions for them — so a hardcoded `targetOrgAlias`
  would point the build at the wrong org for anyone whose org isn't named that. Keep your **prompt**
  org-agnostic too — say "my connected org", never a specific alias — because the engine has already made
  the right org the default, so the build just targets it (the engine does *not* substitute placeholders
  into the prompt). Only your **`handoff`** names the org in a copy-pasteable command; there, use the
  **`<targetOrg>`** placeholder (and `<agentApiName>`-style placeholders for values the build produces),
  which the engine substitutes from what the run settled on.
- **Leave showcase decisions live.** The design questions that make the build interesting — persona,
  topics, tone, escalation rules — should be asked live by the underlying skills. That collaboration
  *is* the demo. Do not pre-answer them.
- **Narrate un-automatable Setup steps.** Where the build needs a manual click in Setup that no CLI or
  API can do, your prompt should pause with a clearly marked checkpoint ("⏸ In Setup, go to … then
  say **continue**.") rather than failing silently. The feasibility spike (see below) is how you find
  these.
- **Target: rehearsable-live.** An SE should be able to run your drive live in front of a customer and
  trust the pauses.

## Find your manual steps and gaps — run the spike

Before you trust a drive, run it once under instrumentation against a throwaway org to produce the
manual-step map, API-gap map, and error catalog:

```text
/salesforce-test-drive:start <your-id> --instrument
```

See [`references/instrumentation.md`](references/instrumentation.md) for what the harness records. Use
the summary to decide what to pre-answer (`presetInputs`) and where to add narrated checkpoints. The
throwaway run artifacts are not committed; only the findings graduate into your catalog entry and
prompt.

## Validation

Today: your catalog entry is checked against `catalog/test-drive.schema.json` (strict — a typo'd field
fails). Value-level checks a schema can't express — the `promptPath` file exists, `orderedSkills` name
real skills, the owner contact is reachable — are intended for a future imperative lint gate (a
follow-up, modeled on the repo's `validate-eval-domains.ts`). Until then, verify those by hand.
