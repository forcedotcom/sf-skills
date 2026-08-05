# Manual Review Checklist — governance & process

These are the Well-Architected criteria a local SFDX repo **cannot reveal**. The reviewer copies them into the report under **"MANUAL REVIEW — not auto-graded; assess with your team."** Do **not** score these from inference — they exist to hand the developer a structured governance checklist, not to fake a grade.

Copy the relevant blocks verbatim into the report as unchecked `[ ]` items.

---

## 🛡️ Trusted

### Secure (organizational / session)
- [ ] A **security matrix** maps every persona and integration to its authentication scheme and authorized data access.
- [ ] MFA enforced for interactive logins; user-to-entity is 1:1 (no shared accounts).
- [ ] Each integration uses a **unique API-only** integration user (not a person's account).
- [ ] Permission sets/groups are capability-based; profiles used minimally (IP ranges, login hours only).
- [ ] Session timeout ≤ 2h; clickjack, CSRF, XSS, content-sniffing, and redirect protections enabled.
- [ ] Credentials live in **Named Credentials**; nothing secret is readable in code or config.
- [ ] Encryption-at-rest (Shield / Hyperforce) applied where data sensitivity requires; in-transit protocols documented.

### Compliant
- [ ] Up-to-date **data dictionary** with Compliance Categorization, Data Owner, and Sensitivity Level on objects/fields.
- [ ] Data **residency** and cross-border replication strategy documented.
- [ ] Analytics granularity (region / nation / global) defined per compliance needs.
- [ ] **AI ethics:** training/RAG datasets are representative, complete, accurate, up-to-date.
- [ ] **AI ethics:** bias, explainability, and robustness assessed; "human at the helm" for high-risk / low-confidence cases.
- [ ] **AI transparency:** generative responses identify their data sources; bots are clearly identified to users.
- [ ] **AI monitoring:** data drift, fairness/bias scores, accuracy, and robustness tracked over time.
- [ ] **Accessibility:** tested across devices and assistive tech; keyboard focus visible; navigation not color-only; forms have labels, helpful errors, review/edit; translations in Translation Workbench.

### Reliable
- [ ] **Risk assessment** framework: risks categorized by people / process / technology and by customer impact; mitigation plans prioritized.
- [ ] Failure triggers and mitigation plans classified; controls automated early; mitigations revisited/improved.
- [ ] **Proactive Monitoring** / Scale Center enabled for anomaly detection; alerts integrated.
- [ ] **Scale / endurance testing** performed before business-critical events.
- [ ] **Archiving / purging** strategy documented and implemented for large data volumes; no data skew (>10k child/owner/lookup).

---

## ⚡ Easy

### Intentional
- [ ] Every work item has a clear, **measurable business-value** metric.
- [ ] Roadmaps prioritized by value, show dependencies and dates, and are maintained (not just kickoff slides).
- [ ] **Standard-vs-custom** decision principle documented: platform services → AppExchange → low-code → code.
- [ ] **Technical-debt registry** with deliverables, dates, and KPIs; trade-offs framed in business terms.
- [ ] Environment strategy and clear **hot-fix path** documented; approved AI models only.
- [ ] Documentation exists and is searchable: solution overview diagrams, **decision records** (options/trade-offs/rationale), code provenance logs.

### Automated
- [ ] Each automated process has **measurable, timebound** inputs/outputs and a named accountable stakeholder.
- [ ] Process KPIs surfaced in reports.
- [ ] "Fatal" vs "recoverable" error semantics defined; user-triggered automations notify users **before** committing changes.

### Engaging
- [ ] UX is streamlined — fewer clicks, clear value — informed by user research / journey mapping.
- [ ] Helpful, guided experiences for the primary personas.

---

## 🔁 Adaptable

### Resilient
- [ ] **Non-functional requirements / SLOs** defined for the next 1–3 years (the experience you want users to have, what you measure, over what period).
- [ ] Release management uses unlocked packages / DevOps Center / source-format deploys; **no failed-deployment** history.
- [ ] Clear release **cadence** with searchable, feature-tied release names; gen-AI quality thresholds defined per stage.
- [ ] Environment strategy: source-driven, source tracking on, metadata independent of release artifacts, **risk-based** release paths; no risky changes in prod at peak.
- [ ] **Recovery** protocols practiced regularly; service ownership and tooling known; recovery scripts repeatable; session-based permission sets for incident response.
- [ ] **Triage:** SMEs identified before incidents; handoff part of go-live; logging + custom error messages in execution paths.
- [ ] **Monitoring/alerting:** alerts only for human-intervention scenarios, delivered before failure, to those who can respond.
- [ ] **Business continuity plan** with triggers, steps, intervals, and dependencies; process + people areas tested; "recovery-first" mindset.
- [ ] **Backup:** strategy for both data **and** metadata; backups secured and human-readable; restores tested 2×/year in a Full/Partial Copy sandbox.

### Composable
- [ ] Naming conventions denote **functional units**; a defined list of units exists with change standards; landscape diagrams map components to units; units labeled in business terms.
- [ ] **State management:** stateful vs stateless use cases defined; Savepoints and rollback (Flow fault paths + Roll Back Records) used in data operations.
- [ ] **APIs** as predictable versioned contracts (one version per API), discoverable and documented; formats defined via CMT / platform events.
- [ ] **Messaging/eventing:** sync vs async use cases identified; data structures right-sized; platform events labeled; consistent patterns across Flow and code.
- [ ] **Dependency management:** hand-offs via messaging/eventing; dependency chains monitored; `LATEST` aliasing in `sfdx-project.json`; developers can build scratch orgs from source.
- [ ] **Packaging end goal:** loosely coupled packages; no unmanaged packages in prod/sandbox; org-dependent unlocked packages only for early-stage.

---

Source: Salesforce Well-Architected — https://architect.salesforce.com/docs/architect/well-architected/guide/overview.html
