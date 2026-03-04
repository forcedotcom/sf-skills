# Agentforce Vibes Library

AI prompts and rules library for Agentforce Vibes development, content creation, and workflow automation.

## 📚 About

This repository curates Salesforce-focused prompts, system rules, and executable skills from the wider developer community to accelerate Agentforce Vibes agentic workflows. Collections are organized by development discipline—Apex, LWC, flows, deployments, testing, investigation, spec-driven delivery, and more—so contributors can share reusable prompts, scaffolds, guardrails, and workflows that other teams can adapt and extend.

## 🗂️ Structure

```
afv-library/
├── prompts/              # Single-file instructions for straightforward tasks
│   ├── apex-development/
│   ├── lwc-development/
│   ├── flow-development/
│   ├── getting-started/
│   └── ...
├── rules/                # Single-file guardrails and standards
│   ├── apex-development/
│   ├── lwc-development/
│   ├── spec-driven-dev/
│   └── ...
├── skills/               # Directory-based executable workflows
│   ├── apex-development/
│   │   └── trigger-refactor-pipeline/
│   │       ├── SKILL.md
│   │       ├── scripts/
│   │       ├── references/
│   │       └── assets/
│   ├── metadata-deployments/
│   ├── testing-automation/
│   └── ...
├── samples/              # Synced sample apps (e.g. from npm)
│   └── webapp-template-app-react-sample-b2e-experimental/
└── README.md
```

## 🚀 Quick Start

### Manual Usage

Browse the repository and copy/paste any prompt, rule, or skill directly into Agentforce Vibes or your preferred AI tool.

### Samples

The `samples/` folder contains synced sample apps. For example, `samples/webapp-template-app-react-sample-b2e-experimental/` is kept in sync with the npm package `@salesforce/webapp-template-app-react-sample-b2e-experimental` (nightly and on manual trigger via GitHub Actions). To run the same sync locally from the repo root:

```bash
npm install
npm run sync-react-b2e-sample
```

The GitHub Action runs these same commands and opens a PR only when the npm package version has changed. See [samples/README.md](samples/README.md) for details.

### Connecting Team or Personal Libraries

You can register additional repos with the extension as long as they mirror this structure:

- Root folders named `prompts/`, `rules/`, and `skills/`, each containing category subfolders (e.g., `prompts/apex-development/`).
- Each prompt or rule stored in its own Markdown file with YAML frontmatter (`name`, `description`, `tags`, optional setup metadata).
- Each skill stored in its own directory containing a `SKILL.md` file with required frontmatter, plus optional `scripts/`, `references/`, and `assets/` subdirectories.
- Category folders may include a `README.md` describing their focus; empty folders are allowed for future content.

When you add a new library:

1. **Structure your repository** with the same folder layout shown in `## 🗂️ Structure`:
   - `prompts/` folder with category subfolders containing `.md` files
   - `rules/` folder with category subfolders containing `.md` files  
   - `skills/` folder with category subfolders, each containing skill directories with `SKILL.md`
2. **Follow format requirements**:
   - Prompts and rules: YAML frontmatter (`name`, `description`, `tags`) + markdown body
   - Skills: Directory with `SKILL.md` + optional `scripts/`, `references/`, `assets/` subdirectories
3. **Ensure script executability** for skills: Mark Python/Bash scripts as executable (`chmod +x`)
4. **Register the repository** with `Agentforce Vibes: Add Library` in VS Code
5. **Refresh the extension** to index and display the new content

## 📝 Prompt Format

Every prompt begins with YAML frontmatter that surfaces key metadata to contributors and tooling:

```markdown
---
name: Concise Prompt Title
description: One-sentence summary of the outcome you want
tags: category, use-case, tooling
requires_deploy: true        # optional – include when pre-work is required
setup_summary: Deploy baseline trigger before refactor  # optional helper text
---
```

- `name`, `description`, and `tags` are required.
- Use lowercase, comma-separated tags drawn from the category and focus area (e.g., `apex, refactor, testing`).
- Add `requires_deploy` (and an optional `setup_summary`) when the prompt depends on seed metadata or data.

After the frontmatter, organize the body with clear sections. A common pattern is:

1. `## Setup` – only when pre-work, sample metadata, or environment configuration is needed.
2. `## Context` – summarize the scenario, constraints, personas, or assets involved.
3. `## Instructions` – detail the tasks in numbered steps, calling out decision points or checkpoints.
4. `## Testing & Reporting` – define verification steps, coverage expectations, or deliverables.
5. `## Follow-ups` – optional space for stretch goals, review questions, or iteration loops.

### Example Prompt

**File:** `prompts/apex-development/trigger-refactoring.md`

```markdown
---
name: Trigger Refactor Helper
description: Refactor the Opportunity trigger into a handler pattern with tests
tags: apex, refactor, testing
requires_deploy: true
setup_summary: Deploy baseline trigger to target org before running instructions
---

## Setup
1. Deploy the baseline trigger shown below to your default or scratch org.
2. Confirm the trigger compiles successfully before continuing.

```apex
// ... baseline trigger omitted for brevity ...
```

## Instructions
Refactor `OpportunityTrigger` into a handler class (or classes) that handles the same behavior using bulk-safe patterns. Ensure the trigger itself delegates and remains behaviorally identical.

## Testing & Reporting
- Create unit tests covering positive and negative paths for each handler method.
- Include a bulk test that updates 50 `Opportunity` records where only half qualify for the `after update` logic.
- Deploy the refactored code and run the tests, then report coverage and key observations.
```

## 🛠️ Agent Skills Format

Agent Skills extend prompts and rules by bundling executable workflows, scripts, and reference materials into self-contained directories. Skills follow the open [Agent Skills specification](https://agentskills.io/) and are portable across many agent tools (Cursor, Claude Code, VS Code extensions, etc.).

### Directory Structure

Each skill is a folder containing:
- `SKILL.md` (required) - instructions + YAML frontmatter
- `scripts/` (optional) - executable Python/Bash/JS
- `references/` (optional) - additional documentation
- `assets/` (optional) - templates, schemas, lookup data

### Required Frontmatter

```yaml
---
name: skill-name-here          # lowercase, hyphens, matches folder name
description: What this skill does and when to use it (1-1024 chars)
license: Apache-2.0            # optional
compatibility: Requires...     # optional
metadata:                      # optional
  author: your-org
  version: "1.0"
allowed-tools: Bash Read Write # optional, space-delimited
---
```

The `name` must:
- Be 1-64 characters
- Use only lowercase letters, numbers, and hyphens
- Match the parent directory name
- Not start or end with hyphens

The `description` should explain both what the skill does and when to use it, including keywords that help agents identify relevant tasks.

### Progressive Disclosure

Skills are designed for efficient context use:

1. **Discovery** - agents load only name + description at startup
2. **Activation** - full SKILL.md loaded when needed
3. **Execution** - scripts/references loaded on-demand

Keep your main `SKILL.md` under 500 lines and move detailed reference material to separate files.

### Example Skill Structure

**File:** `skills/apex-development/trigger-refactor-pipeline/SKILL.md`

```markdown
---
name: trigger-refactor-pipeline
description: Refactor Salesforce triggers into handler patterns with automated test generation and deployment. Use when modernizing legacy triggers with DML/SOQL in loops.
license: Apache-2.0
compatibility: Requires Salesforce CLI, Python 3.9+, jq
metadata:
  author: afv-library
  version: "1.0"
---

## When to Use This Skill

Use when you need to modernize legacy triggers with DML/SOQL in loops or inconsistent patterns.

## Step 1: Analyze Trigger

Run `scripts/analyze_trigger.py <TriggerName>` to identify anti-patterns:
- DML operations inside loops
- SOQL queries inside loops
- Missing bulkification

The script outputs a report showing:
- Line numbers with issues
- Recommended refactoring approach
- Complexity score

## Step 2: Generate Handler

See [handler patterns reference](references/handler_patterns.md) for templates that match your trigger context:
- Before insert/update patterns
- After insert/update/delete patterns
- Bulk collection strategies

Copy the appropriate template from `assets/` and customize.

## Step 3: Create Tests

Use `assets/test_template.apex` as a scaffold. Ensure coverage includes:
- Single record operations
- Bulk operations (200+ records)
- Mixed scenarios
- Negative cases

## Step 4: Deploy and Validate

Deploy using Salesforce CLI and run all tests. Verify:
- All tests pass with 100% coverage
- No new governor limit issues
- Behavior matches original trigger
```

### Validation

Skills can be validated using the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) tool:

```bash
skills-ref validate ./skills/apex-development/trigger-refactor-pipeline
```

This checks that your `SKILL.md` frontmatter is valid and follows all naming conventions.

## 📂 Categories Guide

These starter categories reflect the current repository layout. Contributors are welcome to propose new ones or reorganize as long as the structure stays consistent for the VS Code extension.

### When to Use Each Format

| Format | Use When | Example |
|--------|----------|---------|
| **Prompt** | Single-shot instruction for a straightforward task | "Create a validation rule on Account that prevents blank NumberOfEmployees" |
| **Rule** | Ongoing guardrail or standard to enforce | "Apex triggers must delegate to handler classes with bulk-safe patterns" |
| **Skill** | Multi-step workflow requiring scripts, templates, or reference docs | "Refactor trigger → analyze anti-patterns → generate handler → create tests → deploy" |

### Prompts

| Category | Purpose | Example Topics |
|----------|---------|----------------|
| **apex-development** | Build and optimize Apex codebases | Trigger frameworks, async patterns, governor limit tuning |
| **lwc-development** | Craft Lightning Web Components | Component architecture, reactive data, UI patterns |
| **metadata-deployments** | Plan and execute releases | Packaging, Git branching, rollback prep |
| **vibe-coding** | Agentforce Vibes coding workflows | Apex/LWC scaffolds, prompt-to-code translation |
| **testing-automation** | Validate platform behavior | Apex tests, Flow scenarios, regression suites |
| **investigation-triage** | Diagnose and resolve issues | Incident response, log analysis, performance forensics |
| **data-operations** | Manage data pipelines | ETL prompts, bulk operations, platform events |
| **spec-driven-dev** | Generate and refine specification-first workflows | Requirement capture, traceability matrices, auto-generated tasks |
| **security-compliance** | Enforce standards and controls | Permission audits, secure coding, compliance narratives |
| **integration-fabric** | Coordinate external services | API design, middleware coordination, error recovery |
| **enablement-docs** | Share knowledge and runbooks | Onboarding guides, release notes, changelog automation |

### Skills

Skills mirror the same category structure as prompts and rules. Each skill is a directory containing executable workflows.

| Category | Purpose | Example Skills |
|----------|---------|----------------|
| **apex-development** | Automated Apex refactoring and analysis | Trigger refactor pipeline, bulk operation optimizer |
| **lwc-development** | Lightning Web Component workflows | Component generator, accessibility audit |
| **flow-development** | Flow automation and optimization | Flow analyzer, subflow extractor |
| **metadata-deployments** | Release management automation | Deployment readiness check, rollback automation |
| **testing-automation** | Test generation and execution | Test data factory, coverage analyzer |
| **investigation-triage** | Debugging and diagnostics | Log parser, governor limit analyzer |
| **data-operations** | Data pipeline automation | ETL validator, data quality checker |
| **spec-driven-dev** | Specification-to-code workflows | Requirements parser, test case generator |

### Rules

| Category | Focus | Example Assets |
|----------|-------|----------------|
| **apex-development** | Standards for Apex architecture and quality | Trigger guardrails, async execution policies |
| **lwc-development** | Front-end guardrails for Lightning Web Components | Accessibility checklists, component review templates |
| **metadata-deployments** | Release management discipline | Branching policies, deployment readiness reviews |
| **vibe-coding** | Coding quality for Agentforce Vibes assets | Code review criteria, secure pattern guides |
| **testing-automation** | Verification and validation expectations | Test coverage thresholds, regression playbooks |
| **investigation-triage** | Incident and root-cause response | Escalation runbooks, logging requirements |
| **data-operations** | Data stewardship and job governance | Data quality SLAs, bulk job safeguards |
| **spec-driven-dev** | Specification-first delivery standards | Definition-of-done templates, traceability requirements |
| **security-compliance** | Platform security and regulatory posture | Access reviews, compliance attestation steps |
| **integration-fabric** | External connection reliability | Retry policies, credential rotation standards |
| **enablement-docs** | Knowledge management and enablement | Release note templates, onboarding workflows |
| **org-governance** | Enterprise policy alignment | Org strategy playbooks, architecture review guidelines |
| **support-operations** | Production support excellence | Incident response SLAs, shift handover procedures |
| **ai-safety** | Responsible agent behavior | Ethical guidelines, bias detection checklists |

## ✨ Creating New Prompts & Rules

1. **Choose the right category** based on use case (if nothing fits, propose a new category)
2. **Create a descriptive filename** (use kebab-case: `my-prompt.md`)
3. **Add frontmatter** with name, description, and tags
4. **Write clear instructions** with placeholders for user input
5. **Test** before committing
6. **Commit with message**: `Add [name] for [use case]`

### Naming Conventions

- Use lowercase with hyphens: `code-review-helper.md`
- Be descriptive: `salesforce-apex-debug.md` not `debug.md`
- Include context: `blog-post-outline.md` not `outline.md`

## 🔧 Best Practices

### Writing Effective Prompts

- ✅ **Be specific** - Clear instructions yield better results
- ✅ **Use structure** - Numbered lists and sections help
- ✅ **Add context** - Explain what you want and why
- ✅ **Include examples** - Show expected output format
- ✅ **Test thoroughly** - Verify prompts work as intended

### Prompt Engineering

- ✅ **Clarify the objective** – Capture the outcome, stakeholders, and success metrics directly in the frontmatter
- ✅ **Share context** – Provide links, metadata, or sample records so the agent can ground its reasoning
- ✅ **Set guardrails** – Define tone, compliance boundaries, what to avoid, and when to ask for confirmation
- ✅ **Guide the workflow** – Break the request into staged checkpoints (ideate → propose → confirm → deliver)
- ✅ **Capture feedback loops** – Invite the agent to flag assumptions, pose questions, and suggest validation steps
- ✅ **Encourage adaptability** – Note how the prompt or rule can flex across org types, industries, and data volumes

#### Structuring Prompts

- **Prime with examples**: Include concise samples that illustrate the desired format or code pattern
- **Model the format**: Provide headings and numbered steps so the agent mirrors the final artifact
- **Address ambiguity**: Explicitly call out unknowns and ask the agent to gather missing inputs
- **Control verbosity**: Specify length limits, number of alternatives, or time horizons
- **Request diagnostics**: Ask the agent to share reasoning, risks, and verification plans when appropriate

#### Template: Multi-Step Prompt

```markdown
---
name: Apex Service Hardening Plan
description: Audit and fortify an Apex service to stay within governor limits while preserving behavior
tags: apex-development, optimization, audit
requires_deploy: false
---

## Context
- Usage profile: [Invocation volume, entry points, data scale]
- Known issues: [Timeouts, limit exceptions, performance complaints]
- Stakeholders: [Product owners, support teams, compliance partners]

## Instructions
1. Summarize existing architecture, dependencies, and limit usage; list assumptions needing confirmation.
2. Propose at least two optimization strategies, including refactor scope, data implications, and rollback considerations.
3. Recommend a preferred strategy once assumptions are resolved, detailing implementation phases and change management steps.

## Testing & Reporting
- Define unit, integration, and bulk test coverage with pass criteria.
- Specify telemetry/observability updates (logging, metrics, alerts) to validate success.
- Produce an execution checklist with owners, timelines, and escalation contacts.
```

### Organizing Rules

- ✅ **One rule per file** - Keep rules focused and modular
- ✅ **Use clear names** - Describe what the rule enforces
- ✅ **Document purpose** - Explain why the rule exists
- ✅ **Keep updated** - Review and refine regularly
- ✅ **Version control** - Track changes over time

## 🤝 Contributing

### How to Contribute

See [Contributing](./CONTRIBUTING.md) for complete details.

**Contribution checklist**
- Confirm the file lives in the correct category folder
- Complete the YAML frontmatter (`name`, `description`, `tags`)
- Include clear instructions and placeholders for user-specific details
- Add a short note on how others can adapt the prompt, especially for varying Salesforce environments
- Verify the content respects licensing and attribution requirements
- Provide any supporting references or context in the pull request description

### Creating New Skills

Skills are more complex than prompts and require additional setup:

1. **Create a folder** under the appropriate `skills/<category>/` directory using lowercase + hyphens (e.g., `trigger-refactor-pipeline`).
2. **Add a `SKILL.md` file** with required frontmatter:
   - `name` - must match the folder name (lowercase, hyphens only)
   - `description` - explain what the skill does and when to use it (1-1024 characters)
   - Optional: `license`, `compatibility`, `metadata`, `allowed-tools`
3. **Optionally add subdirectories**:
   - `scripts/` - executable Python, Bash, or JavaScript files
   - `references/` - additional documentation files
   - `assets/` - templates, schemas, or lookup data
4. **Validate your skill** using the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) tool:
   ```bash
   skills-ref validate ./skills/<category>/<skill-name>
   ```
5. **Test the skill end-to-end** before submitting. Ensure:
   - The skill activates correctly when the description keywords match
   - All scripts execute without errors
   - Reference files are accessible and well-organized
   - The workflow produces the expected outcomes
6. **Document dependencies** clearly in the `compatibility` field if your skill requires specific tools or system packages.

### Feedback

Found an issue or have a suggestion?
- Open an issue in GitHub
- Suggest improvements via pull request
- Start a discussion in GitHub Discussions or the pull request thread

## 🔄 Maintenance

### Updating Prompts

To update an existing prompt:
1. Edit the `.md` file
2. Update the description if behavior changed
3. Test the updated prompt
4. Commit with clear message: `Update [prompt]: [what changed]`

### Adding New Categories

To add a new category:
1. Create new folders in `prompts/`, `rules/`, and `skills/` with matching names
2. Add a `README.md` in each folder explaining the category's purpose
3. Add initial prompts, rules, or skills following the format guidelines
4. Update the main README with the new category in the appropriate tables
5. Submit a pull request with the rationale for the new category

### Updating Skills

To update an existing skill:
1. Modify the `SKILL.md` or supporting files (`scripts/`, `references/`, `assets/`)
2. Update the `metadata.version` field in the frontmatter
3. Test all scripts and workflows end-to-end
4. Validate using `skills-ref validate ./skills/<category>/<skill-name>`
5. Commit with clear message: `Update [skill-name]: [what changed]`


# Experimental 

### Using with supporting AFV Library VS Code Extension

1. Install the Agentforce Vibes VS Code extension (preview or later).
2. Install the experiemnt [AFV library VSCode extension](https://github.com/forcedotcom/afv-library-extension). 
2. Open the command palette and run `Agentforce Vibes: Add Library`.
3. Provide the Git URL (or local path) to this repository; the extension indexes every folder and `.md` file under `prompts/`, `rules/`, and `skills/`.
4. The extension displays prompts, rules, and skills organized by category. Select any item to preview the metadata and copy instructions into the editor.
5. Use the refresh command whenever new prompts, rules, or skills are added.