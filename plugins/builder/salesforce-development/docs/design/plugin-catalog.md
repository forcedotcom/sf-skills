# Plugin-catalog gap detection — design note

Design rationale for the plugin-level extension to Headless 360 discovery: when no installed
skill matches a task, a new tier proposes installing an **uninstalled plugin** whose curated
description matches the prompt. This note captures the plugin-specific decisions; the broader phased
implementation plan is tracked separately as a design-plans working document, and the cross-cutting
invariant reinterpretations are recorded in
[`docs/design/README.md`](../../../../../docs/design/README.md). Read the latter before modifying
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
  this same line by default. A plugin may explicitly retain anchor qualification on
  solicited surfaces with `enforceAnchorsOnAllSurfaces`: see below.
- **Informational matches and flow candidates are different sets, for discovery and bypass-gate.**
  `discovery-command` and `bypass-gate` deliberately return every high+medium match for
  display/telemetry/ledger purposes — that is the point of the anchor-ungated, solicited-evidence
  bar above. But the live decision flow those two surfaces open (`_open_plugin_flow`, from
  `cmd_plugin_match` and the bypass advisory respectively) narrows to the high-band subset when at
  least one exists, falling back to the full match list only when none are high. Without that
  narrowing, a prompt that scores one clear high match plus several medium alternatives puts all of
  them in the flow, so a bare "yes" answering the single plugin actually proposed in prose is
  declared ambiguous against matches the user was never told were part of the ask (a PR-1696 review
  finding, since fixed). A named medium match remains selectable regardless: `_select_plugin_flow`'s
  existing ledger fallback re-derives it from the proposal ledger — written for every match
  regardless of band — even when it sits outside the flow's narrowed candidate set.
- **Project scoped, except when explicitly asked.** UserPromptSubmit, SessionStart, and the bypass
  gate require `sfdx-project.json` in cwd. The explicit `plugin-match` query remains un-gated because
  invoking it is itself sufficient intent. This keeps a globally installed foundation plugin from
  presuming that an unrelated React tree or a generic media request is Salesforce work. One further
  out-of-project path exists and is deliberately narrow: when a user with no project names Salesforce
  or CRM (its product category), the getting-started note fires, and that note reuses the *same* UserPromptSubmit
  scorer at its full proactive bar (high band + `require_anchor_terms=True`) to fold at most a
  one-line install recommendation into itself. Since the entered-project-splash plan (Change 2) that
  getting-started surface is **model-facing only** — it rides `additionalContext`, never a visible paint —
  so the recommendation is re-homed onto that model channel too: `_prompt_plugin_recommendation_surface`
  is called with `shown_to_user=False` (its framing then states the match was found but *not* displayed,
  and gates the relay on genuine build intent), and the visible half of its return is discarded. Naming
  the product or its category out of a project is the sufficient-intent signal here — the exact parallel to
  explicit discovery — but the high+anchor bar still governs, so a bare product-cue mention (`salesforce` /
  `crm`) with no strong capability match adds nothing. It is install-only (like SessionStart it never points
  at an installed plugin's command) and opens the same one decision workflow, so a subsequent sole-candidate
  `yes` installs through the ordinary accepted-proposal path. This is not a fifth surface: it is the
  UserPromptSubmit proactive match reached from the getting-started branch, so every evidence-bar knob is
  identical. (The visible getting-started welcome that used to paint this rec is gone — the sole visible
  out-of-project splash is now the scaffold-success paint.)
- **The scaffold-success paint persists the project type it observed.** The splash project header reads
  `name · type · API version`, where the type is the `sf project generate --template` value. The SF CLI
  stores that nowhere, so `cmd_scaffold_paint` writes the observed template into the created
  `sfdx-project.json`'s top-level `template` key (`_persist_scaffold_template`) — **only on an observed
  generate, and only when the key is absent**. Every other read is read-only (`_project_type_from_descriptor`),
  so a project we merely open is never touched and one with no `template` key simply shows no type (we never
  sniff to guess it). Add-only means the write becomes a no-op the day a future SF CLI writes `template`
  itself — the CLI's value then flows through unchanged. A tracked descriptor key (not a machine-local `.sf`
  sidecar) was chosen so the type survives a clone and is shared with teammates.
- **Installation state never changes confidence — it decides eligibility only.** BM25 scores use the
  stable registry add-on corpus, then enabled plugins are removed from the returned candidates.
  Filtering the scoring corpus first changes IDF and can promote a weak neighboring match from medium
  to high simply because the correct plugin is already installed. Enabled state therefore controls
  eligibility, never confidence — and **recommendations are uninstalled-only**: an already-installed
  match has nothing to install, so it is dropped after scoring and never surfaces. The whole point of
  dynamic plugin loading is to surface plugins the user does *not* have; a user who already has the
  plugin just runs its command, with no recommendation in the way. Dropping the top-ranked installed
  match still leaves any weaker *uninstalled* neighbor eligible to be proposed in its place (matching
  develop's pre-existing behavior), because the drop happens *after* the full corpus was scored, so it
  never changes a band. Fail-open `enabled is None` (settings unreadable) treats every candidate as
  uninstalled, so the recommender stays useful rather than going silent when it cannot confirm install
  state. (This reverses the short-lived "you already have this — run its command" routing; see the
  decision-log entry "Recommendations are uninstalled-only", 2026-08-31.)
- **Request scaffolding is not product evidence.** The scorer removes common function words,
  generic action verbs, and the shared `Salesforce` umbrella term from both prompts and registry
  documents before scoring. A follow-up such as "add a field to it" therefore cannot accumulate a
  high React score from marketplace prose; confidence must come from substantive vocabulary such
  as `CMS`, `media asset`, `LWC`, `React`, `ui bundle`, or `Agentforce`.
- **Capability evidence is not task intent.** Exact product vocabulary can produce a strong
  catalog score in an informational question, comparison, historical observation, or bare
  declaration. `UserPromptSubmit` therefore requires a conservative deterministic action-request
  shape before invoking the scorer. Imperatives, explicit requests, and diagnostic questions can
  proceed; definitions, comparisons, product mentions, and ambiguous statements stay quiet.
  Explicit discovery and the reactive bypass gate do not use this prompt gate because invoking
  those surfaces already supplies the missing intent. SessionStart remains project-signal driven.
- **Tool syntax is not user intent.** The reactive gate scores only the bounded prompt captured by
  UserPromptSubmit. If no prompt marker is available, it stays quiet rather than treating a raw
  command or file path as the task; terms such as `project`, `source`, or `app` otherwise create
  plausible but false cross-product matches.
- **Only the user's own words are matched.** `UserPromptSubmit` strips host-injected context before
  any decision or score: IDE open-file/selection/diagnostic notices, `<task-notification>` and
  `<system-reminder>` blocks. The surfaces then read three views of that text:
  - *Decisions* (confirm, install, decline) read the whole host-stripped prompt, unbounded, so
    selected README text or a task notification that says "install X" can never confirm an install,
    while a typed "yes install it" next to an IDE notice still does. A prompt that is empty after
    stripping decides nothing.
  - *Prompt-time matching and request checks* read the intent text (`_prompt_intent_text`): the
    first 64 KB of the stripped prompt minus URLs, paths, slash-command names, and `UPPER_SNAKE`
    identifiers, with line breaks kept so the request checks still split sentences on them. Any non-ASCII
    letter or combining mark (except U+FE0E/U+FE0F presentation selectors) in the full
    host-stripped prompt yields no matching intent, even beyond the scan window: incidental
    English logs are not the ask.
    The outside-project Salesforce/CRM cue reads the same filtered words without the matching abstention
    (`_prompt_user_words`), so a non-Latin prompt that names Salesforce still gets its note.
  - *The reactive bypass gate* reads the recorded filtered user words (`prompt.txt`),
    preserved as UTF-8 within the existing 2048-byte limit, truncated at character boundaries.
    Preservation is independent of matching eligibility; user spelling is retained. A separate
    ASCII `catalog-eligible` marker records eligibility of the full host-stripped prompt before
    either scan or byte truncation. Missing/corrupt eligibility abstains, including legacy markers.
    This prevents an English prefix or pasted log from denying a non-English request.
  - *Unclosed host blocks run to the end of the prompt, wherever they open.* Dropping the tail of
    a typed sentence only makes matching quieter (the safe direction); restricting the strip to
    openings at a line start would let a mid-line injected block be scored as the user's ask.
    The accepted cost: a user who types a host tag name in prose loses the rest of that prompt.
  - *Path vs. product name.* A relative slashed token is a path only with a known project root
    (`force-app`, `src`, `scripts`, `docs`, `node_modules`) or a file extension on its last segment,
    optionally with a `:line[:col]` suffix. Hyphens, digits, or three segments alone do not make a
    path, so `B2B/B2C`, `Experience-Cloud/CMS`, `OAuth2/JWT`, and `Apex/LWC/Node.js` keep the
    vocabulary the catalog anchors on; dotted product names in `_PROMPT_DOTTED_PRODUCT_NAMES`
    (`Node.js`, `Next.js`, ...) are not file extensions. Other dotted names such as `Site.com` and
    `Force.com` in a slashed token are treated as file names.
  - *Typed capability paths are dropped.* `why is lwc/heroBanner/heroBanner.js not rendering`
    loses `lwc/...` as evidence on every automatic surface, including the bypass gate, which reads
    the already-filtered recorded text; only explicit discovery recovers it. The accepted cost: the
    gate may warn about a different plugin than the one the path implies. Keeping the leading
    directory as a capability hint would add a token-rewrite transform with its own false
    positives, so the precise, auditable rule wins: a path the user names is a thing, not an ask.
- **A generic word shared with the corpus cannot carry a match alone.** A plugin declares
  `metadata.match.anchorTerms` (marketplace.json) when its capability vocabulary overlaps a
  domain-sounding-but-generic word used elsewhere in the corpus. For example, before package
  post-install routing moved out of `dx-org-lifecycle`, its "package post install" phrase made
  `install` look like org-lifecycle evidence when it was not. The scorer's `require_anchor_terms`
  option (default `True`) drops such a candidate unless the prompt's matched terms include at least
  one of its own anchor terms —
  closing the failure class where "install agentforce-adlc plugin" high-confidence-matched the
  wrong plugin on the word "install" alone. This gate exists to stop a generic-word coincidence
  from **interrupting** the user unprompted, so — mirroring the high/medium band split — only the
  two proactive surfaces (`UserPromptSubmit`, SessionStart) pass `require_anchor_terms=True`;
  explicit discovery and the reactive bypass gate pass `False` and, by default, see plain high+medium matches,
  because the user's own act of invoking those surfaces is itself the missing evidence. A plugin's
  anchor set can therefore still be too narrow to cover every phrase a user would reasonably type
  into explicit discovery — that is an authoring quality issue to fix by broadening the anchor set,
  not a gap in this surface split. When an anchor term is *itself* an everyday word — test-drive's
  `drive` is a verb in "drive adoption/revenue/traffic" — the anchor gate alone still leaks, because
  the term matches the corpus on its own. Score thresholds cannot separate the leaks from the
  must-keeps (their ranges overlap); the real signal is a *bigram* like "test drive". Such a term
  therefore declares `metadata.match.anchorCompanions` (`{"drive": ["test"]}`): an anchor with
  companions counts as a hit only when at least one companion token is also present in the prompt, so
  bare "drive" is gated while "test drive" fires. This is scorer-general (any anchor may declare
  companions), and a companion-less anchor on the same plugin (`walkthrough`, `rehearsable`) still
  fires on its own. Author anchor terms by hand, checked against that plugin's own
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
- **Successful command-owned preference mutations emit one bounded telemetry event.** After (and
  only after) `/salesforce-development:plugin-recommendations` successfully writes or clears the
  saved override, it emits `plugin_recommendation_configured` with only a closed action/level pair:
  `disable::off`, `reset::default`, `set::low`, `set::standard`, `set::high`, or `set::custom`.
  Numeric thresholds, raw arguments, previous/effective settings, paths, prompts, and environment
  values never enter telemetry. Native `userConfig` and environment changes remain unobserved.
- **One session proposal ledger.** SessionStart, prompt, discovery, and bypass consumers reconcile
  against the same per-session plugin marker. The first surface owns telemetry and incidental
  paint; later prompt/tool surfaces must not deny, repaint, or count it again. Explicit discovery
  queries may still render because they are solicited. SessionStart project hints run only for
  known fresh-context sources (`startup`, `clear`, and legacy blank payloads); `/clear` deliberately
  repaints because the prior conversation is absent. `resume`, `compact`, and unknown future sources
  return before project scanning or matching: they neither render nor touch proposal/telemetry
  state. This matters most for proactive paths: once the user has already seen an install choice
  at startup or before the model answers, a lifecycle replay, next prompt, or tool gate must not
  turn that same choice into another interruption.
- **The ledger records why a proposal fired, in curated vocabulary only.** Beside `confidence` and
  `surface`, an entry may carry `match_keywords`: the sorted, comma-joined tokens of the match
  evidence that belong to that plugin's own curated `keywords`/`anchorTerms`, capped at 8 tokens and
  120 characters. `plugin_catalog.curated_match_terms` computes that subset, so the privacy step
  lives next to the scorer and `sf_context` only forwards it; `anchorCompanions` qualify an anchor
  rather than name a capability and are deliberately not part of it. A `session-start` entry may
  also carry `match_signal`, one fixed file-signal code (`lwc`, `react`, `agentforce`, `cms`) —
  never a file name, path, or the human signal label, which stays paint/model copy. Both keys are
  written once, with the first recorded surface: a repeat match updates `confidence` but never
  overwrites them, a decline carries them forward beside `decision: "declined"`, and the later
  `plugin_loaded`/`plugin_installed`/`plugin_suggestion_declined` events report them from the entry.
  They are additive and best-effort: omitted when there was no curated evidence (the deterministic
  test-drive writers, or a match carried only by description/example-prompt words), and shed from
  every entry first if the encoded marker would exceed its 8192-byte cap, so they never cost the
  first-occurrence ledger itself. `sf_telemetry` keeps its own copy of the signal codes, so a new
  `_PLUGIN_SIGNALS` code must be added there too or capture drops it. The analytics contract is in
  [`dynamic-plugins-funnel.md`](./dynamic-plugins-funnel.md).

## Unicode matching and denial audit (W-24445750)

Catalog tokenization applies NFC, case folding, then NFC again to both query and catalog text.
Words retain Unicode alphanumeric characters and attached combining marks; punctuation and
underscores separate words. Accents are neither deleted nor transliterated, and an ASCII product
fragment inside a larger Unicode word is not a token. This is lexical consistency only, not
translation, multilingual semantic understanding, or Japanese word segmentation.

`_plugin_catalog_match` abstains on non-ASCII letters/combining marks before scoring or ledger
writes on every surface. Text/emoji presentation selectors U+FE0E/U+FE0F are exempt:
English requests containing `✔️` or `❤️` remain eligible. Tokenization also ignores these
selectors, including those attached directly to letters, so they do not change word identity. ZWJ is formatting (category Cf) and
already does not count as a letter or combining mark. Other marks, accented letters, fullwidth
Latin, and mixed-script words still cause abstention. Explicit discovery also abstains, so it
cannot seed a later denial from incomplete evidence. SessionStart still uses its fixed English project-signal queries. Prompt-time
matching, existing-flow promotion, and the outside-project bridge use eligible intent; non-English
text is still stored and the Salesforce/CRM cue can still read filtered user words.

The only catalog-to-tool-denial path is `cmd_skills_first_advisory`: no installed owner → captured prompt
plus full-prompt eligibility marker → `_plugin_catalog_match(..., surface="bypass-gate")` →
first-occurrence high match → `emit(..., decision="deny")`. Medium/repeated matches advise.
Other catalog consumers (SessionStart hints, UserPromptSubmit, flow promotion, explicit
`cmd_plugin_match`) render/open proposals, never deny a tool call. The shared matcher guard and
the pre-truncation marker close both direct and ledger-mediated multilingual paths. Installed
skill ownership, dispatch suppression, and enforced installed-skill gates are unchanged.
Abstention may miss useful suggestions, including mixed English/product requests or an English
request with a non-ASCII filename/URL (eligibility precedes incidental-token removal); it does not
assert that no plugin can help. Translation and multilingual catalog expansion remain out of scope.

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
matcher copy), and the generator fails fast if that pairing is missing. Every entry's `source` is a
relative-path string pointing at the plugin's own directory in this repo; the catalog generator
rejects any other shape.

**What may be recorded about a match.** The same boundary decides what the proposal ledger and
telemetry may record about *why* a proposal fired. The scorer's `matched_terms` are query ∩
document tokens, and the query is normally the user's own prompt or discovery text, so they are
fragments of what the user typed; they are never persisted or sent verbatim. Only their
intersection with the plugin's curated `keywords`/`anchorTerms` is, so every recorded token is
first-party, owner-approved, already-public vocabulary, and a word the catalog does not curate can
never surface. The SessionStart file scan scores a fixed per-signal query and records a fixed
signal code, never what file matched. `sf_telemetry` does not trust its in-process caller: at
capture and again at egress it keeps only tokens of *that* plugin's vocabulary re-derived from the
shipped `catalog/plugins.json`, and only the fixed signal codes, only on `session-start`. The
residual disclosure — which curated words a prompt contained — is bounded by that finite
dictionary; whether the first-run telemetry notice must say so is an open copy review.

## Accepted-proposal install mechanic

The workflow treats the user's explicit acceptance of a recommendation as the authorization to
install a plugin from a trusted source. UserPromptSubmit pins that exact
candidate and routes one fixed command: `plugin-install <name> --accept-proposed`. The runtime
independently requires a valid same-session proposal, the same selected plugin in `selected` state,
and a **trusted install target** (`_plugin_install_is_trusted_source` — the exact local
`./plugins/builder/<name>` source; see the trust predicate below). If all three checks hold, it installs in
that call; no dry run, nonce, second prose confirmation, or ordinary Bash approval is added. The
PreToolUse hook can return `allow` only for that complete standalone command and those same checks.
Appending shell syntax, changing the name, omitting the selected workflow, or targeting an
untrusted source falls outside the allowance. Claude Code's user, project, and managed ask/deny
policy remains authoritative over hook output.

Three ways a user acceptance reaches `selected` — all funnel through the same
`--accept-proposed` command and the same trust split, so none can bypass the nonce for an untrusted
source: (1) a **typed** bare/named affirmative in the live flow; (2) a **late bare affirmative**,
which re-arms the single candidate a topic change just cleared from the live flow — but *only* on
the very next prompt, via a short-lived, one-shot marker (`_PLUGIN_LAST_OFFER_DIR`,
`_save_plugin_last_offer`/`_load_plugin_last_offer`) written at the moment the flow is cleared, not
the durable, un-timestamped proposal ledger (an earlier design let any surviving ledger entry
re-arm at any later, unrelated "yes" — a PR-1696 review finding, since fixed). It never re-arms a
proposal the user declined (a declined flow is terminal, not `"recommended"`, so it is never
snapshotted), and never snapshots a still-undecided *multi*-candidate recommendation (so a bare
"yes" can never auto-pick among several); and (3) an **AskUserQuestion selection** whose chosen
option names exactly one open proposal, bridged by a PostToolUse `AskUserQuestion` hook
(`cmd_post_ask_question`). The bridge only advances the flow — it never installs, mints a nonce, or
applies trust — so a generic "Yes"/"No" option (which names no plugin) is a no-op and a structured
answer can never auto-install. The bridge reads the answer text via
`_ask_question_selected_texts`, which must specifically walk the real result's `answers` field (a
mapping from arbitrary, model-authored question text to the answer string, multi-select
comma-joined) rather than only descending through a fixed allowlist of generic field names — the
mapping's own keys are never one of those names, so a plain "descend only when the key matches"
walk can never reach it (also a PR-1696 review finding, since fixed).

An accepted source that is not the exact reviewed `./plugins/builder/<name>` path does
**not** inherit that fast path. The first
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
or through `awaiting-confirmation` for an untrusted/self-directed source, and finally to `installed`
or `declined`. A SessionStart batch can hold several candidates, but a generic reply can select one
only when exactly one candidate remains unambiguous; an explicitly named valid proposal can always
select itself. When a generic acceptance arrives against more than one open proposal, the runtime
neither picks one nor falls silent: it returns a disambiguation instruction that names the open
candidates and asks the user to name the single plugin they mean (a named acceptance then selects
itself). This preserves the direct-leaf "no best pick" rule while keeping a terse `yes` from
dead-ending in a bare missing-selection refusal that a model would otherwise be tempted to retry. The marker contains only plugin names, state, and one boolean stating whether the
recommendation interrupted a concrete task. Marketplace instructions and the user's prompt/task
text are never persisted — not in this marker, and not in the proposal ledger, whose only match
evidence is curated catalog tokens and a fixed signal code (see the security boundary above).

If SessionStart or an explicit discovery query opened a recommendation-only flow and the user then
submits an explicit action request matching one of those candidates, UserPromptSubmit promotes it
to a task-backed flow and surfaces it for the task. This promotion intentionally bypasses only the
proposal ledger's first-occurrence display deduplication; it does not bypass source classification
or the same-session selected-proposal checks.

UserPromptSubmit resolves that workflow before any catalog scoring. A terse reply such as `OK`,
`Go`, or `ok install it` can therefore accept the sole/selected plugin without rescoring the prompt.
A trusted marketplace entry installs from that acceptance; an untrusted entry writes a separate
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
install, and revalidates the source-bound nonce when confirmation is required.

## Trust posture

The catalog no longer stores byte-level pins or an explicit trust flag, and every entry is local:
the catalog generator rejects any `source` that is not a non-empty relative-path string (see
`plugin_catalog.py`'s `build_catalog`/`_validate_catalog`). A plugin's assurance level is still
derived from the exact shape of its verbatim marketplace `source`, but the only distinction left is
whether that string is the one reviewed path or not:

- Only the **exact string** `./plugins/builder/<name>` is eligible for the accepted-proposal fast
  path. It identifies the same named plugin in the reviewed monorepo from which the registry was
  built. A merely relative string, mismatched directory, normalized/traversal variant, or future
  source form does not qualify.
- Anything else — a mismatched path, a local entry outside `plugins/builder/` (e.g. an opted-in
  `./plugins/internal/*` plugin, tracked separately as the W-24078663 gap), or a hypothetical future
  mutable source form — is not byte-verified against a known-good identity, so the confirmation flow
  surfaces this as an explicit trust warning rather than imply a guarantee it cannot deliver. The
  trust-warning guard in `_render_plugin_install_dry_run` is shape-based
  (`_plugin_install_is_same_marketplace`) — trust is decided once, at the install fork, and not
  duplicated in the display path.

There is no support in this codebase for installing a plugin from outside this repo (no
externally-hosted/URL source, no per-entry marketplace routing, no curated allowlist of trusted
external identities). If that capability is reintroduced later, do not reintroduce a build-time tree
hash of an external repo as a substitute for review: it would break the build's offline hermeticity
and would only pin the wrong moment.

### Which sources may skip the nonce (the trust predicate)

`_plugin_install_is_trusted_source(name, entry)` is the single predicate that decides whether a
source may be accepted with looser confirmation (the accepted-proposal fast path, a late bare
affirmative, or an AskUserQuestion selection — see below). It grants trust on exactly one ground,
**explicit**, never inferred from source shape alone: the exact local source
`./plugins/builder/<name>` (`_plugin_install_is_same_marketplace`). Everything else stays on the
nonce + trust-warning path.

### Optional anchor enforcement on all surfaces

`metadata.match.enforceAnchorsOnAllSurfaces: true` retains the existing
`anchorTerms`/`anchorCompanions` gate on explicit discovery and the reactive bypass
as well as proactive surfaces. This is a deliberate precision-over-recall choice
for entries whose generic vocabulary produces unrelated solicited matches.
The flag requires nonempty `anchorTerms`; build and runtime loading both validate
an actual boolean. Omitted or false preserves the existing anchor bypass.

All companions are checked against raw lowercase prompt tokens, including
`salesforce`, which is removed from BM25 scoring. This rule is independent of the
all-surface flag: the flag controls only where the anchor gate applies. Existing
companion sets without stop words or one-letter tokens keep the same behavior.
Anchors still need to be among the scored matched terms. Each anchor qualifies
with any one declared companion, anywhere in the prompt; punctuation separates
words, and no adjacency, phrase matching or multi-word AND groups are implied.

This consolidates capability qualification into one anchor vocabulary. It replaces
the proposed `requiredEvidence` phrase groups after Omni and Education comparisons
showed that all-surface anchors plus raw companions preserve the existing discovery
regressions. Scores, confidence thresholds, scoring corpus, installation policy,
and task-intent classification remain unchanged. Authors must test supported tasks
and unrelated overlaps through all four consumers before opting in.

Omni matching favors supported domain context over generic telephony recall.
Capacity requires `omni`, `agent` or `agents`: generic queue routing plus agent
capacity is accepted as capability evidence, while storage/API capacity is not.
Work sharing uses `sharing` with
`work`. The generic `voice` anchor is omitted: Salesforce/Omni routing and
`VoiceCall` routing remain covered, while bare "Route voice calls", generic
Twilio routing and Amazon Connect provisioning do not recommend this plugin.
No vendor exclusions or additional matching fields implement that boundary.

Education companions require workflow evidence rather than an ordinary calendar or
hierarchy reference. `academic` accepts years, terms, sessions or registration,
not `calendar` alone; `institutional` requires Education or a specific Education
object. `hierarchy` accepts multi-campus wording or Education/object context,
not `campus` alone. This preserves multi-campus setup while excluding field-service
territories and institutional knowledge-article hierarchies. A `student` anchor
with `enrollment` covers the curated recruitment request. Bare academic-calendar
requests without workflow qualifiers deliberately remain quiet. Shared thresholds
and the existing all-surface anchor contract remain unchanged.
