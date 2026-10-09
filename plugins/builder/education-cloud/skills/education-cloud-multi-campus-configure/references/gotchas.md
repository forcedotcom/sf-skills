# Gotchas

| Issue | Resolution |
|-------|------------|
| Rename vs. delete-plus-add is indistinguishable from a bare desired tree | Only treat a change as RENAME/MOVE when the user names it explicitly; otherwise an absent node is CREATE and an extra node is EXTRA (report, don't delete) |
| Update run recreates everything (duplicates) | Ensure Step 4 detected update mode and Step 5 loaded `existingTree`; a missing root Id defaults to new setup — confirm mode with the user |
| `ChildAccounts` relationship returns partial/paged results | Follow `nextRecordsUrl`/paging if present; if the relationship is unavailable, fall back to a SOQL `/query` with `WHERE ParentId = ...` (confirmed routable), or ask the user to paste current node Ids |
| API rate limit during Business Profile creation | Retry failed records after 2-second delay; print which records succeeded vs. failed |
| Ambiguous college-to-campus mapping in parsed text | Ask user: "Which campus does [College name] belong to?" before creating College Account |
| Duplicate names across campuses (e.g., "School of Arts & Sciences" on multiple campuses) | Append campus name to college name: "School of Arts & Sciences (Main Campus)" |
| PDF parsing extracts noise (headers, footers, page numbers) | Filter lines matching common noise patterns before parsing hierarchy; see `references/hierarchy_parsing_rules.md` |
| User uploads flattened list without parent relationships stated | Ask user to clarify structure: "I see these names — please describe which items are campuses, colleges, and departments" |
| BusinessProfile creation fails with "AccountId field not found" | User's org may not have Education Cloud provisioned; check access prerequisites returned error |
| User expects a stored materialized-path field to read back | There is none — build the path on demand by GET-ing the Account and walking its ParentId chain to the System root, joining Names with ` / ` |
| Requested URL is blocked/unreachable during Step 1 | Do not silently substitute another source (e.g. a research agent pulling from Wikipedia) — stop and ask the user for a PDF, CSV, or pasted text from the institution's own site |
| User wants `InstitutionType` set on a Business Profile for a non-K-12/higher-ed institution (vocational, allied health, satellite/extension) | `InstitutionType` is a managed, restricted picklist (typically `Public`/`Private`/`Charter` only) — cannot be extended; tell the user upfront and offer `Description` as the only workaround field |
