# UX rules for `ask_user_tool`

## VERBATIM QUESTION CONTRACT — EVERY `ask_user_tool`, no exceptions

All questions go through `ask_user_tool`, never plain text. Each is a fixed template in `assets/questions.md`; before ANY `ask_user_tool` call, have that file open and copy BOTH the `question` string AND the `answers` array **character-for-character**, filling only `<placeholders>`. You may NOT:
- reword, shorten, expand, or re-punctuate the `question` — identical wording every run (the 6 different Step 3 phrasings in the trace are this bug);
- invent, rename, reorder, add, or drop `answers` — the set is fixed (`Approve / Edit topics / Cancel` vs `Looks good, create them / Let me adjust` drift is banned);
- put list/table content or per-item numbers INTO an answer. Answers are the fixed choices only — numbering a list into them (`"1 - Spider-Man"`, `"2 - The Batman"`) is forbidden (renders run-on, doubles the index). Variable lists go in a chat-text Part 1 (two-part pattern below); answers stay the template's fixed set.

No template covers it? STOP and re-read `assets/questions.md` — never compose one ad hoc.

## Asking Questions — MANDATORY UX Rule

**EVERY question to the user MUST use the `ask_user_tool` tool.** Never ask a question as plain text in your chat response. Plain-text questions look like the skill has finished and the user has no visual cue that they need to respond.

The `ask_user_tool` renders an interactive prompt with clickable answer options, making it unmistakable that the user must respond before the workflow continues.

| Wrong (plain text — looks like skill ended) | Correct (interactive tool) |
|---|---|
| Printing "Which content space should I create the content in?" as part of your response text | Calling `ask_user_tool` with `question: "Which content space or folder should I create the content in? Provide the ID (Content Space IDs start with `0Zu`; Folder IDs start with `9Pu`)."` |

This applies to ALL questions in the workflow — see `assets/questions.md` for every prompt template. The complete list of question points:

- Step 0-U / Step 0-P: identifier ask when the user named content by title with no ID (shared template, single sentence, `Cancel`-only)
- Step 2 (Bucket 3 only): FQN-correction confirmation
- Step 3: workspace question (UIBundle selection or manual ID)
- Step 3: invalid workspace ID re-ask (format-gate fail OR server-confirm fail — MUST say "invalid")
- Step 4.B.2: bulk topic approval
- Step 5a: bulk pre-dispatch blanket approval
- Step 7: post-action loop (Edit / Publish / End)
- Step 8a: edit scope selection
- Step 8b: edit instructions
- Step 7: publish subset selection
- Step 10: post-publish next action

## Formatting rule for `ask_user_tool`

The `question` field in `ask_user_tool` renders as a **single paragraph** — it does NOT support line breaks, markdown, or lists. Long content (like topic lists, error details, or summaries) becomes an unreadable wall of text inside the prompt.

**Pattern: Split complex questions into two parts:**

1. **Print structured content as formatted chat text** (markdown lists, tables, bold, code blocks — all render correctly in chat output).
2. **Then call `ask_user_tool` with ONLY a short question** (one sentence max).

| Wrong | Correct |
|---|---|
| Stuffing a numbered list into `ask_user_tool.question` | Print the list in chat text, then call `ask_user_tool` with just "Do these look good?" |
| Putting error details in `ask_user_tool.question` | Print error details in chat text, then call `ask_user_tool` with just "How would you like to proceed?" |

## FAILURE LOOK — recognize the rendering bug

The `question` field does NOT render markdown — it shows every character literally, on one line. Reformatting a templated sentence into markdown is the #1 reported UX defect.

**Broken (what NOT to produce)** — a `question` field containing:

```text
To create the content, provide one of the following: - **Content Space ID** (starts with `0Zu…`) - **Folder ID** (starts with `9Pu…`)
```

The user sees the literal `- **…**` — asterisks and dashes printed as text, no list, no bold. Looks broken.

**Correct** — dispatch the template's single sentence unchanged:

```text
Which content space or folder should I create the content in? Provide the ID (Content Space IDs start with `0Zu`; Folder IDs start with `9Pu`).
```

Same rule for the field-proposal table, topic lists, and error details: the structured part is printed as chat text FIRST (Part 1), and the `question` (Part 2) stays a single plain sentence. Never move a table or list into `question`.
