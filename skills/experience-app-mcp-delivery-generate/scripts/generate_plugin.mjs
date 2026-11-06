#!/usr/bin/env node
// Preview or create a standalone Claude plugin without changing Salesforce,
// Git state, or an existing destination. The OAuth client ID is public; no secrets belong here.
import { createMcpConfig } from "./mcp_config.mjs";
import fs from "node:fs";
import path from "node:path";

const KEBAB = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;
const SKIP = new Set([".git", "node_modules", ".DS_Store", "__pycache__"]);
function need(condition, message) { if (!condition) throw new Error(message); }
function text(value, name) { need(typeof value === "string" && value.trim(), `${name} must be a non-empty string`); return value.trim(); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function shellQuote(value) { return "'" + value.replaceAll("'", "'\\''") + "'"; }
function within(parent, child) { const rel = path.relative(parent, child); return rel === "" || (!rel.startsWith(`..${path.sep}`) && rel !== ".." && !path.isAbsolute(rel)); }

function iconFile(input) {
  need(typeof input === "string" && path.isAbsolute(input), "iconPath must be an absolute path to the user-selected image");
  const stat = fs.lstatSync(input);
  need(stat.isFile(), "iconPath must be a regular file, not a directory or symlink");
  need(stat.size > 0 && stat.size <= 5 * 1024 * 1024, "Plugin icon must be non-empty and at most 5 MiB");
  const extension = path.extname(input).toLowerCase();
  const content = fs.readFileSync(input);
  const valid = extension === ".png" ? content.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
    : [".jpg", ".jpeg"].includes(extension) ? content[0] === 255 && content[1] === 216 && content[2] === 255
    : extension === ".webp" && content.toString("ascii", 0, 4) === "RIFF" && content.toString("ascii", 8, 12) === "WEBP";
  need(valid, "iconPath must contain a PNG, JPEG or WebP image matching its extension");
  return { relative: `assets/icon${extension}`, content, mode: 0o644 };
}

function skillFiles(input, destination) {
  need(path.isAbsolute(input), "Skill paths must be absolute");
  const source = fs.realpathSync(input);
  need(fs.statSync(source).isDirectory(), "A skill path must point to a directory");
  need(!within(source, destination), "Plugin destination cannot be inside an included skill");
  const content = fs.readFileSync(path.join(source, "SKILL.md"), "utf8");
  const frontmatter = content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1];
  const name = frontmatter?.match(/^name:\s*["']?([a-z0-9]+(?:-[a-z0-9]+)*)["']?\s*$/m)?.[1];
  need(name && name.length <= 64 && /^description:\s*\S/m.test(frontmatter), `Skill must have a kebab-case name and description in SKILL.md: ${input}`);
  const files = [];
  function visit(dir, relative = "") {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (SKIP.has(entry.name)) continue;
      const rel = path.posix.join(relative, entry.name);
      need(!entry.isSymbolicLink(), `Resolve skill symlinks before packaging: ${rel}`);
      need(!/^(?:\.env(?:\..*)?|\.npmrc|\.pypirc|\.sf|\.sfdx|a4d_mcp_settings\.json)$|\.(?:pem|key)$/i.test(entry.name), `Remove credential/configuration files from the skill before packaging: ${rel}`);
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) visit(file, rel);
      else {
        need(entry.isFile(), `Unsupported skill entry: ${rel}`);
        files.push({ relative: `skills/${name}/${rel}`, content: fs.readFileSync(file), mode: fs.statSync(file).mode & 0o777 });
      }
    }
  }
  visit(source);
  return { name, files };
}

function main() {
  const args = process.argv.slice(2);
  need(args.length === 1 || (args.length === 2 && args[1] === "--write"), "Usage: generate_plugin.mjs <CONFIG_JSON> [--write]");
  const config = readJson(args[0]);
  const name = text(config.name, "name");
  need(KEBAB.test(name) && name.length <= 64, "Plugin name must be kebab-case and at most 64 characters");
  need(!/^(?:claude|anthropic|anthropics|cc-plugin)(?:-|$)/.test(name), "Choose a plugin name that does not impersonate the client vendor");
  const version = config.version ?? "1.0.0";
  need(SEMVER.test(version), "Plugin version must be semantic versioning, for example 1.0.0");
  need(typeof config.destination === "string" && path.isAbsolute(config.destination), "destination must be the user-selected absolute path for a new plugin directory");
  const destination = path.resolve(config.destination);
  need(destination !== path.parse(destination).root && !fs.existsSync(destination), "Destination already exists or is a filesystem root; select a new directory");
  const description = text(config.description, "description");
  const author = { name: text(config.author?.name, "author.name") };
  if (config.author.email) author.email = text(config.author.email, "author.email");
  const manifest = { name, version, description, author };
  if (config.repository) {
    need(/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/.test(config.repository), "repository must be the intended github.com repository URL");
    manifest.repository = config.repository;
  }
  if (config.license) manifest.license = text(config.license, "license");
  const icon = config.iconPath === undefined ? null : iconFile(config.iconPath);
  if (icon) manifest.icon = `./${icon.relative}`;
  const mcpConfig = createMcpConfig(config);
  const server = Object.values(mcpConfig.mcpServers)[0];
  const url = server.url;
  const authStyle = config.authStyle ?? "claude-code";
  const sources = config.skills ?? [];
  need(Array.isArray(sources), "skills must be an array of absolute skill directory paths");
  const skills = sources.map((source) => skillFiles(source, destination));
  need(new Set(skills.map((skill) => skill.name)).size === skills.length, "Included skills have duplicate names");
  const jsonFile = (relative, value) => ({ relative, content: JSON.stringify(value, null, 2) + "\n", mode: 0o644 });
  const repository = config.repository ? new URL(config.repository).pathname.replace(/^\/|\/$/g, "") : `OWNER/${name}`;
  const localCheck = `Copy and run each command separately. Continue only after changing directory successfully.

Enter the plugin directory:

\`\`\`bash
cd -- ${shellQuote(destination)}
\`\`\`

Validate:

\`\`\`bash
claude plugin validate .
\`\`\`

Launch Claude with the plugin:

\`\`\`bash
claude --plugin-dir .
\`\`\``;
  const publication = `Review files before uploading; a private repository must not contain secrets. Use a private GitHub repository and retain the kebab-case plugin name. ${config.repository ? "The commands use your selected repository." : "Replace OWNER below with your approved GitHub username or organization."} Check the active GitHub account and owner permissions; private visibility does not bypass enterprise-managed account restrictions.

Copy and run each command separately using its own code block, and stop on any error. Do not copy the entire multi-step section at once. The following is for a new local repository and a new remote only. For an existing repository, skip initialization, commit only changed files and inspect any existing origin before adding or changing it.

Initialize:

\`\`\`bash
git init -b main
\`\`\`

Stage files:

\`\`\`bash
git add .
\`\`\`

Commit:

\`\`\`bash
git commit -m "Initial plugin package"
\`\`\`

Create the private remote and upload:

\`\`\`bash
gh repo create ${repository} --private --source . --remote origin --push
\`\`\`

Only after successful upload, create the release tag if it does not already exist. Do not recreate or move an existing tag.

\`\`\`bash
git tag v${version}
\`\`\`

Push the tag:

\`\`\`bash
git push origin v${version}
\`\`\`

Bump the semantic version for later releases. Private hosting is separate from public directory submission: review the access/visibility requirements and licensing before submission, and do not change repository visibility automatically. Follow [Submit your plugin](https://claude.com/docs/plugins/submit); local validation does not guarantee directory approval.
`;
  const files = [
    jsonFile(".claude-plugin/plugin.json", manifest),
    jsonFile(".mcp.json", mcpConfig),
    ...(icon ? [icon] : []),
    { relative: ".gitignore", content: ".DS_Store\n.env\n.env.*\n*.log\nnode_modules/\n", mode: 0o644 },
    { relative: "README.md", content: `# ${name}\n\n${description}\n\n## Connection\n\nThis plugin connects to the Salesforce hosted MCP server at:\n\n${url}\n\nSign in as the intended Experience Site user through the client's OAuth flow. The ECA consumer key is a public OAuth client ID; this package contains no client secret or access token. Confirm that the ECA callback URLs match the client, that required MCP scopes are enabled, and that the user has access to the selected server and its actions.\n\n${authStyle === "requested" ? "This package uses the requested submission profile, `auth.CLIENT_ID`. Verify that the target client accepts it; current Claude Code documents `oauth.clientId` instead. This profile is not proof of runtime compatibility." : "This package uses Claude Code's documented `oauth.clientId` configuration."}\n\n## Local check\n\n${localCheck}\n\nIn Claude Code, open \`/mcp\`, complete OAuth, and check that expected tools are listed. Inspect tool descriptions before executing an action. Local metadata validation alone does not verify routing, OAuth, or tool execution.\n\n## Included skills\n\n${skills.length ? skills.map((skill) => `- \`${name}:${skill.name}\` — see \`skills/${skill.name}/SKILL.md\`.`).join("\n") : "No skills are bundled; this plugin provides the MCP connection."}\n\n## Publication\n\n${publication}`, mode: 0o644 },
    ...skills.flatMap((skill) => skill.files),
  ];
  if (args[1] === "--write") {
    const parent = path.dirname(destination);
    fs.mkdirSync(parent, { recursive: true });
    const staging = fs.mkdtempSync(path.join(parent, ".plugin-package-"));
    try {
      for (const file of files) {
        const target = path.join(staging, file.relative);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, file.content, { mode: file.mode });
      }
      need(!fs.existsSync(destination), "Destination appeared during generation; nothing was replaced");
      fs.renameSync(staging, destination);
    } catch (error) {
      fs.rmSync(staging, { recursive: true, force: true });
      throw error;
    }
  }
  console.log(JSON.stringify({ status: args[1] === "--write" ? "created" : "preview", destination, plugin: name, version, url, authStyle, skills: skills.map((skill) => skill.name), files: files.map((file) => file.relative), runtimeVerified: false }, null, 2));
}

try { main(); } catch (error) {
  console.log(JSON.stringify({ status: "blocked", error: error.message }, null, 2));
  process.exitCode = 1;
}
