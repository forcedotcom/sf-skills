# Regex Rule Examples

Real-world custom regex rules solving problems from the Code Analyzer community.

## Example 1: Ban Hardcoded Salesforce IDs

**Problem:** Developers hardcode record IDs that differ between orgs.
(GitHub issue #738 — community request for detecting bad patterns)

```yaml
engines:
  regex:
    custom_rules:
      NoHardcodedSalesforceIds:
        regex: "/['\"](?<target>0[a-zA-Z0-9]{14}(?:[a-zA-Z0-9]{3})?)['\"]/g"
        description: "Detects hardcoded 15 or 18 character Salesforce record IDs"
        violation_message: "Replace hardcoded ID with Custom Label, Custom Metadata, or Custom Setting"
        severity: 2
        tags: ["Custom", "Security"]
        file_extensions: [".cls", ".trigger"]
```

**Why this pattern:**
- Salesforce IDs are exactly **15 or 18 characters** (never 16 or 17)
- They always **start with `0`** (the key prefix)
- `0[a-zA-Z0-9]{14}` matches 15-char IDs (0 + 14 more)
- `(?:[a-zA-Z0-9]{3})?` optionally matches the 3-char case-safe suffix (making 18-char)
- `(?<target>...)` narrows the violation highlight to just the ID, not the surrounding quotes
- ⚠️ Do NOT use `{15,18}` — this also matches 16/17 char strings and false-positives on normal words like `'BusinessAccount'` or `'RecordTypeInfos'`

**Note on `regex_ignore`:** This field works **per-line**, not per-file. Adding `/@isTest/` only skips lines that literally contain `@isTest` — it does NOT exclude entire test classes. To exclude test files entirely, use `ignores.files` in `code-analyzer.yml` with a glob like `**/*Test.cls`.

---

## Example 2: Flag TODO/FIXME Before Merge

**Problem:** Developers leave TODOs that never get resolved.

```yaml
engines:
  regex:
    custom_rules:
      NoUnresolvedTodos:
        regex: "/(?:TODO|FIXME|HACK|XXX)\\b/gi"
        description: "Flags unresolved TODO/FIXME comments"
        violation_message: "Resolve this TODO/FIXME before merging to main"
        severity: 4
        tags: ["Custom", "BestPractices"]
```

---

## Example 3: Enforce WITH USER_MODE on SOQL

**Problem:** SOQL queries without FLS enforcement are a security risk.

```yaml
engines:
  regex:
    custom_rules:
      RequireUserModeOnSoql:
        regex: "/\\[\\s*SELECT(?![^\\]]*WITH\\s+(?:USER_MODE|SECURITY_ENFORCED))[^\\]]*\\]/gi"
        description: "SOQL queries must use WITH USER_MODE or WITH SECURITY_ENFORCED"
        violation_message: "Add WITH USER_MODE to this SOQL query for FLS enforcement"
        severity: 2
        tags: ["Custom", "Security"]
        file_extensions: [".cls", ".trigger"]
        regex_ignore: "/@isTest|@IsTest|@testSetup|@TestSetup/"
```

---

## Example 4: Ban @SuppressWarnings and NOPMD

**Problem:** Teams want to prevent suppression of violations.
(GitHub issue #1972 — real user request)

```yaml
engines:
  regex:
    custom_rules:
      ProhibitSuppressWarnings:
        regex: "/@SuppressWarnings\\([^)]*\\)|\\/\\/\\s*NOPMD/gi"
        description: "Prohibits suppression of code analysis warnings"
        violation_message: "Fix the underlying issue instead of suppressing warnings"
        severity: 2
        tags: ["Custom", "BestPractices"]
        file_extensions: [".cls", ".trigger"]
```

---

## Example 5: Detect Old API Versions in Metadata

**Problem:** Metadata files using API versions more than 2 years old.

```yaml
engines:
  regex:
    custom_rules:
      NoOldApiVersions:
        regex: "/<apiVersion>(4[0-9]|5[0-5])\\.0<\\/apiVersion>/g"
        description: "Detects metadata files using API version 55.0 or below"
        violation_message: "Update API version to 60.0 or higher"
        severity: 3
        tags: ["Custom", "BestPractices"]
        file_extensions: [".xml"]
```

---

## Example 6: Enforce Test Class Naming Convention

**Problem:** Test classes should end with `_TEST` or `Test`.

```yaml
engines:
  regex:
    custom_rules:
      TestClassNaming:
        regex: "/@(?:isTest|IsTest)(?:\\([^)]*\\))?\\s*(?:public|private)\\s+class\\s+(?!.*(?:_TEST|Test)\\b)\\w+/g"
        description: "Test classes must end with _TEST or Test suffix"
        violation_message: "Rename this test class to end with _TEST or Test (e.g., MyServiceTest)"
        severity: 3
        tags: ["Custom", "CodeStyle"]
        file_extensions: [".cls"]
```
