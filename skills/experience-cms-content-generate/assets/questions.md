# `ask_user_tool` question templates

Every user question in the workflow MUST be dispatched via `ask_user_tool` (never printed as plain text). Copy-paste the template for the step you're on and fill in placeholders. Follow the two-part pattern from `references/ux-rules.md` when the question needs a list, table, or error detail — print structure in chat text FIRST, then call `ask_user_tool` with a single short question.

**Dispatch every `question` string VERBATIM — it is final copy, not a draft to reformat.** The `question` field renders as ONE plain paragraph: markdown is NOT interpreted, so `**bold**` prints the literal asterisks and a `-`/`1.` list collapses into run-on text. Do NOT expand a templated sentence into bullet lines, numbered lists, or bolded labels inside `question`. If you catch yourself turning `Provide the ID (Content Space IDs start with \`0Zu\`; Folder IDs start with \`9Pu\`)` into `- **Content Space ID** (0Zu…) - **Folder ID** (9Pu…)`, STOP — that reformatting IS the rendering bug users report. Any structure (tables, lists, bold) belongs ONLY in a chat-text Part 1 printed before the tool call, never in `question`.

## Step 0-U / Step 0-P — Identifier ask (no ID supplied)

**Shared by BOTH the UPDATE direct-entry (Step 0-U) and PUBLISH direct-entry (Step 0-P) gates.** Dispatch this the instant the gate stops for a name-only request (user named the content by title/subject with no ID and it is not in the session registry). This is the ONLY template for the identifier ask — do NOT hand-write your own sentence, do NOT split the accepted-ID list into `- **Content Key**…` bullets (that is the literal-asterisk render users report), and do NOT vary the answer set between update and publish. Dispatch the `question` string VERBATIM and use these exact answers every time:

```text
Tool: ask_user_tool
question: "Which record should I work with? Paste the content key (starts with `MC`), the Managed Content ID (starts with `20Y`), or the Variant ID (starts with `9Ps`)."
answers: ["Cancel"]
```

The user types/pastes the identifier as free text; the single `Cancel` option lets them abort. On `Cancel`, print `Session ended.` and stop. On a pasted identifier, resolve it per `references/identifier-resolution.md` (Step 0-U → Step 8c; Step 0-P → Step 9b). Same wording, same one-option answer set on both paths — that consistency is the point.

## Step 1 — Multi-type disambiguation (prompt spans ≥2 distinct content types)

**Dispatch ONLY when Step 1's multi-type gate fires** (the one prompt spans two or more distinct content TYPES — different content domains, NOT multiple topics/records of one type; detection rule + examples → `references/content-type-classification.md` § Multi-type gate). This is the one question Step 1 may raise. Dispatch the `question` string VERBATIM — it is fixed copy, identical every run; the only thing that varies is the answer set. Do NOT reword it, do NOT stuff the domain descriptions into `question`.

```text
Tool: ask_user_tool
question: "Your request covers more than one kind of content. I create one content type per run — which should I create now?"
answers: ["<domain 1>", "<domain 2>", ..., "Cancel"]
```

One answer per distinct content domain, labeled from the user's OWN words (e.g. `"Grooming packages"`, `"Service area coverage"`), plus a final `"Cancel"`. On a domain pick: carry ONLY that domain forward as `intent` into Step 2 (the other domains are dropped this run — Step 10's "Create more content" lets the user create the next one). On `Cancel`: print `Session ended.` and stop.

## Step 2 — Bucket 3 FQN correction proposal

**When the user's content-type token is FQN-ish but the correction has more than one reasonable interpretation** (bare name without namespace, case correction, unknown namespace). Print chat text FIRST describing the ambiguity if useful, then:

```text
Tool: ask_user_tool
question: "You provided `<original>` — this doesn't match a valid FQN format. Would you like to proceed with `<corrected>` as the content type?"
answers: ["Yes, use <corrected>", "Let me provide a different FQN", "Cancel"]
```

Replace `<original>` and `<corrected>` with the actual literal strings. Do NOT dispatch this prompt for Bucket 2 (high-confidence near-miss) — Bucket 2 announces the correction in chat text and proceeds without a confirmation turn.

**Follow-up when the user selects "Let me provide a different FQN":**

```text
Tool: ask_user_tool
question: "Please provide the content type FQN in `namespace__DeveloperName` format (e.g. `c__BlogPost`, `sfdc_cms__news`)."
```

On the returned string, restart Step 2 classification from Bucket 1 (treat the new input as a fresh capture).

## Step 3 — Workspace resolution (Question 1)

**When local UIBundles were found:**

```text
Tool: ask_user_tool
question: "Where should I create the content? Pick a local UIBundle (I'll resolve the space automatically) or provide an ID manually."
answers: ["<masterLabel1> (<developerName1>)", "<masterLabel2> (<developerName2>)", ..., "Provide a space or folder ID manually"]
```

One entry per discovered UIBundle formatted as `"<masterLabel> (<developerName>)"`, plus a final `"Provide a space or folder ID manually"` option.

**When no local UIBundles were found:**

```text
Tool: ask_user_tool
question: "Which content space or folder should I create the content in? Provide the ID (Content Space IDs start with `0Zu`; Folder IDs start with `9Pu`)."
answers: ["Cancel"]
```

The user types/pastes the ID as free text; the single `Cancel` option lets them abort. On `Cancel`, print `Session ended.` and stop (Principle 7).

**When the user picks "Provide a space or folder ID manually":**

```text
Tool: ask_user_tool
question: "Please enter the Content Space or Folder ID (Content Space IDs start with `0Zu`; Folder IDs start with `9Pu`)."
answers: ["Go back"]
```

**Do NOT invent placeholder tokens.** Emit the exact prefixes above (`0Zu`, `9Pu`) — do NOT fabricate patterns like `0pdXXX...` or `0apXXX...`. The screenshot regression showing `0pdXXXXXXXXXXXXX` / `0apXXXXXXXXXXXXX` was hallucinated ID prefixes that never appear in Salesforce content-space or folder IDs. When in doubt about a Salesforce ID prefix, do NOT guess — the two above are the only ones this skill supports.

If the user clicks "Go back", re-present the original Step 3 question with all UIBundle options.

**Invalid workspace ID — re-ask (format-gate fail OR server-confirmation fail).** Dispatch this the instant a manual ID fails validation: either it wasn't a 15/18-char `0Zu`/`9Pu` ID (Layer 1), or the first server call touching it returned invalid/not-found (Layer 2, incl. the sibling's `get_content_types_for_workspace` on the delegation path). This is the ONLY re-ask after a bad ID — it MUST state the ID was invalid (the neutral manual-ID prompt above does NOT; using it here is the reported "not even saying invalid" defect). Print the raw server error as chat text FIRST when Layer 2 failed, then dispatch VERBATIM, filling `<reason>`:

```text
Tool: ask_user_tool
question: "That ID wasn't valid — <reason>. Enter a Content Space ID (starts with `0Zu`) or Folder ID (starts with `9Pu`) — must be 15 or 18 characters."
answers: ["Cancel"]
```

`<reason>` is one of: `it wasn't a 15- or 18-character 0Zu/9Pu ID` (Layer 1 format-gate fail) OR the server error text verbatim (Layer 2 fail). On `Cancel`, print `Session ended.` and stop. Do NOT improvise an org picker or run `sf org list` (see `references/workspace-resolution.md`).

**When `get_or_create_cms_workspace_and_web_app_channel` fails for the selected UIBundle:**

```text
Tool: ask_user_tool
question: "Could not resolve space for this UIBundle. How would you like to proceed?"
answers: ["Retry", "Pick a different option", "Provide a space or folder ID manually"]
```

## Step 4.B.2 — Bulk topic approval

Print the topic list as formatted chat text FIRST (numbered markdown list with title + prompt), then call:

```text
Tool: ask_user_tool
question: "Do these topics look good?"
answers: ["Looks good, create them", "Let me adjust"]
```

Never stuff the topic list into the `question` field — it renders as an unreadable paragraph.

## Step 5a — Bulk pre-dispatch blanket approval

Print `Ready to create all <N> content items in your org. Proceed?` as chat text, then:

```text
Tool: ask_user_tool
question: "Create all <N> items now?"
answers: ["Yes, create all", "Cancel"]
```

**Do not leak dispatch mechanics.** The user asked for N content items — they see "N items." Do NOT mention parallel calls, `create_cms_content`, or the tool id in either the chat text or the `ask_user_tool` question. `"Approve all <N> create_cms_content calls?"` and `"Ready to dispatch 7 parallel create_cms_content calls to your org. Proceed?"` are both regressions — the user sees `create_cms_content` and the dispatch fan-out, both of which are internal implementation. Say `Create all 7 items now?` — NOT `Approve all 7 create_cms_content calls?`, NOT `Ready to dispatch 7 parallel create_cms_content calls`.

## Step 7 — Post-action loop

**Single content:**

```text
Tool: ask_user_tool
question: "What would you like to do next?"
answers: ["Edit content", "Publish content", "End session"]
```

**Bulk content:**

```text
Tool: ask_user_tool
question: "What would you like to do next?"
answers: ["Edit content", "Publish all", "Publish subset", "End session"]
```

**Publish subset — item selection:**

```text
Tool: ask_user_tool
question: "Which item numbers would you like to publish? (e.g. 1, 3, 5)"
```

## Step 8a — Edit scope

**Bulk edit scope:**

```text
Tool: ask_user_tool
question: "Which content would you like to edit?"
answers: ["All items", "Specific items (by number)", "Cancel"]
```

**Specific-items follow-up:**

```text
Tool: ask_user_tool
question: "Which item numbers would you like to edit? (e.g. 1, 3)"
```

## Step 8b — Edit instructions

Free-text, and **multiple properties can be changed in one message** — the server-side pipeline reads the whole instruction and applies every change against the existing body in a single `update_cms_content_variant` call. The user does not pick fields one at a time.

If the current content body was just displayed (Step 0-U direct-entry, or Step 6 after a prior edit), the user can name fields from it. Dispatch:

```text
Tool: ask_user_tool
question: "What would you like to change? Describe all edits in one message — you can update several fields at once (e.g. 'shorten the description, change the title to X, and add a note about Y')."
```

Do NOT loop field-by-field and do NOT restrict the user to a single property — one free-text instruction covering any number of properties is the expected input.

## Retry prompts

**Bulk create/update/publish partial failure — after printing failed items with prompts and errors as chat text:**

```text
Tool: ask_user_tool
question: "How would you like to proceed?"
answers: ["Retry failed items", "Skip and continue", "End session"]
```

**Total failure:**

```text
Tool: ask_user_tool
question: "How would you like to proceed?"
answers: ["Retry all", "End session"]
```

**Total failure — uniform error (Guard A from `references/error-recovery.md`).** Dispatch this variant ONLY when every one of the N failed calls returned the same error signature — the retry option is deliberately hidden because the failure is systemic. Print the uniform-error chat text from `error-recovery.md` FIRST, then:

```text
Tool: ask_user_tool
question: "How would you like to proceed?"
answers: ["End session"]
```

**Total failure — retry exhausted (Guard B from `references/error-recovery.md`).** Dispatch this variant ONLY on the 3rd+ consecutive total failure of the same bulk-operation instance — the retry option is deliberately hidden after two failed attempts. Print chat text FIRST: `<N> items have failed on <retryCount> consecutive attempts. Ending the session — resolve the underlying issue and re-run.` Then:

```text
Tool: ask_user_tool
question: "How would you like to proceed?"
answers: ["End session"]
```

## Step 10 — Post-publish

**`workspaceMethod=uibundle` — replace `<masterLabel>` and `<developerName>` with the actual values selected in Step 3:**

```text
Tool: ask_user_tool
question: "Content published! What would you like to do next?"
answers: ["Create more content", "Render it to the UI Bundle (<masterLabel> (<developerName>))", "End session"]
```

**`workspaceMethod=manual` — no UIBundle was selected in Step 3, so no `channelId` is available for the render handoff. Print this one-liner as chat text FIRST so the user knows why the Render option is missing, then dispatch the prompt:**

Chat text (Part 1):

```text
Rendering to a UI Bundle requires a UIBundle selection at the workspace step, which resolves the channel automatically. This run used a folder ID directly — to render the content, re-run this skill and pick a UIBundle at Step 3.
```

Prompt (Part 2):

```text
Tool: ask_user_tool
question: "Content published! What would you like to do next?"
answers: ["Create more content", "End session"]
```
