# Education Cloud Domain Features — Complete Setup Guide

Configuration guide for each Education Cloud domain and its sub-features. Based on Salesforce Help Articles. Each domain's full setup steps live in its own reference file under `domain-features/` — open the one matching the domain being configured.

## Domain Reference Files

| Domain | File |
|--------|------|
| 1. Student Success | [domain-features/student-success.md](domain-features/student-success.md) |
| 2. Recruitment & Admissions | [domain-features/recruitment-admissions.md](domain-features/recruitment-admissions.md) |
| 3. Academic Operations | [domain-features/academic-operations.md](domain-features/academic-operations.md) |
| 4. Alumni Relations | [domain-features/alumni-relations.md](domain-features/alumni-relations.md) |
| 5. Student Management | [domain-features/student-management.md](domain-features/student-management.md) |
| 6. Mentoring | [domain-features/mentoring.md](domain-features/mentoring.md) |
| Cross-Domain Dependencies | [domain-features/cross-domain-dependencies.md](domain-features/cross-domain-dependencies.md) |
| IndustriesSettings Toggle Fields — Quick Reference | [domain-features/industriessettings-toggle-reference.md](domain-features/industriessettings-toggle-reference.md) |

## General Notes

- All domains require Education Cloud Foundation and Person Accounts enabled first
- Some sub-features require additional licenses (Field Service for Scheduler, Fundraising for gift management, Experience Cloud for portals)
- Object names may vary by Education Cloud version — check API version compatibility
- Verification queries may fail if objects are not yet provisioned (async provisioning) — wait 2-3 minutes and retry
- Setup menu paths may change with Salesforce UI updates — if path not found, search Setup for the feature name
- Write domain/feature toggles via the headless metadata PUT path (IndustriesSettings `xmlRep`, write `dispatch` tool); never `setup/org/preferences/{name}` (404). Fall back to UI instructions only on error
- EDU toggles are IRREVERSIBLE (`false → true` only) — warn the user, never promise a revert
- Student Management has no separate domain toggle — it is enabled when Academic Operations is configured with student enrollment records
