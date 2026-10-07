const fs = require('fs');
const https = require('https');
const path = require('path');
const { execFileSync } = require('child_process');
const { execSfJson, getOrgDetails } = require('./utils');

/**
 * Step 1: Download and extract the CGCloudAddons static resource
 */
async function downloadStaticResource(orgAlias, setupDir) {
  console.log('\n=== Step 1: Downloading CGCloudAddons static resource ===');

  const staticResourceName = 'CGCloudAddons';

  // Get org details for REST API call
  console.log('Getting org connection details...');
  const orgDetails = getOrgDetails(orgAlias);

  // Query for the static resource
  console.log(`Looking up ${staticResourceName} in org...`);
  const queryResult = execSfJson(['data', 'query', '--query', `SELECT Id, Name FROM StaticResource WHERE Name = '${staticResourceName}'`, '--target-org', orgAlias, '--json']);

  if (queryResult.status !== 0 || !queryResult.result.records || queryResult.result.records.length === 0) {
    console.error(`Error: Static resource ${staticResourceName} not found in org`);
    process.exit(1);
  }

  const staticResourceId = queryResult.result.records[0].Id;
  console.log(`Found ${staticResourceName} (ID: ${staticResourceId})`);

  // Download the static resource body using REST API
  console.log('Downloading static resource content...');
  const targetFile = path.join(setupDir, `${staticResourceName}.zip`);
  const bodyUrl = `${orgDetails.instanceUrl}/services/data/v${orgDetails.apiVersion}/sobjects/StaticResource/${staticResourceId}/Body`;

  await new Promise((resolve, reject) => {
    const url = new URL(bodyUrl);
    const req = https.get({
      hostname: url.hostname,
      path: url.pathname + url.search,
      headers: { Authorization: `Bearer ${orgDetails.accessToken}` }
    }, res => {
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode} downloading static resource`));
        res.resume();
        return;
      }
      const out = fs.createWriteStream(targetFile);
      res.pipe(out);
      out.on('finish', resolve);
      out.on('error', reject);
    });
    req.on('error', reject);
  });

  if (!fs.existsSync(targetFile)) {
    console.error('Error: Failed to download static resource');
    process.exit(1);
  }

  console.log(`Static resource saved to: ${targetFile}`);

  // Extract the zip file
  console.log('Extracting static resource...');
  const extractDir = path.join(setupDir, staticResourceName);

  // Remove existing extraction directory if it exists
  if (fs.existsSync(extractDir)) {
    fs.rmSync(extractDir, { recursive: true });
  }

  // Extract: tar on Windows (bsdtar handles ZIP), unzip on macOS/Linux.
  // GNU tar on Linux cannot read ZIP archives.
  const [unzipCmd, unzipArgs] = process.platform === 'win32'
    ? ['tar', ['-xf', targetFile, '-C', extractDir]]
    : ['unzip', ['-o', '-q', targetFile, '-d', extractDir]];
  try {
    execFileSync(unzipCmd, unzipArgs, { stdio: 'pipe' });
    console.log(`Extracted to: ${extractDir}`);
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.error(
        `Error: "${unzipCmd}" is not installed or not on PATH — ` +
        (process.platform === 'win32'
          ? 'expected the tar.exe bundled with Windows 10 (1803+) / 11'
          : 'install it (e.g. `apt install unzip`) and retry')
      );
    } else {
      console.error(`Error: Failed to extract zip file — ${error.message}`);
    }
    process.exit(1);
  }

  console.log('[OK] CGCloudAddons static resource downloaded and extracted successfully\n');
}

module.exports = downloadStaticResource;
