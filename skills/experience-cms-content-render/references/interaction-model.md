# Interaction model — ask with options, and where the session ends

This skill is **interactive**. At every decision the prompt leaves open, ASK the
user with an **option-select** question (the `AskUserQuestion` tool) instead of
free-text: one decision per question, a short header, 2–4 labeled options, and
wait for the answer. Never guess past an unanswered required decision — it HALTs.

Two answers are **terminal**: they END the session with no scaffolding. They are called out below and in `SKILL.md` (*HALT behaviour*) and `references/failure-modes.md`.

## Bypass mode (non-interactive / automation)

When the prompt explicitly asks to bypass the interaction model — e.g. "bypass the
interaction model", "non-interactive", "don't ask", "proceed/yes to all prompts",
"auto-proceed" — do **not** call `AskUserQuestion` at all. Treat every would-be
question as answered with the **affirmative / recommended** intent ("proceed/yes")
and continue. This is for automation/eval where nothing can reply to a prompt.

Per-decision defaults in bypass mode (the Recommended option, or the obvious value):

| Decision | Bypass default |
|----------|----------------|
| Framework — ambiguous | The framework the prompt names; if truly none, HALT (no safe default). |
| Run Init? | **Yes, scaffold it** (proceed — the affirmative). |
| Complete a partial runtime? (drift) | **Yes, write the missing files.** |
| Content type — unnamed | The type the prompt states or most strongly implies. |
| Media alt text — foreign `url` image/document, none from hand-off | Register with `altText: ''` (image → decorative) / no `title` (document → "Download"). Bypass ships the a11y fallback rather than HALT — this is not a safe-default-less stop. |
| Channel ID — unresolved for a contentKey | **No safe default — HALT.** Bypass never invents a channel; write only a catalog/prompt-provided one, else HALT (like unnamed in-place placement). |
| Channel conflict — prompt channel differs from catalog | **Keep the catalog channel** (the Recommended option): leave `public/content-metadata.json` unchanged, do NOT overwrite it with the prompt channel. The catalog is primary. |
| Render target | **Dedicated detail page/route.** |
| Group render target | **A detail page for each item.** |
| Candidate uiBundle | The single scaffoldable/named bundle. |

Bypass changes ONLY the answer source (recommended option instead of a user reply)
— it makes NO pipeline-logic change. It does **not** suppress stops that are not
questions: a genuine **zero-content** search result still ends the session (there is
nothing to render), and any true HALT with no safe default still stops — e.g. an
**in-place** render with no placement named anywhere in the prompt (bypass defaults
to a detail page, so this only bites if the prompt forces in-place without a target),
a candidate-bundle choice that can't be resolved to one bundle, or a **`CmsRef` whose
channel is unresolvable** (no catalog, no prompt-provided channelId) — bypass never
invents a channel, so this HALTs.

## How to ask

- **One decision per question.** Short `header` chip (≤12 chars); 2–4 options.
- **Recommended option FIRST**, its label suffixed " (Recommended)".
- Each option carries a one-line description of what happens if chosen.
- **Free-text only for open answers** — a component/region name, a URL, a slug.
  There the option list is a fallback; let the user type the value ("Other").
- After a **terminal** option (declined Init, zero search results), END the turn.
  Do not scaffold, do not proceed, do not re-ask in a loop.

## Decision points

### Framework — ambiguous
Both `react` and `@angular/core` are dependencies (unknown/neither → HALT, not a
supported app; do not ask).
- Question: "Which framework should I target for the CMS renderer?"
- Header: `Framework`
- Options: **React** — use the `assets/react/*` templates · **Angular** — use the
  `assets/angular/*` templates.

### Run Init? — runtime not scaffolded  ·  ⛔ TERMINAL on "No"
All foundation files are missing (see *Init vs Embed detection*).
- Question: "The CMS runtime isn't scaffolded in this uiBundle yet. Scaffold it now (Init)?"
- Header: `Init`
- Options:
  - **Yes, scaffold it (Recommended)** — run `npm i` for the toolkit and write the
    foundation runtime once, then continue to Embed.
  - **No — stop here; the skill will HALT and the session will end** — nothing is
    installed or written; the skill cannot Embed without the runtime.
- On **No**: state that Init was declined, so the skill HALTS and the **session
  ends**. Do NOT scaffold, install, or partially write anything. End the turn.

### Complete a partial runtime? — drift
Some foundation files present, some missing (never Embed onto a partial runtime).
- Question: "The CMS runtime is partially scaffolded (present: {present}; missing:
  {missing}). Complete the {N} missing foundation file(s) from the templates?"
- Header: `Drift`
- Options:
  - **Yes, write the missing files (Recommended)** — write ONLY the {N} missing
    files verbatim from `assets/…`; never touch the present ones. Then re-check.
  - **No — stop** — leave the tree as-is and HALT; the user restores or removes the
    partial set.

### Content type — unnamed item
The item's `fqn` is unknown (URL pasted, `contentKey` given, or search returned an empty `fqn`). Ask ONCE.
- Question: "What content type is this item?"
- Header: `Type`
- Options: **News** (`sfdc_cms__news`) · **Blog** · **Announcement** · plus let the
  user type another type name (open answer) when it isn't one of these.

### Media alt text — foreign `url` image/document, none from the hand-off
Only for a **foreign `url` media ref** of type `image` or `document` when the search
hand-off supplied no `altText`/`title` (the direct-URL path has no fetched body to read
them from — SKILL.md step 3). `audio`/`video` never ask (controls + optional aria-label).
Ask ONCE, open answer.
- Question: "What alt text describes '{title}'? (Leave blank if it's decorative.)" — for a
  document instead: "What label should the download link for '{title}' show?"
- Header: `Alt text`
- Open answer — the user types the alt text / link label; the skill sets it as `altText`
  (image) or `title` (document) on the `CmsExternalRef`. Blank is a valid answer for an
  image (decorative → `alt=''`, WCAG 1.1.1). In **bypass** mode do NOT HALT: register with
  the a11y fallback (`altText: ''` / no `title`) and continue.

### Channel ID — unresolved for a contentKey
A `CmsRef` (contentKey) needs a channel and none was found in `public/content-metadata.json`
or provided with the prompt (channel resolution, SKILL.md step 3). Ask ONCE, open answer.
- Question: "Which channel serves '{title}'? Paste the channelId (e.g. `0apSG0000000…`)."
- Header: `Channel`
- Open answer — the user pastes the channelId; the skill writes it to
  `public/content-metadata.json`. No safe default: no answer → HALT (never invent or
  placeholder a channel). In **bypass** mode there is NO auto-fill — an unresolved
  channel HALTs like an unnamed in-place placement.

### Channel conflict — prompt channel differs from the catalog
A `channelId` came with the prompt/identity, but `public/content-metadata.json` already
holds a DIFFERENT non-empty `channelId` (channel resolution, SKILL.md step 3). One
channel serves EVERY contentKey ref in the app, so overwriting repoints them all — never
silently. Ask ONCE; both concrete channels are known, so this is option-select, not open.
- Question: "'{title}' names channel `{promptChannel}`, but the catalog already uses
  `{catalogChannel}`. Which channel is correct?"
- Header: `Channel`
- Options:
  - **Keep the catalog channel `{catalogChannel}` (Recommended)** — leave
    `public/content-metadata.json` UNCHANGED (no write); register the ref and proceed. The
    catalog is primary and cross-org-safe, and any other refs already resolve through it.
  - **Use the prompt channel `{promptChannel}`** — overwrite ONLY the `channelId` in
    `public/content-metadata.json` (preserve the existing `contents` array); then register
    the ref and proceed. This repoints EVERY contentKey ref in the app to `{promptChannel}`.
- Overwrite the catalog channel only on the explicit **Use the prompt channel** answer.
  Same channel, or an empty/absent catalog, is NO conflict — use/write per *Channel ID*.

### Render target — neither placement nor page stated
Only when the prompt names no route AND no in-place placement (step 4).
- Question: "How should I render '{title}'?"
- Header: `Render as`
- Options:
  - **Dedicated detail page/route** — generate a page under `src/pages/<type>/` and
    add its route.
  - **In place in an existing view** — embed the renderer at a location you name.
- On **In place**, follow up for the location (open answer): "Where should '{title}'
  render? Name a component, page, or region." An unanswered location HALTs — never
  guess a placement.

### Group render target — N items, same type
Only when neither a list/grid nor per-page layout is stated (step 4, *Groups*).
- Question: "Render the {N} items as separate detail pages, or together on one page?"
- Header: `Group as`
- Options:
  - **A detail page for each item (Recommended)** — loop the Detail Page branch, one
    page + slug per item.
  - **One list/grid on a single page** — generate the list wrapper, place one node.

### Candidate uiBundle — more than one qualifies
Multiple bundles under `force-app/main/default/uiBundles/` look scaffolded/targetable and the prompt didn't name one.
- Question: "Which uiBundle should I render into?"
- Header: `Bundle`
- Options: one per candidate bundle name (label = bundle dir); if >4, list the most
  likely and allow an open answer.

## Terminal stops (session ends — no scaffolding)

| Stop | When | What to say and do |
|------|------|--------------------|
| **Init declined** | User picks "No" at the *Run Init?* question | State Init was declined → the skill HALTS and the session ends. Write nothing; end the turn. |
| **Zero search content** | experience-search-coordinate returns ZERO content for the phrase (search succeeded, found nothing) | The item isn't authored in this uiBundle space yet. STOP the session and tell the user to generate the content there first — author + publish it (e.g. via `experience-cms-content-generate` / `experience-cms-content-type-generate`) — then re-run this skill. Do NOT guess an identity or scaffold. |

**Zero content vs. search failure** — distinct. ZERO content (nothing exists yet)
ends the session with an *author-the-content-first* instruction. A **cancelled,
errored, or unavailable** search is a recoverable HALT: ask the user to paste the
item's public delivery URL (`unauthenticatedUrl`) OR its `contentKey` (plus
`channelId` / content type), and resume once they do — see `SKILL.md` step 1.
