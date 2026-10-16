---
name: author-governance-ruleset
description: Use when the user asks to create, write, generate, modify, update, fix, or validate an API Governance ruleset (Validation Profile). Covers governance rules for OpenAPI, RAML, AsyncAPI, MCP servers, Anypoint API instances, and API projects. Trigger phrases include "governance ruleset", "validation profile", "governance rule", "API conformance", "enforce policy", "create ruleset", "validate ruleset".
license: Apache-2.0
compatibility: Requires Anypoint CLI v4 with the governance plugin installed (anypoint-cli-governance-plugin)
metadata:
  author: mule-dx-tooling
  version: "2.0.0"
allowed-tools: Bash Read Write Edit AskUserQuestion
---

# API Governance Ruleset Author

Write valid Anypoint API Governance rulesets (Validation Profile 1.0 YAML) using the governance CLI tools for model discovery, validation, and simplification.

## Overview

A governance ruleset is a YAML file that starts with `#%Validation Profile 1.0` and declares validation rules against a domain model (API specs, API instances, MCP servers, etc.). Each rule targets a class, constrains its properties, and is assigned a severity (violation, warning, info).

This skill uses the `anypoint-cli-v4 governance:ruleset` CLI commands to discover the model, validate rulesets, and simplify output. Do NOT guess class names, property names, or constraint compatibility — always query the CLI.

---

## Prerequisite: Ensure the Governance Plugin Version

Before running any governance CLI commands, force-install the latest governance plugin so the model, constraints, and validation logic match this skill. Version 1.0.20 or greater is required:

```bash
anypoint-cli-v4 plugins:install mulesoft-anypoint-cli-governance-plugin@latest
```

Run this every time the skill starts, even if the plugin appears to already be installed — `@latest` guarantees a compatible version (1.0.20 or newer). Only proceed to the steps below once this completes successfully.

## Step 1: Understand the Intent

Parse the user request. Identify:
- **What class/node** is being targeted (e.g., Operation, WebAPI, APIInstance, MCPServer)
- **What property** is being constrained (e.g., description, version, policies)
- **What condition** must hold (e.g., must exist, must match a pattern, must have at least one)

If the user uses domain language (e.g., "consumerUrl", "endpointUrl", "rate-limit policy"), resolve it:

```bash
anypoint-cli-v4 governance:ruleset:resolve <term>
```

Aliases are author-time helpers ONLY — they must NEVER appear in the ruleset YAML. Use the canonical targetClass + path returned by the resolve command.

## Step 2: Pick the Domain

List available domains and match the user intent:

```bash
anypoint-cli-v4 governance:ruleset:domains
```

**Critical rule:** A single ruleset must target only ONE specKind. Never combine `api-spec` and `mcp` targets in the same ruleset. Domains without a specKind mix freely.

## Step 3: Discover the Model

List the targetable classes for the chosen domain:

```bash
anypoint-cli-v4 governance:ruleset:classes --domain <domain-name>
```

Then list properties and their types for the specific class:

```bash
anypoint-cli-v4 governance:ruleset:properties <prefix.ClassName>
```

The property type (scalar, node, scalarArray, nodeArray) determines which constraints are valid.

## Step 4: Choose Constraints

Query valid constraints for the property type:

```bash
anypoint-cli-v4 governance:ruleset:constraints --type <propertyType>
```

Where `<propertyType>` is one of: `scalar`, `node`, `scalarArray`, `nodeArray`.

**Common mistakes to avoid:**
- NEVER use `pattern` or `in` on a nodeArray or node property
- Use `atLeast`/`atMost` on nodeArray to check "at least one item matches X"
- Use `containsSome` on scalarArray to check "at least one value is X"
- Use `in` on scalarArray to restrict ALL values to an allowed set
- Property paths using `/` traverse nested nodes; the LAST property determines valid constraints

## Step 5: Write the Ruleset

Write valid Validation Profile 1.0 YAML to a file:

```yaml
#%Validation Profile 1.0
profile: <profile-name>
prefixes:                    # Only needed for non-default namespaces
  management: http://anypoint.com/vocabs/management#
validations:
  <rule-name>:
    targetClass: <prefix.ClassName>
    message: <human-readable error message>
    propertyConstraints:
      <prefix.propertyName>:
        <constraint>: <value>
violation:                   # MUST assign every rule to a severity
  - <rule-name>
warning:
  - <other-rule>
info:
  - <another-rule>
```

**Default prefixes** (do NOT redeclare these):
- `apiContract`, `core`, `shacl`, `shapes`, `raml-shapes`, `doc`, `meta`, `security`, `data`, `xsd`, `rdfs`, `rdf`, `sourcemaps`

**Non-default prefixes** (MUST declare in `prefixes:` block):
- `management: http://anypoint.com/vocabs/management#`
- `mulesoft: http://anypoint.com/vocabs/management#mulesoft.com/`
- `gcl: http://anypoint.com/vocabs/gcl#`
- `api: http://anypoint.com/vocabs/api#`
- `catalog: http://anypoint.com/vocabs/digital-repository#`
- `mcp: http://anypoint.com/vocabs/mcp#`
- `apiExt: http://a.ml/vocabularies/api-extension#`

## Step 6: Validate the Ruleset

After writing or modifying a ruleset, validate it with the CLI:

```bash
anypoint-cli-v4 governance:ruleset:validate-authoring <path-to-ruleset.yaml>
```

This checks: YAML syntax, JSON schema conformance, targetClass validity, property path correctness, constraint-type compatibility, and severity assignments.

If validation returns errors, fix them and re-validate. Do NOT present a ruleset to the user until it passes validation with zero errors.

## Step 7: Simplify

Once validation passes, simplify the ruleset:

```bash
anypoint-cli-v4 governance:ruleset:simplify <path-to-ruleset.yaml>
```

This flattens nested property paths and removes redundant logical wrappers. If changes are made, write the simplified output back to the file and validate again.

## Step 8: Present the Result

Show the final validated and simplified ruleset to the user. Briefly explain:
- What it checks
- Which constraints were chosen and why
- The severity assignments

---

## Rules

- ALWAYS start with `#%Validation Profile 1.0` on line 1
- ALWAYS assign every validation to a severity level (violation, warning, or info)
- NEVER use an alias in the ruleset YAML — always use canonical targetClass + property path
- NEVER combine api-spec and mcp targets in the same ruleset
- NEVER guess property names — always run `governance:ruleset:properties <class>` to look them up
- NEVER guess constraint compatibility — always run `governance:ruleset:constraints --type <type>`
- ALWAYS validate with `governance:ruleset:validate-authoring` after every write or modification
- ALWAYS simplify with `governance:ruleset:simplify` after validation passes
- Property paths use ` / ` (space-slash-space) to separate segments
- Alternate paths use ` | ` (space-pipe-space) between alternatives wrapped in `( )`
- For conditional rules, use `if:` / `then:` at the validation level
- For logical combinations, use `and:`, `or:`, `not:`, or `xone:` at the validation level
- Rego (`rego:`) is a last resort for cross-resource checks — prefer declarative constraints
- Message templates can reference property values: `"{{ prefix.property }}"`
- When modifying an existing ruleset, apply the change then re-validate
- If the user asks about supported domains, run `governance:ruleset:domains` — never claim something is unsupported without checking
