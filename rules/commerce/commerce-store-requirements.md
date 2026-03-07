---
name: Commerce Store Creation Requirements
description: Critical workflow for creating B2B/B2C Commerce stores and storefronts - understand the distinction between Commerce Store (runtime data) and Storefront (LWR site).
tags: commerce, b2b, b2c, store, storefront, lwr, experience-cloud, rules, scom
---

## ⚠️ CRITICAL: Commerce Store vs Storefront Distinction

When creating a Commerce B2B or B2C solution, you must understand the distinction between two separate but related components:

### 1. Commerce Store (For Merchandisers)
**What it is:**
- Runtime data and configuration created in the Salesforce org
- NOT source-controllable metadata
- Created through the Commerce app UI or Commerce APIs

**What it includes:**
- Store configuration and settings
- Default buyer groups
- Entitlement policies
- Pricing policies
- Payment, tax, and shipping configurations
- Product catalog associations
- Price book mappings
- Inventory locations
- Search index configurations

**Where it lives:**
- Data records in standard Commerce objects (WebStore, BuyerGroup, EntitlementPolicy, etc.)
- Configured via Setup → Commerce → Stores

### 2. Storefront (For Buyers)
**What it is:**
- Digital Experience (LWR site) for buyer-facing shopping experience
- Source-controllable as ExperienceBundle metadata
- Created automatically when you create a Commerce Store, or manually via Experience Builder

**What it includes:**
- ExperienceBundle metadata (StorefrontName.digitalExperience-meta.xml, routes, views, navigation)
- Lightning Web Components (product list, product detail, cart, checkout)
- Branding and theme configuration
- Page layouts and content
- Custom LWCs for unique functionality

**Where it lives:**
- `force-app/main/default/digitalExperiences/site/StorefrontName/`
- Example: `force-app/main/default/digitalExperiences/site/My_B2B_Store1/`
- Retrievable and deployable via Salesforce CLI

---

## 🚫 Common Mistake: Creating Storefront Metadata from Scratch

**DO NOT** attempt to manually create Commerce storefront metadata files (StorefrontName.digitalExperience-meta.xml, StorefrontName.digitalExperience-meta.xml) from scratch in your repository.

**Why this fails:**
- Commerce storefronts have complex dependencies on the Commerce Store data
- Out-of-box Commerce components require specific configurations tied to WebStore records
- Commerce-managed components (search, PLP, PDP, cart, checkout) are generated and configured by the Commerce setup wizard
- Missing the Store-to-Storefront associations will result in non-functional pages

---

## ✅ Required Workflow for Creating Commerce B2B/B2C Sites

### Step 1: Create Commerce Store in the Org (MUST BE DONE FIRST)

1. **Access Commerce Setup:**
   - Navigate to Setup → Commerce → Stores
   - OR use the Commerce app from App Launcher → Create / Select App

2. **Create New Store (via UI):**
   - Click "Create Store" or "Setup New Store"
   - Choose store type:
     - **B2B Store** - For business buyers with account hierarchies, buyer groups, negotiated pricing
     - **B2C Store** - For individual consumers with guest checkout
   - Follow the store setup wizard

3. **Store Setup Wizard will create:**
   - WebStore record with unique name
   - Default buyer group (B2B: associated with Accounts; B2C: AllBuyers)
   - Default entitlement policies (who can see which products)
   - Default price book association
   - Default checkout flow configuration
   - **Associated Digital Experience (Storefront)** - This is auto-generated!

4. **Configure Store Settings:**
   - Payment gateway (Stripe, Adyen, etc.)
   - Tax provider (Avalara, Vertex, manual)
   - Shipping methods
   - Search settings
   - Guest checkout (B2C)
   - Account-based features (B2B)

5. **Verify Store Creation:**
   - Setup → All Sites → Find your new Experience Cloud site
   - The site name will match your store name (e.g., "My B2B Store" → "My_B2B_Store")
   - The Experience was created automatically during Store setup

### Step 2: Retrieve Digital Experience Metadata (Storefront)

After the Commerce Store is created in the org, retrieve the generated Experience metadata:

```bash
# List all Digital Experiences in your org
sf project retrieve start --metadata DigitalExperience

# Or retrieve specific Experience by name
sf project retrieve start --metadata DigitalExperience:My_B2B_Store

# Retrieve the complete ExperienceBundle
sf project retrieve start --metadata ExperienceBundle:My_B2B_Store
```

**What you'll get:**
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

**Example:** For a store named "My B2B Store", the folder structure would be:
```
force-app/main/default/digitalExperiences/site/My_B2B_Store1/
├── My_B2B_Store1.digitalExperience-meta.xml
└── [subdirectories as shown above]
```

### Step 3: Customize Storefront (Optional)

Once you have the retrieved metadata, you can:

1. **Add custom LWCs** following LDS-first patterns
2. **Modify page layouts** in Experience Builder
3. **Customize branding** (colors, fonts, logos)
4. **Add content pages** (About Us, FAQ, Terms)
5. **Configure navigation** and menus

**Important:**
- Test changes in Experience Builder before committing to source control
- Use `sf project retrieve start` after each change to sync metadata
- Deploy to other orgs using `sf project deploy start`

### Step 4: Version Control Workflow

```bash
# After creating store and retrieving metadata
git add force-app/main/default/digitalExperiences/
git commit -m "feat: add My B2B Store digital experience metadata"

# Deploy to scratch org or sandbox (replace My_B2B_Store1 with your storefront name)
sf project deploy start --source-dir force-app/main/default/digitalExperiences/site/My_B2B_Store1

# Note: Commerce Store data must be recreated in target org first!
```

---

## 🎯 Summary: The Correct Order

```
1. ✅ Create Commerce Store in org (Setup → Commerce)
   ↓
2. ✅ Store wizard creates WebStore + Digital Experience
   ↓
3. ✅ Retrieve Experience metadata to local repo
   ↓
4. ✅ Customize and extend (LWCs, pages, branding)
   ↓
5. ✅ Commit to source control
   ↓
6. ✅ Deploy to other orgs (after creating Store in target org)
```

---

## 🚨 What NOT to Do

❌ **Don't create storefront metadata from scratch**
- The Commerce setup wizard generates hundreds of configuration values
- Manual creation will miss critical Store-to-Experience associations

❌ **Don't try to deploy storefront without Store**
- Deploying Experience metadata to an org without the Commerce Store will fail
- Commerce components require WebStore records to exist

❌ **Don't version control Commerce Store data**
- WebStore records, BuyerGroups, EntitlementPolicies are runtime data
- Cannot be captured as deployable metadata (use data export/import instead)

❌ **Don't skip the Commerce setup wizard**
- Even if you think you can do it faster manually
- The wizard creates essential relationships and default configurations

---

## 📋 Pre-Deployment Checklist for Other Orgs

When deploying your storefront to a new org:

- [ ] Target org has Commerce licenses (B2B Commerce or B2C Commerce)
- [ ] Experience Cloud is enabled and domain configured
- [ ] Commerce Store has been created in target org (via Commerce app UI)
- [ ] WebStore name matches the Experience name in your metadata
- [ ] Buyer users and Commerce Admin permissions are assigned
- [ ] Product catalog, price books, and inventory exist in target org
- [ ] Payment, tax, shipping providers configured
- [ ] Only then deploy the Experience metadata:
      ```bash
      sf project deploy start --source-dir force-app/main/default/digitalExperiences/
      ```

---

## 🔗 Related Workflows

### For B2B Commerce:
- Create Buyer Accounts and Contacts
- Assign Accounts to Buyer Groups
- Configure negotiated pricing and entitlement policies
- Set up account hierarchies

### For B2C Commerce:
- Configure guest checkout settings
- Set up customer registration flows
- Configure AllBuyers entitlement policy

### For Both:
- Seed product catalog (Products, ProductCategory, ProductCatalog)
- Create price books and price book entries
- Configure inventory (ProductItem, LocationInventory)
- Set up search facets and filters

---

## 💡 Agent Guidance: What to Create vs What to Retrieve

**When user asks: "Create a B2B Commerce storefront"**

**Your response should be:**
1. ✅ Explain the Store vs Storefront distinction
2. ✅ Instruct them to create the Commerce Store in their org first
3. ✅ Provide the Salesforce CLI retrieve commands
4. ✅ Optionally: Create custom LWCs for extending the retrieved storefront
5. ❌ DO NOT create StorefrontName.digitalExperience-meta.xml or StorefrontName.digitalExperience-meta.xml from scratch

**Acceptable to create from scratch:**
- Custom LWCs for storefront extensions (hero banners, promotions, custom product cards)
- Content pages that don't use Commerce components
- Utility components (navigation helpers, breadcrumbs)

**Must be retrieved from org:**
- Core storefront Experience metadata
- Commerce-managed pages (PLP, PDP, Cart, Checkout)
- Store configuration and routing

---

## 📚 Additional Resources

**Commerce Store Setup:**
- Setup → Commerce → Stores
- Commerce app from App Launcher → Create / Select App
- Help Article: "Set Up a B2B Commerce Store"
- Help Article: "Set Up a B2C Commerce Store"

**Storefront Customization:**
- Experience Builder → Open your store site
- Help Article: "Customize Your Commerce Storefront"
- Developer Guide: "Build Custom Commerce Components"

**Metadata Retrieval:**
```bash
# List all retrievable metadata types
sf org list metadata --metadata-type DigitalExperience
sf org list metadata --metadata-type ExperienceBundle

# Retrieve specific experience
sf project retrieve start --metadata ExperienceBundle:YourStoreName
```

---

## 🎓 Key Takeaway

**Commerce is a TWO-STEP process:**
1. **Create Store** (in org, runtime data) → Generates default storefront
2. **Retrieve & Customize Storefront** (source control, metadata) → Extend with custom features

**Never skip step 1. Never manually create what step 1 generates.**
