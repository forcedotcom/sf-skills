#!/usr/bin/env node
/**
 * Updates unique fields in data JSON files so "sf data import tree" can be run
 * repeatedly (e.g. after org already has data). Run before: node prepare-import-unique-fields.js
 */
const fs = require("fs");
const path = require("path");
const dataDir = __dirname;
const runId = Date.now();
const runSuffix2 = String(runId % 100).padStart(2, "0"); // 00-99 for Company_Code__c (10-char limit)

// Contact: Email + LastName — unique so re-runs don't hit DUPLICATES_DETECTED (matching may use name)
const contactPath = path.join(dataDir, "Contact.json");
let contact = JSON.parse(fs.readFileSync(contactPath, "utf8"));
contact.records.forEach((r, i) => {
	if (r.Email && r.Email.includes("@"))
		r.Email = r.Email.replace(/\+[0-9]+@/, "@").replace("@", "+" + runId + "@");
	if (r.LastName)
		r.LastName = r.LastName.replace(/\s*\[[0-9-]+\]$/, "") + " [" + runId + "-" + i + "]";
});
fs.writeFileSync(contactPath, JSON.stringify(contact, null, 2));

// Agent__c: License_Number__c — strip any existing suffix and add run id + index (each record must be unique)
const agentPath = path.join(dataDir, "Agent__c.json");
let agent = JSON.parse(fs.readFileSync(agentPath, "utf8"));
agent.records.forEach((r, i) => {
	if (r.License_Number__c)
		r.License_Number__c =
			r.License_Number__c.replace(/-[0-9]+(-[0-9]+)?$/, "") + "-" + runId + "-" + i;
});
fs.writeFileSync(agentPath, JSON.stringify(agent, null, 2));

// Property_Management_Company__c: Company_Code__c — max 10 chars, use 8-char base + 2-digit suffix
const companyPath = path.join(dataDir, "Property_Management_Company__c.json");
let company = JSON.parse(fs.readFileSync(companyPath, "utf8"));
company.records.forEach((r) => {
	if (r.Company_Code__c) r.Company_Code__c = r.Company_Code__c.slice(0, 8) + runSuffix2; // 8-char base + 2-digit = 10 chars max
});
fs.writeFileSync(companyPath, JSON.stringify(company, null, 2));

// Property_Owner__c: Email__c — add +runId before @
const ownerPath = path.join(dataDir, "Property_Owner__c.json");
let owner = JSON.parse(fs.readFileSync(ownerPath, "utf8"));
owner.records.forEach((r) => {
	if (r.Email__c && r.Email__c.includes("@"))
		r.Email__c = r.Email__c.replace(/\+[0-9]+@/, "@").replace("@", "+" + runId + "@");
});
fs.writeFileSync(ownerPath, JSON.stringify(owner, null, 2));

// Remap @TenantRefN in dependent files to only use refs that exist in Tenant__c.json (fix UnresolvableRefsError)
const tenantPath = path.join(dataDir, "Tenant__c.json");
const tenantData = JSON.parse(fs.readFileSync(tenantPath, "utf8"));
const validTenantRefs = tenantData.records.map((r) => r.attributes?.referenceId).filter(Boolean);
if (validTenantRefs.length === 0) throw new Error("Tenant__c.json has no referenceIds");

function remapTenantRef(refValue) {
	if (typeof refValue !== "string" || !refValue.startsWith("@TenantRef")) return refValue;
	const match = refValue.match(/^@(TenantRef)(\d+)$/);
	if (!match) return refValue;
	const n = parseInt(match[2], 10);
	const idx = (n - 1) % validTenantRefs.length;
	return "@" + validTenantRefs[idx];
}

const leasePath = path.join(dataDir, "Lease__c.json");
let lease = JSON.parse(fs.readFileSync(leasePath, "utf8"));
lease.records.forEach((r) => {
	if (r.Tenant__c) r.Tenant__c = remapTenantRef(r.Tenant__c);
});
fs.writeFileSync(leasePath, JSON.stringify(lease, null, 2));

const maintPath = path.join(dataDir, "Maintenance_Request__c.json");
let maint = JSON.parse(fs.readFileSync(maintPath, "utf8"));
maint.records.forEach((r) => {
	if (r.User__c && String(r.User__c).startsWith("@TenantRef"))
		r.User__c = remapTenantRef(r.User__c);
});
fs.writeFileSync(maintPath, JSON.stringify(maint, null, 2));

console.log(
	"Unique fields updated: runId=%s companySuffix=%s validTenants=%s",
	runId,
	runSuffix2,
	validTenantRefs.length,
);
