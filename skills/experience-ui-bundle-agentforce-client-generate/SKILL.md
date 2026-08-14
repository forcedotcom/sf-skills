---
name: experience-ui-bundle-agentforce-client-generate
description: "Use this skill when the user asks to add, embed, integrate, configure, style, or remove an agent, chatbot, chat widget, conversation client, or AI assistant in a UI Bundle project (React or Angular). TRIGGER when: project contains a uiBundles/*/src/ directory and the task involves adding or modifying a chat widget, chatbot, or conversational AI; files under uiBundles/*/src/ import AgentforceConversationClient in React `.tsx`/`.jsx` files, or use the app-agentforce-conversation-client element in Angular `.html` templates and AgentforceConversationClientComponent in `.component.ts` files; user asks to add any chat or agent functionality to a page. DO NOT TRIGGER when: user wants to create a custom agent, chatbot, or chat widget component from scratch; the project has no uiBundles directory."
metadata:
  version: "1.2"
  cliTools:
    - tool: ["npm"]
      semver: ">=9.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Managing Agentforce Conversation Client

This skill is **framework-agnostic**: it supports both React and Angular UI Bundle apps. The Agentforce client ships as two feature packages that wrap the same Lightning Out glue — pick the one matching the app's framework (detected in Step 0):

| Framework | Feature package | Element | Component symbol |
|-----------|-----------------|---------|------------------|
| React | `@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client` | `<AgentforceConversationClient />` | `AgentforceConversationClient` |
| Angular | `@salesforce/ui-bundle-template-feature-angular-agentforce-conversation-client` | `<app-agentforce-conversation-client>` | `AgentforceConversationClientComponent` |

**HARD CONSTRAINT:** NEVER create a custom agent, chatbot, or chat widget component. ALL such requests MUST be fulfilled by importing and rendering the existing framework-appropriate component (React `<AgentforceConversationClient />` or Angular `<app-agentforce-conversation-client>`) from its feature package as documented below. If a requirement is unsupported by the component's props/inputs, state the limitation — do not improvise an alternative.

## Prerequisites

Before the component will work, the following Salesforce settings must be configured by the user. ALWAYS call out the prequisites after successfully embedding the agent.

**Trusted domains (required only for local development):**

- Setup → Session Settings → Trusted Domains for Inline Frames → Add your domain
  - Local development: `localhost:<dev-server-port>` — React (Vite) defaults to `localhost:5173`; the Angular template may use a different port (check the app's dev-server config, e.g. `localhost:5174`). Add whichever port the app actually runs on.
  - **Warning:** Remove this trusted domain entry before deploying to production.

## Instructions

### Step 0: Detect the app framework

Determine whether the target UI Bundle app is **React** or **Angular** before doing anything else — it drives discovery, import, element syntax, and prop binding in every step below.

Run the bundled detector against the app (or uiBundle) root. It performs the detection deterministically and prints exactly one token — `react`, `angular`, `ambiguous`, or `unknown`:

```bash
bash "<skill_dir>/scripts/detect-framework.sh" "<app-or-uiBundle-root>"
```

The detector combines: an `angular.json` at/above the root; `@angular/core` / `react` in any non-`node_modules` `package.json`; and source-file signatures (`*.component.ts`, `app.routes.ts`, or `@Component`-decorated classes for Angular; `*.tsx`/`*.jsx` for React).

Act on the result:

- `react` or `angular` → use that framework. **Do NOT ask the user** — the detection is deterministic.
- `ambiguous` (both frameworks detected) or `unknown` (neither) → ask the user which framework the app uses before proceeding.

Carry the resolved framework through the remaining steps.

### Step 1: Check if component already exists

Search for existing usage across all app files (not implementation files). Use the grep for the detected framework:

**React:**
```bash
grep -r "AgentforceConversationClient" --include="*.tsx" --include="*.jsx" --exclude-dir=node_modules
```

**Angular:**
```bash
grep -rn "app-agentforce-conversation-client" --include="*.html" --exclude-dir=node_modules
grep -rn "AgentforceConversationClientComponent" --include="*.ts" --exclude-dir=node_modules
```

**Important:** Look for the files that USE the element (for example, shared shells/layouts, route components, or feature pages) — for Angular the `<app-agentforce-conversation-client>` tag lives in a `*.html` template and the component is registered in the host's `imports: [...]`. Do NOT open the component *implementation* files:
- React: `AgentforceConversationClient.tsx` / `AgentforceConversationClient.jsx`
- Angular: `conversation.ts`, `conversation.html`, `__inherit__conversation.ts`, `agentforce-embed.service.ts`

**If multiple files found:** Ask the user which component file they are referring to. Do not proceed until clarified.

**If found:** Read the file and check the current `agentId` value.

**Agent ID validation rule (deterministic):**

- Valid only if it matches: `^0Xx[a-zA-Z0-9]{15}$`
- Meaning: starts with `0Xx` and total length is 18 characters

**Decision:**

- If `agentId` matches `^0Xx[a-zA-Z0-9]{15}$` and user wants to update other props → Go to Step 4 (update props)
- If `agentId` matches `^0Xx[a-zA-Z0-9]{15}$` and user asks to "embed" or "add" the chat client → Inform: "The Agentforce Conversation Client is already embedded in `<file>` with agent ID `<agentId>`. Would you like to change the agent or update other props?"
  - Change agent → Step 2
  - Update props → Step 4b
- If `agentId` is missing, empty, or does NOT match `^0Xx[a-zA-Z0-9]{15}$` → Continue to Step 2 (need real ID)
- If not found → Continue to Step 2 (add new)

**If user reports an error:**

If the user says the component is "not working", "showing an error", or similar — ask them for the specific error message. Then proceed to Step 2 to cross-check the configured agentId against the org.

### Step 2: Resolve and Validate Agent ID

#### Prerequisites

1. **Verify sf CLI is available:**
   ```bash
   sf --version
   ```
   If fails:
   - Inform: "The Salesforce CLI (`sf`) is not installed. It's needed to query available agents from your org."
   - Ask: "Would you like me to install it?"
     - Yes → Install via `npm install -g @salesforce/cli`, then continue.
     - No → "You can find your agent ID manually in Setup → Agentforce Agents → click the agent name → copy the ID from the URL. Would you like to provide it now, or skip this step?"
       - User provides ID → validate format (`^0Xx[a-zA-Z0-9]{15}$`), store it, proceed to Step 3.
       - Skip → proceed to Step 4 with placeholder `<YOUR_AGENT_ID>`.

2. **Verify org connectivity:**
   ```bash
   sf org display --json
   ```
   If fails:
   - Inform: "No authenticated org found."
   - Ask: "Would you like to connect to your org now? Run `sf org login web` to authenticate."
     - User authenticates → retry the query, continue.
     - User declines → "You can find your agent ID manually in Setup → Agentforce Agents → click the agent name → copy the ID from the URL. Would you like to provide it now, or skip this step?"
       - User provides ID → validate format, store it, proceed to Step 3.
       - Skip → proceed to Step 4 with placeholder `<YOUR_AGENT_ID>`.

**Note:** Even if the user provides their own agentId, the org must be connected for the agent to function at runtime. An agentId without a connected org will not work.

#### Query all Employee Agents

Run the SOQL query defined in `references/agent-id-resolution.md`.

#### Handle results

**No records at all:**
> "No Employee Agents found in this org. Create one in Setup → Agentforce Agents."

Ask user if they want to provide an agent ID manually or skip. If skip, proceed to Step 4 with placeholder `<YOUR_AGENT_ID>`.

**All agents are inactive:**
> Found Employee Agents but none are active:
>   - Agentforce Sales Agent (0Xxxx000000001dCAA)
>   - HR Assistant (0Xxxx0000000002BBB)
>
> To activate: Setup → Agentforce Agents → click the agent name → open in Agent Builder → press Activate.
> Then re-run this step.

Ask user if they want to provide an agent ID manually or skip. If skip, proceed to Step 4 with placeholder `<YOUR_AGENT_ID>`.

**Has active agents — Path A (fresh install / no existing agentId):**

Present only active agents for selection:
> Which agent should the chat widget use?
>   1. Property Manager Agent (0Xxxx0000000001CAA)
>   2. HR Assistant (0Xxxx0000000002BBB)

- One agent → still confirm with user, do not auto-select.
- If user picks one → store the selected `Id` for use in Step 4.
- If user declines to pick ("skip", "no", "I don't want to set one") → accept it and move to next steps. Do not re-ask. In Step 4, use placeholder `<YOUR_AGENT_ID>` for fresh installs. For existing projects, leave the component as-is.

**Has active agents — Path B (existing agentId from Step 1, passed format check):**

Cross-check the existing agentId against query results:

- **ID found, agent is Active** → "Agent ID maps to 'Property Manager Agent' — active in the org." Proceed.
- **ID found, agent is Inactive** → "The configured agent 'Sales Agent' exists but is Inactive. To activate: Setup → Agentforce Agents → click the agent name → open in Agent Builder → press Activate. Or pick a different active agent:" → show active list.
- **ID not found at all** → "The configured agent (0Xxxx...) doesn't exist in this org — it may have been deleted or belongs to a different org. Pick a replacement:" → show active list. If no active agents available, show inactive list with activation instructions.

If user reported an error → surface the agent name even if active, so user can confirm it's the intended one.

#### Query error handling

If the SOQL query fails, surface the error message from the response directly to the user. Do not guess at the fix — just report what came back. For example:
> "The query failed with: `[error message from response]`. Check your org permissions or that the API version supports this object."

#### What this step does NOT do

- No fallback to GraphQL or Tooling API — SOQL only
- No auto-selection (always confirm with user)
- No programmatic activation (only via Setup UI)
- No file writes (that's Step 4)

### Step 3: Canonical import strategy

Use the import for the detected framework.

**React** — import the component by default in app code:

```tsx
import { AgentforceConversationClient } from "@salesforce/ui-bundle-template-feature-react-agentforce-conversation-client";
```

If the package is not installed, install it:

```bash
npm install @salesforce/ui-bundle-template-feature-react-agentforce-conversation-client
```

**Angular** — import the standalone component **and register it in the host component's `imports` array** (Angular renders nothing without this registration — there is no React analogue):

```ts
import { AgentforceConversationClientComponent } from "@salesforce/ui-bundle-template-feature-angular-agentforce-conversation-client";

@Component({
  selector: "app-layout",
  imports: [/* existing imports */, AgentforceConversationClientComponent],
  templateUrl: "./app-layout.html",
})
export class AppLayoutComponent {}
```

If the package is not installed, install it:

```bash
npm install @salesforce/ui-bundle-template-feature-angular-agentforce-conversation-client
```

**Local/composed imports:** Only use a local relative import when the user explicitly asks to use a patched/local component, OR when the app is a composed UI Bundle that already inherits the feature file locally — React composed apps import from `./components/AgentforceConversationClient`, and Angular composed apps import `AgentforceConversationClientComponent` from the inherited feature file (for example `../../../features/agentforce/__inherit__conversation`). If the host already imports it that way, match the existing import rather than switching to the package.

Do not infer the import path from file discovery alone. Prefer one consistent import across the codebase.

### Step 4: Add or update component

Determine which sub-step applies:

- Component NOT found in Step 1 → go to **4a (New installation)**
- Component found in Step 1 → go to **4b (Update existing)**

#### 4a — New installation

1. If the user already specified a target file, use that file. Otherwise, ask the user: _"Which file should I add the Agentforce Conversation Client to?"_ Do NOT proceed until a target file is confirmed. (React: a `*.tsx`/`*.jsx` component. Angular: the host component's `*.html` template — plus its `*.ts` for import + `imports: []` registration.)
2. Read the target file(s) to understand the existing imports and template structure.
3. Add the import from Step 3. **Angular additionally requires registering the component in the host `@Component({ imports: [...] })` array** — without this the element renders nothing.
4. Insert the element as a sibling of existing content — do NOT wrap or restructure existing markup. Use the real `agentId` from Step 2, or the placeholder `<YOUR_AGENT_ID>` if the user skipped Step 2.

**React (JSX):**
```tsx
<AgentforceConversationClient agentId="0Xx8X00000001AbCDE" />
```

**Angular (template):**
```html
<app-agentforce-conversation-client agentId="0Xx8X00000001AbCDE" />
```

5. Do NOT add any other code (wrappers, layout components, new functions) unless the user explicitly requests it.

> **Angular prop-binding rule (critical):** input *names* are identical to React, but binding syntax differs. A bare attribute is a **string**, so booleans/numbers/objects MUST use `[prop]` binding:
> - string → `agentId="0Xx..."`, `width="420px"` (plain attribute is fine)
> - boolean → `[inline]="true"`, `[headerEnabled]="false"` (NOT bare `inline`, which yields the string `""`)
> - number → `[width]="420"`
> - object → `[styleTokens]="{ headerBlockBackground: '#0176d3' }"`

**Verify before finishing (Angular):**

- [ ] Every non-string input (boolean/number/object) uses `[prop]` binding — no bare `inline`/`headerEnabled` attributes.
- [ ] `AgentforceConversationClientComponent` is registered in the host component's `@Component({ imports: [...] })` array (the element renders nothing without it).

#### 4b — Update existing

1. Read the file identified in Step 1.
2. Locate the existing element (`<AgentforceConversationClient ... />` for React, `<app-agentforce-conversation-client ...>` for Angular).
3. Apply **only** the changes the user requested. Rules:
   - **Add** new props that the user asked for.
   - **Change** prop values the user asked to update.
   - **Preserve** every prop and value the user did NOT mention — do not remove, reorder, or reformat them.
   - **Never** delete the component and recreate it.
4. If Step 2 was triggered (cross-check or fresh selection) and a new agent ID was resolved, replace the existing agentId value with the new one.
5. If the current `agentId` is already valid and the user did not ask to change it and Step 2 confirmed it is active, leave it as-is.

#### Post-Step-4 error handling

If the user reports an error after the component has been set up (e.g., "it's not working", "I see an error"), go to Step 2 to validate the configured agentId against the org. Cross-check whether the agent is active, exists, and belongs to the connected org.

### Step 5: Configure props

**Available props/inputs (identical names in both frameworks; only the binding syntax differs — see the Angular rule in Step 4a):**

- `agentId` (string, required) - Salesforce agent ID
- `inline` (boolean) - `true` for inline mode, omit for floating
- `width` (number | string) - e.g., `420` or `"100%"`
- `height` (number | string) - e.g., `600` or `"80vh"`
- `headerEnabled` (boolean) - Show/hide header
- `styleTokens` (object) - For all styling (colors, fonts, spacing)
- `salesforceOrigin` (string) - Auto-resolved
- `frontdoorUrl` (string) - Auto-resolved
- `agentLabel` (string) - header title for agent

**Examples:**

Floating mode (default):

```tsx
// React
<AgentforceConversationClient agentId="0Xx..." />
```
```html
<!-- Angular -->
<app-agentforce-conversation-client agentId="0Xx..." />
```

Inline mode with dimensions:

```tsx
// React
<AgentforceConversationClient agentId="0Xx..." inline width="420px" height="600px" />
```
```html
<!-- Angular — boolean input needs [ ] binding -->
<app-agentforce-conversation-client agentId="0Xx..." [inline]="true" width="420px" height="600px" />
```

Adding or updating agent label:

```tsx
// React
<AgentforceConversationClient agentId="0Xx..." agentLabel="<dummy-agent-label>" />
```
```html
<!-- Angular -->
<app-agentforce-conversation-client agentId="0Xx..." agentLabel="<dummy-agent-label>" />
```

**Styling rules (mandatory):**

- ALL visual customization (colors, fonts, spacing, borders, radii, shadows) MUST go through the `styleTokens` prop/input. There are no exceptions.
- ONLY use token names listed in the tables below. Do NOT invent custom token names.
- NEVER apply styling via CSS files, `style` attributes, `className`/`class`, or wrapper elements. These approaches will not work and will be ignored by the component.
- Angular: pass tokens with `[styleTokens]="{ ... }"` binding (an object), not a bare attribute.
- If the user requests a visual change that does not map to a token below, inform them that the change is not supported by the current token set.

For the complete list of available style tokens, consult `references/style-tokens.md`.

**For complex patterns,** consult `references/examples.md` for:

- Sidebar containers and responsive sizing
- Dark theme and advanced theming combinations
- Inline without header, calculated dimensions
- Complete host component examples


**Common mistakes to avoid:** Consult `references/constraints.md` for:

- Invalid props (containerStyle, style, className)
- Invalid styling approaches (CSS files, style tags)
- What files NOT to edit (implementation files)

## Common Issues

If component doesn't appear or authentication fails, see `references/troubleshooting.md` for:

- Agent activation and deployment
- Localhost trusted domains
- Cookie restriction settings

## Reference File Index

| File | When to read |
|------|-------------|
| `references/agent-id-resolution.md` | Step 2 — SOQL query structure, response format, activation path, manual lookup |
| `references/style-tokens.md` | Step 5 — Complete style token reference for all UI areas |
| `references/examples.md` | Step 5 — Layout patterns, sizing, theming combinations, host component examples |
| `references/constraints.md` | Step 4 — Invalid props, invalid styling approaches, files not to edit |
| `references/troubleshooting.md` | Post-setup — Agent activation, trusted domains, cookie settings |
