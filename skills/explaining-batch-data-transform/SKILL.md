---
name: explaining-batch-data-transform
description: "Explain and investigate an existing Salesforce Data Cloud Batch Data Transform (BDT) JSON definition. Use when the user provides or references a BDT JSON export and asks to understand, summarize, walk through, trace lineage in, or debug that specific BDT — for example, 'explain this BDT', 'what does this batch data transform do', 'where does field X come from in this BDT', 'which nodes feed OUTPUT5', or 'what does this computeRelative formula mean'. Accepts a path to a BDT JSON file or pasted JSON content. Does not author, edit, run, or fetch BDTs from an org."
allowed-tools: Bash Read Write
metadata:
  version: "1.0"
---

## 1. When to Use This Skill

Use this skill when the user asks you to understand a Salesforce Data Cloud **Batch Data Transform (BDT)** JSON export. The BDT's JSON is a dependency graph of 3 to 100+ nodes — loads, joins, filters, formulas, window functions, aggregates, and outputs — that together describe how data flows from source DMOs/DLOs to target DMOs/DLOs.

Trigger on prompts like:

- "Explain this BDT." / "What does this BDT do?"
- "Walk me through this batch data transform."
- "Summarize this BDT JSON."
- "Which nodes feed OUTPUT5?"
- "Where does field `ssot__ProductAmount__c` come from in this BDT?"
- "Trace the lineage of `TotalAmount__c`."
- "What does this computeRelative formula mean?" / "Why would this field be zero?"
- "What DMOs does this BDT read from?" / "What does this filter do?"

The skill accepts both shapes a BDT can appear in: the **editor export** (what customers download from the BDT viewer — `{version, nodes, ui}`) and the **Connect API create payload** (what developers POST when authoring via the API — with outer wrapper `{name, label, type, dataSpaceName, definition: {...}}`). See `references/bdt-reference.md` for details. Developers and customers alike can use the skill to understand a BDT — validation is out of scope for v1 but planned as a follow-up.

## 2. Prerequisites

- **Python 3.9+** on `PATH`. The parser script uses only the standard library — no `pip install` required.
- A **BDT JSON** — either a file path the user gives you, content the user pastes into the chat, or a file attachment you can read locally.

Do NOT assume the user has Salesforce CLI, `gh`, `jq`, Node, or any Salesforce org auth. The skill runs entirely locally against a static JSON file.

## 3. Input Handling

Decision tree for getting the BDT JSON into a local file the script can read:

1. **User gives a file path** (absolute or relative) → use it directly.
2. **User pastes JSON inline** → write it to `/tmp/bdt-<epoch_seconds>.json` with the Write tool, then use that path.
3. **User attaches a file** → the path is in the attachment metadata; use it.
4. **No BDT provided yet** → ask: *"Please paste the BDT JSON, give me a file path, or attach the export."*

Before any further work, validate by running `python bdt_analyze.py summary <path>`. If it exits 3 with "Invalid JSON", tell the user:

> "This file doesn't appear to be valid JSON. Could you re-export from the BDT viewer and try again? The exact error was: \<paste stderr\>."

### 3.1 Multi-definition payloads

**Multi-definition payloads.** If the user provides a Connect API payload with a `definitions[]` array containing multiple entries, first run `python bdt_analyze.py definitions <path>` to list them. Then offer the user a choice — *"The payload has 3 definitions: MyTransform, OtherTransform, ThirdTransform. Which do you want me to explain?"* — and invoke subsequent subcommands with `--definition N` (0-indexed). For example: `python bdt_analyze.py summary <path> --definition 1`. All analysis subcommands (summary, sources, outputs, stages, nodes, node, lineage, field-trace, formula) accept the `--definition` flag. Editor exports and single-definition payloads can be explained directly without this step; running `definitions` on them still succeeds and shows one row, so it is safe to run on any input if you are unsure.

## 4. Explanation Flow (Job A — Progressive Disclosure)

The default flow for "explain this BDT":

**Step 1.** Run `python bdt_analyze.py summary <path>` and render the **Executive Summary (Mode A)** in plain English to the user. Target ≤ 200 words. Name every source DMO/DLO and every output target. Identify at least one business-domain cue from the DMO names (e.g., *"looks like a sales-orders pipeline"*).

**Step 2.** Offer the four explanation modes:

> Want to go deeper? I can give you:
>
> - **(A) Executive summary** — reprint of what I just gave you.
> - **(B) Layered breakdown** — per-output lineage + per-stage mini-explanations.
> - **(C) Node-by-node walkthrough** — every node in topological order.
> - **(D) Business-intent read** — what this BDT is *trying to do*, in business language (marked as inference).

**Step 3.** Based on the user's pick:

- **Mode A** — reprint the summary; no further script calls.
- **Mode B** — run `python bdt_analyze.py stages <path>`, then for each sink run `python bdt_analyze.py lineage <path> <sink>`. Narrate: one section per output (its lineage), then a per-stage narration using the topo order.
- **Mode C** — run `python bdt_analyze.py nodes <path>` (add `--limit 50` if the BDT is large). Walk through each node in topo order, translating the digest into plain English. Consult `references/bdt-node-catalog.md` before narrating any action type the conversation hasn't already covered.
- **Mode D** — narrate the inferred business purpose from the `summary` digest + DMO/DLO names + output structure. **Always prefix with** *"Based on the structure, this appears to…"*. Explicit uncertainty marker is mandatory.

**Override rule.** If the user's first message names a mode (e.g., *"walk me through every node"* = Mode C), skip Step 2 entirely and go straight to the chosen mode.

## 5. Q&A Flow (Job B — Investigation)

When the user asks a follow-up question, route it to the right subcommand using this table. **Always narrate the output in plain English — never dump raw script output to the user.**

| User question pattern | Subcommand to run |
|---|---|
| "What does node X do?" / "Explain X" (L2) | `node <path> X` |
| "Which nodes feed X?" / "Upstream of X?" (L1) | `lineage <path> X` |
| "Where does field F come from?" (L3) | `field-trace <path> F` |
| "What DMOs/DLOs does this read from?" (L4) | `sources <path>` |
| "What fields does OUTPUT N produce?" (L5) | `node <path> OUTPUT_N` |
| "What does this formula mean?" (I1) | `formula <path> X` |
| "Why would F be null/zero/unexpected?" (I2) | `field-trace <path> F` to locate the defining node(s), **then** `formula <path> <defining-node>` on the formula or computeRelative node that computes the field (not the output mapping — pick the earliest formula/computeRelative node in the field-trace output). |
| "What does this filter do?" (I3) | `node <path> X` |

After running the subcommand(s), translate the output into plain English. For I1/I2 you **must** consult `references/bdt-function-catalog.md` (and `references/bdt-window-functions.md` if it's a `computeRelative` node) before narrating.

## 6. Output Style Guidance

- **Plain language first, technical detail second.** Lead with what the BDT or node does in business terms; only then mention the action type / parameter shape.
- **Use UI labels when available.** Say *"Join Users (JOIN0)"* rather than just *"JOIN0"* whenever `ui.nodes[X].label` exists.
- **Prefer field purpose over expression.** *"Product amount, zeroed except on the first ranked product per order"* rather than echoing the `case when ... end`.
- **Explicit uncertainty markers** on Mode D and I2 answers: *"Based on the structure, this appears to…"*.
- **Never fabricate lineage or definitions.** If `field-trace` returns no match, say the field isn't defined in this BDT. Don't invent a source.
- **Redact Salesforce record IDs in narration** (15/18-char IDs starting `0`) unless the user asks about them specifically. This keeps conversations shareable.
- **Don't fabricate features that aren't in the JSON.** If the user asks about scheduling, run history, or streaming behavior and those aren't in the JSON, say so plainly.
- **Don't dump raw JSON.** If the user wants to see raw params, run `node --json <path> <name>` and *then* explain what's interesting in the result.

## 7. Reference Consultation (mandatory)

- **Always-loaded:** `references/bdt-reference.md` — the top-level overview. Assume this is in context every conversation.
- **Consult `references/bdt-node-catalog.md`** via the Read tool **before**:
  - Explaining any node type you haven't already explained in this conversation.
  - Narrating any of: `bucket`, `flatten`, `flattenJson`, `split`, `extractGrains`, `extractTable`, `appendV2`, `multidefinitionMerge`, `cdpPredict`, `extension`, `extensionFunction`, `jsonAggregate`, `typeCast`, `formatDate` — these are rarer action types where the parameter shape matters.
- **Consult `references/bdt-function-catalog.md`** **before** interpreting any `formulaExpression` (I1 or I2). Look up each function named in the expression.
- **Consult `references/bdt-window-functions.md`** **whenever** you narrate a `computeRelative` node.
- **Cite the source when narrating deep detail.** Good: *"Per the node catalog, `computeRelative` runs a window function over the rows partitioned by `<partitionBy>` and ordered by `<orderBy>`."* Bad: asserting SQL semantics with no grounding.
- **If a node type or function isn't in any of the reference files**, narrate what the JSON shows (action name + pretty-printed parameters) and **explicitly flag that the item is not in the documentation materials shipped with this skill**. Do not guess at semantics.

## 8. Error Handling Guidance (what to tell the user)

| Script outcome | What to say |
|---|---|
| Exit 3: `Invalid JSON at line X` | "This file isn't valid JSON at line X. Could you re-export from the BDT viewer?" Then paste the exact error. |
| Exit 3: `Expected top-level 'nodes' object` | "This doesn't look like a BDT export — a BDT has a top-level `nodes` object. Is this the right file?" |
| Exit 3: `Cycle or broken reference detected` | "This BDT has a dependency cycle or references a non-existent node. You'll need to edit the BDT in the Data Cloud viewer to fix the circular dependency or broken reference — re-exporting won't help because the cycle exists in the BDT definition itself. The problematic nodes are: \<list from stderr\>." |
| Exit 2: `No node named 'X'` | "I don't see a node named `X` in this BDT. Did you mean one of: \<list of available names the script printed on stderr\>?" |
| Exit 2: `Field 'F' is not defined by any node` | "That field isn't defined anywhere in this BDT. Closest matches from the fields I can see: \<list from stderr\>. Is it possibly a field from the source DMO that's not pulled in?" |
| User's BDT uses an action type not in the catalog | "This BDT uses `<action>`, which isn't in my reference material. Here's what its parameters look like: \<raw params\>. I can describe the graph structure around it, but I can't vouch for the exact semantics of this action type." |

## 9. Non-Goals (explicit "Do not" directives)

**Do not** author, create, or edit BDTs. If the user asks to modify a BDT, explain that this skill only explains BDTs and point them at the BDT viewer in Data Cloud.

**Do not** run, schedule, or trigger BDTs. Execution happens in Data Cloud; this skill works on the JSON export only.

**Do not** fetch BDTs from a live org. v1 accepts only a user-provided file path or pasted JSON. If the user asks, say that live-org fetch is planned for v2.

**Do not** validate BDTs — don't claim a BDT is "correct" or "will run successfully". Validation (required-field checks, enum checks, dangling-ref detection) is planned as a follow-up v1.1 and is explicitly out of scope. If the user asks "is my BDT valid?", reply with *"This skill explains BDTs but doesn't validate them; validation is planned for a follow-up release. Want me to explain what the BDT does so you can spot issues manually?"*

**Do not** guess at node-type or function semantics not covered by the reference materials. Say "this isn't in the reference material shipped with this skill" and surface the raw parameters.

**Do not** invent business intent. Mode D and I2 answers must be prefixed with *"Based on the structure, this appears to…"* — never claim business purpose as fact.

**Do not** echo Salesforce record IDs verbatim (15/18-char IDs) in narration unless the user asks specifically about an ID.

**Do not** output raw Python script output to the user — always narrate.

**Do not** modify the BDT JSON file on disk. This skill is read-only.

**Do not** visualize the BDT as a graph image or diagram. Skill output is text only.

**Do not** compare multiple BDTs. This is a v1 limitation (single-BDT focus). If asked, suggest running the skill on each BDT separately.

## 10. Troubleshooting

Common issues and how to address them:

| Issue | Solution |
|---|---|
| `python: command not found` or `python3: command not found` | Ask the user to install Python 3.9+. Point them at https://www.python.org/downloads/. The skill's parser uses only the standard library, so `pip install` is **not** needed. |
| `ModuleNotFoundError: No module named 'bdt_analyze'` | The script path is wrong. The script lives at `scripts/bdt_analyze.py` inside the skill directory. Run it by absolute path (the Bash tool invocation should include the full path from the repo root). |
| BDT file path contains spaces (e.g. `"default B2C (Prod).json"`) | Quote the path when calling the script: `python bdt_analyze.py summary "default B2C (Prod).json"`. |
| Script output is very large for a big BDT (Mode C) | Use `--limit 50` on the `nodes` subcommand, or recommend Mode B (layered) instead of Mode C. |
| Field trace returns no match despite the field clearly appearing in the BDT | The field may only appear qualified (e.g., `SalesOrder.ssot__Id__c`). Try the qualified form. If still no match, the field may be passed through from a source DMO but not explicitly defined in the BDT — in that case field-trace cannot locate it; narrate "this field originates from the load node's source DMO" instead. Do NOT attempt to trace it by stripping the `__c` suffix — that would risk matching a different field with a similar name. |
| User says output "doesn't match what I see in BDT viewer" | Verify the version in the JSON header matches the org's current release. The canonical schema reference in `references/bdt-node-catalog.md` may predate the user's BDT, so older/newer BDTs may use variants not yet documented. Flag as "version drift" and narrate best-effort. |

## 11. Example Interactions

**Example 1 — "Explain this BDT" on a small DMO-to-DMO BDT.**

User: *"Explain this BDT."* (attaches `minimal_dmo_to_dmo.json`)

Skill:
1. Runs `summary` → gets: 3 nodes (1 load, 1 formula, 1 output), reads from `ssot__Account__dlm`, writes to `Account_Upper__dlm`.
2. Narrates in plain English:
   > This BDT takes accounts from the `ssot__Account__dlm` DMO, uppercases the account name, and writes the result to `Account_Upper__dlm`. Three nodes: **Account** (load), **Uppercase Name** (formula), **Account Upper** (output).
3. Offers modes: *"Want the layered breakdown, node-by-node walkthrough, or business-intent read?"*

**Example 2 — Field lineage on a larger BDT.**

User: *"Where does `TotalAmount__c` come from in this BDT?"* (after already loading `window_and_aggregate.json`)

Skill:
1. Runs `field-trace window_and_aggregate.json TotalAmount__c`.
2. Receives: defined by `AGG_BY_ACCOUNT` (action `aggregate`), specifically as `SUM` over `ssot__GrandTotalAmount__c`, grouping by `ssot__AccountId__c`. Upstream chain: `LOAD_ORDERS → RANK_ORDERS → AGG_BY_ACCOUNT`.
3. Consults `references/bdt-node-catalog.md` for the `aggregate` section.
4. Narrates:
   > `TotalAmount__c` is produced by the **Totals per account (`AGG_BY_ACCOUNT`)** aggregate node. It's a `SUM` of `ssot__GrandTotalAmount__c`, grouped by `ssot__AccountId__c` (one row per account). The amount values come from the original Sales Orders DMO via `LOAD_ORDERS`. The `RANK_ORDERS` node between them adds a per-account order rank but doesn't alter the amount.

## 12. Next Steps

After completing an explanation or Q&A, if the conversation seems to be wrapping up, offer:

- "Want to trace another field or explain another node?"
- "Need this BDT's summary in a different format (e.g., as a bulleted list for a doc)?"
- "If you want to edit or run this BDT, use the BDT viewer in Data Cloud — this skill explains BDTs but doesn't author or execute them."
- If the user found a bug or limitation, point them at the [afv-library GitHub issues](https://github.com/forcedotcom/afv-library/issues) to report it.
