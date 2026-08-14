---
name: experience-lwc-runtime-observe
description: "Use when running Salesforce Lightning Preview for an app or a single LWC component to extract the runtime DOM for inspection. TRIGGER when the user says \"preview an LWC locally\", \"run sf lightning dev\", \"launch Local Dev\", \"inspect a component's shadow DOM at runtime\", \"grab rendered HTML from a live preview\", \"troubleshoot what actually renders versus the template\", \"set up Salesforce Live Preview plugin\", \"lightning preview\", \"local dev server\", or \"extract runtime DOM\". DO NOT TRIGGER when the user is authoring or editing LWC source code (use experience-lwc-generate) or reviewing component code statically without running it."
metadata:
  version: "1.0"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - experience-lwc-generate
---
<!-- adk-managed-skill -->

# Previewing LWC Runtime — Local Dev + DOM Inspection

Guides the agent through two sequential jobs that typically run together:

1. **Start a Lightning Preview session** with the Salesforce CLI so an LWC app
   or component renders in a local dev environment.
2. **Navigate to that preview URL and extract the runtime DOM subtree** so the
   agent (or user) can reason about what actually rendered.

Preview is the prerequisite for DOM inspection. Keep them in this order.

## When to Use This Skill

- The user wants to preview an LWC app or component locally before deploying
  (`sf lightning dev app` / `sf lightning dev component`).
- The user wants the rendered HTML subtree for a specific component at runtime
  — for a diff, a screenshot pipeline, or to reason about shadow DOM.
- The user asks why the template content "isn't in the DOM" — almost always
  a shadow-DOM misunderstanding handled in Step 2.

## Prerequisites

- Salesforce CLI (`sf`) installed. Check with `sf version`.
- `@salesforce/plugin-lightning-dev` installed. Check with `sf plugins`.
- An authenticated org (`sf org list` shows at least one connected org).
- For DOM extraction: browser automation available in the agent harness
  (Playwright, Puppeteer, Chrome DevTools Protocol — whatever is wired up).

---

## Step 1 — Start the Lightning Preview

Ask the user (or infer from the request) whether the scope is **app** or
**component**.

### 1a. Verify the toolchain

Ask the user for (or infer from the request) the org alias the preview
should target. Run the bundled verification script with that alias and
surface any error it emits — do not re-invoke `sf version` /
`sf plugins` / `sf org display` in prose. The script checks CLI
presence, `@salesforce/plugin-lightning-dev` installation, and that the
specific target alias is authenticated and Connected, and exits nonzero
with an actionable message on failure:

```bash
"<skill_dir>/scripts/verify-toolchain.sh" <orgAlias>
```

If it reports that the target alias is not authenticated or not
Connected, direct the user to
[Enable Local Dev](https://developer.salesforce.com/docs/platform/lwc/guide/get-started-test-components.html#enable-local-dev)
and have them run `sf org login web --alias <orgAlias>`, then re-run the
verification script before proceeding.

### 1b. Read the subcommand's flags

```bash
# For app scope
sf lightning dev app --help

# For component scope
sf lightning dev component --help
```

Note required vs optional flags. If a required flag is ambiguous, ask the user
before running.

### 1c. Launch the preview

Prefix every preview command with `OPEN_BROWSER=false` — the CLI opens a
browser window by default, which we do **not** want when an agent is driving.
(This env var is undocumented in `--help`; rely on it unless the user
explicitly asks for a browser window.)

| Scope       | Command                                                                               |
|-------------|---------------------------------------------------------------------------------------|
| `app`       | `OPEN_BROWSER=false sf lightning dev app -o <orgAlias> -n <appName> -t desktop`       |
| `component` | `OPEN_BROWSER=false sf lightning dev component -o <orgAlias> -n <componentName>`      |

When the preview is up, capture the URL and log it in exactly this format:

```text
Lightning Preview running at URL: <URL>
```

If any sub-step fails, stop and surface the error to the user — don't try to
paper over auth or plugin-install problems.

---

## Step 2 — Extract the Runtime DOM

Only run this step once Step 1 has produced a live preview URL.

### 2a. Get an authenticated front-door URL — **without surfacing the token to agent context**

The front-door URL returned by `sf org open --url-only --json` contains a
short-lived OTP that authenticates the session. **Never run `sf org open`
directly — its output would land in the agent tool-output stream and leak
an auth token into the transcript, violating agent-safety standard S1.**
The bundled helper is the *only* supported way to obtain the URL: it runs
`sf org open` internally with stdout redirected into a `chmod 600` tempfile
and stderr suppressed, so no URL fragment or token substring ever reaches
agent context.

Instead, use the bundled helper script, which writes the URL to a
`chmod 600` tempfile and prints only `export` assignments (no token
material). Capture the helper output first so a nonzero exit status
aborts the caller — `eval "$(...)"` alone masks failures, letting the
agent proceed with an unset `$FRONTDOOR_URL_FILE`:

```bash
frontdoor_env="$("<skill_dir>/scripts/open-frontdoor.sh" <orgAlias> <previewUrl>)" || exit 1
eval "$frontdoor_env"
```

The helper suppresses `sf` and `python3` stderr as well as stdout, so
partial URLs and progress noise never reach the agent transcript.

The browser driver must:
1. Read the URL from `$FRONTDOOR_URL_FILE`.
2. Navigate to it to establish a session.
3. Delete the tempfile immediately after use.
4. **Never `cat` or otherwise echo the file contents.**

**OTP tokens expire fast.** Bring up the browser driver *first*, then invoke
the helper just before navigating — otherwise the token goes stale.

### 2b. Navigate and wait

1. Open the preview URL from Step 1 in the automation browser.
2. Wait for the network to go idle and the initial render to complete.
3. If the expected element isn't there, back off briefly and retry before
   declaring failure — local dev pages sometimes hydrate in two phases.

### 2c. Extract the subtree

Two deterministic string operations — turning a component name into its
`c-<kebab>` selector and wrapping the extracted HTML in the exact
`DOM_OUTPUT_START` / `DOM_OUTPUT_END` markers — are handled by
`<skill_dir>/scripts/extract-dom.sh`. Do NOT re-derive the selector or
compose the markers in prose; call the script.

Actual DOM traversal must be run by the browser-automation driver
(Playwright / Puppeteer / CDP); the script does not drive the browser.

#### If scope is `component`

Compute the selector deterministically:

```bash
selector="$("<skill_dir>/scripts/extract-dom.sh" selector <componentName>)"
```

Then, using the driver, pierce the `lwr_dev-preview-container` shadow
root, locate the first visible element matching `$selector`, and read its
subtree HTML (via `element.shadowRoot.innerHTML`). Pipe that HTML into
the wrap step:

```bash
printf '%s' "$html_subtree" \
  | "<skill_dir>/scripts/extract-dom.sh" wrap component <componentName>
```

#### If scope is `app`

Using the driver, identify the primary app root (prefer `document.body`
or the main app container — not `document.documentElement`), exclude
`<head>` and non-rendered nodes, and read the subtree HTML. Pipe it into
the wrap step:

```bash
printf '%s' "$html_subtree" \
  | "<skill_dir>/scripts/extract-dom.sh" wrap app
```

Emit the script's stdout unchanged as the DOM output.

### 2d. About LWC Shadow DOM (the #1 gotcha)

Lightning Web Components use Shadow DOM. The template content is **not**
directly queryable on the host element:

| Access pattern                | What you get                         |
|-------------------------------|--------------------------------------|
| `element.innerHTML`           | empty, or only slotted light-DOM content |
| `element.outerHTML`           | just the host tag, no children       |
| `element.shadowRoot.innerHTML`| the real rendered template content   |

If the browser driver's DOM query doesn't pierce shadow roots by default,
walk `shadowRoot` explicitly. Most modern automation drivers have a
shadow-piercing query helper — use it.

---

## Examples

For a worked end-to-end example (preview a component, capture the front-door
URL safely, and extract its DOM), load
[`examples/component-preview-and-dom.md`](examples/component-preview-and-dom.md).

---

## Verification Checklist

- [ ] `<skill_dir>/scripts/verify-toolchain.sh <orgAlias>` exited zero for the target alias.
- [ ] Preview command ran with `OPEN_BROWSER=false`.
- [ ] Preview URL logged in the `Lightning Preview running at URL: <URL>` format.
- [ ] Front-door URL fetched via `<skill_dir>/scripts/open-frontdoor.sh` (never `sf org open` directly).
- [ ] DOM extraction used `shadowRoot` traversal (not `innerHTML` on the host).
- [ ] DOM output was produced by `<skill_dir>/scripts/extract-dom.sh wrap …` (script owns the markers).

---

## Troubleshooting

- **`verify-toolchain.sh` reports "Target org alias is not authenticated or not Connected"** —
  run `sf org login web --alias <orgAlias>` (the alias must match the one
  you passed to `verify-toolchain.sh` and the `-o` value the preview
  command uses).
- **`verify-toolchain.sh` reports the plugin is missing** — install it with
  `sf plugins install @salesforce/plugin-lightning-dev`.
- **Preview opens a browser window** — you forgot `OPEN_BROWSER=false`.
- **Empty DOM on extraction** — you're looking at `innerHTML` on a host. Use
  `element.shadowRoot.innerHTML` instead. Also verify you pierced the
  `lwr_dev-preview-container` shadow root.
- **Front-door token fails** — it's expired. Re-invoke
  `<skill_dir>/scripts/open-frontdoor.sh` and navigate within ~60 seconds.
