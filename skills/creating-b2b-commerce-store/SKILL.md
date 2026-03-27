---
name: creating-b2b-commerce-store
description: "Interactive workflow to create Commerce B2B Stores and retrieve storefront metadata. Use when users want to: create B2B Commerce stores, build Commerce storefronts, set up B2B stores from Vibes, retrieve Commerce metadata, deploy Commerce experiences, work with DigitalExperienceBundle for Commerce."
Critical: "Agents must follow the interactive flow and NEVER create storefront metadata from scratch."
license: Apache-2.0
compatibility: "Requires Commerce licenses, Experience Cloud, Salesforce CLI"
metadata:
  version: "1.0"
  category: "commerce"
---

# Commerce B2B Storefront Creation

Interactive workflow to create a Commerce B2B Store in Salesforce and retrieve the auto-generated storefront metadata to your repository.

## Critical Concepts

Commerce B2B = Store (backend data) + Storefront (frontend metadata). **Store must be created first** in the org to auto-generate the Storefront. Never create storefront metadata manually.

> See [Store vs Storefront Reference](references/store-vs-storefront.md)

## When to Use This Skill

Trigger when users request:
- "Create a B2B Commerce store"
- "Build a Commerce storefront"
- "Set up Commerce B2B"
- "Create B2B Commerce"
- "Retrieve Commerce storefront metadata"
- "Deploy B2B storefront"

## Rules That Always Apply

1. **Always follow the interactive flow.** Do NOT skip steps. Each step requires user confirmation before proceeding.

2. **Never create storefront metadata manually.** The Commerce setup wizard generates hundreds of configuration values. Manual creation will fail.

3. **Always list sites before retrieval.** Store names get underscores and number suffixes (e.g., "My B2B Store" → "My_B2B_Store1"). Let the user select from the actual list.

4. **Always use `--json` flag.** Include `--json` on all Salesforce CLI commands for parseable output.

## Interactive Workflow: 7 Steps

### Step 1: Explain Commerce B2B Concept

**Agent explains:** Commerce has Store (data) + Storefront (metadata). Store must be created first.

> See: [Store vs Storefront Reference](references/store-vs-storefront.md)

---

### Step 2: Guide User to Create B2B Store

**Agent provides these steps:**

1. Navigate to **Setup → Commerce → Stores**
   - Or: **App Launcher → Commerce → Create Store**

2. Click **"Create Store"** or **"Setup New Store"**

3. Select **"Commerce Store"** as the store type

4. Follow the wizard:
   - **Store Name**: Choose descriptive name (e.g., "My B2B Store")
     - Important: Spaces become underscores in folder names
   - **Site URL**: Unique URL name for the site 

5. Complete wizard - it creates:
   - WebStore record
   - Default buyer group and entitlement policies
   - Associated Digital Experience (LWR site)

6. Optional: Configure payment gateway, tax provider, shipping

**Agent then asks:**
"Have you completed creating the B2B Store in your org? Reply 'yes' when ready and provide the store name you used."

---

### Step 3: Get User Confirmation

**Agent waits for:** User confirmation and store name

**Agent validates:** Store name format (no special characters, spaces will appear as underscores)

**Agent acknowledges:** "Great! Let me list the available storefronts in your org..."

---

### Step 4: List Available LWR Sites

**Agent executes:**
```bash
sf org list metadata --metadata-type DigitalExperienceConfig --json
```

**Agent should:**
- Parse JSON output to extract site names
- Display as numbered list
- Explain naming (underscores, number suffixes)

**Example output:**
```
Available Digital Experience sites:
1. My_B2B_Store1
2. Partner_Portal
3. Customer_Community
```

---

### Step 5: Let User Select Storefront

**Agent asks:**
"Which site corresponds to your B2B Store? Select the site name:"

**Agent validates:** Selection matches available sites

**Agent confirms:** "Got it! I'll retrieve metadata for [site-name]..."

---

### Step 6: Retrieve Storefront Metadata

**Agent executes:**
```bash
sf project retrieve start -m DigitalExperienceBundle:site/<selected-store-name> --json
```

**Agent should:**
- Show retrieval progress
- Confirm successful retrieval
- List retrieved directory structure

**Expected output:**
```
Retrieved: force-app/main/default/digitalExperiences/site/My_B2B_Store1/
├── My_B2B_Store1.digitalExperience-meta.xml
├── sfdc_cms__view/ (home, current_cart, detail_*, list_*, etc.)
├── sfdc_cms__site/
├── sfdc_cms__route/
└── [other sfdc_cms__* directories]
```

---

### Step 7: Provide Next Steps

**Agent provides:**

✅ **Metadata retrieved successfully!**

**Next steps:**
- Customize with custom LWCs or branding changes
- Deploy: `sf project deploy start --source-dir force-app/main/default/digitalExperiences/site/My_B2B_Store1/ --json`

**Resources:** [DigitalExperienceBundle Docs](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_digitalexperiencebundle.htm), [B2B Commerce Guide](https://developer.salesforce.com/docs/atlas.en-us.b2b_commerce_dev_guide.meta/b2b_commerce_dev_guide/)

---

## Reference

- **[store-vs-storefront.md](references/store-vs-storefront.md)** - Technical details on Store vs Storefront, source control, and why manual creation fails

---

## Remember

**Store first (creates storefront) → Retrieve → Customize**
