#!/usr/bin/env node
/**
 * Dev preview: refresh the GraphQL schema/types against a target org, then launch
 * the Vite dev server (spec §5.5, M4). This is the step that used to be the final
 * `dev` stage of org-setup.mjs — extracted here so `npm run setup` terminates
 * cleanly after graphql, and the long-lived dev server is an explicit, separate
 * `npm run dev:preview`.
 *
 * Unlike setup, this does NOT log in or deploy — it assumes the org is already
 * set up. It shares org/bundle resolution and the process runner with org-setup
 * via org-setup-utils.mjs.
 *
 * Usage:
 *   npm run dev:preview                                 # prompt to pick an org + bundle
 *   npm run dev:preview -- --target-org myorg
 *   npm run dev:preview -- --target-org myorg --ui-bundle-name my-app
 *
 * Flow (in order):
 *   1. resolve target org (explicit --target-org, else prompt / default org)
 *   2. resolve UI bundle (explicit --ui-bundle-name, else picker / warning)
 *   3. npm install            (in the UI bundle)
 *   4. npm run graphql:schema (SF_TARGET_ORG=<org>)  — introspect the live schema
 *   5. npm run graphql:codegen                       — regenerate typed operations
 *   6. npm run dev            (blocking, Ctrl+C to stop)
 */

import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { run, resolveSfdxSource, discoverUIBundleDir, resolveTargetOrg } from './org-setup-utils.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

function parseArgs() {
  const args = process.argv.slice(2);
  let targetOrg = null;
  let uiBundleName = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--target-org' && args[i + 1]) {
      targetOrg = args[++i];
    } else if (args[i] === '--ui-bundle-name' && args[i + 1]) {
      uiBundleName = args[++i];
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log(`
Dev preview — refresh GraphQL types then launch the Vite dev server

Usage:
  npm run dev:preview -- [--target-org <alias>] [--ui-bundle-name <name>]

Options:
  --target-org <alias>    Target Salesforce org alias. If omitted, you are prompted
                          to pick from authenticated orgs (or the default org is used).
  --ui-bundle-name <name> UI bundle folder under uiBundles/ (default: auto-detect / prompt)
  -h, --help              Show this help
`);
      process.exit(0);
    }
  }
  return { targetOrg, uiBundleName };
}

/**
 * Print a heads-up about auth surfaces that only work on the deployed Experience
 * site. In local preview, `sdk.fetch` is proxied to the org outside the site's
 * guest/community context, so social login and password/MFA login cannot be
 * exercised on localhost. This mirrors the "Local preview limitations" sections
 * in the feature-react-authentication / feature-react-mfa READMEs — surfaced here
 * so it is seen even when the READMEs are not.
 */
function printLocalPreviewWarning() {
  console.log(
    [
      '',
      '⚠️  Local preview limitation — some auth surfaces only work on the DEPLOYED site',
      '   Local preview proxies sdk.fetch to the org outside the Experience site guest',
      '   context (Site.getBaseUrl() is blank, no site session), so on localhost:',
      '     • Social Login buttons do not render (/auth/social-login-config returns no providers)',
      '     • Password / MFA login fails with "Your login attempt has failed…" (Site.login() cannot',
      '       establish the site session)',
      '   This is expected, not a misconfiguration. Test social login and MFA on the published',
      '   site login page: https://<domain>.site.com/<site-path>/login',
      '',
    ].join('\n'),
  );
}

async function main() {
  const parsed = parseArgs();

  const targetOrg = await resolveTargetOrg(parsed);
  const uiBundlesDir = resolve(resolveSfdxSource(ROOT), 'uiBundles');
  const uiBundleDir = await discoverUIBundleDir(uiBundlesDir, parsed.uiBundleName);

  console.log('Dev preview — target org:', targetOrg, '| UI bundle:', uiBundleDir);

  run('UI Bundle npm install', 'npm', ['install'], { cwd: uiBundleDir });
  run('GraphQL schema (introspect)', 'npm', ['run', 'graphql:schema'], {
    cwd: uiBundleDir,
    env: { ...process.env, SF_TARGET_ORG: targetOrg },
  });
  run('GraphQL codegen', 'npm', ['run', 'graphql:codegen'], { cwd: uiBundleDir });

  printLocalPreviewWarning();

  console.log('\n--- Launching dev server (Ctrl+C to stop) ---\n');
  const devResult = run('Dev server', 'npm', ['run', 'dev'], { cwd: uiBundleDir, optional: true });
  process.exit(devResult.status ?? 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
