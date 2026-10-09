# 5. Student Management

**Purpose**: Centralized student information, enrollment tracking, and records management.

**Prerequisites**:
- All Foundation prerequisites (Section 0)
- Person Accounts enabled (students are stored as Person Account records)
- Academic Operations set up (courses, programs, calendar must exist before enrollment records)
- OmniStudio — for portal-based student management components
- Experience Cloud — for student-facing access
- SIS Integration (optional) — for syncing student records from external Student Information System

**Core features**:
- Student records (Person Accounts)
- Enrollment status and history
- Attendance tracking
- Academic standing
- Degree progress

### Sub-Feature Configuration

#### Step 1 — Configure Student Record Types

**What it does**: Confirms Student record type exists and configures student-specific page layout.

**Setup path**:
1. Navigate to Setup → Object Manager → Account (Person Account)
2. Confirm Student record type exists and is active
3. Edit Student record type page layout
4. Add student-specific fields:
   - Enrollment status
   - Academic standing
   - GPA
   - Advisor assignment
   - Major/program
5. Save

**Verification**: `GET /services/data/v68.0/tooling/query` with `queryParams: {"q": "SELECT Id, Name, SobjectType FROM RecordType WHERE SobjectType='Account' AND Name='Student'"}` — confirm the Student record type exists. Or describe the object (`GET /services/data/v68.0/sobjects/Account/describe`) to confirm via `recordTypeInfos`.

---

#### Step 2 — Configure Enrollment Records

**What it does**: Sets up enrollment record types per term and configures enrollment status picklist values.

**Setup path**:
1. Navigate to Student Management App → Enrollment
2. Set up enrollment record types per term
3. Configure enrollment status picklist values:
   - Enrolled
   - Withdrawn
   - Completed
   - Pending
4. Link enrollment records to Academic Term and Learning Course
5. Save

**Verification**: `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM Enrollment__c"}` (add a `WHERE` filter on the term/course lookup once confirmed via describe — no need to ask the user for a raw Id). Describe the object (`GET /services/data/v68.0/sobjects/Enrollment__c/describe`) first to confirm field names/record types.

---

#### Step 3 — Set Up Student Academic Records

**What it does**: Configures grade record types and academic standing calculation rules.

**Setup path**:
1. Configure Grade record types:
   - Midterm Grade
   - Final Grade
   - Transfer Credit Grade
2. Configure page layouts for grade records
3. Set up academic standing calculation rules:
   - GPA ≥ 3.0 = Good Standing
   - 2.0 ≤ GPA < 3.0 = Probation
   - GPA < 2.0 = Academic Suspension
4. Link grade records to Course Offering and Enrollment
5. Save

**Verification**: `GET /services/data/v68.0/tooling/query` with `queryParams: {"q": "SELECT Id, Name, SobjectType FROM RecordType WHERE SobjectType='Account' AND Name IN ('Midterm Grade','Final Grade','Transfer Credit Grade')"}` — no need to ask the user for a raw Id. Describe the object (`GET /services/data/v68.0/sobjects/Account/describe`) as a fallback to confirm via `recordTypeInfos`.

---

#### Step 4 — Configure Advisor Assignments

**What it does**: Sets up advisor-to-student assignment rules.

**Setup path**:
1. Navigate to Student Management App → Advisor Assignments
2. Set up advisor-to-student assignment rules:
   - By major
   - By department
   - By caseload (max students per advisor)
3. Link advisor assignments to Advisor Console (Student Success)
4. Save

**Verification**: `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM AdvisorAssignment__c"}` (add a `WHERE` filter on the advisor/student lookup once confirmed via describe — no need to ask the user for a raw Id). Describe the object (`GET /services/data/v68.0/sobjects/AdvisorAssignment__c/describe`) first to confirm field names/record types.

---

#### Step 5 — Set Up Student Holds (Centralized View)

**What it does**: Links holds from Academic Operations to Student Management record.

**Setup path**:
1. Navigate to Student Management App → Student record page
2. Add Holds component to page layout
3. Link holds from Academic Operations
4. Configure holds view on student profile page
5. Set up hold notification flows for students and staff
6. Save

**Verification**: Check Student record page shows Holds component.

---

#### Step 6 — Configure the Student 360 View

**What it does**: Adds comprehensive components to Student record page.

**Setup path**:
1. Navigate to Setup → Object Manager → Account (Person Account)
2. Edit Student record type page layout
3. Add components:
   - Enrollment history
   - Academic plan / Degree plan
   - Advising history and care plans
   - Financial account summary
   - Holds and alerts
   - Involvement and extracurriculars
4. Publish updated page layout to relevant profiles
5. Save

**Verification**: Check Student record page shows all 360 view components.

---

#### Step 7 — (Optional) Configure SIS Integration

**What it does**: Sets up SIS connector or middleware integration and configures sync schedule.

**Setup path**:
1. Navigate to Setup → Integrations → SIS Connector
2. Configure SIS connector settings (API credentials)
3. Map SIS fields to Education Cloud object fields:
   - Student ID → External ID
   - Name → Account Name
   - Enrollment status → Enrollment Status
   - Grades → Grade records
4. Configure sync schedule (real-time or batch)
5. Test bidirectional sync for student records, enrollment, and grades
6. Activate sync

**Verification**: Check Student records populated with SIS data.

---

