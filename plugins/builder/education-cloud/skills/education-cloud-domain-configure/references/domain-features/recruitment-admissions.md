# 2. Recruitment & Admissions

**Purpose**: Manage student recruitment, application processing, and admission decisions.

**Prerequisites**:
- All Foundation prerequisites (Section 0)
- Experience Cloud license — for applicant portal
- Salesforce Scheduler — for campus tour and appointment booking
- OmniStudio — for Application Stages (FlexCards + OmniScripts)
- Marketing Cloud Engagement for Education (optional) — for prospect nurture campaigns

**Core features**:
- Applicant tracking (Person Accounts)
- Application forms and portals
- Admission processes and workflows
- Communication templates
- Digital engagement channels

### Enablement & Toggles

> **No domain master toggle.** This domain has no single on/off switch. It is configured through two independent sub-feature settings under Setup → Set Up Education Cloud → Recruitment & Admissions. Configure each on its own; there is no "enable Recruitment & Admissions" step.
>
> Both are individual settings on the `IndustriesSettings` metadata object (`fullName = Industries`), toggled via the headless metadata endpoint and cold-verified against the Tooling API read. These are UPDATE ops that toggle both ways (`true`↔`false`) — unlike the one-way domain toggles.

#### Sub-feature 1 — Turn Off Automatic Decision Sharing

**What this controls (customer-facing)**: Prevent automatic sharing of application decision data with portal users.

- **ON** → automatic decision sharing is turned OFF. Application decision records are NOT automatically shared with portal users.
- **OFF** → application decision records are automatically shared on the date defined on the application timeline.

Enable this when you do NOT want application decisions to surface to portal users automatically on the timeline date — for example, when decisions are released manually or through a controlled communication.

**Setup UI path (for reference)**:
1. From Setup, in Quick Find enter `Set Up Education Cloud`, then select **Set Up Education Cloud**.
2. Under Recruitment & Admissions, find **Turn Off Automatic Decision Sharing** and turn on **Turn Off Application Decision Sharing**.

**Before changing — confirm with customer.** UPDATE operation on org metadata. Present for approve / reject / modify before executing.

**API call (technical)** — metadata element `enableApplnDecStdSharing` (flat read `IsApplnDecStdSharingEnabled`). Turn OFF automatic decision sharing (enable the "turn off sharing" setting):
```http
PUT /services/data/v68.0/headless/metadata
```
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableApplnDecStdSharing>true</enableApplnDecStdSharing></IndustriesSettings>"
}
```
Send `false` to allow automatic sharing again.

#### Sub-feature 2 — Application Materials Protection

**What this controls (customer-facing)**: Control post-submission edit protection for admissions application materials. When ON, application materials are protected from edits after submission.

**Setup UI path (for reference)**:
1. From Setup → Set Up Education Cloud → Recruitment & Admissions.
2. Find **Application Materials Protection** and turn it on.

**Before changing — confirm with customer.** UPDATE operation on org metadata. Present for approve / reject / modify before executing.

**API call (technical)** — metadata element `enableAppMaterialsProtection` (flat read `IsAppMaterialsProtectionEnabled`):
```http
PUT /services/data/v68.0/headless/metadata
```
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableAppMaterialsProtection>true</enableAppMaterialsProtection></IndustriesSettings>"
}
```
Send `false` to remove post-submission edit protection.

#### Cold verification (mandatory — both sub-features)

`success:true` on the write is necessary but NOT sufficient. Always cold-verify against the Tooling API record:
```http
GET /services/data/v68.0/tooling/sobjects/IndustriesSettings/bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=
```
(Raw trailing `=`, NOT URL-encoded `%3D`.) Confirm each element AND its flat read match intended state:
- `.Metadata.enableApplnDecStdSharing` ↔ `.IsApplnDecStdSharingEnabled`
- `.Metadata.enableAppMaterialsProtection` ↔ `.IsAppMaterialsProtectionEnabled`

Only report a setting as changed after both the metadata element and its flat `Is*Enabled` field read the intended value.

### Sub-Feature Configuration

#### Step 1 — Run the Guided Setup Wizard

**What it does**: Runs the Education Cloud Guided Setup wizard to apply foundation settings.

**Setup path**:
1. Navigate to Setup → Feature Settings → Set Up Education Cloud
2. Click "Run Guided Setup" or "Get Started"
3. Follow wizard steps to completion
4. Confirm all foundation settings are applied

**Verification**: Check Setup → Set Up Education Cloud shows wizard completed.

---

#### Step 2 — Set Up the Admissions Console

**What it does**: Configures Admissions Console app for admissions officers.

**Setup path**:
1. Navigate to Setup → App Manager → Find "Admissions Console"
2. Click Edit
3. Assign to admissions officer profiles
4. Configure page layouts for Application, Inquiry, and Opportunity objects
5. Add components:
   - Application pipeline
   - Inquiry management
   - Document review
6. Save

**Verification**: Check App Launcher shows Admissions Console for admissions users.

---

#### Step 3 — Set Up the Recruiter Console

**What it does**: Configures Recruiter Console for recruiter profiles.

**Setup path**:
1. Navigate to Setup → App Manager → Find "Recruiter Console"
2. Click Edit
3. Assign to recruiter profiles
4. Add components:
   - Prospect list
   - Inquiry management
   - Communication log
   - Event registration
5. Save

**Verification**: Check App Launcher shows Recruiter Console for recruiter users.

---

#### Step 4 — Set Up the Reviewer Console

**What it does**: Configures Reviewer Console for application reviewers.

**Setup path**:
1. Navigate to Setup → App Manager → Find "Reviewer Console"
2. Click Edit
3. Assign to application reviewer profiles
4. Configure Application Review and Scoring components:
   - Rubric scoring
   - Reviewer assignments
   - Decision workflow
5. Save

**Verification**: Check App Launcher shows Reviewer Console for reviewer users.

---

#### Step 5 — Set Up the Director Console (Admissions)

**What it does**: Configures Director Console with KPI and pipeline visibility for admissions directors.

**Setup path**:
1. Navigate to Setup → App Manager → Find "Director Console"
2. Click Edit
3. Configure KPI and pipeline visibility components:
   - Application pipeline metrics
   - Reviewer performance
   - Admission funnel
4. Save and assign to director user profiles

**Verification**: Check App Launcher shows Director Console for director users.

---

#### Step 6 — Configure Application Stages

**What it does**: Activates Application Stage OmniScripts and FlexCards, maps stages to OmniScripts.

**Setup path**:
1. Navigate to Setup → OmniStudio → OmniScripts
2. Activate Application Stage OmniScripts (e.g., "Application Submission", "Application Review", "Decision")
3. Navigate to Setup → OmniStudio → FlexCards
4. Activate Application Stage FlexCards
5. Map each Application Stage to the appropriate OmniScript:
   - Submission Stage → Application Submission OmniScript
   - Review Stage → Application Review OmniScript
   - Decision Stage → Decision OmniScript
6. Configure stage transitions and required fields per stage

**Verification**: Check Application object has Stage picklist values and OmniScript assignments.

---

#### Step 7 — Configure Inquiry and Opportunity Management

**What it does**: Sets up Lead/Inquiry record types for prospective students and Opportunity record types for application pipeline.

**Setup path**:
1. Navigate to Setup → Object Manager → Lead
2. Create Lead/Inquiry record types:
   - Prospective Student
   - Transfer Inquiries
   - Graduate Inquiries
3. Navigate to Setup → Object Manager → Opportunity
4. Create Opportunity record types for application pipeline:
   - Undergraduate Application
   - Graduate Application
   - Transfer Application
5. Map inquiry sources (web form, event, direct) to record creation flows

**Verification**: `GET /services/data/v68.0/tooling/query` with `queryParams: {"q": "SELECT Id, Name, SobjectType FROM RecordType WHERE SobjectType IN ('Lead','Opportunity')"}` — confirm each created record type by Name. Or describe the object (`GET /services/data/v68.0/sobjects/Lead/describe` or `Opportunity/describe`) to confirm via `recordTypeInfos`.

---

#### Step 8 — Set Up Campus and Program Finder

**What it does**: Configures Campus Finder component in Experience Cloud and links to Learning Program and Business Account data.

**Setup path**:
1. Navigate to Experience Builder for the applicant portal
2. Add Campus Finder component to the portal
3. Link to Learning Program records
4. Link to Business Account records (Campus level)
5. Publish to the applicant-facing portal

**Verification**: Navigate to portal URL and verify Campus Finder component loads.

---

#### Step 9 — Set Up Application Permissions and Sharing

**What it does**: Configures OWD (Org-Wide Defaults) for Application object and sets up sharing rules.

**Setup path**:
1. Navigate to Setup → Sharing Settings → Application
2. Set OWD to Private or Public Read Only
3. Create sharing rules to ensure applicants can only see their own records
4. Assign permission sets to admissions staff with broader access

**Verification**: Test with applicant user profile to confirm they see only their own application.

---

#### Step 10 — Configure Recommendation Collection

**What it does**: Sets up recommendation request flows and email templates for recommender outreach.

**Setup path**:
1. Navigate to Setup → Flows → Create new Flow
2. Configure Recommendation Request flow:
   - Trigger: Application reaches "Submitted" stage
   - Action: Send email to recommenders
3. Configure email templates for recommender outreach
4. Link recommendations to the Application record
5. Activate flow

**Verification**: Test with test application to confirm recommendation request email is sent.

---

#### Step 11 — Configure Application Review Process and Scoring

**What it does**: Configures rubric templates for application scoring and assigns reviewer pools.

**Setup path**:
1. Navigate to Admissions Console → Rubric Templates
2. Create rubric templates for application scoring:
   - Academic Achievement (GPA, test scores)
   - Extracurricular Involvement
   - Essays and Personal Statement
   - Recommendations
3. Assign reviewer pools per program or application type
4. Set up automated assignment rules for reviewer distribution
5. Save

**Verification**: Check Reviewer Console shows rubric templates and assigned applications.

---

#### Step 12 — Configure the Applicant Portal (Experience Cloud)

**What it does**: Deploys applicant-facing portal with application form, status tracker, document upload, recommendation status.

**Setup path**:
1. Navigate to Setup → Digital Experiences → All Sites
2. Create new Experience Cloud site or configure existing site
3. Add components:
   - Application form
   - Status tracker
   - Document upload
   - Recommendation status
4. Set up unauthenticated and authenticated access paths
5. Publish and activate the portal

**Verification**: Navigate to portal URL and verify components load for applicant users.

---

#### Step 13 — (Optional) Import Common App Data

**What it does**: Configures Common App integration connector and maps fields to Education Cloud Application fields.

**Setup path**:
1. Navigate to Setup → Integrations → Common App Connector
2. Configure connector settings (API credentials)
3. Map Common App fields to Education Cloud Application fields
4. Run initial data import
5. Validate imported data

**Verification**: Check Application records populated with Common App data.

---

