# Commerce Prompts

Prompts for building and managing Salesforce B2B Commerce and B2C Commerce storefronts.

## Overview

Commerce on Core enables you to build digital storefronts using Experience Cloud (LWR sites) integrated with Commerce capabilities for product catalogs, pricing, shopping cart, checkout, and order management.

### Two-Part Architecture

Commerce consists of two distinct but connected parts:

1. **Commerce Store** (Backend - Runtime Data)
   - WebStore configuration
   - Buyer groups and entitlements
   - Pricing policies
   - Payment, tax, shipping setup
   - Product catalog associations
   - **Created in org via Setup → Commerce app**
   - **NOT source-controllable**

2. **Storefront** (Frontend - Metadata)
   - Digital Experience (LWR site)
   - Page layouts and components
   - Custom LWCs
   - Branding and theme
   - **Source-controllable as ExperienceBundle**
   - **Deployable via Salesforce CLI**

## Usage Pattern

**Critical:** Always create Commerce Store in org FIRST, then retrieve the auto-generated storefront metadata.

### Correct Workflow

```bash
# 1. Create Commerce Store in org (via UI)
#    Setup → Commerce → Store Administration → Create Store

# 2. Retrieve the auto-generated storefront metadata
sf project retrieve start --metadata ExperienceBundle:My_Store_Name

# 3. Customize with additional LWCs or pages
#    Add custom components, modify layouts in Experience Builder

# 4. Version control and deploy
git add force-app/main/default/experiences/
git commit -m "feat: add My Store storefront"
```

### ❌ Incorrect Approach

Don't manually create StorefrontName.digitalExperience-meta.xml or StorefrontName.digitalExperience-meta.xml from scratch. The Commerce setup wizard generates complex configurations that are difficult to replicate manually.

## Available Prompts

### Retrieve Commerce Storefront Metadata
**Use when:** You've created a Commerce Store in your org and want to download the storefront to version control

**Prerequisites:**
- Commerce Store created via Commerce app
- Experience Cloud site exists and is associated with store
- Default org authorized with Salesforce CLI

**What it does:**
- Guides you through retrieving ExperienceBundle metadata
- Explains what files you'll get
- Provides customization next steps
- Includes deployment instructions for other orgs

## Related Rules

Before using these prompts, review:

**`rules/commerce/commerce-store-requirements.md`**
- Explains Store vs Storefront distinction
- Details the required creation workflow
- Lists what is/isn't source-controllable
- Provides deployment checklist

## Common Scenarios

### Scenario 1: New B2B Store
```
1. Follow commerce-store-requirements.md rule
2. Create Store in org via Commerce app
3. Use "Retrieve Commerce Storefront Metadata" prompt
4. Customize with custom LWCs (hero banner, promotions)
5. Commit and deploy to other environments
```

### Scenario 2: Extend Existing Storefront
```
1. Retrieve current metadata if not already in repo
2. Create custom LWCs following LDS-first patterns
3. Add to pages in Experience Builder
4. Retrieve updated metadata
5. Commit changes
```

### Scenario 3: Multi-Org Deployment
```
1. In target org, create Commerce Store (same name as source)
2. Deploy storefront metadata from repo
3. Verify Commerce components render correctly
4. Configure org-specific settings (payment, tax, shipping)
```

## Best Practices

### ✅ Do:
- Create Commerce Store in org first (always!)
- Retrieve auto-generated storefront metadata
- Version control Experience metadata
- Use LDS-first approach for custom LWCs
- Document store configuration steps
- Test in Experience Builder before deploying

### ❌ Don't:
- Create StorefrontName.digitalExperience-meta.xml from scratch
- Deploy storefront without creating Store in target org
- Try to version control WebStore records (use data APIs)
- Skip the Commerce setup wizard
- Forget to associate Experience with WebStore

## File Structure

After retrieving a Commerce storefront:

```
force-app/main/default/
├── experiences/
│   └── My_B2B_Store/
│       ├── StorefrontName.digitalExperience-meta.xml                  # Site config
│       ├── StorefrontName.digitalExperience-meta.xml      # Bundle metadata
│       ├── config/                    # Store settings
│       ├── views/                     # Page definitions
│       │   ├── home.json
│       │   ├── category.json          # PLP
│       │   ├── product.json           # PDP
│       │   ├── cart.json
│       │   └── checkout.json
│       └── routes/                    # URL routing
└── lwc/
    ├── b2bHeroBanner/                 # Custom components
    ├── b2bPromotionCard/
    └── b2bNavHelper/
```

## Tags

Commerce prompts use these tags:
- `commerce` - General Commerce functionality
- `b2b` - B2B Commerce specific
- `b2c` - B2C Commerce specific
- `storefront` - Buyer-facing storefront
- `store` - Backend store configuration
- `lwr` - Lightning Web Runtime sites
- `experience-cloud` - Experience Cloud/Digital Experiences
- `retrieve` - Metadata retrieval operations
- `metadata` - Source-controllable assets

## Additional Resources

**Salesforce Documentation:**
- [B2B Commerce Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.b2b_commerce_dev_guide.meta/b2b_commerce_dev_guide/)
- [B2C Commerce on Core Guide](https://help.salesforce.com/s/articleView?id=sf.comm_digital_overview.htm)
- [Experience Cloud LWR Sites](https://developer.salesforce.com/docs/platform/lwr-sites/guide/overview.html)

**Trailhead:**
- [B2B Commerce Basics](https://trailhead.salesforce.com/content/learn/modules/b2b-commerce-basics)
- [Build a B2B Commerce Store](https://trailhead.salesforce.com/content/learn/projects/build-a-b2b-commerce-store)

**CLI Commands:**
```bash
# List Commerce metadata
sf org list metadata --metadata-type DigitalExperience
sf org list metadata --metadata-type ExperienceBundle

# Retrieve storefront
sf project retrieve start --metadata ExperienceBundle:StoreName

# Deploy storefront
sf project deploy start --source-dir force-app/main/default/experiences/
```
