#!/usr/bin/env node
/**
 * Updates unique fields in data JSON files so "sf data import tree" can be run
 * repeatedly (e.g. after org already has data). Run before data import.
 *
 * Usage:
 *   node scripts/prepare-import-unique-fields.js
 *   node scripts/prepare-import-unique-fields.js --data-dir /path/to/<sfdx-source>/data
 *
 * Expects data dir to contain (optional) JSON files:
 *   Contact.json (Email with unique domain per run, LastName, FirstName, Phone — standard Contact)
 *   Agent__c.json (License_Number__c — unique per record)
 *   Property_Management_Company__c.json (Company_Code__c, max 10 chars)
 *   Property_Owner__c.json (Email__c)
 * Missing files are skipped. Customize this script for your app's objects/fields.
 */

const fs = require('fs');
const path = require('path');

function resolveSfdxSource() {
  const sfdxPath = path.resolve(__dirname, '..', 'sfdx-project.json');
  if (!fs.existsSync(sfdxPath)) {
    console.error('Error: sfdx-project.json not found at project root.');
    process.exit(1);
  }
  const sfdxProject = JSON.parse(fs.readFileSync(sfdxPath, 'utf8'));
  const pkgDir = sfdxProject?.packageDirectories?.[0]?.path;
  if (!pkgDir) {
    console.error('Error: No packageDirectories[].path found in sfdx-project.json.');
    process.exit(1);
  }
  return path.resolve(__dirname, '..', pkgDir, 'main', 'default');
}

const DEFAULT_DATA_DIR = path.resolve(resolveSfdxSource(), 'data');

function parseArgs() {
  const args = process.argv.slice(2);
  let dataDir = DEFAULT_DATA_DIR;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--data-dir' && args[i + 1]) {
      dataDir = path.resolve(args[++i]);
      break;
    }
  }
  return dataDir;
}

const dataDir = parseArgs();
const runId = Date.now();
const runSuffix2 = String(runId % 100).padStart(2, '0'); // 00-99 for Company_Code__c (10-char limit)

// Contact: Email (unique domain + local), LastName, FirstName, Phone — avoid duplicate rules
const contactPath = path.join(dataDir, 'Contact.json');
if (fs.existsSync(contactPath)) {
  let contact = JSON.parse(fs.readFileSync(contactPath, 'utf8'));
  if (contact.records) {
    contact.records.forEach((r, i) => {
      if (r.Email && r.Email.includes('@')) {
        const parts = r.Email.replace(/\+[0-9]+@/, '@').split('@');
        const local = (parts[0] || 'user') + '+' + runId;
        const domain = 'run' + runId + '.example.com';
        r.Email = local + '@' + domain;
      }
      if (r.LastName)
        r.LastName = String(r.LastName).replace(/-[0-9]+$/, '') + '-' + runId;
      if (r.FirstName)
        r.FirstName = String(r.FirstName).replace(/-[0-9]+$/, '') + '-' + (i + 1);
      if (r.Phone)
        r.Phone = String(r.Phone).replace(/\d{2}$/, runSuffix2);
    });
    fs.writeFileSync(contactPath, JSON.stringify(contact, null, 2));
    console.log('Updated Contact.json (Email, LastName, FirstName, Phone)');
  }
}

// Agent__c: License_Number__c — unique per record (field is often unique in org)
const agentPath = path.join(dataDir, 'Agent__c.json');
if (fs.existsSync(agentPath)) {
  let agent = JSON.parse(fs.readFileSync(agentPath, 'utf8'));
  if (agent.records) {
    agent.records.forEach((r, i) => {
      if (r.License_Number__c) {
        const base = r.License_Number__c.replace(/-[0-9]+(-[0-9]+)?$/, '');
        r.License_Number__c = base + '-' + runId + '-' + (i + 1);
      }
    });
    fs.writeFileSync(agentPath, JSON.stringify(agent, null, 2));
    console.log('Updated Agent__c.json (License_Number__c)');
  }
}

// Property_Management_Company__c: Company_Code__c — max 10 chars, use 8-char base + 2-digit suffix
const companyPath = path.join(dataDir, 'Property_Management_Company__c.json');
if (fs.existsSync(companyPath)) {
  let company = JSON.parse(fs.readFileSync(companyPath, 'utf8'));
  if (company.records) {
    company.records.forEach((r) => {
      if (r.Company_Code__c)
        r.Company_Code__c = r.Company_Code__c.slice(0, 8) + runSuffix2;
    });
    fs.writeFileSync(companyPath, JSON.stringify(company, null, 2));
    console.log('Updated Property_Management_Company__c.json (Company_Code__c)');
  }
}

// Property_Owner__c: Email__c — add +runId before @
const ownerPath = path.join(dataDir, 'Property_Owner__c.json');
if (fs.existsSync(ownerPath)) {
  let owner = JSON.parse(fs.readFileSync(ownerPath, 'utf8'));
  if (owner.records) {
    owner.records.forEach((r) => {
      if (r.Email__c && r.Email__c.includes('@'))
        r.Email__c = r.Email__c.replace(/\+[0-9]+@/, '@').replace('@', '+' + runId + '@');
    });
    fs.writeFileSync(ownerPath, JSON.stringify(owner, null, 2));
    console.log('Updated Property_Owner__c.json (Email__c)');
  }
}

console.log('Unique fields updated: runId=%s companySuffix=%s', runId, runSuffix2);
