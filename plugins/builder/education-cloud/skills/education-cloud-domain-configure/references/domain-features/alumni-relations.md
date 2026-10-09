# 4. Alumni Relations

**Purpose**: Track alumni engagement, giving campaigns, events, and networking.

**Prerequisites**:
- All Foundation prerequisites (Section 0)
- Experience Cloud — for alumni-facing portal and profile components
- Fundraising license — for gift management features (optional)
- Marketing Cloud Engagement for Education (optional) — for alumni email campaigns
- Donor Support Agent / Philanthropic Research Agent (optional) — requires Agentforce add-on license + Einstein GenAI

**Core features**:
- Alumni records (Person Accounts)
- Engagement tracking
- Giving campaigns and donations
- Event management
- Volunteer opportunities

### Sub-Feature Configuration

#### Step 1 — Configure Alumni Profiles and Data

**What it does**: Converts or tags existing Contact records with alumni record type and configures alumni-specific fields.

**Setup path**:
1. Navigate to Setup → Object Manager → Account (Person Account)
2. Create Alumni record type if not exists
3. Assign Alumni record type to existing Contact records or create new
4. Configure alumni-specific fields:
   - Graduation year
   - Degree
   - Department
   - Employer
   - Industry
5. Set up RFM (Recency, Frequency, Monetary) scoring for donor segmentation

**Verification**: `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM Account WHERE RecordType.Name='Alumni'"}` — no need to ask the user for a raw Id. Describe the object (`GET /services/data/v68.0/sobjects/Account/describe`) as a fallback to confirm fields/record types.

---

#### Step 2 — Set Up Alumni Engagement Tracking

**What it does**: Configures interaction/engagement record types and engagement scoring rules.

**Setup path**:
1. Navigate to Alumni Relations Console → Engagement tab
2. Configure interaction/engagement record types:
   - Event attendance
   - Donation
   - Volunteer activity
   - Mentoring participation
3. Set up engagement scoring rules (e.g., event attendance = 10 points, donation = 50 points)
4. Link engagements to alumni Contact records
5. Save

**Verification**: `GET /services/data/v68.0/tooling/query` with `queryParams: {"q": "SELECT Id, Name, SobjectType FROM RecordType WHERE SobjectType='Engagement__c'"}` to confirm the configured record types, plus `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM Engagement__c"}` to spot-check records — no need to ask the user for a raw Id. Describe the object (`GET /services/data/v68.0/sobjects/Engagement__c/describe`) as a fallback to confirm fields/record types.

---

#### Step 3 — Set Up the Alumni Portal (Experience Cloud)

**What it does**: Deploys alumni-facing portal with profile components, event registration, mentoring sign-up, giving forms.

**Setup path**:
1. Navigate to Setup → Digital Experiences → All Sites
2. Create new Experience Cloud site or configure existing site
3. Add alumni profile components:
   - Bio
   - Career info
   - Giving history
   - Engagement score
4. Add engagement features:
   - Event registration
   - Mentoring sign-up
   - Giving forms
   - Volunteer opportunities
5. Publish and activate the portal

**Verification**: Navigate to portal URL and verify components load for alumni users.

---

#### Step 4 — Configure Fundraising (if licensed)

**What it does**: Sets up Gift Commitment, Gift Transaction, and Gift Entry workflows.

**Setup path**:
1. Navigate to Alumni Relations Console → Fundraising tab
2. Set up Gift Commitment record types
3. Configure Gift Transaction workflows
4. Configure Gift Entry workflows
5. Set up Gift Processing rules and approvals
6. Link giving data to Donor Profiles
7. Save

**Verification**: `GET /services/data/v68.0/tooling/query` with `queryParams: {"q": "SELECT Id, Name, SobjectType FROM RecordType WHERE SobjectType='GiftCommitment__c'"}` to confirm the configured record types, plus `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM GiftCommitment__c"}` to spot-check records — no need to ask the user for a raw Id. Describe the object (`GET /services/data/v68.0/sobjects/GiftCommitment__c/describe`) as a fallback to confirm fields/record types.

---

#### Step 5 — Set Up Donor Profiles and Briefs

**What it does**: Configures Donor Profile page layout with giving history, engagement scores, and relationship data.

**Setup path**:
1. Navigate to Setup → Object Manager → Account (Person Account)
2. Edit Alumni record type page layout
3. Add Donor Profile section with:
   - Giving history
   - Engagement scores
   - Relationship data
   - Philanthropic interests
4. Enable Philanthropic Research data integration if available
5. Configure Donor Briefs for major gift officers
6. Save

**Verification**: Check Alumni record page shows Donor Profile section.

---

#### Step 6 — Configure Reporting and Insights

**What it does**: Activates Education Analytics dashboards for Advancement and configures alumni engagement KPIs.

**Setup path**:
1. Navigate to Setup → Analytics → Education Analytics
2. Activate dashboards for Advancement:
   - Alumni Engagement KPIs
   - Fundraising pipeline reports
   - Donor retention metrics
3. Link to CRM Analytics for Advisor-style insights on donor behavior
4. Save

**Verification**: Check Analytics Studio shows Education Analytics dashboards.

---

#### Step 7 — (Optional) Set Up Marketing Cloud Engagement for Alumni

**What it does**: Connects Marketing Cloud Engagement to Salesforce org and configures alumni email journeys.

**Setup path**:
1. Navigate to Setup → Integrations → Marketing Cloud Engagement
2. Configure Marketing Cloud connection (API credentials)
3. Configure alumni email journeys:
   - Event invites
   - Giving campaigns
   - Newsletters
   - Reunion reminders
4. Sync alumni segments from Education Cloud to Marketing Cloud
5. Activate journeys

**Verification**: Check Marketing Cloud shows synced alumni segments.

---

