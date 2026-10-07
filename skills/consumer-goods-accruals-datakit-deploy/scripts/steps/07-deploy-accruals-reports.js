const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { exec, execDeployJson, getSfBin } = require('./utils');

const OBJECT_SOURCE_TARGET_MAPS_DIR = 'objectSourceTargetMaps';

/**
 * Step 7: Deploy Accruals Reports with Data Space replacements.
 *
 * The Accruals Reports payload contains references between objects (DLOs/DLMs)
 * and ObjectSourceTargetMap definitions. The maps reference fields that only
 * exist after the other folders (objects, wave, ...) are deployed, so we must
 * deploy them in two passes: first everything except objectSourceTargetMaps,
 * then objectSourceTargetMaps on its own.
 *
 * @param {string} orgAlias - The Salesforce org alias
 * @param {string} setupDir - The setup directory path
 * @param {boolean} skipDataSpace - Whether to skip data space configuration
 * @param {string} configuredDataSpaceName - The data space name from config
 * @param {string} configuredDataSpacePrefix - The data space prefix from config
 * @param {string} namespace - Org namespace prefix (e.g. "cgcloud_dev__"), or '' for unmanaged orgs
 * @param {boolean} dryRun - If true, skip deployment but keep temp files
 */
async function deployAccrualsReports(
  orgAlias,
  setupDir,
  skipDataSpace,
  configuredDataSpaceName,
  configuredDataSpacePrefix,
  namespace = '',
  dryRun = false
) {
  console.log('\n=== Step 7: Deploying Accruals Reports ===');

  // Use "default" and empty prefix if skipping data space, otherwise use configured values
  const dataSpaceName = skipDataSpace ? 'default' : configuredDataSpaceName;
  const dataSpacePrefix = skipDataSpace ? '' : configuredDataSpacePrefix;

  console.log(`Data Space Name: ${dataSpaceName}`);
  console.log(`Data Space Prefix: ${dataSpacePrefix || '(empty)'}`);
  console.log(`Org Namespace: ${namespace || '(none)'}`);

  const sourceDir = path.join(setupDir, 'CGCloudAddons', 'TPM', 'Accruals', 'Accruals Reports');
  const tempDir = path.join(setupDir, 'temp-accruals-reports');

  if (fs.existsSync(tempDir)) {
    console.log('Cleaning up existing temp directory...');
    fs.rmSync(tempDir, { recursive: true });
  }

  console.log('Copying Accruals Reports to temp directory...');
  copyDirectory(sourceDir, tempDir);

  console.log('Replacing Data Space placeholders and namespace in file names and contents...');
  replaceDataSpacePlaceholders(tempDir, dataSpaceName, dataSpacePrefix, namespace);

  const deployPath = path.join(tempDir, 'force-app');
  const defaultDir = path.join(deployPath, 'main', 'default');
  const objectSourceTargetMapsPath = path.join(defaultDir, OBJECT_SOURCE_TARGET_MAPS_DIR);
  const hasMaps = fs.existsSync(objectSourceTargetMapsPath);

  if (dryRun) {
    console.log('[DRY RUN] Skipping deployment - files prepared at:');
    console.log(`  ${tempDir}`);
    if (hasMaps) {
      console.log(`[DRY RUN] objectSourceTargetMaps would deploy in a second pass from:`);
      console.log(`  ${objectSourceTargetMapsPath}`);
    }
    console.log('[DRY RUN] Temp directory preserved for inspection');
    console.log('[OK] Step 7 completed (dry run)\n');
    return;
  }

  // Pass 1: Deploy everything except objectSourceTargetMaps. The maps depend on
  // fields that only exist once the DLM objects are in place, so we briefly
  // move the maps folder out of the deploy tree, deploy the rest, then deploy
  // the maps on their own.
  let stagedMapsPath = null;
  if (hasMaps) {
    stagedMapsPath = path.join(tempDir, '__staged-objectSourceTargetMaps');
    if (fs.existsSync(stagedMapsPath)) {
      fs.rmSync(stagedMapsPath, { recursive: true });
    }
    console.log('Setting aside objectSourceTargetMaps for the second deployment pass...');
    fs.renameSync(objectSourceTargetMapsPath, stagedMapsPath);
  }

  try {
    console.log('Deploying Accruals Reports metadata (pass 1: objects, wave, ...)...');
    execDeployJson(['project', 'deploy', 'start', '--source-dir', 'force-app', '--target-org', orgAlias], { cwd: tempDir });

    if (stagedMapsPath) {
      console.log('Restoring objectSourceTargetMaps for the second deployment pass...');
      fs.renameSync(stagedMapsPath, objectSourceTargetMapsPath);
      stagedMapsPath = null;

      console.log('Deploying Accruals Reports metadata (pass 2: objectSourceTargetMaps)...');
      execDeployJson(['project', 'deploy', 'start', '--source-dir', path.relative(tempDir, objectSourceTargetMapsPath).replace(/\\/g, '/'), '--target-org', orgAlias], { cwd: tempDir });
    }
  } finally {
    // If pass 1 failed before we restored the staged maps, put them back so
    // dry-run inspection still shows the full tree.
    if (stagedMapsPath && fs.existsSync(stagedMapsPath) && !fs.existsSync(objectSourceTargetMapsPath)) {
      fs.renameSync(stagedMapsPath, objectSourceTargetMapsPath);
    }
  }

  console.log('Cleaning up temp directory...');
  fs.rmSync(tempDir, { recursive: true });

  console.log('[OK] Accruals Reports deployed successfully\n');
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
function replaceNamePlaceholders(name, dataSpaceName, dataSpacePrefix, namespace) {
  let newName = name;
  if (dataSpacePrefix === '') {
    newName = newName.replace(/_DATASPACE_PREFIX__/g, '');
  } else {
    newName = newName.replace(/_DATASPACE_PREFIX__/g, dataSpacePrefix);
  }
  newName = newName
    .replace(/_DATASPACE_PREFIX_/g, dataSpacePrefix)
    .replace(/_DATASPACE_NAME_/g, dataSpaceName)
    .replace(/_ORG_NS_/g, namespace || '');
  return newName;
}

/**
 * Replace Data Space placeholders in both file names and file contents
 */
function replaceDataSpacePlaceholders(dir, dataSpaceName, dataSpacePrefix, namespace) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const oldPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      replaceDataSpacePlaceholders(oldPath, dataSpaceName, dataSpacePrefix, namespace);

      if (entry.name.includes('_DATASPACE_PREFIX_') || entry.name.includes('_DATASPACE_NAME_') || entry.name.includes('_ORG_NS_')) {
        const newName = replaceNamePlaceholders(entry.name, dataSpaceName, dataSpacePrefix, namespace);
        const newPath = path.join(dir, newName);
        fs.renameSync(oldPath, newPath);
      }
    } else {
      replaceInFile(oldPath, dataSpaceName, dataSpacePrefix, namespace);

      if (entry.name.includes('_DATASPACE_PREFIX_') || entry.name.includes('_DATASPACE_NAME_') || entry.name.includes('_ORG_NS_')) {
        const newName = replaceNamePlaceholders(entry.name, dataSpaceName, dataSpacePrefix, namespace);
        const newPath = path.join(dir, newName);
        fs.renameSync(oldPath, newPath);
      }
    }
  }
}

/**
 * Replace placeholders in file contents
 */
function replaceInFile(filePath, dataSpaceName, dataSpacePrefix, namespace) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');

    if (content.includes('_DATASPACE_PREFIX_') || content.includes('_DATASPACE_NAME_') || content.includes('_ORG_NS_')) {
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

      fs.writeFileSync(filePath, content, 'utf8');
    }
  } catch (error) {
    if (error.code === 'EISDIR') {
      // Directory entry — skip silently, expected when walking mixed trees
      return;
    }
    // Unexpected I/O failure (missing file, permission error, write error)
    throw new Error(`Failed to process template file ${filePath}: ${error.message}`, { cause: error });
  }
}

module.exports = deployAccrualsReports;
