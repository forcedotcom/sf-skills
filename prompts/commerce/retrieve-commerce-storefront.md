---
name: Retrieve Commerce Storefront Metadata
description: Download and version-control an existing B2B/B2C Commerce LWR storefront from your org after creating the Commerce Store
tags: commerce, b2b, b2c, storefront, lwr, retrieve, metadata, scom
category: commerce
requires_setup: true
setup_summary: Commerce Store must be created in the org first via Setup → Commerce → Stores
---

## Context

You have created a Commerce Store (B2B or B2C) in your Salesforce org using the Commerce app, and now you want to:
1. Download the auto-generated Experience Cloud storefront metadata
2. Version-control it in your repository
3. Customize it with additional LWCs or pages

**Important:** This prompt assumes you have ALREADY created the Commerce Store in your org. If you haven't done that yet, refer to the "Commerce Store Creation Requirements" rule first.

## Setup

### 1. Verify Commerce Store Exists in Org

Before proceeding, confirm your Commerce Store is set up:

```bash
# Check your connected org
sf org display --verbose

# Verify the store exists
# Go to Setup → Commerce → Stores
# You should see your store listed with status "Active"
```

**Required information:**
- Store name (e.g., "My B2B Store")
- Associated Experience Cloud site name (usually matches store name with underscores)
- Store is active and has default configurations

### 2. Find Your Experience Site Name

The Commerce setup wizard automatically creates an Experience Cloud site. To find it:

1. **In Setup:**
   - Go to Setup → Digital Experiences → All Sites
   - Look for the site with same name as your store (e.g., "My B2B Store")
   - Note the exact folder name used in metadata (e.g., "My_B2B_Store1")

2. **Or use CLI:**
   ```bash
   sf org list metadata --metadata-type DigitalExperience
   ```

## Instructions

### Step 1: List Available Digital Experiences

First, see what's available in your org:

```bash
# List all Digital Experiences
sf org list metadata --metadata-type DigitalExperience

# List all Experience Bundles (more detailed)
sf org list metadata --metadata-type ExperienceBundle
```

**Example output:**
```
DigitalExperience/My_B2B_Store
DigitalExperience/Partner_Community
```

### Step 2: Retrieve the Experience Bundle

Retrieve the complete storefront metadata for your Commerce store:

```bash
# Replace "My_B2B_Store" with your actual store name
sf project retrieve start --metadata ExperienceBundle:My_B2B_Store

# Alternative: Retrieve all experiences (if you're unsure of the name)
sf project retrieve start --metadata ExperienceBundle
```

**What this retrieves:**
```
force-app/main/default/digitalExperiences/site/StorefrontName/
├── StorefrontName.digitalExperience-meta.xml  # Digital Experience Bundle metadata
├── sfdc_cms__appPage/                 # App page configuration
├── sfdc_cms__brandingSet/             # Branding assets
├── sfdc_cms__label/                   # Labels and translations
├── sfdc_cms__languageSettings/        # Language configuration
├── sfdc_cms__lwc/                     # Lightning Web Components (custom)
├── sfdc_cms__mobilePublisherConfig/   # Mobile configuration
├── sfdc_cms__route/                   # URL routing configuration
├── sfdc_cms__site/                    # Site settings
├── sfdc_cms__styles/                  # CSS styles
├── sfdc_cms__theme/                   # Theme configuration
├── sfdc_cms__themeLayout/             # Theme layouts
└── sfdc_cms__view/                    # Page definitions (views)
    ├── home/                          # Homepage
    ├── current_cart/                  # Shopping cart page
    ├── current_checkout/              # Checkout page
    ├── detail_*/                      # Product Detail Pages (PDP)
    ├── list_*/                        # Product List Pages (PLP)
    ├── order/                         # Order confirmation
    ├── global_search/                 # Search results
    └── [other pages...]
```

**Example:** For a store named "My B2B Store", the folder would be:
```
force-app/main/default/digitalExperiences/site/My_B2B_Store1/
├── My_B2B_Store1.digitalExperience-meta.xml
└── [subdirectories as shown above]
```

### Step 3: Verify Retrieved Files

Check that the metadata was retrieved successfully:

```bash
# List the experience files
ls -la force-app/main/default/digitalExperiences/My_B2B_Store1/

# Check the digitalExperience metadata file
cat force-app/main/default/digitalExperiences/site/My_B2B_Store1/My_B2B_Store1.digitalExperience-meta.xml
```

**Expected content in digitalExperience-meta.xml:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<DigitalExperienceBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My B2B Store</label>
    <modules>...</modules>
</DigitalExperienceBundle>
```

### Step 4: Inspect Commerce Pages

Review the out-of-box Commerce pages:

```bash
# List all views (pages)
ls force-app/main/default/digitalExperiences/site/My_B2B_Store1/sfdc_cms__view/

# View a product detail page directory
ls force-app/main/default/digitalExperiences/site/My_B2B_Store1/sfdc_cms__view/detail_*/
```

**Key Commerce pages you'll find in sfdc_cms__view/:**
- **home/** - Homepage with hero banner, featured products
- **list_*/** - Product List Pages (PLP) with filters, facets
- **detail_*/** - Product Detail Pages (PDP) with images, add-to-cart
- **current_cart/** - Shopping cart with quantity updates, remove items
- **current_checkout/** - Multi-step checkout flow (shipping, payment, review)
- **global_search/** - Search results page
- **addresses/** - Buyer address management (B2B)
- **order/** - Order confirmation and history

### Step 5: Commit to Version Control

Add the retrieved metadata to your repository:

```bash
# Add the experience files
git add force-app/main/default/digitalExperiences/My_B2B_Store1/

# Commit with descriptive message
git commit -m "feat: add My B2B Store commerce storefront metadata

Retrieved from org after creating Commerce Store via Setup.
Includes home, category, product, cart, checkout pages with
out-of-box Commerce components."

# Push to remote
git push origin main
```

## Testing & Verification

### 1. Test Retrieval in a Scratch Org

**Important:** You cannot deploy Commerce storefront metadata to a scratch org without first creating the Commerce Store in that org.

To test in another org:

```bash
# 1. Create scratch org with Commerce features
sf org create scratch --definition-file config/project-scratch-def.json --alias commerce-scratch

# 2. In the scratch org Setup, create a Commerce Store with the SAME NAME as your source org
#    (Setup → Commerce → Stores → Create Store)
#    Use the same store name: "My B2B Store"

# 3. THEN deploy the experience metadata
sf project deploy start --source-dir force-app/main/default/digitalExperiences/My_B2B_Store1/ --target-org commerce-scratch

# 4. Open Experience Builder to verify
sf org open --target-org commerce-scratch --path /lightning/setup/SetupNetworks/home
```

### 2. Verify Components in Experience Builder

1. Open your org in Setup
2. Go to Digital Experiences → All Sites
3. Click "Builder" next to your store site
4. Verify all pages load correctly:
   - Home page with hero banner
   - Category page with product grid
   - Product page with add-to-cart
   - Cart with line items
   - Checkout flow

## Customization Next Steps

Now that you have the storefront metadata, you can customize it:

### 1. Add Custom LWCs

```bash
# Create a custom promotion banner component
sf lightning generate component --type lwc \
  --name b2bPromotionBanner \
  --output-dir force-app/main/default/lwc

# Make it available to Experience Builder
# Edit b2bPromotionBanner.js-meta.xml:
#   <isExposed>true</isExposed>
#   <targets>
#     <target>lightningCommunity__Page</target>
#   </targets>
```

**Follow these rules for Commerce LWCs:**
- Use LDS-first approach (no Apex unless necessary)
- Expose `@api` properties for Experience Builder configuration
- Use `lightning-` base components (SLDS)
- Use `NavigationMixin` for routing
- Follow naming: `b2b[ComponentName]` or `b2c[ComponentName]`

### 2. Modify Page Layouts

1. Open Experience Builder in your org
2. Edit the page layout (e.g., add your custom component to Home)
3. Save and publish
4. Retrieve the updated metadata:
   ```bash
   sf project retrieve start --metadata ExperienceBundle:My_B2B_Store
   ```
5. Commit the changes:
   ```bash
   git add force-app/main/default/digitalExperiences/
   git commit -m "feat: add custom promotion banner to home page"
   ```

### 3. Add Content Pages

Create additional non-commerce pages (About Us, FAQ, Contact):

1. In Experience Builder → Pages → New Page
2. Add content (text, images, forms)
3. Retrieve updated metadata
4. Commit changes

## Important Notes

### ⚠️ Commerce Store Data vs Storefront Metadata

**What IS source-controllable (Storefront):**
- ✅ ExperienceBundle metadata (this prompt)
- ✅ Custom LWCs
- ✅ Page layouts and content
- ✅ Navigation structure

**What is NOT source-controllable (Commerce Store):**
- ❌ WebStore records (store settings, buyer groups)
- ❌ Product catalog data
- ❌ Price books and pricing rules
- ❌ Entitlement policies
- ❌ Inventory data
- ❌ Payment/tax/shipping configurations

**To migrate Commerce Store data between orgs:**
- Use Data Loader or Salesforce Data APIs
- Or recreate via Commerce app UI
- Or use Commerce APIs for programmatic setup

### 🔄 Sync Workflow

After making changes in Experience Builder:

```bash
# Always retrieve after UI changes
sf project retrieve start --metadata ExperienceBundle:My_B2B_Store

# Check what changed
git diff

# Commit meaningful changes
git add force-app/main/default/digitalExperiences/
git commit -m "chore: update homepage hero banner CTA"
```

## Troubleshooting

### Issue: "No ExperienceBundle found"

**Cause:** Store name mismatch or store not yet created

**Fix:**
1. Verify store exists: Setup → Commerce → Stores
2. Verify Experience site exists: Setup → Digital Experiences → All Sites
3. Check exact name (case-sensitive, underscores for spaces)
4. Try: `sf org list metadata --metadata-type ExperienceBundle`

### Issue: "Deployment failed - Store not found"

**Cause:** Target org doesn't have a Commerce Store with matching name

**Fix:**
1. In target org, create Commerce Store with SAME NAME as source
2. Then deploy Experience metadata

### Issue: "Commerce components not rendering"

**Cause:** Store configuration missing or incorrect WebStore association

**Fix:**
1. Verify WebStore is active in target org
2. Check Experience is associated with correct WebStore
3. Verify buyer user has correct entitlements and permissions

## Follow-ups

After retrieving your storefront:

- [ ] Document your store name and configuration in README.md
- [ ] Create deployment scripts for other environments
- [ ] Set up CI/CD pipeline for storefront changes
- [ ] Create a catalog of custom LWCs for reusability
- [ ] Document Commerce Store setup steps for new environments
- [ ] Test complete buy flow (browse → PDP → cart → checkout)

## Additional Resources

**Salesforce CLI:**
- `sf project retrieve start --help`
- `sf org list metadata --help`

**Commerce Documentation:**
- [B2B Commerce Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.chatterapi.meta/chatterapi/connect_resources_commerce_webstore.htm)
- [Commerce Customization Guide](https://help.salesforce.com/s/articleView?id=sf.comm_digital_customize.htm)

**Experience Cloud:**
- [LWR Sites Developer Guide](https://developer.salesforce.com/docs/platform/lwr-sites/guide/overview.html)
