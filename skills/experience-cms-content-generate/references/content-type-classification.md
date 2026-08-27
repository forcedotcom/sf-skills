# Step 2 — content-type classification buckets (full detail)

Step 2 classifies Step 1's captured content-type reference into one of four buckets. Buckets 1/2/3 are fast-paths (skip the sibling); Bucket 4 delegates.

## Bucket 1 — Exact FQN

Token matches `^[a-zA-Z_][a-zA-Z0-9_]*__[A-Za-z][A-Za-z0-9_]*$` exactly (e.g. `c__BlogPost`, `sfdc_cms__news`, `my_ns__CustomerStory`). Capture `contentTypeFqn = "<user's token>"` and go directly to Step 3. **Silent — no chat text, no confirmation prompt.**

## Bucket 2 — High-confidence auto-correctable near-miss

Token is a clear FQN with a mechanical typo where the correction is unambiguous — exactly one reasonable interpretation. Detection: **single-underscore separator between a recognizable namespace and a developer name.** Recognizable namespaces = `c` (default custom), `sfdc_cms` (standard CMS), or any namespace-prefix pattern matching `^[a-z][a-z0-9_]{0,14}$` where the segment before the single underscore looks like a namespace identifier and the segment after starts with an alphabetic character. Correction: replace the single underscore between namespace and developer name with `__`. Qualifies: `c_news`, `sfdc_cms_news`, `myns_BlogPost`. Does NOT qualify: `blog_post` (both segments look like developer-name words), `news_article_topic` (three-segment, no confident split).

Auto-correct silently, then **announce in chat text**: `You provided \`<original>\` — this isn't a valid FQN format. Proceeding with \`<corrected>\` as the content type. If this isn't right, cancel and re-run with the correct FQN.` Then go directly to Step 3 with `contentTypeFqn = "<corrected>"`. **Do NOT dispatch an `ask_user_tool` prompt for Bucket 2** — single-answer mechanical correction; asking wastes a turn.

## Bucket 3 — Medium/low-confidence FQN-ish token

Token looks like a naming attempt but has more than one reasonable interpretation. Falls into Bucket 3 if any of the following is true AND it is not already Bucket 1 or 2:

- **Bare developer name with no namespace** (e.g. `BlogPost`, `News`, `PressRelease`) — could be `c__BlogPost` or `<managed>__BlogPost`. Default proposal: prepend `c__`.
- **Unknown namespace with a single-underscore separator** where the left segment doesn't obviously match a namespace pattern (e.g. `foobar_thing`). Propose the double-underscore version; user confirms.

**Case does NOT trigger Bucket 3.** Salesforce API names — including ContentTypeBundle FQNs — are case-insensitive at lookup, so `c__BlogPost`, `C__blogpost`, `c__BLOGPOST` all resolve to the same record. Any token matching the Bucket 1 regex is Bucket 1 — do NOT propose a "case correction" via Bucket 3 (it would burn an `ask_user_tool` turn for zero functional effect).

For Bucket 3, dispatch the **Step 2 FQN-correction prompt** from `assets/questions.md` (`Yes, use <corrected>` / `Let me provide a different FQN` / `Cancel`). Route:

- `Yes, use <corrected>` → capture `contentTypeFqn = "<corrected>"`, go to Step 3.
- `Let me provide a different FQN` → dispatch the follow-up "provide FQN" prompt from `assets/questions.md`. On the returned string, restart Step 2 classification from Bucket 1 (treat as a fresh Step 1 capture).
- `Cancel` → **STOP silently.** Print `Session ended.` and exit.

## Invalid-FQN gate — a token that MEANT to be an FQN but is malformed

Before falling to Bucket 4, catch a token the user clearly intended as an FQN (contains `__`, or a namespace-style `<seg>__<seg>` shape) but which does NOT match the Bucket 1 regex and is NOT a Bucket 2 single-underscore near-miss — e.g. `c__` (empty developer name), `__BlogPost` (empty namespace), `c__Blog Post` (space in name), `c__123` (developer name starts with a digit), `c____Post` (doubled separator). These are broken FQNs, not natural-language phrases — do NOT silently delegate them to the sibling as free text (the sibling would treat the garbage as a search phrase). Instead dispatch the **Step 2 FQN-correction prompt** from `assets/questions.md`: show the invalid token, offer `Let me provide a different FQN` and `Cancel` (omit a "use `<corrected>`" option when there is no confident single correction). On `Let me provide a different FQN`, dispatch the follow-up "provide FQN" prompt and restart Step 2 from Bucket 1 on the new string. A token with NO FQN punctuation at all (`blog post`, `news article`) is genuine natural language → Bucket 4, not this gate.

## Bucket 4 — Natural-language type name or no token

Token is a free-text phrase (`"blog post"`, `"news article"`, `"customer story"`) or Step 1 captured no content-type reference at all. Delegate to `experience-cms-content-type-generate` — proceed to Step 2a.

## Fast-path invariants (Buckets 1, 2, 3)

Once a fast-path bucket captured the FQN, do NOT: verify it exists in the org (the `INVALID_TYPE` response at Step 5 IS the verification), delegate to the sibling (the FQN IS the answer), scan `contentTypes/` locally, dispatch `metadata-grounding.search_metadata`, run `sf project retrieve start`, or read `schema.json` from disk. If the FQN doesn't resolve, `create_cms_content` fails with `INVALID_TYPE` — see `references/error-recovery.md`.

## Multi-type gate (Step 1 — fires BEFORE classification)

A single prompt sometimes names **two or more distinct content TYPES** (e.g. `Create content covering the grooming packages and the service area coverage` → a grooming-package type AND a service-area type). This skill resolves **one content type per run** — the delegation contract passes ONE `intent` and consumes ONE `{status, fqn}`. Attempting to resolve two types in one run is sequencing drift (the sibling emits one outcome; a second in-turn resolution corrupts its state machine). So when the prompt spans multiple types, ask the user to pick ONE before Step 2.

**TRIGGER (ask) — the prompt maps to ≥2 distinct content types.** Judge by content domain, not word count. Distinct domains that would each be their own `ContentTypeBundle`:

- `grooming packages` **and** `service area coverage` → grooming-service type + service-area type → **ASK**
- `a product page and an FAQ` → product type + FAQ type → **ASK**
- `event details plus a press release` → event type + press-release type → **ASK**

**DO NOT trigger (stay silent — existing paths) — one type, no matter the topic/quantity count:**

- `5 blog posts about our launch` → ONE type (blog), bulk of 5 records → silent, existing bulk path
- `a blog about cheese and wine` → ONE type (blog), two subjects in one record/topic set → silent
- `news articles on X, Y, and Z` → ONE type (news), three topics → silent (bulk topic generation owns this)
- any single-domain prompt → silent
- FQN provided (Buckets 1/2/3) → the fast-path already fixed the type; the gate does NOT run

**The distinction:** multiple *content types* → ASK; multiple *topics/records of one type* → silent (bulk owns it). If unsure whether two domains are really different types, prefer to ASK — a false ask costs one extra turn; a false silence resurfaces the two-types-in-one-run drift.

**On the pick:** carry ONLY the chosen domain forward as the `intent` into Step 2 (all downstream steps — classification, delegation, create — see exactly one domain, so every existing invariant holds unchanged). The dropped domain(s) are NOT lost — Step 10's post-publish "Create more content" lets the user create the next type in a fresh run. Question template (fixed copy, verbatim every run) → `assets/questions.md` § Step 1.

**This is the ONLY exception to Step 1's "never ask" rule.** It does NOT reopen the general clarifying-questions regression: it fires solely on the objective ≥2-distinct-types condition, never for goal refinement, mode, body details, "do you have a type in mind?", or quantity. If you are asking anything other than "which of these N distinct types," that is the Step 1 anti-pattern, not this gate.

## What the sibling owns (delegated path only)

When the fast-path does not apply, this skill hands the user's intent to `experience-cms-content-type-generate` and waits for exactly one of four terminal outcomes (`success` / `not_deployed` / `cancelled` / `error`). All of the following are the sibling's job:

- Local `contentTypes/` scan and `metadata-grounding` lookup
- The user-facing pick question when multiple candidates match
- Creating a new `ContentTypeBundle` when nothing matches, and asking to deploy it
- Constructing the namespace-prefixed FQN after a deploy
- Retrieve-and-reconcile against the org copy, drift resolution

## Drift-safety net (delegated path) — five signals that delegation is broken

The harness cannot enforce delegation between two markdown skills, so treat every one of these as a hard stop and route to Step 2b's `load failed` row instead of doing the sibling's work:

1. Constructing a `search_metadata` query for `ContentTypeBundle` yourself.
2. Running `find` / `ls` / `cat` (or `Read`) against `contentTypes/`, `schema.json`, or any local content-type-bundle file to answer "what FQN should I use?".
3. Running `sf project retrieve start` for `ContentTypeBundle` metadata.
4. Dispatching `create_cms_content` (Step 4+) without a sibling-emitted (or fast-path-captured) `contentTypeFqn` in hand. (Resolving the workspace via `get_or_create_cms_workspace_and_web_app_channel` BEFORE the FQN is expected on the delegation path — that ID is passed to the sibling — and is NOT drift.)
5. Dispatching `create_cms_content` with an FQN reconstructed from a folder name, a `schema.json` filename, or a local scan result.

If drift #1 has already happened despite this rule, then since the harness cannot enforce delegation, the query construction rules live in a single shared file so the wrong-skill outcome is at least a right query. Read `../experience-cms-content-type-generate/references/discovery-query-rules.md` before emitting any `search_metadata` call. Common bug queries this file exists to prevent: `"CMS content type bundle"`, `"content type bundle"`, `"<domain> content type"` — any query containing the words `content type`, `bundle`, or `CMS` is filler-only and has stripped out the intent.

**Do not** downgrade `not_deployed` to `success` because "the bundle is validated and the FQN is predictable." A local-only bundle is not in the org; `create_cms_content` returns `INVALID_TYPE` and the user sees a confusing error two turns later. Trust the sibling's status verbatim.
