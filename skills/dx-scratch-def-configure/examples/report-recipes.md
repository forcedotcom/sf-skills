# Scratch Def report.md recipes

Copy the matching recipe into `report.md`. First line of every report.md:

# Scratch Def Report

Plain prose — never the backtick character. Spell skill names as plain words.

STOP recipes go on disk (Write / write_file). Chat is not a substitute. Name
the next skill. Never Skill() another skill. Never run `sf`.

If they change the draft (including a write request that also edits it), use
Happy-path draft. This turn's wording is the full draft. Do not require a
prior file or earlier chat. Do not apply. If they consent that this preview
is the draft they want written, unchanged — accepting this draft as drafted,
not a first generate that says write or skip preview — use Happy-path write.

---

## Shape-only stop

- Shape-only request with no features to layer. Not writing a scratch-def.
- Next: dx-org-shape-manage for org shape lifecycle. Pass along any
  source org alias, username, or shape id the user named.

## Snapshot-only stop

- Next: dx-org-snapshot-manage.
- Pass along Dev Hub, snapshot name/id, and create/list/get intent.

## Trial stop

- Next: platform-trial-org-create. Scratch-defs are not trial templates.

## Underspecified stop

- Need two details before drafting a scratch-def.
- 1. What are you building or demoing?
- 2. Which products or clouds should the org include?
- Stopping here without inventing an edition or feature set.

If `config/` is also missing, add the Missing-project question to this same
report. Do not invent a path.

## Underspecified refine stop

- Need to know what to change on the existing scratch-def.
- What would you like to change — features, edition, or settings?
- Stopping here without inventing a delta. Not asking about agents.

## Multi-def ask-which stop

- More than one config scratch-def file is present.
- List each config path that matches config/*scratch-def.json.
- Which file should I patch?

## Invalid existing JSON stop

- The target scratch-def is not valid JSON.
- Report the parse problem in plain prose.
- Not patching garbage. Fix or regenerate the file first.

## Other-user / no path stop

- Cannot read another user's machine or invent a seed file.
- Provide a readable workspace path or paste the file contents to continue.

## Shape or snapshot plus features, missing id

- Ask for a sourceOrg or snapshot id/name. Name dx-org-shape-manage /
  dx-org-snapshot-manage to list. Resume this skill with the id.

## Missing project config stop

- Current directory has no config folder, so this is not the Salesforce DX
  project where scratch orgs will be created.
- Not creating a config folder.
- What is the path to your Salesforce DX project (the directory that already
  contains a config folder)?

## Batch generation stop

- Batch generation of multiple scratch-def files in one turn is not supported yet.
- Want me to make the first one?

## Batch refine stop

- Batch refinement of multiple scratch-def files in one turn is not supported yet.
- Want me to refine one file?

## Happy-path draft (preview)

Keep the draft in chat/tool context and pass it to preview on stdin with <<'EOF'.

In chat, show the schema-valid preview document (helper result document) as a
fenced JSON block alongside this report.

- Paraphrase the intent.
- Edition (or sourceOrg / snapshot when layering).
- Features kept; settings enriched.
- Output path after confirm: config/project-scratch-def.json (or another
  config/purpose-scratch-def.json).
Write file?

Do not name dx-org-manage. JSON and the card go in chat.
Do not mention dropped tokens, prior cache date, shipped snapshot JSON, or
jsonschema in this report unless the helper actually warned this turn. When
jsonschema is missing, also ask in chat to install it; continue if install
fails.

## Happy-path write (after consent to this preview)

In chat, show the final written scratch-def JSON as a fenced block alongside
this report.

- Applied the in-context draft (stdin quoted heredoc) to
  config/project-scratch-def.json (or the purpose-named path used).
- One-line summary of edition and features.
- Next: dx-org-manage with that path; dx-org-devhub-configure if Dev Hub is off.
Do not ask Write file?.

Same helper-warnings rule as preview: include them only when the helper
warned this turn.

## Happy-path refine draft (preview)

Keep the structured refine delta in chat/tool context. Pass it to preview on
stdin with --base pointing at the existing file (delta only — never a full
rewrite).

In chat, show the schema-valid resulting document as a fenced JSON block and the
diff card (features added/removed, featuresQuantityChanged for same-base
quantity edits, edition/fields/objectSettings/settings changes, orphaned
required settings) alongside this report. Optionally keep helper baseSha256
for apply (race guard).

- Paraphrase the refine intent (delta on the existing file).
- Diff summary from the helper.
- Output path after confirm: the same --base path (prior file kept as .bak on write).
Write file?

Do not name dx-org-manage. Do not apply yet. If orphaned required settings are
present, ask whether to delete them before writing.

## Happy-path refine write (after consent to this delta preview)

In chat, show the final written scratch-def JSON as a fenced block alongside
this report.

- Applied the same delta (stdin quoted heredoc, --base, --out equal to --base)
  to the same path; prior file at the matching .bak.
- One-line summary of additions and removals.
- Next: dx-org-manage with that path; dx-org-devhub-configure if Dev Hub is off.
Do not ask Write file?.
