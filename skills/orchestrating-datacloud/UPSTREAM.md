# Upstream Distillation Map for orchestrating-datacloud

This file exists to make downstream maintenance easy without sacrificing sf-skills consistency.

## Maintenance contract

When upstream changes, do **not** copy blindly.

Instead:
1. review new upstream commits
2. identify changed command behaviors, install patterns, or gotchas
3. update sf-skills prompts and templates in a distilled form
4. keep naming, attribution, and cross-skill boundaries consistent with sf-skills
5. update this file with the new reviewed commit SHAs

## High-priority upstream areas to re-check

- installation / linking workflow for the community plugin
- command counts and topic coverage
- API-version guidance
- known issues and bug-fix notes
- live-tested command set
- any new commands affecting Connect / Prepare / Harmonize / Segment / Act / Retrieve boundaries
- connector-specific payload examples worth distilling into generic repo-safe examples
- search-index / hybrid-search guidance and any command-surface changes around hybrid scoring or prefilter behavior
- Ingestion API schema-upload flow, send-data examples, and problem-record guidance
- unstructured-source setup differences between connection-level reruns, stream refreshes, and initial UI seeding
- UI-only gaps where upstream introduces browser automation; validate before importing

## Cross-skill boundary reminders

Keep Data Cloud product work in `*-datacloud`, but do not blur into:
- `observing-agentforce` for STDM/session tracing/parquet workflows
- `querying-soql` for CRM SOQL-only tasks
- `handling-sf-data` for CRM record seeding/cleanup
- `generating-*` skills for CRM schema creation (custom objects, fields, validation rules, etc.)

## Local helper files in this family

- `references/plugin-setup.md`
- `scripts/bootstrap-plugin.sh`
- `scripts/verify-plugin.sh`
- `assets/definitions/`

These are sf-skills-owned conveniences and should evolve independently from upstream when that improves user experience.
