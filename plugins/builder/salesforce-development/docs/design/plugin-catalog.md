# Plugin-catalog gap detection — design note

Design rationale for the plugin-level extension to Headless 360 discovery: when no installed
skill matches a task, a new tier proposes installing an **uninstalled plugin** whose curated
description matches the prompt. This note captures the plugin-specific decisions; the full phased
implementation plan lives in
[`docs/dev-notes/dynamic-loading-strategy-plan.md`](../../../../docs/dev-notes/dynamic-loading-strategy-plan.md)
and the cross-cutting invariant reinterpretations are recorded in
[`docs/design/README.md`](../../../../docs/design/README.md). Read both before modifying
`plugin_catalog.py`, the `UserPromptSubmit`/`PreToolUse` consumers in `sf_context.py`, the
SessionStart project-signal hint, or the discovery-command plugin-match mode.

## Point of view

Skill-level discovery answers "which installed skill handles this?" This effort answers a
different, narrower question one layer down: "is there an **uninstalled** plugin that would?" It
is deliberately not a general plugin recommender: it considers only curated registry entries that
are not already enabled, is scoped to a Salesforce project except for an explicit discovery query,
and only ever proposes; it never installs anything itself.

Two properties are load-bearing and easy to erode by accident during future edits:

- **Direct-leaf, not a router.** The deterministic BM25-lite matcher may surface more than one
  plugin for a single prompt — a prompt can legitimately implicate two distinct uninstalled
  plugins' domains — but each candidate is scored and thresholded independently against its own
  plugin's matchable text. Candidates are ranked by descending score for a stable, legible order,
  but no winner is ever automatically selected or dispatched: the matcher emits N self-standing
  single-owner proposals; the user, never the system, decides which (if any) to act on. Installing
  exactly one named plugin at a time, even when several were proposed, is what keeps this a
  direct-leaf shape applied N times rather than a compact router that fans a request out to a chosen
  leaf. The score order is presentational only — do not add a "best pick," auto-selection, dispatch,
  or a lazy-load claim.
- **Four deterministic proposal surfaces, with different evidence bars.** The same matcher is
  reachable from (a) `UserPromptSubmit` for a concrete task, (b) the reactive `PreToolUse`
  bypass-gate advisory, (c) an explicit user-/model-initiated discovery query, and (d) SessionStart
  project-file signals. Prompt-time matching exists because a model can answer from defaults and
  never make the guarded tool call that used to trigger a recommendation. It is deliberately
  **high-confidence-only**; medium prompt matches stay quiet and remain available to explicit
  discovery or the reactive gate. SessionStart is also high-confidence-only and driven by concrete
  local file signals, not a free-form ambient model guess. All four paths are deterministic and
  share the catalog scorer; none makes a recommendation-time LLM call. The two proactive surfaces
  (UserPromptSubmit, SessionStart) and the two solicited ones (discovery, bypass-gate) split along
  this same line for *every* evidence-bar knob the scorer exposes, not just the band: see
  `require_anchor_terms` below.
- **Project scoped, except when explicitly asked.** UserPromptSubmit, SessionStart, and the bypass
  gate require `sfdx-project.json` in cwd. The explicit `plugin-match` query remains un-gated because
  invoking it is itself sufficient intent. This keeps a globally installed foundation plugin from
  presuming that an unrelated React tree or a generic media request is Salesforce work.
- **Installation state never changes confidence.** BM25 scores use the stable registry add-on
  corpus, then enabled plugins are removed from the returned candidates. Filtering the scoring
  corpus first changes IDF and can promote a weak neighboring match from medium to high simply
  because the correct plugin is already installed. Enabled state controls eligibility only.
- **Request scaffolding is not product evidence.** The scorer removes common function words,
  generic action verbs, and the shared `Salesforce` umbrella term from both prompts and registry
  documents before scoring. A follow-up such as "add a field to it" therefore cannot accumulate a
  high React score from marketplace prose; confidence must come from substantive vocabulary such
  as `CMS`, `media asset`, `LWC`, `React`, `ui bundle`, or `Agentforce`.
- **Tool syntax is not user intent.** The reactive gate scores only the bounded prompt captured by
  UserPromptSubmit. If no prompt marker is available, it stays quiet rather than treating a raw
  command or file path as the task; terms such as `project`, `source`, or `app` otherwise create
  plausible but false cross-product matches.
- **A generic word shared with the corpus cannot carry a match alone.** A plugin declares
  `metadata.match.anchorTerms` (marketplace.json) when its capability vocabulary overlaps a
  domain-sounding-but-generic word used elsewhere in the corpus (e.g. `install` appears inside
  `dx-org-lifecycle`'s "package post install" phrase, but is not evidence of any org-lifecycle
  intent). `score_prompt_against_catalog`'s `require_anchor_terms` (default `True`) drops such a
  candidate unless the prompt's matched terms include at least one of its own anchor terms —
  closing the failure class where "install agentforce-adlc plugin" high-confidence-matched the
  wrong plugin on the word "install" alone. This gate exists to stop a generic-word coincidence
  from **interrupting** the user unprompted, so — mirroring the high/medium band split — only the
  two proactive surfaces (`UserPromptSubmit`, SessionStart) pass `require_anchor_terms=True`;
  explicit discovery and the reactive bypass gate pass `False` and see plain high+medium matches,
  because the user's own act of invoking those surfaces is itself the missing evidence. A plugin's
  anchor set can therefore still be too narrow to cover every phrase a user would reasonably type
  into explicit discovery — that is an authoring quality issue to fix by broadening the anchor set,
  not a gap in this surface split. Author anchor terms by hand, checked against that plugin's own
  `examplePrompts`/`keywords` so an anchor set never silently makes an example unmatchable.
- **Sensitivity is one configurable value, not a separate on/off switch.** `off` is simply the most
  conservative point on the same scale as the high/medium band threshold, resolved with precedence
  (highest wins): the `SF_DISABLE_PLUGIN_MATCH` / `SF_PLUGIN_MATCH_SENSITIVITY` env vars, a per-user
  in-session preference (`/salesforce-development:plugin-recommendations on|off|status|set
  <level-or-number>`, persisted to `~/.sf/plugin-recommendations/config.json`), the plugin's own
  `userConfig.plugin_match_sensitivity` install-level default, then `standard`. Named levels
  (`low`/`standard`/`high`) keep a stable customer-facing contract even if the BM25 scoring is
  retuned later; a custom number in `1.0`-`10.0` gives finer control. The custom number IS the raw
  threshold compared against the match score, so its direction is the *inverse* of the "high"/"low"
  words: `high` sensitivity resolves to the low end of the range (3.0, easiest to clear), `low`
  resolves to the high end (6.0, hardest to clear). Anyone editing the command doc, the design doc,
  or a default value here must state the number next to the word every time — this pairing has
  already shipped backwards once (see the `plugin-recommendations.md` fix that accompanied this
  note) precisely because the two scales run in opposite directions. Every read-time step is
  fail-open on anything malformed, falling through to the next tier — matching this file's existing
  `except Exception: return []` posture — while the write-time `plugin-match-config set` command
  fails loud on an invalid value.
- **One session proposal ledger.** SessionStart, prompt, discovery, and bypass consumers reconcile
  against the same per-session plugin marker. The first surface owns telemetry and incidental
  paint; later prompt/tool surfaces must not deny, repaint, or count it again. Explicit discovery
  queries and SessionStart resume/compact replays may still render because they are solicited or
  lifecycle replays, but remain side-effect-free. This matters most for proactive paths: once the
  user has already seen an install choice at startup or before the model answers, the next prompt
  or tool gate must not turn that same choice into another interruption.

## Security boundary: what text may be exposed

Skill-level discovery hides an uninstalled skill's real, mined description and shows only a
sanitized `examplePrompt`. The plugin catalog inverts that for plugins — it deliberately exposes
matchable description text for uninstalled plugins, because matching against real text is the
whole point. The boundary this depends on: that matchable text must be **first-party, curated,
reviewed copy** sourced from the owning plugin's own marketplace entry — its `description`,
`keywords`, and `metadata.match.examplePrompts` (all already public, already owner-approved) — and
**never** untrusted prose mined from an uninstalled plugin's internal `SKILL.md`/files. If a
future change lets the catalog's `match` text be derived from anything other than a curated
`.claude-plugin/marketplace.json` entry — e.g. scraping a plugin's own skill descriptions — it has
crossed this boundary. The release leak-scanner additionally forbids any internal/held plugin's
text from reaching a public catalog artifact.

**Opt-in rule (uniform for every entry).** The catalog is generated from the repo-root
`.claude-plugin/marketplace.json` — Claude Code's real marketplace schema — with no separate
hand-authored catalog. An entry becomes a discovery candidate **iff** it declares a non-empty
`keywords` array *and* is not held via `internalPlugins` in `config.yml`; entries with no keywords
are simply invisible to the matcher. Opting in via `keywords` obliges the entry to also carry
`metadata.match.examplePrompts` (Claude Code ignores `metadata`, so it is the correct home for
matcher copy), and the generator fails fast if that pairing is missing. "Local vs external" is no
longer a stored field — it is derived at read time from whether an entry's `source` is a
relative-path string (local, in this repo) or a source object (fetched from elsewhere).

## Accepted-proposal install mechanic

The workflow treats the user's explicit acceptance of a recommendation as the authorization to
install a plugin from the reviewed Salesforce marketplace. UserPromptSubmit pins that exact
candidate and routes one fixed command: `plugin-install <name> --accept-proposed`. The runtime
independently requires a valid same-session proposal, the same selected plugin in `selected` state,
and an exact source value of `./plugins/builder/<name>`. If all three checks hold, it installs in
that call; no dry run, nonce, second prose confirmation, or ordinary Bash approval is added. The
PreToolUse hook can return `allow` only for that complete standalone command and those same checks.
Appending shell syntax, changing the name, omitting the selected workflow, or using another source
shape falls outside the allowance. Claude Code's user, project, and managed ask/deny policy remains
authoritative over hook output.

An accepted external or otherwise mutable source does **not** inherit that fast path. The first
call prints the plugin name and concrete source, adds a trust warning, and returns a nonce derived
from the exact `{name, source}` lookup. It installs nothing. Only a subsequent explicit source
confirmation routed as `--confirm <nonce>` proceeds. The comparison is constant-time
(`hmac.compare_digest`), and any source change invalidates the nonce and forces a fresh preview.
A bare self-directed `plugin-install <name>` call retains this preview/confirmation behavior for
compatibility; it cannot claim the accepted-proposal trust boundary.

Natural-language declines are handled directly by UserPromptSubmit after the same-session proposal
checks, so acknowledging a decline no longer creates a Bash approval prompt. The hook records the
decision, preserves the proposal ledger entry for deduplication, clears any pending nonce, advances
the flow to `declined`, and fires telemetry. The CLI's `--decline` form remains as a compatibility
path with the same validation.

Every visible recommendation surface opens one private, bounded, expiring session workflow. Its
state advances from `recommended` to `selected`, then directly to `installed` for a trusted source
or through `awaiting-confirmation` for an external/self-directed source, and finally to `installed`
or `declined`. A SessionStart batch can hold several candidates, but a generic reply can select one
only when exactly one candidate remains unambiguous; an explicitly named valid proposal can always
select itself. The marker contains only plugin names, state, and one boolean stating whether the
recommendation interrupted a concrete task. Marketplace instructions and the user's prompt/task
text are never persisted.

If SessionStart or an explicit discovery query opened a recommendation-only flow and the user then
submits a concrete task matching one of those candidates, UserPromptSubmit promotes that candidate
to a task-backed flow and surfaces it for the task. This promotion intentionally bypasses only the
proposal ledger's first-occurrence display deduplication; it does not bypass source classification
or the same-session selected-proposal checks.

UserPromptSubmit resolves that workflow before any catalog scoring. A terse reply such as `OK`,
`Go`, or `ok install it` can therefore accept the sole/selected plugin without rescoring the prompt.
A trusted marketplace entry installs from that acceptance; an external entry writes a separate
content-bound nonce marker, after which confirmation routes only that exact `--confirm` command.
Declines are recorded directly for only the selected proposal. Install/reload continuations and
plugin questions stay inside the workflow, and the PreToolUse fallback also stays silent while it
is active. The workflow remains after a
successful install or decline until a substantive new task releases it. Explicit terminal resume
language such as `continue` after a task-backed recommendation resumes only that interrupted task
after the refreshed host inventory proves activation (or resumes it without the declined plugin).
The successful install handoff makes that next action explicit: task-backed flows say to run
`/reload-plugins` and then say `continue`, while recommendation-only flows ask for a concrete task
after reload instead of implying that work is waiting.
Status questions and bare `OK` never authorize resumption or re-enter installation. A
recommendation-only or SessionStart flow may report activation, but it cannot inspect the project,
invoke a skill/tool, or invent work; it asks for a new concrete task and stops. A substantive changed
task before completion abandons the old workflow and clears any pending nonce. Expired or corrupt
state fails closed, and control language without valid state stays recommendation-free.

The hook never performs an install. It does record a validated natural-language decline directly;
the CLI independently revalidates accepted proposal, name, selected workflow, and source before an
install, and revalidates the source-bound nonce when external confirmation is required.

## Trust posture: local vs. externally hosted

The catalog no longer stores byte-level pins or an explicit trust flag. A plugin's assurance
level is derived from the shape of its verbatim marketplace `source`:

- Only the **exact string** `./plugins/builder/<name>` is eligible for the accepted-proposal fast
  path. It identifies the same named plugin in the reviewed monorepo from which the registry was
  built. A merely relative string, mismatched directory, normalized/traversal variant, or future
  source form does not qualify.
- An **object** `source` (e.g. `{ "source": "github", "repo": …, "ref": … }`) is fetched from
  outside this repo at **install** time by `claude plugin install`. There is no build-time hook to
  hash-verify that fetch, and installing a whole external plugin can run arbitrary hooks it ships —
  an inherently lower assurance level. Rather than imply a byte-level guarantee it cannot deliver,
  the external confirmation flow surfaces this as an explicit trust warning because it does not
  equal the exact reviewed same-name marketplace path. The pinned `ref`/`sha` in the source object
  is recorded for provenance, not verification. Do not reintroduce a build-time tree
  hash of an external repo: it would break the build's offline hermeticity and would only pin the
  wrong moment.
