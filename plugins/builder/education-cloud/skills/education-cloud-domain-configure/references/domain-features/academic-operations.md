# 3. Academic Operations

**Purpose**: Manage course catalog, section scheduling, enrollment, and academic calendar.

**Prerequisites**:
- All Foundation prerequisites (Section 0)
- OmniStudio — for course search and registration portal components
- Experience Cloud — for student-facing course registration portal
- Business Rules Engine — for Policy Rules Framework (enrollment eligibility, holds/blocks)
- Data Processing Engine — for academic data transformations
- SIS/LMS Integration (optional) — for external system sync

**Core features**:
- Course catalog management
- Section scheduling and capacity
- Enrollment tracking
- Prerequisites and corequisites
- Waitlist management

### Enablement & Toggles (executed order)

**Org context**: On `IndustriesSettings` metadata object, `fullName = Industries`. All feature toggles are `enableXXX` metadata elements (camelCase) with a matching flat read field `Is<X>Enabled`.

**Working method (this org)**:

- **Toggle write** (headless metadata):
  ```http
  PUT /services/data/v68.0/headless/metadata
  {"type":"IndustriesSettings","fullName":"Industries","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><ELEMENT>true</ELEMENT></IndustriesSettings>"}
  ```
- **Cold verify** (mandatory — `success:true` alone unreliable):
  ```http
  GET /services/data/v68.0/tooling/sobjects/IndustriesSettings/bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=
  ```
  Check `.Metadata.<element>` == true AND flat `Is<X>Enabled` == true. Durable Id ends in raw `=` (not `%3D`). Result is large (~25 KB) — grep, don't full-read.
- Query endpoints (`/query`, `/tooling/query`) work via this router — pass the query through `queryParams: {"q": "SELECT ..."}`, NOT inlined as `?q=` in the URL (that 404s). On sObject GET, no `?fields=` param (router treats it as external-id path) — use `/describe` for field lists instead.

Order: Turn On Academic Operations → Automatically Validate Pathway Selections → Create Learning Achievement Record Types → Set Up Learning Achievement Configuration → Turn On Advanced Academic Operations → Enforce Time Conflicts → Configure Course Waitlists. `IndustriesSettings` toggles are IRREVERSIBLE; Course Waitlists (Step 7) is a separate, reversible CRUD object — see that step for its own write path. Try API first; fall back to manual UI on failure.

#### Step 1 — Turn On Academic Operations

**What it does**: Academic Operations — manage learner pathways, course catalog, learning achievements.

**Metadata element**: `enableAcademicOperations` (flat read: `IsAcademicOperationsEnabled`)

**API call**:
```http
PUT /services/data/v68.0/headless/metadata
{"type":"IndustriesSettings","fullName":"Industries","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableAcademicOperations>true</enableAcademicOperations></IndustriesSettings>"}
```

**Verification** (cold): GET IndustriesSettings → `.Metadata.enableAcademicOperations` == true AND `IsAcademicOperationsEnabled` == true.

**Sub-features** (enumerate + confirm with customer before proceeding): Automatically Validate Pathway Selections, Learning Achievement Record Types + Configuration, Advanced Academic Operations, Enforce Time Conflicts, Configure Course Waitlists.

---

#### Step 2 — Automatically Validate Pathway Selections

**What it does**: Automatically Validate Pathway Selections — validates prerequisite and corequisite requirements automatically when a learner drops a course in the pathway canvas. Off by default.

**Metadata element**: `enablePathwayPlannerRealTimeValidation` (flat read: `IsPathwayPlannerRealTimeValidationEnabled`)

**API call**:
```http
PUT /services/data/v68.0/headless/metadata
{"type":"IndustriesSettings","fullName":"Industries","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enablePathwayPlannerRealTimeValidation>true</enablePathwayPlannerRealTimeValidation></IndustriesSettings>"}
```

**Verification** (cold): GET IndustriesSettings → `.Metadata.enablePathwayPlannerRealTimeValidation` == true AND `IsPathwayPlannerRealTimeValidationEnabled` == true.

**Note**: When ON, the "Verify Program Requirements" button does NOT appear in the Learner Pathway Builder — validation runs automatically.

---

#### Step 3 — Create Learning Achievement Record Types (CREATE)

**What it does**: Learning Achievement Record Types — the record types backing learning objects (courses, programs, achievement groups, skills, and custom types like degrees/diplomas).

**Announce every create** (approve / reject / modify) before executing.

**Object**: `RecordType` (Tooling API). SObjectType = `LearningAchievement`.

**API call** (per record type):
```http
POST /services/data/v68.0/tooling/sobjects/RecordType
{"FullName":"LearningAchievement.<DeveloperName>","Metadata":{"label":"<Label>","active":true,"description":"..."}}
```
- `active:true` = UI "Select Active" step.
- Picklists inherited from Master automatically.
- Profile permissions NOT settable via this shape — assign separately via perm sets/profiles.
- Returns record Id.

**Minimum**: create at least 3 (Learning Course, Learning Program, Achievement Group). This org created 6 (Skill skipped — `enableEDCSkillsGenerator` = false):

| Label | DeveloperName | RecordType Id (example — this org) |
|-------|---------------|--------------------------|
| Learning Course | Learning_Course | 012SB00000BRNBuYAP |
| Learning Program | Learning_Program | 012SB00000BRNYTYA5 |
| Achievement Group | Achievement_Group | 012SB00000BRNa5YAH |
| Achievement Group All | Achievement_Group_All | 012SB00000BRNbhYAH |
| Degree | Degree | 012SB00000BRNdJYAX |
| Diploma | Diploma | 012SB00000BRNevYAH |

Skipped: Skill (only needed if Einstein Skills Generator / `enableEDCSkillsGenerator` is on).

**Verification** (cold, per Id): GET `/services/data/v68.0/tooling/sobjects/RecordType/<Id>` → confirm `IsActive` == true, `SobjectType` == LearningAchievement, `Name`, `FullName` match.

---

#### Step 4 — Set Up Learning Achievement Configuration (CREATE)

**What it does**: Learning Achievement Configuration (Set Up Learning Achievement Types) — maps each Learning Achievement type to a Learning Achievement record type. Every learning achievement type requires ≥1 config record. Learning Course, Learning Program, and Achievement Group config records CAN'T be deleted.

**Prerequisite**: Learning Achievement record types created first (Step 3). Capture their Ids.

**Announce every create** (approve / reject / modify) before executing.

**Object**: `LearningAchievementConfig` (Data API + Tooling API). Key prefix `14y`.

**Create fields**:
- `MasterLabel` — Name (label)
- `DeveloperName` — API Name (unique, no spaces)
- `LearningAchievementType` — picklist. Values: `LearningCourse`, `LearningProgram`, `AchievementGroup`, `AchievementGroupAll`, `Skill`, `Custom`
- `LearningAchvRecordTypeId` — reference to RecordType (UNIQUE — one config per record type)
- Optional: `Description`, `IconName`

**API call** (per record):
```http
POST /services/data/v68.0/sobjects/LearningAchievementConfig
{"MasterLabel":"Learning Course","DeveloperName":"LearningCourse","LearningAchievementType":"LearningCourse","LearningAchvRecordTypeId":"<RecordTypeId>"}
```
Returns record Id (`14y...`).

**Standard mappings** (this org created 6; Skill skipped):

| Name (MasterLabel) | API Name (DeveloperName) | LearningAchievementType | Record Type | Config Id (example — this org) |
|--------------------|--------------------------|-------------------------|-------------|----------------------|
| Learning Course | LearningCourse | `LearningCourse` | Learning_Course | 14ySB0000001WvVYAU |
| Learning Program | LearningProgram | `LearningProgram` | Learning_Program | 14ySB0000001Wx7YAE |
| Achievement Group | AchievementGroup | `AchievementGroup` | Achievement_Group | 14ySB0000001WyjYAE |
| Achievement Group All | Achievement_Group_All | `AchievementGroupAll` | Achievement_Group_All | 14ySB0000001X0LYAU |
| Degree | Degree | `Custom` | Degree | 14ySB0000001X1xYAE |
| Diploma | Diploma | `Custom` | Diploma | 14ySB0000001X3ZYAU |

Notes:
- Rows 1-3 mandatory + non-deletable.
- Custom configs (Degree, Diploma) use type `Custom` — no dedicated picklist value.
- Skill config only if Einstein Skills Generator (`enableEDCSkillsGenerator`) is on.

**Verification** (cold, per Id): GET `/services/data/v68.0/sobjects/LearningAchievementConfig/<Id>` → confirm `LearningAchievementType` + `LearningAchvRecordTypeId` match intended mapping.

---

#### Step 5 — Turn On Advanced Academic Operations

**What it does**: Advanced Academic Operations — course search + registration for students. Includes SIS features: course registration, holds management, GPA calculation, and enrollment policy enforcement. Turning it on in Education Cloud lets you manage licenses/access, enable features per-student, monitor usage, and manage billing centrally.

**Prerequisites / dependencies**:
- Assign the **Education Cloud Advanced Academic Operations for Experience Cloud** permission set license to students → enables course registration, waitlists, and student portal features.
- Includes access to the **Business Rules Engine (BRE)** and **Expression Sets**, plus the quotas required to run them. EVERY feature in the Advanced Academic Operations feature set requires BRE and quota capacity.
- (These PSL assignment + BRE/quota provisioning steps are manual/admin work, outside this toggle.)

**Metadata element**: `enableEduAdvncdAcadOper` (flat read: `IsEduAdvncdAcadOperEnabled`)

**API call**:
```http
PUT /services/data/v68.0/headless/metadata
{"type":"IndustriesSettings","fullName":"Industries","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableEduAdvncdAcadOper>true</enableEduAdvncdAcadOper></IndustriesSettings>"}
```

**Verification** (cold): GET IndustriesSettings → `.Metadata.enableEduAdvncdAcadOper` == true AND `IsEduAdvncdAcadOperEnabled` == true.

**Note**: Related agent toggles (`enableCourseSearchAgent`, `enableCourseOpsAgent`) are separate Agentforce features, NOT part of this switch.

---

#### Step 6 — Enforce Time Conflicts

**What it does**: Enforce Time Conflicts — enforces time-conflict validation to prevent learners from registering for course offerings that have conflicting schedules.

**Metadata element**: `enableCosConflicts` (flat read: `IsCosConflictsEnabled`) (COS = Course Offering Schedule.)

**API call**:
```http
PUT /services/data/v68.0/headless/metadata
{"type":"IndustriesSettings","fullName":"Industries","xmlRep":"<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableCosConflicts>true</enableCosConflicts></IndustriesSettings>"}
```

**Verification** (cold): GET IndustriesSettings → `.Metadata.enableCosConflicts` == true AND `IsCosConflictsEnabled` == true.

---

#### Step 7 — Configure Course Waitlists

**What it does**: Course Waitlists — configures waitlist ranking rules (`WaitlistPosition`) and the enrollment-offer acceptance window (`EnrollmentOfferExpiration`) that drive course-waitlist behavior org-wide.

**Object**: `CourseWaitlistConfig` — NOT an `IndustriesSettings` toggle; its own setup object with a dedicated Aura-backed API (confirmed live on this org — `GET` below returned `200`). **AURA-IS-CANONICAL**: the controller maintains the `WaitlistPositionFieldOrder` sibling cascade server-side (insert shifts higher rows +1, update reorders the affected window, delete compacts to a contiguous `1..N`) — a raw Tooling Insert/Update/Delete or Metadata XML deploy lands the row but breaks that invariant. Use the endpoints below, not a generic sObject/Tooling write.

**Read existing configs first** (ordered by `WaitlistPositionFieldOrder` ASC):
```http
GET /headless/invoke/platform/course-waitlist-config
```
Returns `[]` when no rows exist yet. Each row: `Id`, `DeveloperName`, `MasterLabel`, `Type` (`WaitlistPosition` | `EnrollmentOfferExpiration`), `Value`, `WaitlistPositionFieldOrder`, `SortOrder`.

**Create**:
```http
PATCH /headless/invoke/platform/course-waitlist-config/create-course-waitlist-config
{"developerName": "<name>", "masterLabel": "<label>", "type": "WaitlistPosition", "value": "<value>", "waitlistPositionFieldOrder": <int>, "sortOrder": "Ascending"}
```
Returns `{"success": true, "recordId": "<id>"}`. When `type = WaitlistPosition` and `waitlistPositionFieldOrder` is set, the controller shifts every sibling row at-or-above the new position by +1 before inserting.

**Update** (by `recordId` from the read step; `developerName`/`type` are immutable post-create):
```http
PATCH /headless/invoke/platform/course-waitlist-config/update-course-waitlist-config
{"recordId": "<id>", "masterLabel": "<label>", "value": "<value>", "waitlistPositionFieldOrder": <int>, "sortOrder": "Ascending"}
```
Changing `waitlistPositionFieldOrder` reorders every sibling row in the affected window server-side.

**Delete** (by `recordId`):
```http
DELETE /headless/invoke/platform/course-waitlist-config/delete-course-waitlist-config
```
`queryParams: {"recordId": "<id>"}`. If the deleted row was `Type = WaitlistPosition`, remaining `WaitlistPosition` rows are compacted to a contiguous `1..N` sequence.

**Verification** (cold, after any write): re-run the GET above and confirm the row is present/absent/updated as expected — for `WaitlistPosition` changes, also confirm sibling `WaitlistPositionFieldOrder` values reflect the cascade (no gaps, no duplicates).

**Preconditions**: Academic Operations enabled (Step 1 of this section) + `AccessEducationCloud` user permission; create/update/delete additionally require admin access (edit/create/delete all require `isAdminUser`).

---

### Sub-Feature Configuration

#### Step 1 — Create Learning Programs

**What it does**: Creates Learning Program records for each degree/certificate/program.

**Setup path**:
1. Navigate to Academic Operations App → Learning Programs
2. Click New
3. Create Learning Program record:
   - Program Name: "Bachelor of Science in Computer Science"
   - Academic Level: Bachelor's
   - Credit Hours Required: 120
   - Link to Business Account (Department or College)
4. Configure program prerequisites and requirements
5. Save
6. Repeat for each degree/certificate/program

**API approach** (try first):
```http
POST /services/data/v68.0/sobjects/LearningProgram__c
{"Name": "Bachelor of Science in Computer Science", "AcademicLevel__c": "Bachelors", "CreditHours__c": 120, "BusinessAccount__c": "<Dept_Account_ID>"}
```

**Verification** (read back by the Id captured at creation — a SOQL `SELECT Id FROM <Object> WHERE ...` via `queryParams` also works if you need to re-find the record later):
```http
GET /services/data/v68.0/sobjects/LearningProgram__c/<id-captured-from-create-response>
```

---

#### Step 2 — Configure Course Search and Registration

**What it does**: Activates Course Search OmniScript and FlexCards, configures search filters.

**Setup path**:
1. Navigate to Setup → OmniStudio → OmniScripts
2. Activate Course Search OmniScript
3. Navigate to Setup → OmniStudio → FlexCards
4. Activate Course Search FlexCards
5. Configure search filters:
   - Term
   - Department
   - Level (100, 200, 300, 400)
   - Availability (open seats)
6. Add Course Search component to the student-facing portal (Experience Cloud)

**Verification**: Navigate to portal URL and verify Course Search component loads.

---

#### Step 3 — Configure Enrollment Eligibility (Policy Rules Framework)

**What it does**: Creates enrollment eligibility rules using Business Rules Engine.

**Setup path**:
1. Navigate to Setup → Business Rules Engine
2. Create enrollment eligibility rules:
   - Credit hour minimum/maximum (e.g., full-time = 12-18 credits)
   - Academic standing requirements (e.g., GPA ≥ 2.0 for enrollment)
   - Prerequisite completion checks
3. Activate rules
4. Link to enrollment workflow

**Verification**: Test enrollment with test student to confirm rules enforce.

---

#### Step 4 — Configure Holds and Blocks

**What it does**: Defines hold types and configures which holds block enrollment.

**Setup path**:
1. Navigate to Academic Operations App → Holds and Blocks
2. Define hold types:
   - Financial hold (unpaid balance)
   - Academic hold (probation/suspension)
   - Administrative hold (missing documents)
3. Configure which holds block enrollment
4. Assign roles that can place/remove holds
5. Save

**Verification**: `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM Hold__c"}` (add a `WHERE Name = '...'` filter once the exact hold-type field name is confirmed via describe — no need to ask the user for a raw Id). Describe the object (`GET /services/data/v68.0/sobjects/Hold__c/describe`) first to confirm the actual field names/record types.

---

#### Step 5 — Configure Course Waitlists

**What it does**: Enables waitlist functionality per course offering and sets automatic promotion rules.

**Setup path**:
1. Navigate to Academic Operations App → Course Offerings
2. Edit course offering record
3. Enable waitlist functionality
4. Set waitlist capacity (e.g., max 10 students on waitlist)
5. Set automatic promotion rules (e.g., promote next student when seat opens)
6. Save

**Verification**: Check Course Offering record has waitlist enabled.

---

#### Step 6 — Set Up Petitions and Waivers

**What it does**: Configures petition record types and assigns review/approval workflows.

**Setup path**:
1. Navigate to Setup → Object Manager → Petition__c
2. Create petition record types:
   - Course waiver
   - Prerequisite waiver
   - Enrollment exception
3. Assign review and approval workflows per record type
4. Link to student academic record
5. Save

**Verification**: `GET /services/data/v68.0/tooling/query` with `queryParams: {"q": "SELECT Id, Name, SobjectType FROM RecordType WHERE SobjectType='Petition__c'"}` — confirm each created record type by Name. Or describe the object (`GET /services/data/v68.0/sobjects/Petition__c/describe`) to confirm via `recordTypeInfos`.

---

#### Step 7 — Configure Transfer Credit Management

**What it does**: Defines transfer credit equivalency rules and configures review workflow.

**Setup path**:
1. Navigate to Academic Operations App → Transfer Credits
2. Define transfer credit equivalency rules (e.g., CS-101 at Community College = CS-101 at University)
3. Configure transfer credit review workflow
4. Link approved transfer credits to student's degree plan
5. Save

**Verification**: `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM TransferCredit__c"}` (add a `WHERE` filter on the relevant lookup/field once confirmed via describe — no need to ask the user for a raw Id). Describe the object (`GET /services/data/v68.0/sobjects/TransferCredit__c/describe`) first to confirm field names/record types.

---

#### Step 8 — Set Up Intelligent Degree Planning

**What it does**: Enables Degree Planning feature and configures degree plan templates per Learning Program.

**Setup path**:
1. Navigate to Setup → Education Cloud Settings
2. Enable Degree Planning feature toggle
3. Navigate to Academic Operations App → Degree Plan Templates
4. Configure degree plan templates per Learning Program:
   - Link to Learning Program
   - Add required courses
   - Add elective requirements
5. Link to Course Catalog and Academic Calendar
6. Add Degree Planning component to Learner Portal (Experience Cloud)
7. Save

**Verification**: Navigate to Learner Portal and verify Degree Planning component loads for student users.

---

