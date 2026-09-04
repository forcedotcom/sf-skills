---
name: life-sciences-prerequisites-validate
description: "Validate Life Sciences Cloud for Customer Engagement org prerequisites. Use when an admin needs to verify that all required settings, permissions, OWD sharing rules, and feature toggles are correctly configured before deploying Life Sciences Cloud. Checks user profile, permission sets, Life Sciences CE settings, surveys, OWD, inventory, account plans, care plans, Chatter, data protection, multi-currency, state/country picklists, and person accounts. Reports pass/fail for each check with remediation steps. TRIGGER when: user says 'check prerequisites', 'verify org setup for Life Sciences', 'LSC readiness check', 'pre-requisites for Life Sciences Cloud', 'validate org for LSC'. DO NOT TRIGGER when: user wants to automatically enable or configure these settings, or when the user asks for the full end-to-end Life Sciences Cloud setup / orchestration (that is the `life-sciences-fieldsalesrep-coordinate` orchestrator's job — this skill runs only as a standalone prerequisites check)."
metadata:
  version: "1.0"
  minApiVersion: "65.0"
  domains: ["Life Sciences"]
  relatedSkills:
    - life-sciences-fieldsalesrep-coordinate
    - life-sciences-territory-configure
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Life Sciences Cloud Prerequisites Validation

Validates that a Salesforce org meets all prerequisites for Life Sciences Cloud for Customer Engagement. Runs checks via the `sf` CLI against the currently authenticated org and produces a consolidated pass/fail report with remediation steps for any failures.

## Scope

- **In scope**: Validating org settings, user permissions, OWD sharing, and feature toggles required for Life Sciences Cloud CE
- **Out of scope**: Automatically enabling or configuring settings that fail validation

### Off-topic requests

If the user asks for something unrelated to this skill (either at the start or mid-execution), do not attempt it. Tell the user you did not understand the request, then show what you *can* help with: validating Life Sciences Cloud org prerequisites (this skill), and — if relevant — point them to `life-sciences-territory-configure` for territory setup or `life-sciences-fieldsalesrep-coordinate` for the full end-to-end setup. Then stop and wait.

---

## Required Inputs

Gather before proceeding:

- **Target org**: The org alias or username to validate (from `sf config get target-org` or user-specified)
- **Confirmation**: The logged-in user must be the admin whose profile and permission sets are being validated

---

## Workflow

All checks run sequentially. Collect all results before presenting the final report.

### Phase 1 — Validate Environment

1. **Confirm org connection** — run `sf org display --target-org <org>` to verify the org is accessible. If it fails, stop and ask the user to authenticate.

2. **Identify the logged-in user** — extract the username from the org display output.

### Phase 2 — Run All Prerequisite Checks

Run each check below. For each, record PASS or FAIL with the remediation steps. The checks use the canonical **Check 1 – Check 12** numbering from the reference files and the final report; the managed-package check is an un-numbered hard-stop gate, not one of the 12 scored categories. Checks 1–3 (and the managed-package gate) are in `references/checks-user-and-package.md`; Checks 4–12 are in `references/checks-org-settings.md`.

> **STOP-GATE (report completeness).** Every check MUST produce a row in the final report — a check that errors (e.g. Multi-Currency returns HTTP 400 `INVALID_TYPE`, or an object isn't deployed) is a **FAIL row**, never a skipped/omitted row or a reason to abort the run. The report's row count MUST equal the full scored-check count (**12 categories**, Check 1 – Check 12). The **one** intended early exit is the managed-package gate (the un-numbered `lsc4ce` package check, step 4 below) — that legitimately stops the run with the "BLOCKED" message. In every other case, a query error is the FAIL signal: record it and continue. Do NOT let a single 4xx or unexpected-shape response silently drop a row or halt the sweep — a short report reads as "fewer things to fix" when the truth is "we didn't check."

3. **Check 1 — user profile and permission sets** — read `references/checks-user-and-package.md` section "User Profile and Permission Sets" for the exact queries and validation logic.

4. **Managed-package gate (un-numbered hard stop)** — read `references/checks-user-and-package.md` section "Managed Package Check". If the `lsc4ce` package is not installed, display the failure message and **stop** — do not proceed with remaining checks.

5. **Check 2 — Life Sciences CE settings** — read `references/checks-user-and-package.md` section "Life Sciences Customer Engagement Setup" for the exact queries.

6. **Check 3 — Surveys enabled** — read `references/checks-user-and-package.md` section "Surveys".

7. **Check 4 — OWD sharing settings** — read `references/checks-org-settings.md` section "OWD Sharing" for the exact objects and expected values.

8. **Check 5 — Inventory Count** — read `references/checks-org-settings.md` section "Inventory Count".

9. **Check 6 — Sales Account Plans** — read `references/checks-org-settings.md` section "Sales Account Plans".

10. **Check 7 — Care Plans** — read `references/checks-org-settings.md` section "Care Plans".

11. **Check 8 — Chatter Settings** — read `references/checks-org-settings.md` section "Chatter Settings".

12. **Check 9 — Data Protection and Privacy** — read `references/checks-org-settings.md` section "Data Protection and Privacy".

13. **Check 10 — Multiple Currencies** — read `references/checks-org-settings.md` section "Multiple Currencies".

14. **Check 11 — State and Country/Territory Picklists** — read `references/checks-org-settings.md` section "State and Country/Territory Picklists".

15. **Check 12 — Person Accounts** — read `references/checks-org-settings.md` section "Person Accounts".

### Phase 3 — Report

16. **Generate consolidated report** — present results in a table:

```markdown
| # | Prerequisite                              | Status | Remediation (if failed/warning)  |
|---|-------------------------------------------|--------|----------------------------------|
| 1 | System Administrator + Permission Sets    | PASS/FAIL | <steps if failed>            |
| 2 | Life Sciences CE Enabled                  | PASS/FAIL | <steps if failed>            |
| ...                                                                                       |
```

Status values are **PASS**, **FAIL**, or **WARNING**. Most checks are PASS/FAIL. The **OWD Sharing** check (Check 4) is WARNING-level: when its values differ from the expected ones, report **WARNING** (with the recommended value in the remediation column), never FAIL — see `references/checks-org-settings.md` for the exact rule.

Include a summary line: `X of 12 prerequisites passed. Y require action (Z warnings).`

If all pass, confirm the org is ready for Life Sciences Cloud deployment.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Run all checks even if early ones fail | Admin needs the full picture to remediate in one pass |
| Use `sf` CLI with `--target-org` for every query | Ensures correct org context even with multiple orgs authenticated |
| Never modify org settings | This skill validates only — it does not enable or configure anything |
| Report exact Setup navigation paths | Admins need to know where to click in Setup UI |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Some settings are not queryable via Metadata API | Use Tooling API or org settings queries where Metadata API lacks coverage |
| Person Accounts cannot be disabled once enabled | Only check if enabled; no rollback possible |
| Multiple Currencies cannot be disabled once activated | Only check if activated; warn that this is irreversible if recommending enablement |
| State/Country Picklists enabling is irreversible | Include this warning in remediation steps |

---

## Output Expectations

Deliverables:
- A formatted table showing pass/fail status for all 12 prerequisite categories
- Remediation steps (Setup navigation paths and actions) for each failed check
- Summary count of passed vs. failed checks

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/checks-user-and-package.md` | During Phase 2 (checks 3–6) — exact sf CLI commands, expected values, and remediation for the user profile/permission-set, managed-package, Life Sciences CE feature, and survey checks |
| `references/checks-org-settings.md` | During Phase 2 (checks 7–15) — exact sf CLI commands, expected values, and remediation for the OWD sharing, inventory, account plans, care plans, chatter, data protection, currencies, picklists, and person-accounts checks |
