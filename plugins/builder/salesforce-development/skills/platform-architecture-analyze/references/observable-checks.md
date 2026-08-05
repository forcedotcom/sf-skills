# Observable Checks — detection map

Each `[observable]` criterion from `well-architected-rubric.md`, mapped to **how to detect it** (preferred skill/MCP tool first, grep fallback) and **the anti-pattern it flags**. Delegate to the named skill when available; use the grep/Bash pattern for lightweight structural signals or when the skill/tool is unavailable.

Conventions below: `<pkg>` = a package directory from `sfdx-project.json` (usually `force-app`).

---

## 🛡️ Trusted

### Secure

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| Sharing keyword on every class | `grep -rLE 'with(out)? sharing\|inherited sharing' --include='*.cls' <pkg>` (lists files with NO sharing keyword) | `ApexSharingViolations` — class omits sharing declaration |
| FLS/CRUD enforced | `dx-code-analyzer-run` (rule `ApexCRUDViolation`); grep `grep -rn 'WITH USER_MODE\|WITH SECURITY_ENFORCED\|stripInaccessible\|AccessLevel.USER_MODE' --include='*.cls' <pkg>` to confirm enforcement present | SOQL/DML with no FLS check |
| No SOQL injection | `dx-code-analyzer-run` (rule `ApexSOQLInjection`); grep dynamic SOQL: `grep -rn 'Database.query\|Database.getQueryLocator' --include='*.cls' <pkg>` then inspect for string concat vs `:bind` | User input concatenated into SOQL |
| No hard-coded secrets | `grep -rnE "(password\|secret\|api[_-]?key\|token)\s*=\s*'[^']+'" --include='*.cls' <pkg>` ; check for inline endpoint URLs | Credentials in code instead of Named Credentials |
| HTTPS callouts / safe crypto | `dx-code-analyzer-run` (`ApexInsecureEndpoint`, `ApexBadCrypto`); grep `grep -rn "'http://" --include='*.cls' <pkg>` | `http://` endpoints; hard-coded IV/key |
| Internal OWD not Public R/W | `platform-metadata-retrieve` + `sf org` inspection (org-connected) — inspect `<sharingModel>` in object metadata: `grep -rn '<sharingModel>' <pkg> ` | OWD ReadWrite without justification |

### Compliant *(mostly manual — weak file signals only)*

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| Accessibility practice in LWC | grep LWC templates for inputs without `label`/`aria-`: `grep -rn '<input\|<lightning-input' <pkg> --include='*.html'` (inspect) | Inputs lacking labels; color-only cues |
| Translatable strings | grep for hard-coded user-facing text vs `$Label`: `grep -rn '{!\$Label\|@salesforce/label' <pkg>` (presence is a positive signal) | Hard-coded text instead of Custom Labels |

> Most Compliant criteria are governance — push to the manual checklist.

### Reliable

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| Bulkified DML/SOQL | `dx-code-analyzer-run` (`OperationWithLimitsInLoop`) — primary | SOQL or DML inside a loop |
| Selective SOQL | `platform-lsp-integrate` → `check_soql_selectivity`; grep `grep -rniE 'LIKE .%|ALL ROWS' --include='*.cls' <pkg>` | Leading-wildcard `LIKE`, `ALL ROWS`, non-selective filters |
| No expensive ops in loops | `dx-code-analyzer-run` (`OperationWithHighCostInLoop`) | `Schema.describe*` / callouts in loops |
| Async for heavy work | grep `grep -rln 'implements Queueable\|implements Database.Batchable\|@future' --include='*.cls' <pkg>` (presence is positive; all-sync heavy logic is the smell) | Heavy/after-commit work forced synchronous |

---

## ⚡ Easy

### Intentional

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| No legacy automation | `find <pkg> -name '*.workflow-meta.xml' -o -name '*.flowDefinition-meta.xml'` ; for Process Builder, grep flow files for `<processType>Workflow</processType>` | Workflow Rules / Process Builder still active |
| No `@future` (prefer Queueable) | `grep -rln '@future' --include='*.cls' <pkg>` | `@future` instead of Queueable |
| Modern API version | `grep -rn '<apiVersion>' <pkg> --include='*.xml' \| awk -F'[<>]' '$3 < 30'` ; check `sourceApiVersion` in `sfdx-project.json` | API version < 30.0 |
| No duplicated standard objects | `find <pkg> -path '*objects*' -name '*__c.object-meta.xml'` then compare base names to standard objects (Account, Contact, Case, Order, …) | `Account__c`, `Case__c` duplicating standard objects |
| Readable naming | Inspect class/object/field names for `Test1`, `tmp`, `asdf`, single letters | Throwaway/cryptic names in committed metadata |
| Documentation present | `grep -rL '/\*\*\|//' --include='*.cls' <pkg>` (files with no comments at all) | Undocumented classes |

### Automated

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| Single-purpose Flows | Inspect Flow metadata count of distinct triggers/objects per flow | One flow doing many unrelated jobs |
| Try-catch around DML/SOQL/callouts | `grep -rLn 'try' --include='*.cls' <pkg>` cross-referenced with files doing DML/callouts | Unhandled DML/SOQL/callout |
| No debug in prod | `dx-code-analyzer-run` (`AvoidDebugStatements`); `grep -rn 'System.debug' --include='*.cls' <pkg>` | `System.debug` left in production paths |
| Sync-before / async-after | Inspect trigger handlers: DML in `after` contexts vs queued | DML in after-context blocking the transaction |

### Engaging *(manual — UX)*

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| LDS over custom Apex for simple CRUD | grep LWC for `lightning/uiRecordApi` vs `@salesforce/apex`: `grep -rln 'lightning/uiRecordApi' <pkg>` | Hand-rolled Apex controllers for simple record CRUD |

---

## 🔁 Adaptable

### Resilient

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| Source-tracked + CI | `test -d .git` ; `ls .github/workflows/*.yml 2>/dev/null` | No CI; not under source control |
| Source/package deploys (not change sets) | `ls manifest/package.xml` (past PoC = smell); confirm `packageDirectories` in `sfdx-project.json` | `package.xml`-driven deployment as the model |
| Meaningful tests | `find <pkg> -name '*Test.cls'` count vs class count; `grep -rln 'SeeAllData=true' --include='*.cls' <pkg>` ; check `System.assert` presence | No tests; `SeeAllData=true`; coverage-padding with no assertions |

### Composable

| Criterion | Detection | Anti-pattern flagged |
|---|---|---|
| Thin triggers → handlers | `grep -rEn 'SELECT\|insert \|update \|delete \|for *\(' --include='*.trigger' <pkg>` (logic/SOQL/DML/loops inside `.trigger` = smell) | Business logic in trigger body |
| CMT over Custom Settings | `find <pkg> -name '*.md-meta.xml'` (CMT, positive) vs custom settings: `grep -rln '<customSettingsType>' <pkg>` | Custom Settings / custom objects holding runtime config |
| Eventing for decoupling | `find <pkg> -name '*__e.object-meta.xml'` ; `grep -rln 'EventBus.publish' --include='*.cls' <pkg>` (presence positive where hand-offs exist) | Tight synchronous coupling for cross-domain hand-offs |
| Packageable + `LATEST` aliasing | `grep -n 'LATEST\|"versionNumber"' sfdx-project.json` ; check `packageDirectories` structure | Explicit pinned deps; no package strategy |
| No unmanaged packages committed | `grep -rln 'installedPackages' <pkg>` ; look for `*.installedPackage-meta.xml` | Unmanaged package artifacts in prod source |
| No duplicated metadata across pkg dirs | Compare component names across multiple `packageDirectories` paths | Same metadata in two package dirs |

---

## Mapping `dx-code-analyzer-run` severities → pillars

When `dx-code-analyzer-run` returns findings, map by rule:

| Rule | Pillar / Sub-pillar | Severity → review verdict |
|---|---|---|
| `ApexSOQLInjection` | Trusted / Secure | Critical → ❌ |
| `ApexCRUDViolation` | Trusted / Secure | High → ❌/⚠️ |
| `ApexInsecureEndpoint`, `ApexBadCrypto`, `ApexOpenRedirect` | Trusted / Secure | High → ⚠️ |
| `ApexSharingViolations` | Trusted / Secure + Adaptable / Composable | Moderate → ⚠️ |
| `OperationWithLimitsInLoop` | Trusted / Reliable + Easy / Automated | Moderate → ⚠️ (❌ if widespread) |
| `OperationWithHighCostInLoop` | Trusted / Reliable | Moderate → ⚠️ |
| `AvoidDebugStatements` | Easy / Automated | Low → note |
| `AvoidNonRestrictiveQueries` | Trusted / Reliable | Low → ⚠️ |

## Notes

- Prefer the skill/MCP tool over grep — `dx-code-analyzer-run` understands Apex structure; grep finds string patterns and over/under-reports. Use grep for structural/file-type signals (sharing keyword presence, legacy file types, deploy strategy) where a string match is reliable.
- Quote glob patterns passed to tools to stop the shell expanding them.
- A grep "hit count" is a signal, not a verdict — open the file and confirm before scoring a finding.
- Org-connected checks (OWD, permission sets) require `sf org display` to succeed; otherwise mark them manual.
