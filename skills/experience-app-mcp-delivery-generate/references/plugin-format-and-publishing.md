# Claude Plugin Package and Publication

This format and the bundled generator support Claude plugins only. Reject Codex, ChatGPT, and other non-Claude plugin requests before running discovery or generation; do not package a Claude plugin as a substitute. If the plugin platform is unspecified, resolve it before proceeding.

Read before generating files. Format sources are the [official example README](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/example-plugin/README.md), [plugin manifest reference](https://code.claude.com/docs/en/plugins-reference), [MCP OAuth reference](https://code.claude.com/docs/en/mcp#use-pre-configured-oauth-credentials), and [submission guide](https://claude.com/docs/plugins/submit). Check these sources again if the target client's validator disagrees; do not treat a locally generated skeleton as directory approval.

## Required layout

```text
<plugin-repository>/
  .claude-plugin/plugin.json
  .mcp.json
  README.md
  .gitignore
  assets/                       # only when the user supplies an icon
  skills/                       # only when requested
    <skill-name>/SKILL.md
    <skill-name>/references/...
    <skill-name>/scripts/...
```

Only the manifest lives inside `.claude-plugin/`; skills and `.mcp.json` live at the plugin root. Prefer `skills/<name>/SKILL.md` over legacy `commands/*.md`. A marketplace manifest is not required merely to package a plugin repository for submission. Do not copy Anthropic branding or its example author's identity/license into a new package.

The plugin manifest contains `name`, semantic `version`, `description`, `author.name`, and the user's optional author email, repository URL and chosen license identifier. Use a stable kebab-case plugin name; never silently rename an already published plugin. First release can use `1.0.0`, then increment patch/minor/major according to the change. The skill's own metadata version and generated plugin's semantic version are separate.

For the icon choice established in the skill, supply `iconPath` as an absolute path to a regular, non-empty PNG, JPEG or WebP file, at most 5 MiB. Directories and symlinks are rejected. Omit `iconPath` when the user skips it. Prefer a square, legible image; local validation does not certify directory acceptance. If the generator rejects the input, report the error and ask for a valid replacement or an explicit decision to omit the icon. Do not substitute a placeholder or reuse a removed icon.

The icon is for the directory listing, not an MCP tool widget. If the client validator warns about the icon field, report the installed Claude Code version and the warning, and check the [manifest reference](https://code.claude.com/docs/en/plugins-reference#directory-listing-fields) before resolving it. Do not silently remove the selected icon.

## Configuration for the bundled generator

This example is a configuration schema illustration, not real connection data. Replace every value using the selected org and user choices. Keep the temporary config outside both this repo and the public output.

```json
{
  "destination": "/absolute/user-chosen/new-plugin-folder",
  "name": "partner-tools",
  "version": "1.0.0",
  "description": "Use approved partner operations through the Experience Site MCP server.",
  "author": { "name": "User-provided author" },
  "repository": "https://github.com/owner/partner-tools",
  "authStyle": "claude-code",
  "iconPath": "/absolute/path/to/user-selected-icon.png",
  "mcp": {
    "serverName": "partner-tools",
    "environment": "production",
    "domain": "your-my-domain",
    "siteDeveloperName": "PartnerPortal",
    "mcpName": "PartnerTools",
    "clientId": "actual-public-eca-consumer-key"
  },
  "skills": ["/absolute/path/to/optional-skill"]
}
```

Use `skills: []` for an MCP-only plugin. Substitute the selected environment (`production`, `developer`, `sandbox` or `scratch`), its My Domain token and the exact site/server developer names as described in the skill; the generator builds the environment's route, so users need not supply or assemble it. Replace the four route components with `mcp.url` only when reusing an authoritative setup URL. Do not normalize the server's DeveloperName or site developer name to the plugin slug. `serverName` is the local MCP configuration key, not a Salesforce record identifier.

`authStyle` accepts `"claude-code"` (the default when omitted) or `"requested"` (a custom OAuth profile requiring an explicit user request for the Claude plugin). Both produce the same Claude plugin package format; `"requested"` does not enable Codex, ChatGPT, or other plugin platforms. Use the default for Claude Code and leave custom OAuth compatibility pending until verified. The generator constructs the connection configuration. Report incompatible or ignored settings found during client validation and resolve the profile or inputs before retrying. A consumer secret, access token, refresh token or org-auth file must never enter either profile.

## Local verification

### Callback port input

Set `mcp.callbackPort` only to a user-selected JSON integer from 1 through 65535, and only with the `claude-code` profile. Omit the input when the user skips or cannot provide a port; do not supply `null`, an empty string or a guessed value. Check that the intended redirect URI matches the ECA registration; report that check as pending if unverified, and do not modify org settings as part of packaging.

Present the generated README's **Local check** instructions, preserving one command per fenced block and its safely quoted destination. Adapt the CLI path when needed. The launch command is for the user to run; do not start an interactive session automatically.

Run validation on the final files, not just an earlier preview. Record exit status, errors and warnings, fix packaging errors, and rerun after changes. Compare the generated connection settings with the approved inputs; a successful manifest check alone does not verify the connection. If the executable is not on PATH, use its installed absolute path when available; otherwise mark validation pending.

In the interactive client, use `/mcp` to authenticate with the intended Experience Site user and inspect the available tools. Check that the OAuth client and allowed redirect URI match the ECA, the server is active, and the user has permission for the backing actions. Read-only listing is sufficient for packaging verification; do not execute an action just to test the connection. A successful connection does not prove every business tool works or a widget renders.

## Private GitHub handoff

Before upload, review every generated and copied file, resolve confidential material or machine-specific references, and clear routing/auth compatibility failures. A private repository still must not contain secrets. Discuss licensing before distribution. Present the generated README's **Publication** instructions and replace any owner placeholder with the user's intended private repository on github.com. Check the active account and intended owner's permissions; private visibility does not bypass managed-account restrictions. Creating a repository, uploading, tagging or submitting requires a separate user request.

Preserve one command per fenced block, with labels and blank lines between blocks. Tell users to run commands separately and stop on the first error. Keep repository creation private by default, and adapt the README's release tag to the selected semantic version. Create and push a release tag only after successful upload.

For an existing local repository, skip `git init`; commit only if there are changes. For an existing GitHub repository, provide its verified `git remote add origin`/push steps instead of creating a duplicate; inspect an existing `origin` before changing it. Do not recreate, move or force-push an existing release tag. The plugin files belong at the repository root. Keep `.claude-plugin/plugin.json` and release tags aligned for later versions. If no license has been chosen, label that distribution work pending rather than copying a sample license.

Private GitHub hosting is separate from public directory submission. After local and client checks, follow [Submit your plugin](https://claude.com/docs/plugins/submit) to review the current access/visibility requirements; do not promise that a private repository is eligible or automatically make it public. Valid structure is not marketplace acceptance. Do not create an Anthropic-owned `/plugins/` entry or submit a PR to the example as the default route for a third-party plugin. End the user-facing completion message with this submission guide as its final documentation link.
