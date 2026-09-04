# Phase 5a / 5b — Generate + deploy the Apex class, register + wire the step

Detailed runbook for the two write phases. `SKILL.md` Phase 5a/5b link here.
Both phases run only on a green Phase 4 and a confirmed Phase 5 interview.
`PREFIX_DOT` / `PREFIX_UNDER` come from the Phase-1 namespace detection.

## Phase 5a — Generate + deploy the customer's Apex class

1. **Idempotency guard** — is the class name already taken?

   ```bash
   sf data query --target-org <alias> --json --query "
     SELECT NamespacePrefix FROM ApexClass WHERE Name = '<stepName>'
   "
   ```

   Non-empty and non-namespaced → an ApexClass by that name already exists in
   the customer's namespace. Ask: overwrite (redeploy same name), rename the
   interview answer, or abort. Namespaced → a *packaged* class with that name
   (unexpected); stop and ask before overwriting anything.

2. **Confirm target-field writeability.** For every entry in `outputWrites`,
   describe the resolved field `${PREFIX_UNDER}<field>` on
   `${PREFIX_UNDER}<entity>__c` and verify `createable=true, updateable=true`
   for the running user. Any failure → stop, print the failing field + FLS
   remediation.

3. **Generate the Apex class from the interview.** The generator takes the
   schema captured in the interview (Phase 5.1) and emits a namespace-agnostic
   Callable in the same shape as the reference example
   (`references/reference-example-set-comment-value.md`). Rules (do not deviate):
   - Declare the class **`global`** and the `call` method **`global`** — `global with sharing class <stepName> implements Callable { global Object call(...) }`. This is REQUIRED, not stylistic: on a managed-INSTALLED org the packaged `CallableManager` resolves/invokes this subscriber class across the namespace boundary via `Type.forName`, which cannot see a `public` class — the step then fails at *runtime* with `Type "<stepName>" does not exist` and the transaction-log row lands in `Error` (the class still shows `Active`, so this is invisible until an ingest runs). `public` only works on a same-namespace source/dev org (e.g. a `cgcloud_dev` scratch org); `global` works on both. Inner exception types may stay `public`.
   - `implements Callable`; single `Object call(String action, Map<String, Object> context)` method.
   - Guard `action != <actionName>` with a class-specific exception.
   - Read `context.get('currentInput')` (Map) and `context.get('currentOutput')` (SObject) — these are the keys `BoTransformationEngine` seeds (verified at `BoTransformationEngine.cls:825-864`).
   - Compute the namespace prefix from `String.valueOf(output.getSObjectType())` at runtime (see the reference example for the exact substring logic). Never emit a compile-time `<ns>__` prefix.
   - For each `outputWrite`, resolve the source value from `currentInput` (via the `inputPaths` map), apply any preconditions, then call `output.put(prefix + '<field>', ...)`.
   - Return `null`.

   Materialize the generated source into a **project-relative** working tree —
   never `/tmp`. Generated deployment artifacts must stay inside the project so
   the workflow is portable and auditable (add `./.promotion-bo-api-deploy/` to
   `.gitignore`; it is ephemeral scratch):

   ```text
   ./.promotion-bo-api-deploy/
     sfdx-project.json
     force-app/main/default/classes/
       <stepName>.cls
       <stepName>.cls-meta.xml
   ```

   `sfdx-project.json`:
   ```json
   {
     "packageDirectories": [{ "path": "force-app", "default": true }],
     "sourceApiVersion": "60.0"
   }
   ```

   `<stepName>.cls-meta.xml`:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
       <apiVersion>60.0</apiVersion>
       <status>Active</status>
   </ApexClass>
   ```

4. **Show the user the generated class + confirm.** Print the full
   `<stepName>.cls` body and ask "Deploy this? [y/N]". `n` → save to
   `./.promotion-bo-api-deploy/` and exit; the user can hand-edit and re-run
   with `--interview-file` pointing at their tweaked answers, or drop their own
   `.cls` into the temp tree before re-invoking. `y` → deploy.

5. **Deploy:**

   ```bash
   sf project deploy start \
     --target-org <alias> \
     --source-dir ./.promotion-bo-api-deploy/force-app \
     --wait 10 --json
   ```

   On `--dry-run`, add `--dry-run` (fall back to `--check-only` on older CLIs).
   Non-success → stop, print `result.details.componentFailures`.

## Phase 5b — Register + wire the step (into the user-chosen workflows)

Insert one `${PREFIX_UNDER}BO_API_Workflow_Step__c` record for the generated
class, then one `${PREFIX_UNDER}BO_API_Workflow_Workflow_Step__c` junction per
**`workflows`** entry from the interview (subset of `{create, update, copy}` —
never assume all three).

Rationale (do not skip):
- Store the **bare** class name (`<stepName>`) in `Classname__c`. The packaged `CallableManager` resolves it against the caller's namespace, so `Classname__c` never carries the `cgcloud`/`cgcloud_dev` prefix. (Every shipped seed row uses a bare name.)
- Compute `Sort__c` per workflow. If the interview supplied a `sortAfter` step name, resolve its junction row for the target workflow and use `sortAfter.Sort__c + 5`. Otherwise use `max(existing sort in that workflow) + 10`.
- `derive` is never wired by this skill. If the user selected `derive`, print "the `derive` workflow is out of scope for this skill — a follow-up skill will handle it" and drop it.

Do the whole thing in a single anonymous-Apex transaction to avoid partial
state. Placeholders in `<...>` come from the Phase 5 interview:

```apex
// ./.promotion-bo-api-deploy/register-step.apex
String salesOrg = '<salesOrg>';
String stepName = '<stepName>';           // e.g. 'SetCommentValue'
String actionName = '<actionName>';       // e.g. 'setCommentValue'
String entityName = '<entity>';           // e.g. 'Tactic'
String description = '<description>';
List<String> workflows = new List<String>{ <workflows-as-quoted-csv> };  // e.g. 'create','update','copy'
List<String> inputPaths = new List<String>{ <inputPaths-as-quoted-csv> };  // e.g. '.Comment' from the interview inputPaths
String inputPathType = '<inputPathType>';  // one of: String, Array, Boolean, Number, Object (SIS RecordType)

// Query the entity id (packaged)
List<${PREFIX_DOT}BO_API_Entity__c> entity = [
  SELECT Id FROM ${PREFIX_DOT}BO_API_Entity__c
   WHERE Name = :entityName
   LIMIT 1
];
if (entity.isEmpty()) {
  throw new CGCloudException(entityName + ' BO API entity not found for sales org ' + salesOrg);
}

// Upsert the step (Unique_Key__c is a writable external id — caller must set it)
${PREFIX_DOT}BO_API_Workflow_Step__c step = new ${PREFIX_DOT}BO_API_Workflow_Step__c(
  Name = stepName,
  ${PREFIX_DOT}Classname__c = stepName,
  ${PREFIX_DOT}Method__c = actionName,
  ${PREFIX_DOT}Sales_Org__c = salesOrg,
  ${PREFIX_DOT}Entity__c = entity[0].Id,
  ${PREFIX_DOT}Description__c = description,
  ${PREFIX_DOT}Unique_Key__c = stepName + salesOrg
);
upsert step ${PREFIX_DOT}Unique_Key__c;

// Ensure entity is in each workflow's WE list before inserting junctions
// (validation rule requires it — copy fails otherwise)
Map<String, Id> wfByName = new Map<String, Id>();
for (${PREFIX_DOT}BO_API_Workflow__c wf : [
  SELECT Id, Name FROM ${PREFIX_DOT}BO_API_Workflow__c
   WHERE Name IN :workflows
     AND ${PREFIX_DOT}BO_API__r.Name = 'Promotion'
     AND ${PREFIX_DOT}BO_API__r.${PREFIX_DOT}Sales_Org__c = :salesOrg
]) {
  wfByName.put(wf.Name, wf.Id);
}
for (String wf : workflows) {
  if (!wfByName.containsKey(wf)) {
    throw new CGCloudException('BO API workflow "' + wf + '" not found for sales org ' + salesOrg);
  }
  Integer existing = [
    SELECT COUNT() FROM ${PREFIX_DOT}BO_API_Workflow_Entity__c
     WHERE ${PREFIX_DOT}BO_API_Workflow__c = :wfByName.get(wf)
       AND ${PREFIX_DOT}BO_API_Entity__c = :entity[0].Id
  ];
  if (existing == 0) {
    insert new ${PREFIX_DOT}BO_API_Workflow_Entity__c(
      ${PREFIX_DOT}BO_API_Workflow__c = wfByName.get(wf),
      ${PREFIX_DOT}BO_API_Entity__c = entity[0].Id
    );
  }
}

// Wire junctions into the interview's chosen workflows only
for (String wf : workflows) {
  AggregateResult ar = [
    SELECT MAX(${PREFIX_DOT}Sort__c) maxSort
      FROM ${PREFIX_DOT}BO_API_Workflow_Workflow_Step__c
     WHERE ${PREFIX_DOT}BO_API_Workflow__c = :wfByName.get(wf)
  ];
  Decimal maxSort = (Decimal) ar.get('maxSort');
  Decimal nextSort = (maxSort == null ? 10 : maxSort + 10);
  // If interview supplied sortAfter, resolve that here and use sortAfter.Sort__c + 5 instead.

  ${PREFIX_DOT}BO_API_Workflow_Workflow_Step__c junction = new ${PREFIX_DOT}BO_API_Workflow_Workflow_Step__c(
    ${PREFIX_DOT}BO_API_Workflow__c = wfByName.get(wf),
    ${PREFIX_DOT}BO_API_Workflow_Step__c = step.Id,
    ${PREFIX_DOT}Enabled__c = true,
    ${PREFIX_DOT}Sort__c = nextSort,
    ${PREFIX_DOT}Unique_Key__c = String.valueOf(wfByName.get(wf)) + stepName + salesOrg
  );
  upsert junction ${PREFIX_DOT}Unique_Key__c;
}

// Register accepted input paths (SIS rows). Required — without these,
// the payload validator rejects with "Properties other than those defined
// were not expected at #.<path>". SIS has no external id → insert with
// pre-check. SIS uses RecordType to declare the JSON type (String, Array,
// Boolean, Number, Object) — a missing RecordTypeId defaults to Array,
// which produces "Expected List<Object>" at runtime.
Id sisRecordTypeId = [
  SELECT Id FROM RecordType
   WHERE SobjectType = '${PREFIX_UNDER}BO_API_Step_Input_Structure__c'
     AND DeveloperName = :inputPathType
   LIMIT 1
].Id;
Set<String> existingPaths = new Set<String>();
for (${PREFIX_DOT}BO_API_Step_Input_Structure__c s : [
  SELECT ${PREFIX_DOT}Path__c FROM ${PREFIX_DOT}BO_API_Step_Input_Structure__c
   WHERE ${PREFIX_DOT}BO_API_Workflow_Step__c = :step.Id
]) {
  existingPaths.add(String.valueOf(s.get('${PREFIX_DOT}Path__c')));
}
List<${PREFIX_DOT}BO_API_Step_Input_Structure__c> sisRows =
  new List<${PREFIX_DOT}BO_API_Step_Input_Structure__c>();
for (String inputPath : inputPaths) {
  if (existingPaths.contains(inputPath)) continue;
  sisRows.add(new ${PREFIX_DOT}BO_API_Step_Input_Structure__c(
    ${PREFIX_DOT}BO_API_Workflow_Step__c = step.Id,
    ${PREFIX_DOT}Path__c = inputPath,
    RecordTypeId = sisRecordTypeId
  ));
}
if (!sisRows.isEmpty()) insert sisRows;
```

`PREFIX_DOT` above is the placeholder the skill textually replaces before
writing the file to `./.promotion-bo-api-deploy/`. In the final on-disk file every `${PREFIX_DOT}`
becomes either `cgcloud.` / `cgcloud_dev.` / empty, and every
`${PREFIX_DOT}Sales_Org__c`-style token becomes `cgcloud__Sales_Org__c` /
`cgcloud_dev__Sales_Org__c` / bare.

Run:

```bash
sf apex run --target-org <alias> --file ./.promotion-bo-api-deploy/register-step.apex
```

Non-zero exit or non-`Compiled: true, Success: true` → stop, print output.

Re-run behaviour: both upserts are keyed on `Unique_Key__c` (writable external
id set from stable interview inputs), so a second run of Phase 5b is a no-op if
the answers are unchanged. Reducing the `workflows` set across runs does **not**
retire junctions the previous run created — the skill only adds. Print a warning
if Phase 2 shows a junction for `<stepName>` on a workflow no longer in the
interview list; a human should decide whether to disable it.
