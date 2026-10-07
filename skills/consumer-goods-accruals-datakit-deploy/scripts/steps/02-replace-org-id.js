const fs = require('fs');
const path = require('path');

function walkFiles(dir, extensions) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) results.push(...walkFiles(full, extensions));
    else if (extensions.some(ext => entry.name.endsWith(ext))) results.push(full);
  }
  return results;
}

/**
 * Step 2: Replace __SF_ORG_ID__ placeholder with actual org ID in all metadata files
 */
async function replaceOrgId(orgId, dataKitPath) {
  console.log('\n=== Step 2: Replacing org ID placeholders ===');
  console.log(`Target directory: ${dataKitPath}`);
  console.log(`Org ID: ${orgId} (truncated to 15 chars: ${orgId.slice(0, 15)})`);

  // Truncate org ID to 15 characters
  const truncatedOrgId = orgId.slice(0, 15);

  // Find all XML and JSON files
  const files = walkFiles(dataKitPath, ['.xml', '.json']);

  let replacementCount = 0;

  files.forEach(file => {
    try {
      const content = fs.readFileSync(file, 'utf8');
      if (content.includes('__SF_ORG_ID__')) {
        const newContent = content.replace(/__SF_ORG_ID__/g, truncatedOrgId);
        fs.writeFileSync(file, newContent, 'utf8');
        replacementCount++;
      }
    } catch (error) {
      console.error(`Warning: Failed to process file ${file}: ${error.message}`);
    }
  });

  console.log(`[OK] Replaced org ID placeholder in ${replacementCount} file(s)\n`);
}

module.exports = replaceOrgId;
