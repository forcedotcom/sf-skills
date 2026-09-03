# salesforce-test-drive

**Take a Salesforce capability for a test drive in Claude Code**

Pick a curated, end-to-end build from a menu and watch it run start to finish against your own org.
The flagship drive builds a **Service help agent** — an Agentforce agent that answers customer
questions, manages support cases, and hands off to a human — and deploys it as a **website chat
widget**. It's built for two moments: an SE running a live, rehearsable demo, and a developer learning
the platform by watching the real thing get built. The plugin checks what you have, helps you connect
or provision an org, then choreographs the [`salesforce-development`](../salesforce-development) skills
to do the build.

## Quick Start

1. **Install prerequisites:**
   - [Claude Code](https://claude.ai/code) — latest
   - [Node.js LTS](https://nodejs.org)
   - [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) — `sf`
   - The **salesforce-development** plugin (the test drive builds on it). This plugin declares
     that companion in `plugin.json` (`dependencies: ["salesforce-development"]`). Install both
     from the same marketplace — Claude Code may still let you install this plugin alone, so do
     not skip the foundation install:
     ```text
     /plugin marketplace add forcedotcom/sf-skills
     /plugin install salesforce-development@salesforce
     ```

2. **Install this plugin** from the same marketplace:
   ```text
   /plugin install salesforce-test-drive@salesforce
   ```

3. **Connect an org** (or let the test drive walk you through getting one — including a free
   Agentforce Developer Edition if you don't have one yet). The alias is yours to choose; `--set-default`
   is what the drive targets:
   ```bash
   sf org login web --alias my-org --set-default
   ```

4. **Start a test drive** — open the menu and pick one:
   ```text
   /salesforce-test-drive:start
   ```
   or launch a specific drive directly by its id:
   ```text
   /salesforce-test-drive:start service-help-agent
   ```

The engine confirms you're ready, gates on the drive's requirements with clear next steps if anything
is missing, then runs the build — pausing only for the design choices that make the demo worth
watching.

## What's Included

| Drive | What it builds |
|------|----------------|
| **Service help agent** (`service-help-agent`) | An Agentforce service agent (FAQs, case management, human handoff) deployed as a website chat widget. |

More drives are contributed by product teams over time — each is a catalog entry plus a prompt, and
shows up in the `/salesforce-test-drive:start` menu (or launches directly via
`/salesforce-test-drive:start <id>`). See [`AUTHORING.md`](AUTHORING.md) to add one.

## Instrumented mode

Add `--instrument` to record a developer-experience session log — call counts, setup-vs-permission
pauses, an API-gap log, and an error catalog — used to measure friction and find automation gaps:

```text
/salesforce-test-drive:start service-help-agent --instrument
```

Instrumentation is off by default; a normal run is clean. See
[`references/instrumentation.md`](references/instrumentation.md).

## Verify, Update, and Uninstall

- **Verify:** `/plugin` lists `salesforce-test-drive`; `/salesforce-test-drive:start` opens the menu.
- **Update:** `/plugin marketplace update salesforce` then `/plugin update salesforce-test-drive@salesforce`.
- **Uninstall:** `/plugin uninstall salesforce-test-drive@salesforce`.

## Contributing a drive

Test drives are owned by product teams; the framework owns the engine and contract. See
[`AUTHORING.md`](AUTHORING.md).
