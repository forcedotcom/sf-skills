# 6. Mentoring

**Purpose**: Facilitate mentoring programs, match mentors with mentees, track sessions.

**Prerequisites**:
- All Foundation prerequisites (Section 0)
- Experience Cloud (Experience Builder) — for Mentoring Portal
- OmniStudio — for assessments and matching experiences

**Core features**:
- Mentor and mentee profiles (Person Accounts)
- Program management
- Matching rules and algorithms
- Session tracking
- Goal setting and progress

### Sub-Feature Configuration

#### Step 1 — Create Mentoring Programs

**What it does**: Creates Mentoring Program records.

**Setup path**:
1. Navigate to Mentoring app (or Education Cloud app) → Mentoring Programs
2. Click New
3. Create Mentoring Program record:
   - Program Name: "Alumni-Student Mentoring"
   - Program Type: Peer Mentoring / Alumni-Student / Professional Mentoring
   - Start Date: 2025-09-01
   - End Date: 2026-05-31
   - Capacity: 100 mentor-mentee pairs
   - Status: Active
4. Define program goals and benefits
5. Save
6. Repeat for additional programs

**Verification** (read back by the Id captured at creation — a SOQL `SELECT Id FROM <Object> WHERE ...` via `queryParams` also works if you need to re-find the record later):
```http
GET /services/data/v68.0/sobjects/MentoringProgram__c/<id-captured-from-create-response>
```

---

#### Step 2 — Set Up Mentoring Programs (Program and Benefit Management Settings)

**What it does**: Set Up Mentoring Programs — define and manage mentoring support programs with related benefits. Under Setup, the single Mentoring sub-feature link ("Set Up Mentoring Programs") leads to **Program and Benefit Management Settings**, the SAME 4 toggles used by Student Success. Mentoring shares this setting group, so if you configured Student Success first these are already on.

The 4 toggles:

- **Program and Benefit Management** — Create and manage your programs, benefits, and goals.
- **Benefit Assignment and Goal Assignment Sharing** — Allow users to access all benefit assignment and goal assignment records when the user has access to the record's parent records.
- **Allow benefit assignments with inactive program enrollments** — Allow benefit assignments even when the related program enrollment is inactive.
- **Program Cohorts** — Create and manage program cohorts.

**Setup UI path (for reference)**:
1. From Setup → Set Up Education Cloud → Mentoring → **Set Up Mentoring Programs**.
2. Open **Program and Benefit Management Settings** and confirm all 4 toggles are on.

**Idempotent behavior**: These may already be enabled from Student Success. Cold-verify FIRST; only write the toggles that read `false`; then re-verify. Skipping already-on toggles is expected — report them as already enabled.

**Before enabling any that are off — confirm with customer.** UPDATE operation on org metadata. Present for approve / reject / modify before executing.

**API call (technical)** — metadata elements on `IndustriesSettings`, `fullName = Industries`:

| Setup toggle | Metadata element | Flat read field |
|---|---|---|
| Program and Benefit Management | `enableBenefitManagementPreference` | `IsBenefitManagementPreferenceEnabled` |
| Benefit Assignment and Goal Assignment Sharing | `enableBenefitAndGoalSharingPref` | `IsBenefitAndGoalSharingPrefEnabled` |
| Allow benefit assignments with inactive program enrollments | `allowBenefitAssignmentWithInactiveProgramEnrollment` | `AllowBenefitAssignmentWithInactiveProgramEnrollment` |
| Program Cohorts | `enableProgramCohorts` | `IsProgramCohortsEnabled` |

Enable any that are off (include only the off ones in the xmlRep, or send all four true — safe/idempotent):

```http
PUT /services/data/v68.0/headless/metadata
```
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableBenefitManagementPreference>true</enableBenefitManagementPreference><enableBenefitAndGoalSharingPref>true</enableBenefitAndGoalSharingPref><allowBenefitAssignmentWithInactiveProgramEnrollment>true</allowBenefitAssignmentWithInactiveProgramEnrollment><enableProgramCohorts>true</enableProgramCohorts></IndustriesSettings>"
}
```

**Cold verification (mandatory)**:
```http
GET /services/data/v68.0/tooling/sobjects/IndustriesSettings/bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=
```
Confirm all four `.Metadata.*` elements AND their flat `Is*Enabled` reads are `true`.

---

#### Step 3 — Configure Mentor and Mentee Profiles

**What it does**: Defines profile fields for Mentors and Mentees.

**Setup path**:
1. Navigate to Mentoring app → Program Members
2. Define profile fields for Mentors:
   - Industry
   - Expertise
   - Graduation year
   - Availability
   - Preferred communication style
3. Define profile fields for Mentees:
   - Academic goals
   - Career interests
   - Preferred communication style
   - Availability
4. Configure matching assessment questions
5. Save

**Verification**: Check Program Members show mentor and mentee profile fields.

---

#### Step 4 — Set Up Mentor-Mentee Matching via Assessments

**What it does**: Activates Mentoring Assessment OmniScript and configures matching criteria.

**Setup path**:
1. Navigate to Setup → OmniStudio → OmniScripts
2. Activate Mentoring Assessment OmniScript
3. Configure matching criteria:
   - Skills alignment
   - Availability overlap
   - Goal compatibility
4. Set matching mode:
   - Manual (admin reviews and matches)
   - Algorithmic (automatic based on criteria)
   - Hybrid (admin-assisted with algorithm suggestions)
5. Create mentor-mentee pair records upon match confirmation
6. Save

**Verification**: Check Mentoring Portal shows matched pairs.

---

#### Step 5 — Set Up the Mentoring Portal (Experience Cloud)

**What it does**: Deploys Mentoring Portal with profile browsing, match requests, meeting log, messaging.

**Setup path**:
1. Navigate to Setup → Digital Experiences → All Sites
2. Create new Experience Cloud site or configure existing site
3. Add Mentoring Portal components:
   - Mentor profile browsing
   - Match request submission
   - Meeting log and milestone tracker
   - Messaging between mentor/mentee
4. Configure access for authenticated mentors and mentees
5. Publish and activate the portal

**Verification**: Navigate to portal URL and verify components load for mentor/mentee users.

---

#### Step 6 — Configure Mentoring Benefits Management

**What it does**: Defines benefit types and assigns benefits to active mentor-mentee pairs.

**Setup path**:
1. Navigate to Mentoring app → Benefits
2. Define benefit types:
   - Career resources (resume review, interview prep)
   - Event invites (networking events, workshops)
   - Recognition (awards, certificates)
3. Assign benefits to active mentor-mentee pairs
4. Configure benefit expiration and renewal rules
5. Save

**Verification**: Check Benefits tab shows assigned benefits.

---

#### Step 7 — Configure Notifications and Milestone Tracking

**What it does**: Sets up automated notifications and milestone completion criteria.

**Setup path**:
1. Navigate to Setup → Flows → Create new Flow
2. Set up automated notifications for:
   - New match confirmations
   - Meeting reminders
   - Milestone completions
   - Program end dates
3. Configure milestone record types:
   - First meeting completed
   - 3-month check-in
   - Program completion
4. Configure milestone completion criteria
5. Link milestones to mentor-mentee pair record
6. Activate flows

**Verification**: Test with test mentor-mentee pair to confirm notifications send.

---

