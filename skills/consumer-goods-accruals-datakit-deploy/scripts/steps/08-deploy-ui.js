const { execFileSync } = require('child_process');
const fs = require('fs');

const path = require('path');

const { exec, execDeployJson, getSfBin } = require('./utils');



/**

 * Step 8: Deploy UI components (TPMAccrualTacticSummary) with Data Space replacements

 * @param {string} orgAlias - The Salesforce org alias

 * @param {string} setupDir - The setup directory path

 * @param {boolean} skipDataSpace - Whether to skip data space configuration

 * @param {string} configuredDataSpaceName - The data space name from config

 * @param {string} configuredDataSpacePrefix - The data space prefix from config

 * @param {string} salesOrg - The sales org identifier

 * @param {string} namespace - Org namespace prefix WITH trailing "__" (e.g. "cgcloud_dev__"), or '' for unmanaged

 * @param {boolean} dryRun - If true, skip deployment but keep temp files

 */

async function deployUI(orgAlias, setupDir, skipDataSpace, configuredDataSpaceName, configuredDataSpacePrefix, salesOrg = '0001', namespace = '', dryRun = false) {

  console.log('\n=== Step 8: Deploying UI Components ===');



  // Use "default" and empty prefix if skipping data space, otherwise use configured values

  const dataSpaceName = skipDataSpace ? 'default' : configuredDataSpaceName;

  const dataSpacePrefix = skipDataSpace ? '' : configuredDataSpacePrefix;



  console.log(`Data Space Name: ${dataSpaceName}`);

  console.log(`Data Space Prefix: ${dataSpacePrefix || '(empty)'}`);

  console.log(`Sales Org: ${salesOrg}`);

  console.log(`Namespace: ${namespace || '(none)'}`);



  const sourceDir = path.join(setupDir, 'CGCloudAddons', 'TPM', 'Accruals', 'UI');

  const tempDir = path.join(setupDir, 'temp-ui');



  // Clean up temp directory if it exists

  if (fs.existsSync(tempDir)) {

    console.log('Cleaning up existing temp directory...');

    fs.rmSync(tempDir, { recursive: true });

  }



  console.log('Copying UI components to temp directory...');

  copyDirectory(sourceDir, tempDir);



  console.log('Replacing Data Space placeholders, namespace, and sales org in file names and contents...');

  replaceDataSpacePlaceholders(tempDir, dataSpaceName, dataSpacePrefix, salesOrg, namespace);



  const deployPath = path.join(tempDir, 'force-app');



  if (dryRun) {

    console.log('[DRY RUN] Skipping deployment - files prepared at:');

    console.log(`  ${tempDir}`);

    console.log('[DRY RUN] Temp directory preserved for inspection');

    console.log('[OK] Step 8 completed (dry run)\n');

    return;

  }



  console.log('Deploying UI components metadata...');

  execDeployJson(['project', 'deploy', 'start', '--source-dir', deployPath, '--target-org', orgAlias]);



  // Clean up temp directory

  console.log('Cleaning up temp directory...');

  fs.rmSync(tempDir, { recursive: true });



  console.log('[OK] UI Components deployed successfully\n');



  // Show manual step instructions

  console.log('+============================================================================+');

  console.log('|                          MANUAL STEP REQUIRED                              |');

  console.log('+============================================================================+');

  console.log('');

  console.log('  Please manually add the TPMAccrualTacticSummary component to the');

  console.log('  Promotion page in your Salesforce org.');

  console.log('');

  console.log('  Steps:');

  console.log('  1. Navigate to the Promotion page layout editor');

  console.log('  2. Add the TPMAccrualTacticSummary Lightning component to the page');

  console.log('  3. Save and activate the page');

  console.log('');

  console.log('============================================================================');

  console.log('');

}



/**

 * Recursively copy a directory

 */

function copyDirectory(src, dest) {

  if (!fs.existsSync(dest)) {

    fs.mkdirSync(dest, { recursive: true });

  }



  const entries = fs.readdirSync(src, { withFileTypes: true });



  for (const entry of entries) {

    const srcPath = path.join(src, entry.name);

    const destPath = path.join(dest, entry.name);



    if (entry.isDirectory()) {

      copyDirectory(srcPath, destPath);

    } else {

      fs.copyFileSync(srcPath, destPath);

    }

  }

}



/**

 * Replace placeholders in a name (file or directory)

 * Handles double underscore pattern to avoid DS2__ becoming DS2___

 */

function replaceNamePlaceholders(name, dataSpaceName, dataSpacePrefix) {

  let newName = name;

  if (dataSpacePrefix === '') {

    newName = newName.replace(/_DATASPACE_PREFIX__/g, '');

  } else {

    newName = newName.replace(/_DATASPACE_PREFIX__/g, dataSpacePrefix);

  }

  newName = newName

    .replace(/_DATASPACE_PREFIX_/g, dataSpacePrefix)

    .replace(/_DATASPACE_NAME_/g, dataSpaceName);

  return newName;

}



/**

 * Replace Data Space placeholders in both file names and file contents

 */

function replaceDataSpacePlaceholders(dir, dataSpaceName, dataSpacePrefix, salesOrg, namespace) {

  const entries = fs.readdirSync(dir, { withFileTypes: true });



  for (const entry of entries) {

    const oldPath = path.join(dir, entry.name);



    if (entry.isDirectory()) {

      // Recursively process subdirectories first

      replaceDataSpacePlaceholders(oldPath, dataSpaceName, dataSpacePrefix, salesOrg, namespace);



      // Rename directory if it contains placeholders

      if (entry.name.includes('_DATASPACE_PREFIX_') || entry.name.includes('_DATASPACE_NAME_')) {

        const newName = replaceNamePlaceholders(entry.name, dataSpaceName, dataSpacePrefix);

        const newPath = path.join(dir, newName);

        fs.renameSync(oldPath, newPath);

      }

    } else {

      // Process file contents

      replaceInFile(oldPath, dataSpaceName, dataSpacePrefix, salesOrg, namespace);



      // Rename file if it contains placeholders

      if (entry.name.includes('_DATASPACE_PREFIX_') || entry.name.includes('_DATASPACE_NAME_')) {

        const newName = replaceNamePlaceholders(entry.name, dataSpaceName, dataSpacePrefix);

        const newPath = path.join(dir, newName);

        fs.renameSync(oldPath, newPath);

      }

    }

  }

}



/**

 * Replace placeholders in file contents

 */

function replaceInFile(filePath, dataSpaceName, dataSpacePrefix, salesOrg, namespace) {

  try {

    let content = fs.readFileSync(filePath, 'utf8');



    // Check if file contains placeholders or hardcoded sales org

    const hasPlaceholders = content.includes('_DATASPACE_PREFIX_') || content.includes('_DATASPACE_NAME_') || content.includes('_ORG_NS_');

    const hasSalesOrgKey = content.includes("'0001':") && filePath.endsWith('Controller.js');



    if (hasPlaceholders || hasSalesOrgKey) {

      if (dataSpacePrefix === '') {

        // If dataspace prefix is empty, remove double underscore pattern entirely

        content = content.replace(/_DATASPACE_PREFIX__/g, '');

      } else {

        // Replace double underscore pattern first to avoid double underscores in output

        // _DATASPACE_PREFIX__ with DS2_ results in DS2_ (not DS2__)

        content = content.replace(/_DATASPACE_PREFIX__/g, dataSpacePrefix);

      }



      content = content

        .replace(/_DATASPACE_PREFIX_/g, dataSpacePrefix)

        .replace(/_DATASPACE_NAME_/g, dataSpaceName)

        .replace(/_ORG_NS_/g, namespace || '');



      // Replace the hardcoded '0001' sales org key in the CONFIGURATION_BY_SALESORG map

      if (hasSalesOrgKey) {

        // Belt-and-suspenders: salesOrg must be validated before splicing into JS source

        if (!/^[A-Za-z0-9]{4}$/.test(salesOrg)) {

          throw new Error(

            `Error: Invalid sales org. Expected a 4-character alphanumeric identifier.`

          );

        }

        content = content.replace(/'0001':/g, `'${salesOrg}':`);

      }



      fs.writeFileSync(filePath, content, 'utf8');

    }

  } catch (error) {

    if (error.code === 'EISDIR') {

      // Directory entry -- skip silently, expected when walking mixed trees

      return;

    }

    // Unexpected I/O failure (missing file, permission error, write error)

    throw new Error(`Failed to process UI template file ${filePath}: ${error.message}`, { cause: error });

  }

}



module.exports = deployUI;

