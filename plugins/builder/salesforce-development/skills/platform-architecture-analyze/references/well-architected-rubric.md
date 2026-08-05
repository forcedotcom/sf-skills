# Salesforce Well-Architected — Review Rubric

Distilled from the [Salesforce Well-Architected framework](https://architect.salesforce.com/docs/architect/well-architected/guide/overview.html). This is the criteria tree the `reviewing-architecture` skill scores against.

Each criterion is tagged:
- **`[observable]`** — gradable from the local repo (code + metadata) or a connected org. The reviewer scores these with `file:line` evidence. See `observable-checks.md` for the detection method.
- **`[manual]`** — a governance / process / human concern the repo cannot reveal. The reviewer lists these in the human checklist (`manual-review-checklist.md`); it never scores them from inference.

The framework has **three pillars**, each with **sub-pillars**:

> **🛡️ Trusted** protects stakeholders · **⚡ Easy** delivers value fast · **🔁 Adaptable** evolves with the business.

---

## 🛡️ TRUSTED

### Secure — organizational, session, and data security

- `[observable]` Every Apex class declares a sharing keyword (`with sharing` / `without sharing` justified / `inherited sharing`).
- `[observable]` SOQL/DML enforce FLS/CRUD — `WITH USER_MODE` / `WITH SECURITY_ENFORCED` on queries, `AccessLevel.USER_MODE` or `stripInaccessible` on DML.
- `[observable]` No SOQL injection — dynamic SOQL uses bind variables (`:var`), not string concatenation of user input.
- `[observable]` No hard-coded credentials/secrets in code; callouts use Named Credentials, not inline URLs/tokens.
- `[observable]` Callout endpoints use `https://` (no `ApexInsecureEndpoint`); crypto uses generated keys/IVs (no `ApexBadCrypto`).
- `[observable]` Internal OWD not Public Read/Write without justification *(org-connected)*.
- `[manual]` Security matrix maps every persona/integration to its authentication scheme and data access.
- `[manual]` MFA enforced; user-to-entity is 1:1 (no shared accounts); unique API-only user per integration.
- `[manual]` Session timeout ≤ 2h; clickjack/CSRF/XSS/content-sniffing protections enabled.
- `[manual]` Encryption-at-rest (Shield/Hyperforce) where data sensitivity requires it; protocols documented.

### Compliant — legal adherence, ethical standards, accessibility

- `[observable]` UI components show evidence of accessibility practice (labels on inputs, no color-only cues in LWC templates) — *partial signal only*.
- `[observable]` Translatable strings use Custom Labels / Translation Workbench, not hard-coded text — *partial signal*.
- `[manual]` Up-to-date data dictionary with Compliance Categorization, Data Owner, Sensitivity Level on objects/fields.
- `[manual]` Data residency / cross-border replication strategy documented.
- `[manual]` AI: datasets representative; bias/explainability/robustness assessed; "human at the helm" for high-risk cases.
- `[manual]` AI: generative responses identify their data sources; bots clearly identified to users; drift monitored.
- `[manual]` Accessibility tested across devices and assistive tech; keyboard focus visible; multilingual support where needed.

### Reliable — availability, performance, scalability

- `[observable]` Data operations bulkified — DML/SOQL operate on collections, not per-record in loops (`OperationWithLimitsInLoop`).
- `[observable]` SOQL is selective — indexed filters, no leading-wildcard `LIKE`, no `ALL ROWS`, minimal fields, no negative/`!=` filters that force table scans.
- `[observable]` No expensive operations in loops (`Schema.describe*`, callouts) — `OperationWithHighCostInLoop`.
- `[observable]` Async processing used for heavy/after-commit work (Queueable/Batch) rather than forcing it synchronous.
- `[observable]` No data-skew red flags in metadata (e.g. default-owner patterns) — *weak signal*.
- `[manual]` Risk assessment framework; failures categorized by people/process/technology and customer impact.
- `[manual]` Proactive Monitoring / Scale Center enabled; alerts integrated.
- `[manual]` Scale/endurance testing before business-critical events; archiving/purging strategy for LDV.

---

## ⚡ EASY

### Intentional — strategy, maintainability, readability

- `[observable]` No active legacy tech: Workflow Rules, Process Builder, `@future` (prefer Queueable), API version < 30.0, PushTopic/Generic events.
- `[observable]` No custom objects duplicating standard-object names/functionality.
- `[observable]` Consistent, human-readable naming across classes/objects/fields (no `Test1__c`, `tmp`, `asdf`).
- `[observable]` Code is documented — class/method headers, ApexDoc, non-trivial logic explained.
- `[manual]` Work items carry clear business-value metrics; roadmaps prioritized by value and maintained (not just kickoff slides).
- `[manual]` Standard-vs-custom decision principle documented (platform → AppExchange → low-code → code).
- `[manual]` Tech-debt registry with KPIs and dates; trade-offs framed in business terms.
- `[manual]` Solution overview diagrams + decision records (options, trade-offs, rationale) exist and are searchable.

### Automated — efficiency, data integrity

- `[observable]` Each Flow has a single purpose; main/subflow hierarchy; no hard-coded IDs in Flows.
- `[observable]` Each Apex class/method has a single, granular purpose (no god-classes).
- `[observable]` DML/SOQL/callouts wrapped in try-catch; custom exceptions used; Flows have fault connectors.
- `[observable]` No `System.debug` in production code paths (`AvoidDebugStatements`).
- `[observable]` Sync DML reserved for *before* contexts; async (Queueable/Batch) for *after*/heavy work.
- `[manual]` Process inputs/outputs measurable and timebound; accountable stakeholders named; metrics in reports.

### Engaging — streamlined, helpful experiences

- `[observable]` UI uses LWC with Lightning Data Service where appropriate (vs heavy custom Apex controllers for simple CRUD) — *partial signal*.
- `[manual]` UX streamlined — fewer clicks, clear value; user research / journey informs the design.

---

## 🔁 ADAPTABLE

### Resilient — ALM, incident response, continuity

- `[observable]` Source-tracked (git present); CI runs tests on commit (`.github/workflows/` or equivalent).
- `[observable]` Source/package-format deploys, not change sets; `package.xml` only for early-stage/PoC.
- `[observable]` Tests exist and are meaningful (TestDataFactory, not `SeeAllData=true`; assertions present, not just coverage-padding).
- `[manual]` Non-functional requirements / SLOs defined for the next 1–3 years.
- `[manual]` Release cadence with searchable, feature-tied release names; no history of failed deployments.
- `[manual]` Environment strategy (source-driven, source tracking, risk-based release paths); no risky changes in prod at peak.
- `[manual]` Recovery protocols practiced; BCP with triggers/steps/intervals incl. dependencies; backups tested 2×/year.
- `[manual]` Health-check APIs/SLOs; graceful degradation; alerts only for human-intervention scenarios, to those who can act.

### Composable — separation of concerns, interoperability, packageability

- `[observable]` Separation of concerns — thin triggers delegate to handler classes (no logic in triggers); UI ↔ logic ↔ data layered.
- `[observable]` Runtime config in Custom Metadata Types, not Custom Settings or custom objects.
- `[observable]` Platform Events / CDC used for decoupled hand-offs rather than tight synchronous coupling — *where eventing is present*.
- `[observable]` Packageable: source organized into package dirs; `LATEST` aliasing in `sfdx-project.json`; no unmanaged packages committed.
- `[observable]` No duplicated metadata across package directories.
- `[manual]` Naming conventions denote functional units; landscape diagrams map components to units.
- `[manual]` State management: stateful vs stateless patterns defined; Savepoints/rollback used in data operations.
- `[manual]` APIs as versioned contracts (one version per API), discoverable; messaging/eventing data structures right-sized.
- `[manual]` Dependency chains monitored; developers can build scratch orgs from source. End goal: loosely coupled packages.

---

## Scoring guidance

- A sub-pillar is **✅** when no anti-pattern is found across its `[observable]` criteria.
- **⚠️** when low/moderate findings exist, or only some criteria were observable (e.g. no org connected).
- **❌** when a critical/high anti-pattern is present (SOQL injection, FLS bypass, SOQL/DML-in-loop at scale, hard-coded secrets, logic-in-trigger).
- Roll sub-pillars up to a pillar verdict as **worst-of**, noting which sub-pillar drove it.
- Sub-pillars with **no** observable criteria gradable (e.g. Engaging, much of Compliant) are reported as **—** ("not auto-graded") and covered entirely by the manual checklist — this is expected, not a failure.

Source: Salesforce Well-Architected — https://architect.salesforce.com/docs/architect/well-architected/guide/overview.html
