#!/usr/bin/env node
/**
 * Salesforce Metadata API - Section-Specific Loading Examples (JavaScript/Node.js)
 *
 * This file demonstrates how to programmatically load only specific sections
 * from metadata JSON files, avoiding the token waste of loading entire files.
 *
 * ⚠️ CRITICAL: Do NOT use built-in Read tools on these JSON files!
 * Use this programmatic approach instead.
 */

const fs = require('fs');
const path = require('path');


/**
 * Read and parse a metadata JSON file, with a clear error on malformed JSON.
 */
function loadMetadataJson(metadataFile) {
    const fileContent = fs.readFileSync(metadataFile, 'utf-8');
    try {
        return JSON.parse(fileContent);
    } catch (e) {
        throw new Error(`Failed to parse ${metadataFile}: ${e.message}`);
    }
}


/**
 * Example 1: Load ONLY the 'fields' section from CustomObject.json
 *
 * Token savings: ~70-80% compared to loading entire file
 */
function loadSingleSectionExample() {
    const metadataFile = path.join('data', 'metadata_api', 'CustomObject.json');

    // Read and parse the JSON file
    const data = loadMetadataJson(metadataFile);

    // Extract only the 'fields' section
    const fieldsOnly = data.fields || {};

    // Use only 'fields', ignore wsdl_segment and other sections
    console.log(`Loaded ${Object.keys(fieldsOnly).length} fields from CustomObject`);
    return fieldsOnly;
}


/**
 * Example 2: Load ONLY 'description' and 'fields' sections from Flow.json
 *
 * Token savings: ~60-75% compared to loading entire file
 */
function loadMultipleSectionsExample() {
    const metadataFile = path.join('data', 'metadata_api', 'Flow.json');

    const data = loadMetadataJson(metadataFile);

    // Extract only needed sections
    const description = data.description || '';
    const fields = data.fields || {};

    // Skip: wsdl_segment, declarative_metadata_sample_definition, etc.
    console.log(`Loaded description and ${Object.keys(fields).length} fields from Flow`);
    return { description, fields };
}


/**
 * Example 3: Check available sections first, then load specific ones
 *
 * Best practice: Always check what sections are available
 */
function loadWithSectionCheck() {
    const metadataFile = path.join('data', 'metadata_api', 'Profile.json');

    const data = loadMetadataJson(metadataFile);

    // Check available sections
    const availableSections = data.sections || [];
    console.log(`Available sections: ${availableSections.join(', ')}`);

    // Load only specific sections you need
    const result = {};
    if (availableSections.includes('fields')) {
        result.fields = data.fields || {};
    }
    if (availableSections.includes('description')) {
        result.description = data.description || '';
    }

    // Explicitly ignore verbose sections
    // - wsdl_segment (very large, rarely needed)
    // - file_information (not needed for field definitions)
    // - directory_location (not needed for field definitions)

    return result;
}


/**
 * Example 4: Async/Promise version (modern Node.js)
 */
async function loadSingleSectionAsync() {
    const metadataFile = path.join('data', 'metadata_api', 'ApexClass.json');

    // Use async file operations
    const fileContent = await fs.promises.readFile(metadataFile, 'utf-8');
    let data;
    try {
        data = JSON.parse(fileContent);
    } catch (e) {
        throw new Error(`Failed to parse ${metadataFile}: ${e.message}`);
    }

    // Extract only the sections you need
    const fields = data.fields || {};
    const description = data.description || '';

    return { fields, description };
}


/**
 * ❌ WRONG APPROACH - DO NOT USE
 *
 * This is what NOT to do - it loads the entire file into context:
 *
 * // Read tool approach (WRONG):
 * // Read data/metadata_api/CustomObject.json  // Loads ALL sections!
 *
 * // This injects the entire file (including massive WSDL segments)
 * // into your context, wasting 60-80% of tokens.
 */
function wrongApproachExample() {
    // Don't do this!
}


// Run examples
if (require.main === module) {
    console.log('Example 1: Single section');
    loadSingleSectionExample();

    console.log('\nExample 2: Multiple sections');
    loadMultipleSectionsExample();

    console.log('\nExample 3: Check sections first');
    loadWithSectionCheck();

    console.log('\nExample 4: Async version');
    loadSingleSectionAsync().then(() => {
        console.log('Async loading complete');
    });
}

module.exports = {
    loadSingleSectionExample,
    loadMultipleSectionsExample,
    loadWithSectionCheck,
    loadSingleSectionAsync
};
