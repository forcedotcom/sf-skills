# OmniSupervisorConfig — API notes

Load this reference **only when the deploy fails or Salesforce reports unexpected state**. Under normal operation the skill's `deploy-and-report.sh` just runs and emits its JSON; this doc is for troubleshooting and future extensions.

**Metadata type:** `OmniSupervisorConfig` (dir `omniSupervisorConfigs`, suffix `omniSupervisorConfig`)
**API version:** v66. **Available in the Metadata API since:** v57 (Winter '23).

---

## Why Metadata deploy (not REST POST)

`OmniSupervisorConfig` is a Metadata API type (since v57), so this skill deploys it as metadata rather than driving a REST POST loop per companion. Every companion sObject (User/Group/Profile/Queue/Skill/Action/Tab) embeds inside the parent as `maxOccurs="unbounded"` elements per the Metadata SOAP XSD.

Trade-off analysis:

| Dimension | REST POST (per-companion loop) | Metadata deploy (this skill) |
|-----------|-----------------|------------------------------|
| API calls | 8+ (1 parent + N companion POSTs) | 1 |
| Idempotency logic | Custom SOQL detect + skip in script | Platform-managed via `state:Unchanged` |
| Atomicity | Partial state on mid-flight failure | All or nothing |
| Source control | Detect scripts + JSON payloads | Single XML file, diff-friendly |
| Rollback | Manual cleanup on error | Automatic |
| Skill script size | ~200 lines | ~150 lines (mostly per-org discovery) |
| Alignment with other skills | Different pattern | Same as ServiceChannel and PresenceStatus skills |

---

## Metadata SOAP XSD (v66, from core/shared/submodules/wsdl)

```xml
<xsd:complexType name="OmniSupervisorConfig">
  <xsd:extension base="mns:Metadata">
    <xsd:sequence>
      <xsd:element name="isTimelineHidden" type="xsd:boolean"/>
      <xsd:element name="masterLabel" type="xsd:string"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSpvsrConfigAIAgent" type="mns:OmniSpvsrConfigAIAgent"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigAction" type="mns:OmniSupervisorConfigAction"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigGroup" type="mns:OmniSupervisorConfigGroup"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigProfile" type="mns:OmniSupervisorConfigProfile"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigQueue" type="mns:OmniSupervisorConfigQueue"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigSkill" type="mns:OmniSupervisorConfigSkill"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigTab" type="mns:OmniSupervisorConfigTab"/>
      <xsd:element maxOccurs="unbounded" minOccurs="0" name="omniSupervisorConfigUser" type="mns:OmniSupervisorConfigUser"/>
      <xsd:element minOccurs="0" name="skillVisibility" type="tns:OmniSuperSkillVisibilityType"/>
    </xsd:sequence>
  </xsd:extension>
</xsd:complexType>
```

## Companion field definitions (all verified against v66 SOAP XSD)

| Companion | Fields | Notes |
|-----------|--------|-------|
| `omniSupervisorConfigUser` | `user` (Username) | Which supervisor(s) this config applies to |
| `omniSupervisorConfigQueue` | `queue` (Queue DeveloperName) | Queues shown in supervisor's queue-monitoring panel |
| `omniSupervisorConfigProfile` | `profile` (Profile **metadata fullName**, NOT the SOQL `User.Profile.Name` label — see note below) | Agent profiles the supervisor can see |
| `omniSupervisorConfigGroup` | `group` (Public Group DeveloperName) | Agent group scope (optional, we omit) |
| `omniSupervisorConfigSkill` | `skill` (Skill DeveloperName) | Skills the supervisor can filter by (optional, we omit) |
| `omniSupervisorConfigAction` | `actionName` (enum), `actionTab` (enum), `customActionFlow` (string, optional), `displayOrder` (int) | Which action buttons render; enums NOT yet exhaustively documented — v1 omits, uses platform defaults |
| `omniSupervisorConfigTab` | `displayOrder` (int), `flexiPage` (string, optional), `tabType` (enum) | Which tabs show; enums NOT yet exhaustively documented — v1 omits, uses platform defaults |

**Important:** `omniSpvsrConfigAIAgent` also embeds but requires bots enabled + UDD 256-era APIs. Kept out of scope until we have a bot to bind.

---

## The canonical template shipped by this skill

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OmniSupervisorConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Omni Supervisor Config</masterLabel>
    <isTimelineHidden>false</isTimelineHidden>
    <skillVisibility>All</skillVisibility>
    <omniSupervisorConfigUser>
        <user>{supervisor_username}</user>
    </omniSupervisorConfigUser>
    <omniSupervisorConfigProfile>
        <profile>Standard</profile>  <!-- metadata fullName; NOT the "Standard User" label -->
    </omniSupervisorConfigProfile>
    <omniSupervisorConfigQueue>
        <queue>CaseQueue</queue>
    </omniSupervisorConfigQueue>
    <omniSupervisorConfigQueue>
        <queue>messagingqueue</queue>
    </omniSupervisorConfigQueue>
</OmniSupervisorConfig>
```

`__SUPERVISOR_USERS_XML__` gets replaced with 1..N `<omniSupervisorConfigUser>` blocks (per `supervisor_count`).
`__QUEUE_LIST_XML__` gets replaced with 1..N `<omniSupervisorConfigQueue>` blocks (canonical + `additional_queues_csv`).

---

## Idempotency contract

Salesforce Metadata deploy response `files[].state` field:

| `state` | Meaning | Skill-level `status` |
|---------|---------|---------------------|
| `Unchanged` | Payload matched org state byte-for-byte | `reused` |
| `Changed` | Config existed, some fields differed and were updated | `updated` |
| `Created` | Config did not exist, freshly created | `created` |
| `Failed` / other | Deploy did not succeed | `blocked` |

Re-running with no template drift returns `status: reused` in ~3 seconds. Adding a new supervisor to the org and re-running returns `status: updated` (adds the companion binding); no need to detect-before-POST because the template regeneration handles the delta.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `INVALID_TYPE: OmniSupervisorConfig` on deploy | Deploying against pre-v57 org | Bump target `sourceApiVersion` to 57.0+ (v66 recommended) |
| `INVALID_FIELD: <fieldname>` on companion | Guessed enum value (actionName / tabType) | v1 template omits action + tab elements; if adding, retrieve a working config from another org first |
| `DUPLICATE_VALUE` on User binding | Same user already bound to another OmniSupervisorConfig | Salesforce allows one supervisor per config; if binding to multiple configs needed, split into separate configs |
| `INVALID_PERSON_OR_GROUP_ID` on queue | Queue DeveloperName typo or queue absent | Verify with: `sf data query -q "SELECT DeveloperName FROM Group WHERE Type='Queue'"` |
| Deploy hangs > 10 min | Retry storm or org load issue | Retrieve deploy status: `sf project deploy report --job-id <id>` |

---

## Post-deploy SOQL verification

```sql
-- 1. Config exists
SELECT Id, DeveloperName, MasterLabel, CreatedDate
FROM OmniSupervisorConfig
WHERE DeveloperName='Omni_Supervisor'

-- 2. Supervisor bindings
SELECT UserId, User.Username
FROM OmniSupervisorConfigUser
WHERE OmniSupervisorConfigId IN (SELECT Id FROM OmniSupervisorConfig WHERE DeveloperName='Omni_Supervisor')

-- 3. Queue bindings
SELECT QueueId, Queue.DeveloperName
FROM OmniSupervisorConfigQueue
WHERE OmniSupervisorConfigId IN (SELECT Id FROM OmniSupervisorConfig WHERE DeveloperName='Omni_Supervisor')

-- 4. Profile scope
SELECT ProfileId, Profile.Name
FROM OmniSupervisorConfigProfile
WHERE OmniSupervisorConfigId IN (SELECT Id FROM OmniSupervisorConfig WHERE DeveloperName='Omni_Supervisor')
```

Expected: 1 config, N supervisor bindings (matches `supervisor_count`), M queue bindings (matches `ALL_QUEUES` after discovery filter), and 1+ profile scope rows (one per resolved agent profile).

## Profile fullName vs. User.Profile.Name

The `<profile>` element resolves against a profile's **metadata fullName**, which for standard profiles differs from the SOQL `User.Profile.Name` label:

| `User.Profile.Name` (SOQL label) | Metadata `<profile>` fullName |
|----------------------------------|-------------------------------|
| `Standard User`                  | `Standard`                    |
| `Service Cloud`                  | `ServiceCloud`                |
| `System Administrator`           | `Admin`                       |
| Custom profiles                  | same as the profile Name      |

Deploying a raw SOQL label fails with `In field: profile - no Profile named <label> found`. Profile companions are optional (omitted by default, since supervisors are bound by user); when you pass `profiles_csv`, supply metadata fullNames and `deploy-and-report.sh` validates each against `sf org list metadata -m Profile`, blocking on any the org does not expose. Get the exact fullNames for an org with:

```bash
sf org list metadata -m Profile -o <org> --json | jq -r '.result[].fullName'
```

## Idempotency signal

`deploy-and-report.sh` maps the Metadata deploy component state to the skill status: `Unchanged` → `reused`, `Changed` → `updated`, `Created` → `created`. Any unrecognized state blocks rather than silently reporting `reused`. The `config_id` is stable across runs and no companion rows are duplicated on redeploy.

---

## Deploy robustness — async + poll (not synchronous `--wait`)

`OmniSupervisorConfig` deploys are done **async**, then polled to a terminal state:

```bash
id=$(sf project deploy start --manifest package.xml --target-org "$ORG" --async --json | jq -r '.result.id')
# poll until Succeeded | Failed | SucceededPartial | Canceled (each report call returns immediately)
sf project deploy report --job-id "$id" --target-org "$ORG" --json
```

**Why not `--wait N`:** under heavy CDO load a synchronous `sf project deploy start --wait` can raise
`ClientTimeoutError` and exit non-zero even though the server-side deploy succeeds — a false failure.
Async start returns a job id instantly; polling `deploy report` in a loop means no single CLI call
can client-timeout, so the terminal server-side status is always the authority. Budget the poll loop
above the slowest deploy/retrieve you expect on a loaded org — the script uses ~20 min.

## Post-deploy verify — bounded retry with backoff

The deploy async+poll above protects the *deploy*; the post-deploy **verification** SOQL reads
(config_id fetch + companion `OmniSupervisorConfigUser`/`OmniSupervisorConfigQueue` counts) are the
remaining latency-fragile step. A slow/dropped query, or the just-persisted record/child rows not
yet visible, could otherwise flip an otherwise-successful deploy to blocked. Each verification read is therefore wrapped in a
**bounded retry loop with backoff** (5 attempts, 10→40s increasing sleeps): retry while the read is
inconclusive (not a parseable records array) *or* the count is still below what the deploy was asked
to bind, then fall through to the existing guards. **Fail-closed is preserved**: after the budget,
an inconclusive read still blocks, an empty/missing config Id still blocks, and a short companion
count still blocks as under-provisioned — retries only survive transient org latency, they never
manufacture success.

## Possible extensions

1. **Add a default action bar** — retrieve a working config from a full CDO to get valid `actionName` / `actionTab` enum values, then bake them into the template.
2. **Add a default tab list** — same as above for `tabType` enum values.
3. **Support `omniSupervisorConfigGroup`** — scope by Public Group in addition to profile.
4. **Support `omniSupervisorConfigSkill`** — scope by Skill for skill-based supervisors.
5. **Support `omniSpvsrConfigAIAgent`** — bind an Agentforce agent once one is available on the org.
