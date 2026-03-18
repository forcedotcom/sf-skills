#!/usr/bin/env node
/**
 * One-command setup: login, deploy, data import, GraphQL schema/codegen, web app build.
 * Provided by the property management feature. Run from the SFDX project root (e.g. dist/).
 *
 * Usage:
 *   node setup-cli.mjs --target-org <alias>   # run all steps
 *   node setup-cli.mjs --target-org afv5 --skip-login
 *   node setup-cli.mjs --target-org afv5 --skip-data --skip-webapp-build
 *   node setup-cli.mjs --target-org myorg --app appreactsampleb2x   # when multiple web apps
 *
 * Steps (in order):
 *   1. login     — sf org login web only if org not already connected (skip with --skip-login)
 *   2. deploy    — sf project deploy start --target-org <alias>
 *   3. permset   — sf org assign permset (default: Property_Management_Access; override with --permset)
 *   4. data      — prepare unique fields + sf data import tree (skipped if no data-plan.json)
 *   5. graphql   — (in webapp) npm run graphql:schema then npm run graphql:codegen
 *   6. webapp    — (in webapp) npm install && npm run build
 *   7. dev       — (in webapp) npm run dev — launch dev server (skip with --skip-dev)
 */

import { spawnSync } from "node:child_process";
import { readdirSync, existsSync } from "node:fs";
import { resolve, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
/** SFDX project root: when run from dist/, the script lives in dist/ and force-app is under dist/ */
const ROOT = __dirname;
const WEBAPPLICATIONS_DIR = resolve(ROOT, "force-app/main/default/webapplications");
const DATA_DIR = resolve(ROOT, "force-app/main/default/data");
const DATA_PLAN = resolve(DATA_DIR, "data-plan.json");
const PREPARE_SCRIPT = resolve(DATA_DIR, "prepare-import-unique-fields.js");

function parseArgs() {
	const args = process.argv.slice(2);
	let targetOrg = null;
	let appName = null;
	let permsetName = "Property_Management_Access";
	const flags = {
		skipLogin: false,
		skipDeploy: false,
		skipPermset: false,
		skipData: false,
		skipGraphql: false,
		skipWebappBuild: false,
		skipDev: false,
	};
	for (let i = 0; i < args.length; i++) {
		if (args[i] === "--target-org" && args[i + 1]) {
			targetOrg = args[++i];
		} else if (args[i] === "--app" && args[i + 1]) {
			appName = args[++i];
		} else if (args[i] === "--permset" && args[i + 1]) {
			permsetName = args[++i];
		} else if (args[i] === "--skip-login") flags.skipLogin = true;
		else if (args[i] === "--skip-deploy") flags.skipDeploy = true;
		else if (args[i] === "--skip-permset") flags.skipPermset = true;
		else if (args[i] === "--skip-data") flags.skipData = true;
		else if (args[i] === "--skip-graphql") flags.skipGraphql = true;
		else if (args[i] === "--skip-webapp-build") flags.skipWebappBuild = true;
		else if (args[i] === "--skip-dev") flags.skipDev = true;
		else if (args[i] === "--help" || args[i] === "-h") {
			console.log(`
Setup CLI (property management feature)

Usage:
  node setup-cli.mjs --target-org <alias> [options]

Required:
  --target-org <alias>   Target Salesforce org alias (e.g. afv5)

Options:
  --app <name>           Web app folder name (default: auto-detect if only one in force-app/.../webapplications/)
  --permset <name>       Permission set to assign (default: Property_Management_Access)
  --skip-login           Skip login step (login is auto-skipped if org is already connected)
  --skip-deploy          Do not deploy metadata
  --skip-permset         Do not assign permission set
  --skip-data            Do not prepare data or run data import
  --skip-graphql         Do not fetch schema or run GraphQL codegen
  --skip-webapp-build    Do not npm install / build the web application
  --skip-dev             Do not launch the dev server at the end
  -h, --help             Show this help
`);
			process.exit(0);
		}
	}
	if (!targetOrg) {
		console.error("Error: --target-org <alias> is required.");
		process.exit(1);
	}
	return { targetOrg, appName, permsetName, ...flags };
}

function discoverWebAppDir(appNameOverride) {
	if (appNameOverride) {
		const dir = resolve(WEBAPPLICATIONS_DIR, appNameOverride);
		if (!existsSync(dir)) {
			console.error(`Error: Web app directory not found: ${dir}`);
			process.exit(1);
		}
		return dir;
	}
	if (!existsSync(WEBAPPLICATIONS_DIR)) {
		console.error(`Error: Web applications directory not found: ${WEBAPPLICATIONS_DIR}`);
		process.exit(1);
	}
	const entries = readdirSync(WEBAPPLICATIONS_DIR, { withFileTypes: true });
	const dirs = entries.filter((e) => e.isDirectory());
	if (dirs.length === 0) {
		console.error(
			"Error: No web application folder found under force-app/main/default/webapplications/",
		);
		process.exit(1);
	}
	if (dirs.length > 1) {
		console.error(
			"Error: Multiple web applications found. Specify one with --app <name>. Choices:",
			dirs.map((d) => d.name).join(", "),
		);
		process.exit(1);
	}
	return resolve(WEBAPPLICATIONS_DIR, dirs[0].name);
}

function isOrgConnected(targetOrg) {
	const result = spawnSync("sf", ["org", "display", "--target-org", targetOrg, "--json"], {
		cwd: ROOT,
		stdio: "pipe",
		shell: true,
	});
	return result.status === 0;
}

function run(name, cmd, args, opts = {}) {
	const { cwd = ROOT, optional = false } = opts;
	console.log("\n---", name, "---");
	const result = spawnSync(cmd, args, {
		cwd,
		stdio: "inherit",
		shell: true,
		...(opts.timeout && { timeout: opts.timeout }),
	});
	if (result.status !== 0 && !optional) {
		console.error(`\nSetup failed at step: ${name}`);
		process.exit(result.status ?? 1);
	}
	return result;
}

function main() {
	const {
		targetOrg,
		appName: appNameOverride,
		permsetName,
		skipLogin,
		skipDeploy,
		skipPermset,
		skipData,
		skipGraphql,
		skipWebappBuild,
		skipDev,
	} = parseArgs();

	const WEBAPP_DIR = discoverWebAppDir(appNameOverride);
	const webAppName = appNameOverride || basename(WEBAPP_DIR);

	console.log("Setup — target org:", targetOrg, "| web app:", webAppName);
	console.log(
		"Steps: login=%s deploy=%s permset=%s data=%s graphql=%s webapp=%s dev=%s",
		!skipLogin,
		!skipDeploy,
		!skipPermset,
		!skipData,
		!skipGraphql,
		!skipWebappBuild,
		!skipDev,
	);

	if (!skipLogin) {
		if (isOrgConnected(targetOrg)) {
			console.log("\n--- Login ---");
			console.log(`Org ${targetOrg} is already authenticated; skipping browser login.`);
		} else {
			run("Login (browser)", "sf", ["org", "login", "web", "--alias", targetOrg], {
				optional: true,
			});
		}
	}

	if (!skipDeploy) {
		run("Deploy metadata", "sf", ["project", "deploy", "start", "--target-org", targetOrg], {
			timeout: 180000,
		});
	}

	if (!skipPermset) {
		console.log("\n--- Assign permission set ---");
		const permsetResult = spawnSync(
			"sf",
			["org", "assign", "permset", "--name", permsetName, "--target-org", targetOrg],
			{
				cwd: ROOT,
				stdio: "pipe",
				shell: true,
			},
		);
		if (permsetResult.status === 0) {
			console.log("Permission set assigned.");
		} else {
			const out =
				(permsetResult.stderr?.toString() || "") + (permsetResult.stdout?.toString() || "");
			if (out.includes("Duplicate") && out.includes("PermissionSet")) {
				console.log("Permission set already assigned; skipping.");
			} else {
				process.stdout.write(permsetResult.stdout?.toString() || "");
				process.stderr.write(permsetResult.stderr?.toString() || "");
				console.error("\nSetup failed at step: Assign permission set");
				process.exit(permsetResult.status ?? 1);
			}
		}
	}

	const hasDataPlan = existsSync(DATA_PLAN);
	const hasPrepareScript = existsSync(PREPARE_SCRIPT);

	if (!skipData) {
		if (hasPrepareScript) {
			run("Prepare data (unique fields)", "node", [PREPARE_SCRIPT], { cwd: DATA_DIR });
		} else {
			console.log("\n--- Prepare data ---");
			console.log("No prepare-import-unique-fields.js found; skipping.");
		}
		if (hasDataPlan) {
			run(
				"Data import tree",
				"sf",
				["data", "import", "tree", "--plan", DATA_PLAN, "--target-org", targetOrg],
				{
					timeout: 120000,
				},
			);
		} else {
			console.log("\n--- Data import ---");
			console.log("No data-plan.json found; skipping data import.");
		}
	}

	if (!skipGraphql || !skipWebappBuild) {
		run("Web app npm install", "npm", ["install"], { cwd: WEBAPP_DIR });
	}

	if (!skipGraphql) {
		run("Set default org for schema", "sf", ["config", "set", "target-org", targetOrg, "--global"]);
		run("GraphQL schema (introspect)", "npm", ["run", "graphql:schema"], { cwd: WEBAPP_DIR });
		run("GraphQL codegen", "npm", ["run", "graphql:codegen"], { cwd: WEBAPP_DIR });
	}

	if (!skipWebappBuild) {
		run("Web app build", "npm", ["run", "build"], { cwd: WEBAPP_DIR });
	}

	console.log("\n--- Setup complete ---");

	if (!skipDev) {
		console.log("\n--- Launching dev server (Ctrl+C to stop) ---\n");
		run("Dev server", "npm", ["run", "dev"], { cwd: WEBAPP_DIR });
	}
}

main();
