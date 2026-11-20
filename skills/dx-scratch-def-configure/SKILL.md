---
name: dx-scratch-def-configure
description: "Drafts or refines a schema-valid Salesforce DX scratch-def from natural language. Preview first (confirm card or refine diff); apply via this skill's helper only after consent that the draft/delta is unchanged — author scratch-def JSON only through the helper. Writes config/<purpose>-scratch-def.json (default project) under an existing SF DX project that already has config/ (requires existing config/). Refine sends a structured delta only (helper copy-through patches the base; catalog on new features only; whole-file diff; apply requires --out equal to --base; optional baseSha256 guards against the file changing between preview and write). Put product names (like Revenue Cloud) in features as-is. Also use for trial, shape/snapshot-only, underspecified, missing config/, multi-def ask-which, invalid JSON, or batch asks: invoke this skill, STOP, and write report.md on disk. Org creation and Dev Hub enablement belong to dx-org-manage / dx-org-devhub-configure. Not for those skills or SKU work."
allowed-tools: Read, Write, Bash(python3), Bash(python)
metadata:
  version: "1.1"
  domains: ["Developer Experience"]
  relatedSkills:
    - "dx-org-devhub-configure"
    - "dx-org-manage"
    - "dx-org-shape-manage"
    - "dx-org-snapshot-manage"
    - "platform-trial-org-create"
  cliTools:
    - tool: ["python3", "python"]
      semver: ">=3.8.0"
---

# Configure Scratch Org Definition File

This skill writes `config/<purpose>-scratch-def.json` (default
`config/project-scratch-def.json`) from a product ask, or refines an existing
file in place. It does **not** create the org. Never `mkdir config`.

Every turn writes `report.md` on disk. Chat is not a substitute. Then exactly
one of these happens:

| Mode | When | What the user gets |
|------|------|--------------------|
| **Stop** | Trial, shape-only, shape/snapshot + features with no id, missing project, unclear ask (generate or refine), batch, other-user path, invalid existing JSON, multi-def without a pick | The next step, named. No scratch-def file write. |
| **Preview** | First generate (including just-write / skip-preview), a revision, or a refine patch, and the project already has `config/` | A draft (generate) or **diff card** (refine) + Write file?. Nothing is written yet. |
| **Write** | They accept this draft **unchanged** (this preview, as drafted). This turn may restate it; no prior chat required. | The file. Name dx-org-manage. |

## CRITICAL first gate (before any helper)

First matching row wins. Copy that recipe into `report.md`.

Never Skill() another skill. Never run `sf`. Name the next skill in `report.md` only.

STOP: write `report.md` on disk. Chat is not a substitute. Skip the helper
and skip scratch-def JSON.

Consent is accepting this draft, **unchanged** — not a closed list of yes-words.
Accepting this draft (this preview, as drafted) and asking to write is consent:
**apply immediately**; reconstruct if they restate the same draft; **do not** ask
Write file? again; **do not** run preview. No prior chat required.
Phrases like "Looks good, write it", "write it", "yes write", "apply it",
"as we drafted", or "as we previewed" **with the same edition/features/settings**
are Write — even when this turn restates the draft or names the refine delta
that was already previewed. That is **not** a first generate and **not** another
refine preview.
A first generate is Preview only when they ask to create/skip-preview **without**
accepting a prior draft (no "looks good" / "as we drafted|previewed" consent).
A **different** edition, product, or setting (a real change) is another preview.
Refine is a **patch on the existing file**, not “this turn’s wording replaces
the whole draft” (that generate-revision path still exists for in-chat drafts).

| If the ask is… | Then |
|----------------|------|
| Shape or snapshot **lifecycle alone** (no features to layer), including "use my org shape only" or "refine my shape" | STOP. Name dx-org-shape-manage or dx-org-snapshot-manage. |
| Trial / trialforce / "trial org definition" / "refine my trial config" | STOP. Name platform-trial-org-create. Do **not** skip this skill. |
| Underspecified generate ("I need a scratch def") — no edition and no products/clouds/features | STOP. Ask the two questions below. If `config/` is also missing, include the Missing-project question. Do not invent an edition. |
| Underspecified refine ("Update my def" / "refine my scratch def") — no features, edition, or settings delta | STOP. Ask: features, edition, or settings? (Not agents — out of scope.) |
| Another user's laptop / no readable workspace path | STOP. Cannot read another user's machine. Ask for a readable workspace path. |
| Batch generation or batch refine (multiple def files in one turn) | STOP. Batch is not supported yet — offer to make or refine the first one. |
| WRITE-eligible (imperative generate with edition and/or products/features, refine with a clear delta, or shape/snapshot **+ features**) but cwd has **no** `config/` | STOP. Ask the Missing-project question (folder that **already** contains `config/`). Do **not** create `config/`. |
| Refine target resolves to more than one `config/*scratch-def.json` (ignore `*.bak`) and the user did not name which | STOP. List the paths and ask which file to patch. Do not pick silently. |
| Refine target exists but is invalid JSON | STOP. Report the parse error. Do not patch garbage. |
| Shape/snapshot **+ features**, root resolved, user omitted `sourceOrg` or snapshot id/name | STOP. Write `report.md` on disk. Ask for the id. Name dx-org-shape-manage / dx-org-snapshot-manage to list. Resume this skill with the id. |
| User consents that this preview is the draft/delta they want written, **unchanged** (this preview, as drafted) — including "Looks good, write it" / "as we drafted|previewed" restating the same generate draft or the already-previewed refine delta — and root resolved | **Write** it (apply / apply `--base`). Reconstruct the **same** draft or delta if needed. Refine: `--out` must equal `--base`; pass preview `baseSha256` when you have it (optional race guard). Missing hash is still a write — do **not** turn consent into another preview. A **different** delta this turn is a new preview. See **Write**. |
| User revises the draft — this turn names a **different** edition, products, settings, or other edits, including a write request that also changes the draft, and root resolved | This turn's wording is the full draft (in-chat generate revision). Preview it. Do not require a prior file or earlier chat. **Do not** apply yet. |
| Refine with a clear delta (add/remove features, change edition, add/remove settings), root resolved, target file chosen, and this turn is **not** consent to write | Read base → build structured **delta only** → Preview the **diff card**. **Do not** apply yet. Removing a feature does **not** silently delete unrelated settings — show orphaned required settings and ask before deleting a required pair. |
| Shape/snapshot **+ features**, root resolved, user supplied the id, and this turn is not consent to write | Preview it. **Do not** apply yet. |
| Imperative generate that names edition and/or products/features (one def), including a first-turn write or skip-preview ask **without** accepting a prior draft, root resolved, and this turn is not consent to write | Preview it. **Do not** apply yet. |

Generate underspecified questions: (1) what are you building/demoing? (2) which products/clouds?

Refine underspecified question: What would you like to change — features, edition, or settings?

Missing-project question: What is the path to your Salesforce DX project (the directory that already contains a config folder)?

## Preview

### Generate / revision

Show the confirmation card (see `examples/confirm-card.md`, or
`artifacts/examples/confirm-card.md` when packaged). Put **schema-valid JSON**
in chat alongside `report.md` (never inside it): the helper `document`. Ask
Write file? in `report.md`. **Do not** apply yet. Do not name dx-org-manage
until they consent to write.

### Refine

If more than one `config/*scratch-def.json` exists (ignore `*.bak`) and the user
did not name which, the CRITICAL multi-def STOP wins — ask which file before
any default. Otherwise resolve the target (default
`config/project-scratch-def.json`). Read it for context. Build a **structured
delta only** for this turn's change — do **not** rebuild or send the full
scratch-def. The helper loads the base as-is (copy-through), applies the
delta, catalogs only newly added features, and returns a whole-file diff.
Pass the delta on stdin with `--base`:

```bash
python3 "$HELPER" preview --base config/project-scratch-def.json <<'EOF'
{"addFeatures":["Communities"]}
EOF
```

Delta keys (only those that apply): `addFeatures`, `removeFeatures` (match by
base name), `setEdition`, `set` / `unset` (top-level scalars such as
`orgName`), `setSettings` (nested object and/or dotted leaf keys — helper
expands dotted keys), `unsetSettings` (dotted path strings; category match is
case-insensitive), `setObjectSettings` / `unsetObjectSettings`. Same-base
quantity change: `addFeatures` with the new `Feature:N` token (replaces the
prior quantity).

Show the **diff card** from helper `diff` (added/removed features,
`featuresQuantityChanged`, edition / fields / objectSettings /
settings changes, orphaned required settings). Optionally keep preview
`baseSha256` for the write turn. Put schema-valid resulting JSON
(`document`) in chat. Ask Write file?. **Do not** apply yet. If
`settingsOrphanedByRemovedFeatures` is non-empty, ask whether to delete those
settings before writing (add matching `unsetSettings` on the next preview if
they consent — use the exact orphan path from the card).

## Write

One `apply` only — no preview, no second card, no Write file?. Reconstruct
if this turn restates the same draft or delta (no in-context copy). `--out config/<purpose>-scratch-def.json`
(default `config/project-scratch-def.json`). For refine, pass the same `--base`,
`--out` **equal to** `--base`, the **unchanged** delta JSON, and optionally
`--base-sha256` from that preview when you have it (refuses if the base file
changed). On success it copies the prior file to `config/<name>.bak` (one
rolling backup for compare/restore), then overwrites the active path:

```bash
python3 "$HELPER" apply --base config/project-scratch-def.json \
  --out config/project-scratch-def.json <<'EOF'
{"addFeatures":["Communities"]}
EOF
```

Report the path + backup path + a one-line summary (refine: additions and
removals) + the **final written JSON in chat**. Name dx-org-manage
(dx-org-devhub-configure if Dev Hub is off).

## Outcome report (always)

**Read** `examples/report-recipes.md` (or `artifacts/examples/report-recipes.md`
when packaged) and copy the matching recipe. First line: `# Scratch Def Report`.
Plain prose — never the backtick character. Spell next-skill names as plain
words (dx-org-shape-manage, platform-trial-org-create).

Omit cache date, shipped-snapshot, jsonschema, and dropped-token notes from
`report.md` unless the helper warned this turn.

## Steps

1. Run the CRITICAL first gate. If it is STOP, write `report.md` and stop here.

2. On WRITE-eligible asks, **resolve the SF DX project root before any helper**:
   cwd with `config/` is the root; otherwise the Missing-config STOP row.

3. Resolve the helper by absolute path:

   ```bash
   HELPER="<skill_dir>/scripts/lib_scratch_def.py"
   [ -f "$HELPER" ] || HELPER="<skill_dir>/artifacts/scripts/lib_scratch_def.py"
   ```

4. **One helper call per turn** from the SF DX project root. Keep the draft or
   refine delta in **chat/tool context**. Pass it on stdin with a quoted heredoc
   (`<<'EOF'`). Invoke `python3` when that binary exists; otherwise `python`.
   - Preview (generate or a revision of the draft):
     ```bash
     python3 "$HELPER" preview <<'EOF'
     {"edition":"Developer","features":["API"]}
     EOF
     ```
   - Preview (refine — structured delta only, never a full rewrite):
     ```bash
     python3 "$HELPER" preview --base config/<purpose>-scratch-def.json <<'EOF'
     {"addFeatures":["Communities"]}
     EOF
     ```
   - After consent that this draft/delta is what they want, unchanged:
     ```bash
     python3 "$HELPER" apply --out config/<purpose>-scratch-def.json <<'EOF'
     …same draft JSON…
     EOF
     ```
     Refine consent: same apply with `--base`, the **same delta JSON**, and
     `--out` equal to `--base` (writes `.bak` then overwrites). Optionally pass
     `--base-sha256` from that preview. (default
     `config/project-scratch-def.json`).
   If the helper warns `jsonschema not installed`, ask the user to install
   (`python3 -m pip install jsonschema` or `python -m pip install jsonschema`).
   On success, retry this same helper call once. If they decline or install fails,
   keep this result — do **not** block preview/apply.
   Do **not** Read `references/features.json` or `settings-map.json` into chat.
   Do not Grep them to pick extra tokens.

5. Generate: put the user's product, cloud, and feature words in the `features`
   array as-is (for example Revenue Cloud, not a guessed token list). Refine:
   put those words in `addFeatures` / `removeFeatures` on the delta only. Use
   lower camelCase settings keys. The helper maps each **new** string to at most
   one PUBLIC token and enriches required settings for additions only. Do not
   add catalog tokens the user did not name. Do not rebuild the full file.

6. Write `report.md` on disk. Put chat JSON and the card per Preview / Write.

Unknown token: drop it and warn in report.md. Ambiguous phrase ties (for
example Sales Cloud matching more than one catalog blurb): drop and warn with
candidates — do not silently pick the first.

## Before you finish

- [ ] `report.md` exists on disk and matches a recipe
- [ ] Preview / revision / refine (including write + change): card or diff card + document JSON in chat; asked Write file?; **Do not** apply yet
- [ ] Consent unchanged (this preview, as drafted; no prior chat required): `apply`; file + final JSON in chat; no Write file?; name dx-org-manage
- [ ] WRITE turns: root resolved; one helper call; features array is the user's words (refine: existing + named delta)
- [ ] Refine remove-feature: orphaned required settings surfaced; asked before deleting a required pair
- [ ] report.md mentions cache date, jsonschema, or dropped tokens only when the helper warned this turn

## Notes

Catalog: each helper invocation loads maps into process memory from:

1. Today's `cache/public-config-values-YYYY-MM-DD.json` if usable.
2. Else GET live PUBLIC config-values markdown; on success write today's cache file.
3. Else newest usable prior dated file in `cache/`. report.md: that date
   (only when this fallback fired).
4. Else shipped snapshot JSON `references/features.json` + `settings-map.json`
   (`artifacts/references/` when packaged). Backup. report.md: shipped snapshot
   (only when this fallback fired).

Every helper call (`preview` and `apply`) may write today's cache file under
`cache/` before the user confirms the scratch-def. Add `cache/` to `.gitignore`.
Treat cache JSON as generated. Delete is safe: the next call refetches if
today's file is missing. Feature tokens come from this catalog.
