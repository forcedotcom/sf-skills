# Channel Scope Resolution — Full Reference

## Step 1 points 1-3 — discovering channel scope

1. **Explicit `channelId` given** (e.g. "search within channel 0apXX0000001001", or passed as an input to this skill) — use it directly as the scoped channel and skip straight to the scope rule in `SKILL.md` Step 1. Do not run uiBundle discovery in this case.
2. **Named uiBundle/app, no `channelId`** (e.g. "search in this uiBundle" or "search in the Homepage app") — locate that named uiBundle (e.g. `<sfdx-source>/uiBundles/<named-uiBundle>/public/content-metadata.json`) and read its `channelId` if present:
   - **Found, with a `channelId`** — use it as the scoped channel, skip to the scope rule.
   - **Not found, or found but no `channelId` present** — fall through to point 3 and scan every uiBundle as if the user hadn't named one.
3. **Otherwise, discover from uiBundles by scanning the local project — never gate this on server-side deployment status:**
   - **Scan the project directly** for every `uiBundles/*/public/content-metadata.json` file using whichever directory-listing/glob capability your environment exposes. Do NOT run `sf org list metadata --metadata-type UIBundle` first and use its result to gate which bundles you check — a uiBundle's CMS channel can exist even when the uiBundle itself is not (yet, or ever) deployed to the currently-targeted org, so a server-side deployed-bundle list would wrongly exclude it.
   - **For each `content-metadata.json` found**, read it and collect the `channelId` if present — no server-side field or API links a UIBundle to a CMS channel, so this local file is the only source for `channelId`.
   - **Zero uiBundles with a `channelId`** — scope is public channels only.
   - **Exactly one** — scope is public channels **plus** that `channelId`.
   - **More than one** — call `ask_followup_question` with the question `"Multiple components have their own CMS channel. Which one should I search within (in addition to public channels)?"` and one **option** per uiBundle in the tool's `options` array — never as numbered lines inside the question text. Scope is public channels plus the selected `channelId`.
