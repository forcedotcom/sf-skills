# Step 3 — workspace resolution (full detail)

Resolves `contentSpaceOrFolderId` (and, for a UIBundle, `channelId` + `workspaceMethod`). See SKILL.md Step 3 for WHEN it runs (fast-path: after Step 2; delegation path: early, as the first action of Step 2a, before the sibling is dispatched).

## Discovery (silent — no output to user)

Scan the project for `uiBundles/` directories — read each `packageDirectories[].path` from `sfdx-project.json` and scan under it; if no `sfdx-project.json` is present, fall back to a recursive search for `uiBundles/` directories. For each `uiBundles/` directory, iterate its subdirectories. For each subdirectory `<name>`, read `<name>/<name>.uibundle-meta.xml` and extract `<masterLabel>`. Build a list of `{ developerName: "<folder-name>", masterLabel: "<masterLabel from XML>" }`. If the `.uibundle-meta.xml` is missing or unreadable, use the folder name as both `developerName` and `masterLabel` fallback.

If the scan returns **zero** UIBundles, use the "no local UIBundles" variant from `assets/questions.md` — ask the user directly for a Content Space or Folder ID. Do NOT invent a workspace, do NOT run SOQL / `sf data query` against `ContentSpace` or any other object, do NOT read `ui-bundle.json` from disk. If nothing is on disk, the user provides the ID.

## Ask (single question)

Use the "Step 3 — Workspace resolution" templates in `assets/questions.md`. Dispatch via `ask_user_tool` — do NOT print as plain text.

## Routing

- **User selects a UIBundle** → call `get_or_create_cms_workspace_and_web_app_channel` with the selected UIBundle's `developerName` and `masterLabel`. Use the returned `spaceId` as `contentSpaceOrFolderId` for the rest of the workflow. **Record** `workspaceMethod=uibundle` and store the selected UIBundle's `developerName`, `masterLabel`, and the returned `channelId` for Step 10. **Then persist the `channelId` to disk** — write it into `uiBundles/<developerName>/public/content-metadata.json` under the `channelId` key. File-writing rules: if `public/` doesn't exist, create it; if `content-metadata.json` doesn't exist, create it as `{"channelId": "<value>"}`; if it exists, merge — preserve every existing key and overwrite ONLY the `channelId` value, do NOT delete or reformat other keys. On failure of the tool call itself, dispatch the retry prompt from `assets/questions.md`.
- **User selects "Provide a space or folder ID manually"** → **Record** `workspaceMethod=manual`. Dispatch the manual-ID prompt from `assets/questions.md` with a "Go back" clickable option. If the user clicks "Go back", re-present the original Step 3 question. Otherwise **validate the provided ID before using it** (see below). **Note:** with `workspaceMethod=manual` there is no resolved `channelId`, so the Step 10 "Render to UI Bundle" option is hidden — the user can still create, edit, and publish, but the render handoff requires selecting a UIBundle up front.

## Validate a user-provided workspace ID — MANDATORY before use

Never accept a manual Content Space / Folder ID blindly (the observed bug: a wrong ID was accepted with no check, then failed deep in `create_cms_content`). Two-layer validation:

1. **Format gate (client-side, before any tool call).** A valid Content Space ID starts with `0Zu`; a valid Folder ID starts with `9Pu`. The full ID must also be a well-formed Salesforce ID: prefix + only alphanumeric chars, exactly 15 or 18 chars total, no spaces. If the pasted value starts with neither prefix, OR is not 15/18 alphanumeric chars (e.g. `9Pualkskjhlkasdfjhlksdf` — right prefix but junk length), do NOT proceed and do NOT call any tool. Re-dispatch the **invalid-ID re-ask** template from `assets/questions.md` with `<reason>` = "it wasn't a 15- or 18-character `0Zu`/`9Pu` ID". Classify a passing ID by prefix: `0Zu` → `spaceId`; `9Pu` → `folderId`.

   **Prefix + length is NECESSARY, NOT SUFFICIENT.** A perfectly well-formed `0Zu`/`9Pu` ID can still be fake, stale, deleted, or from a different org — the format gate cannot prove the space exists. Passing Layer 1 does NOT confirm the ID; only a server call does (Layer 2). Do NOT reason "the format looks right, so I'll proceed and validation will happen later at create" — that deferral IS the bug. The ID is unconfirmed until Layer 2 fires.
2. **Server confirmation — fires on the FIRST server call that touches the space, whichever comes first.** The ID is confirmed real only when that call succeeds:
   - **Delegation path (Bucket 4):** the space is passed to the sibling's `get_content_types_for_workspace` BEFORE any content type is built. That is the first touch. If the sibling returns `INVALID_API_INPUT` / "'spaceId' must be a valid ManagedContentSpace id" / space-not-found, the space is invalid — **HARD STOP. Do NOT let the sibling build or deploy a content type on a bad space.** Surface the server error **verbatim**, then re-dispatch the **invalid-ID re-ask** template with `<reason>` = the server error text. Only after a corrected ID passes Layer 1 do you re-dispatch the sibling.
   - **Fast path (Buckets 1/2/3):** the first touch is `create_cms_content`. If it returns `INVALID_ID` / "Content space not found" / an invalid cross-reference error, same handling — surface verbatim, re-ask via the invalid-ID template.

   Do NOT retry the same ID. Do NOT defer confirmation past the first touch.

**Cross-reference / wrong-org error — do NOT improvise an org picker.** On an invalid cross-reference error, the ID belongs to a different org than the connected default. Surface the error verbatim and re-ask for the correct `0Zu`/`9Pu` ID via the manual-ID template ONLY. Do NOT run `sf org list`, do NOT enumerate available orgs, and do NOT invent an "Which org should I use?" question with an org list as answers — org selection is not this skill's job and that improvised prompt is a documented regression. The connected org is fixed; the user supplies an ID that belongs to it.
