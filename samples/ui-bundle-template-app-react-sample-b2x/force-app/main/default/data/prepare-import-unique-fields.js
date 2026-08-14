#!/usr/bin/env node
/**
 * Property-management seed-data prep for "sf data import tree".
 *
 * Ships alongside this feature's seed data so it can be run repeatedly (e.g.
 * after the org already has data) without hitting duplicate rules, and so all
 * @-references resolve. org-setup.mjs invokes whatever prepare script lives in
 * the app's data dir — the generic template script carries no object-specific
 * logic.
 *
 * Usage:
 *   node prepare-import-unique-fields.js
 *   node prepare-import-unique-fields.js --data-dir /path/to/<sfdx-source>/data
 *
 * Operates on (each optional — missing files are skipped):
 *   Contact.json                         (Email unique domain+local, LastName, FirstName, Phone)
 *   Agent__c.json                        (License_Number__c — unique per record)
 *   Property_Management_Company__c.json  (Company_Code__c, max 10 chars)
 *   Property_Owner__c.json               (Email__c)
 *   Lease__c.json                        (Tenant__c → @TenantRef remapped into Tenant__c.json's refs)
 *   Maintenance_Request__c.json          (User__c → @TenantRef remapped likewise)
 */

const fs = require("fs");
const path = require("path");

function parseArgs() {
	const args = process.argv.slice(2);
	let dataDir = __dirname;
	for (let i = 0; i < args.length; i++) {
		if (args[i] === "--data-dir" && args[i + 1]) {
			dataDir = path.resolve(args[++i]);
			break;
		}
	}
	return dataDir;
}

const dataDir = parseArgs();
const runId = Date.now();
const runSuffix2 = String(runId % 100).padStart(2, "0"); // 00-99 for Company_Code__c (10-char limit)

// Contact: Email (unique domain + local), LastName, FirstName, Phone — avoid duplicate rules
const contactPath = path.join(dataDir, "Contact.json");
if (fs.existsSync(contactPath)) {
	let contact = JSON.parse(fs.readFileSync(contactPath, "utf8"));
	if (contact.records) {
		contact.records.forEach((r, i) => {
			if (r.Email && r.Email.includes("@")) {
				const parts = r.Email.replace(/\+[0-9]+@/, "@").split("@");
				const local = (parts[0] || "user") + "+" + runId;
				const domain = "run" + runId + ".example.com";
				r.Email = local + "@" + domain;
			}
			if (r.LastName) r.LastName = String(r.LastName).replace(/-[0-9]+$/, "") + "-" + runId;
			if (r.FirstName) r.FirstName = String(r.FirstName).replace(/-[0-9]+$/, "") + "-" + (i + 1);
			if (r.Phone) r.Phone = String(r.Phone).replace(/\d{2}$/, runSuffix2);
		});
		fs.writeFileSync(contactPath, JSON.stringify(contact, null, 2));
		console.log("Updated Contact.json (Email, LastName, FirstName, Phone)");
	}
}

// Agent__c: License_Number__c — unique per record (field is often unique in org)
const agentPath = path.join(dataDir, "Agent__c.json");
if (fs.existsSync(agentPath)) {
	let agent = JSON.parse(fs.readFileSync(agentPath, "utf8"));
	if (agent.records) {
		agent.records.forEach((r, i) => {
			if (r.License_Number__c) {
				const base = r.License_Number__c.replace(/-[0-9]+(-[0-9]+)?$/, "");
				r.License_Number__c = base + "-" + runId + "-" + (i + 1);
			}
		});
		fs.writeFileSync(agentPath, JSON.stringify(agent, null, 2));
		console.log("Updated Agent__c.json (License_Number__c)");
	}
}

// Property_Management_Company__c: Company_Code__c — max 10 chars, use 8-char base + 2-digit suffix
const companyPath = path.join(dataDir, "Property_Management_Company__c.json");
if (fs.existsSync(companyPath)) {
	let company = JSON.parse(fs.readFileSync(companyPath, "utf8"));
	if (company.records) {
		company.records.forEach((r) => {
			if (r.Company_Code__c) r.Company_Code__c = r.Company_Code__c.slice(0, 8) + runSuffix2;
		});
		fs.writeFileSync(companyPath, JSON.stringify(company, null, 2));
		console.log("Updated Property_Management_Company__c.json (Company_Code__c)");
	}
}

// Property_Owner__c: Email__c — add +runId before @
const ownerPath = path.join(dataDir, "Property_Owner__c.json");
if (fs.existsSync(ownerPath)) {
	let owner = JSON.parse(fs.readFileSync(ownerPath, "utf8"));
	if (owner.records) {
		owner.records.forEach((r) => {
			if (r.Email__c && r.Email__c.includes("@"))
				r.Email__c = r.Email__c.replace(/\+[0-9]+@/, "@").replace("@", "+" + runId + "@");
		});
		fs.writeFileSync(ownerPath, JSON.stringify(owner, null, 2));
		console.log("Updated Property_Owner__c.json (Email__c)");
	}
}

// Remap @TenantRefN in dependent files to only use refs that exist in Tenant__c.json.
// The valid ref count is derived from the data (no magic number), so refs stay in
// range and resolve even if Tenant__c.json's record count changes.
const tenantPath = path.join(dataDir, "Tenant__c.json");
if (fs.existsSync(tenantPath)) {
	const tenantData = JSON.parse(fs.readFileSync(tenantPath, "utf8"));
	const validTenantRefs = (tenantData.records || [])
		.map((r) => r.attributes?.referenceId)
		.filter(Boolean);
	if (validTenantRefs.length === 0) throw new Error("Tenant__c.json has no referenceIds");

	const remapTenantRef = (refValue) => {
		if (typeof refValue !== "string" || !refValue.startsWith("@TenantRef")) return refValue;
		const match = refValue.match(/^@(TenantRef)(\d+)$/);
		if (!match) return refValue;
		const n = parseInt(match[2], 10);
		const idx = (n - 1) % validTenantRefs.length;
		return "@" + validTenantRefs[idx];
	};

	const leasePath = path.join(dataDir, "Lease__c.json");
	if (fs.existsSync(leasePath)) {
		let lease = JSON.parse(fs.readFileSync(leasePath, "utf8"));
		if (lease.records) {
			lease.records.forEach((r) => {
				if (r.Tenant__c) r.Tenant__c = remapTenantRef(r.Tenant__c);
			});
			fs.writeFileSync(leasePath, JSON.stringify(lease, null, 2));
			console.log(
				"Updated Lease__c.json (Tenant__c @TenantRef remap, validTenants=%s)",
				validTenantRefs.length,
			);
		}
	}

	const maintPath = path.join(dataDir, "Maintenance_Request__c.json");
	if (fs.existsSync(maintPath)) {
		let maint = JSON.parse(fs.readFileSync(maintPath, "utf8"));
		if (maint.records) {
			maint.records.forEach((r) => {
				if (r.User__c && String(r.User__c).startsWith("@TenantRef"))
					r.User__c = remapTenantRef(r.User__c);
			});
			fs.writeFileSync(maintPath, JSON.stringify(maint, null, 2));
			console.log("Updated Maintenance_Request__c.json (User__c @TenantRef remap)");
		}
	}
}

console.log("Unique fields updated: runId=%s companySuffix=%s", runId, runSuffix2);
