# Missing Account RecordType — Prerequisite Handling (Step 3.5)

This skill can be run standalone, without any prior org-setup skill having run first. A common gap on a
fresh org: `Account/describe` returns only the `Master` RecordType — no institutional/business
RecordType exists yet to select in Step 3.5. Treat this as a missing prerequisite to resolve, not a
dead end.

## Procedure

1. **Tell the user** the org has no non-Master Account RecordType, and this skill needs one to
   distinguish institution Accounts (System/Campus/College/Department) from other Account records.
2. **Ask for a Label** if the user hasn't already stated one (e.g. "Institution", "Educational
   Institution", "Business Account") — offer "Institution" as the default suggestion. Derive the
   `DeveloperName` from the label (strip spaces/special chars, e.g. `Institution`).
3. **Confirm before creating** — same create/update/delete confirmation convention as every other
   write in this skill: "Create Account RecordType '[Label]' (API name `Account.[DeveloperName]`)?
   (Yes/No)". If "No": stop the workflow — the hierarchy cannot be created without a RecordType.
4. **Create via Tooling API** (write-enabled `dispatch`, not `dispatch_readonly`):
   ```json
   {
     "url": "/services/data/v68.0/tooling/sobjects/RecordType",
     "method": "POST",
     "body": {
       "FullName": "Account.[DeveloperName]",
       "Metadata": {
         "label": "[Label]",
         "active": true,
         "description": "Institutional hierarchy Account (System/Campus/College/Department)"
       }
     }
   }
   ```
5. **Cold-verify** — re-run the Step 3.5 describe call. Confirm the new entry appears in
   `recordTypeInfos`.
   - **If `available: true` for the running user** — capture `recordTypeId`, proceed with Step 3.5's
     normal selection logic.
   - **If `available: false`** — RecordType creation does not automatically grant profile/permission-set
     visibility (there is no supported API for Record Type Visibility assignment). Tell the user to
     assign it manually: Setup → Profiles (or Permission Sets) → Record Type Visibilities → assign the
     new RecordType to their own profile/permission set → Save. Wait for their confirmation, then
     repeat the describe call to cold-verify `available: true` before proceeding.
6. **If Tooling API creation fails** (e.g. no Tooling API access): fall back to manual creation —
   instruct the user via Setup → Object Manager → Account → Record Types → New, then repeat the
   describe call to cold-verify.
