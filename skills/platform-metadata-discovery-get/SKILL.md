---
name: platform-metadata-discovery-get
description: "Use for Salesforce metadata discovery and configuration questions, and before creating, changing, or writing code against metadata. Routes each question to metadata grounding, scoped SOQL with sf data query, sf sobject list or describe, sf org list metadata, source retrieval, or local files, and covers orgs and setups where grounding is not available. Use to check whether an object, field, picklist, permission set, page, app, or flow already exists before creating one, confirm field names, types, and picklist values before writing Apex, LWC, SOQL, or Flow logic, list every field on an object or every member of a metadata type, find automation that runs on an object, or explain how something in the org is configured and who can access it. DO NOT TRIGGER for whole-org overviews, org comparison, or drift (use dx-org-analyze), metadata file structure or XML shape (platform-metadata-api-context-get), or Data Cloud DLO and DMO schema (data360-code-extension-generate)."
metadata:
  relatedSkills:
  - data360-code-extension-generate
  - dx-org-analyze
  - platform-metadata-api-context-get
  - platform-metadata-grounding-get
  - platform-metadata-retrieve
  version: "1.3"
  domains:
  - "Platform"
  cliTools:
  - tool:
    - "sf"
    semver: ">=2.0.0"
  mcpTools:
    metadata-grounding:
      tools:
      - "search_metadata"
      - "query_metadata"
      - "describe_metadata"
      semver: ">=1.0.0"
    headless-360:
      tools:
      - "describe"
      - "dispatch"
      - "dispatch_readonly"
      semver: ">=1.0.0"
id: "platform-metadata-discovery-get"
---

# Salesforce Metadata Discovery

Before you create metadata, change it, or write code that references it, know what already exists in the org. This skill picks the tool for each question. Metadata grounding finds metadata by meaning when you do not know its name. It needs Salesforce Catalog and a connected grounding server, and many orgs and setups have neither. Every other route works with the `sf` CLI alone.

Before calling any metadata grounding operation, load `platform-metadata-grounding-get` if it has not already been loaded in this conversation. This applies to exact-name lookups, configuration queries, semantic searches, and fallback to grounding after another route fails. Choosing grounding is a separate decision from choosing this discovery skill; do not call its tools using only the routing table below. If the skill cannot be loaded, explain that and choose another supported route.

Skip discovery when the request only changes local files and adds no new references to org metadata.

## Check What You Have

Establish the target and available routes once per session; revisit them when the target changes.

1. **Target org.** Use the org explicitly selected by the user or supplied by the host, workspace, or authenticated tool connection. An explicit user target takes precedence over defaults and other connections. A CLI default alone does not establish which org the user intends. Do not run an unqualified `sf org display` or ask for CLI login as a prerequisite to using an already connected MCP.
2. **Available tools.** A working authenticated Metadata Grounding MCP or Salesforce MCP can answer supported questions without local CLI authorization. Discover the tools actually available. Before the first grounding operation on either server, load `platform-metadata-grounding-get` if it is available, including when discovery was entered through another skill. Its related-skill listing alone does not load its instructions. If loading fails, report the limitation and use another supported route; do not pretend the skill loaded.
3. **CLI when needed.** Use an explicit target with each CLI command: `--target-org <confirmed-alias-or-username>`. Confirm that target's identity before combining its results with another connection. If the host has not provided a target, or connections disagree, ask which org to use before making CLI calls. Do not choose a default org or log into a different org to make a lookup work.
4. **One org.** Grounding identifiers begin with the org id; use returned identifiers unchanged. If combining tools, compare the authenticated org identities, rather than comparing an MCP connection against an unrelated CLI default. A local authentication failure says nothing about whether grounding is available. Use another connected route only when it is known to target the intended org.

## Route by Intent

| Intent | Use | If that is not available |
|---|---|---|
| Find metadata by meaning, check a name you are guessing, or check for something to reuse | Metadata grounding search. Load `platform-metadata-grounding-get`, which picks the server. | Name and label fallback, below. Notify. |
| Explain how something is configured, or who can access it | Metadata grounding query after loading `platform-metadata-grounding-get` | Scoped SOQL on `EntityParticle`, `FieldPermissions`, `ObjectPermissions`, or Tooling `ValidationRule`. Notify. |
| Check names, types, or picklist values you know. Every field on one object. Data records | Scoped SOQL on a confirmed, authenticated CLI target. If CLI access is unavailable, use a connected same-org grounding query or the Salesforce MCP; load the grounding skill before grounding calls. If a scoped lookup returns nothing, search by meaning. | See the note below the table. |
| Full shape of one object, including relationships | `sf sobject describe --sobject <Type>`, only when you need all of it. It is very large. | Same |
| Every object in the org | `sf sobject list --sobject all` or `--sobject custom` | Same |
| Every member of a type, or a count ("all flows", "how many flows") | `sf org list metadata --metadata-type <Type>` | Same |
| Source to edit or deploy, including changes to existing metadata | Load `platform-metadata-retrieve`. Grounding never returns source. | Tell the user this needs the `sf` CLI. |
| Metadata you are already editing locally | Local files | |
| Compare orgs, find drift, or an overview of a whole org when the user asks for one | `dx-org-analyze`. It takes minutes and returns names and counts. | Tell the user this needs the `sf` CLI. |
| Where is this used, what depends on it, what breaks if I change it, or is it safe to delete | Comprehensive analysis is not available yet. State that boundary before offering explicitly labeled partial checks. | |

**Without the CLI.** A connected same-org grounding server can still answer the search and query questions it supports. For inventory and other routes, read `references/h360-routes.md` when the Salesforce MCP is connected. If no available route can supply the requested information or completeness, explain that limit.

Choose a route based on the information needed and the connections that are actually usable for the intended org. Do not force a CLI route merely because a shell exists. Ranked grounding results cannot replace a complete enumeration or source retrieval; when no suitable route is available, state that limit.

A question about a topic or purpose ("what do we have for loyalty") is discovery, not an overview. Do not run an org analysis for it, even when grounding is not available.

This skill covers core platform metadata. For Data Cloud DLO and DMO schema, use `data360-code-extension-generate`.

When a request mixes intents, use the right tool for each part. "Add a tier discount step to our order flow" means finding the flow and the field, then retrieving the flow to edit.

## Scoped SOQL

In all examples below, add `--target-org <confirmed-alias-or-username>` to CLI commands. Never substitute an unconfirmed CLI default.

Scoped SOQL is a targeted query on setup objects, filtered to what you need. It is exact, real time, and far smaller than a describe. It never returns source.

```text
sf data query --json --query "SELECT QualifiedApiName, Label, DataType FROM EntityParticle WHERE EntityDefinition.QualifiedApiName = 'Contact'"
sf data query --json --query "SELECT Value, Label, IsDefaultValue, IsActive FROM PicklistValueInfo WHERE EntityParticle.EntityDefinition.QualifiedApiName = 'Contact' AND EntityParticle.QualifiedApiName = 'Loyalty_Tier__c'"
```

- To check specific fields, add `AND QualifiedApiName IN ('Loyalty_Tier__c', 'Lifetime_Orders__c')`. For custom fields only, add `AND QualifiedApiName LIKE '%__c'`.
- `EntityParticle` includes parts of compound fields, such as `MailingCity`.
- Add `--use-tooling-api` for `CustomField` and `ValidationRule`.
- `EntityDefinition`, `EntityParticle`, and `FieldDefinition` do not accept `OR`. Run one scoped query per condition instead of broadening the query or removing its object/type filters.

More patterns, including access and automation, are in `references/scoped-soql.md`.

## When Grounding Is Not Available

Say the line below once per session, in your answer, next to the results of the name and label search. Do not announce the fallback before you search, and do not repeat it later in the session. Use the line that matches the cause, word for word, including the last sentence. Do not shorten or rephrase it. If you stop before you can report results, say it in that message instead.

| Cause | Say |
|---|---|
| No grounding server connected | "Metadata Grounding isn't connected, so I matched by name and label, which can miss metadata named differently. Connect the Metadata Grounding MCP to search by meaning." |
| Catalog not enabled | "Salesforce Catalog isn't turned on in this org, so I matched by name and label, which can miss metadata named differently. An admin can turn on Salesforce Catalog through Feature Manager in Data Cloud Setup." |
| Permission missing | "Catalog search needs the Customize Application permission, so I matched by name and label, which can miss metadata named differently." |

Then search names and labels. Try two or three likely words, one `LIKE` per query.

```text
sf data query --json --query "SELECT QualifiedApiName, Label FROM EntityDefinition WHERE Label LIKE '%loyalty%'"
sf data query --json --query "SELECT QualifiedApiName, Label, DataType FROM EntityParticle WHERE EntityDefinition.QualifiedApiName = 'Contact' AND Label LIKE '%tier%'"
sf data query --json --use-tooling-api --query "SELECT DeveloperName, EntityDefinition.QualifiedApiName FROM CustomField WHERE DeveloperName LIKE '%tier%' AND NamespacePrefix = null"
sf data query --json --query "SELECT ApiName, Label, ProcessType, IsActive FROM FlowDefinitionView WHERE Label LIKE '%order%'"
```

- The `CustomField` query searches custom fields on every object. `DeveloperName` has no `__c`. Drop rows with no object name. They are Data Cloud fields.
- For other types, and for types the catalog does not cover, list names with `sf org list metadata` and scan them.
- Name matching misses metadata labeled differently. A search for "status" will not find a field labeled Loyalty Tier. Say "no name match found," never "does not exist."

Everything else in this skill still applies.

## Reuse Before You Create

Before you create an object, field, picklist, permission set, page, app, or flow:

1. Search by business meaning for existing metadata that stores the same data or does the same job. For a field, first search `SObject` for the exact object API name, then pass that result's returned `identifier` as `parentIdentifier` to the `SObjectField` search. Never pass the raw object API name as `parentIdentifier`. A proposed API name or label is only an exact collision check and does not prove that equivalent metadata is absent. Similar words alone are not enough to declare a match.
2. **If you find matches:** show up to 3, best first, with API name, label, description, and type. Do not accept or reject an ambiguous match from its name alone. Offer to reuse, extend, or create new in one consolidated reuse checkpoint covering every type you plan to create, then wait. Do not combine this checkpoint with values or other generation-specific questions.
3. **After the user decides:** preserve the decision for the request and do not ask again unless the scope changes or new conflicting evidence appears. For reuse, stop creation and inspect configuration only if needed. For extension, inspect the existing component before asking for changes. For new metadata, collect the required configuration and continue with the generation guidance.
4. **If nothing matches:** say so in one line and continue.
5. **If the user gave an exact API name:** check it with scoped SOQL and say if it already exists.
6. **If the user asked for new metadata or said not to reuse:** mention close matches in one line at most and continue.

Treat namespaced items, such as `force__` permission sets or managed package components, as references, not things to edit. Say so when a match is managed.

## Ground Code in Real Org Names

Before you write Apex, LWC, SOQL, or Flow logic, confirm every object, field, and picklist value it references.

- Skip references already in the local project, already confirmed in this conversation, or standard fields every org has (such as `Account.Name` or `Contact.Email`).
- Always look up picklist values, including on standard fields. Never invent values.
- Values shown only as examples in a skill, tool description, or prior assistant response are not user-approved values. If the user has not explicitly supplied or approved the values or an existing value set, ask once and wait before creating the picklist.
- If the request depends on an order or meaning the values do not state ("the top tier"), list the values and ask.
- Look up all references for a request together.

## Existing Automation

- **To find automation by what it does,** search `Flow` or `ApexClass` by meaning. A grounding query on a flow shows its trigger object, trigger type, and active status.
- **To list everything that runs on an object** before adding automation:

  ```text
  sf data query --json --query "SELECT Name, Status FROM ApexTrigger WHERE TableEnumOrId = 'Contact'"
  sf data query --json --query "SELECT ApiName, Label, TriggerType, IsActive FROM FlowDefinitionView WHERE TriggerObjectOrEventId = 'Contact'"
  ```
- **To understand what a flow or trigger does,** retrieve its source and read it.

## What You Can Explain

| Question | Answer with |
|---|---|
| What exists that does X | Grounding search |
| How a field, object, or validation rule is configured | Grounding query, or `EntityParticle` and Tooling `ValidationRule` |
| Who can read or edit a field or object | Grounding on `FieldPermissions`, or SOQL on `FieldPermissions` and `ObjectPermissions` for a complete list. These records prove configured access, not actual use; a permission container's name does not prove an integration or dependency is active. |
| Sharing rules, roles, groups, and which package a component came from | Grounding |
| What a flow is | Grounding gives the header only (type, trigger, active). For its steps, retrieve the source. |
| What an Apex class does | Grounding gives signatures only. Retrieve the source. |
| Why a save failed | A partial answer. Check validation rules on the object, then retrieve the automation that runs on it. |
| Page layouts, reports, custom metadata types, custom settings | Not in the catalog. Use `sf org list metadata` and retrieve. |
| Where something is used, what depends on it, what breaks if it changes, or whether it is safe to delete | Comprehensive analysis is not available yet. Say so before any checks. You may offer narrow checks, but label each one as partial and never present their union as complete or conclude that the change is safe. |

## Working With Skills

- This skill decides what already exists. Build skills decide how to create it. Run discovery before any skill writes files.
- If a loaded skill has its own equivalent semantic reuse check, use it instead of the matching step here. Do not run both. An exact-name or exact-label collision check is not equivalent and does not replace semantic reuse discovery.
- Always look up picklist values. Prefer a scoped query for exact facts when an authenticated, confirmed route is available; avoid a full object describe unless its full shape is needed. Load the grounding skill whenever the chosen route is grounding.
- If a skill's discovery step fails or its tool is not available, use the routes in this skill and tell the user once.

## Freshness and Local Files

- Reuse discovery results for the rest of the conversation unless that item has changed.
- The catalog can take several minutes to reflect deploys and other org changes. For anything changed in this session, trust the local source and deploy results, and confirm with SOQL, which is real time. If the user reports a change SOQL does not show, ask them to confirm the name and org before you write code that uses it.
- When the metadata you need is not in the local project, retrieve it before editing, and tell the user you did.
- If you learn the org version differs from local in ways you did not make, for example from a retrieve or a deploy conflict, show the difference and ask before you overwrite either one.
- When scanning local source for references, read the package directories from `sfdx-project.json` and search those directories. Exclude response exports, logs, generated output, caches, and agent configuration unless the user explicitly asks to inspect them.
- Searching local files finds exact text only. Do not use it to find org metadata by meaning.

## Never

- Write or deploy files built from grounding query output. It returns properties, not source.
- Treat grounding results as a complete list. They are ranked and capped.
- Say metadata does not exist because a search or a name match found nothing.
- Combine results from two different orgs.
- Present partial dependency or reference checks as a complete impact analysis, or conclude from them that metadata is safe to change or delete.
- Treat illustrative values from examples, skills, or tool descriptions as user-approved metadata.
