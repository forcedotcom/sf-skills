# IndustriesSettings Toggle Fields — Quick Reference

All EDU toggles are `enableXXX` fields inside the `IndustriesSettings` settings file (NOT ORG_PREFERENCES). Write via `PUT /services/data/v68.0/headless/metadata` (see SKILL.md **Domain & Feature Toggle Write Path**). All are one-way (`false → true` only).

| Feature | `IndustriesSettings` field |
|---------|----------------------------|
| Education Cloud (Foundation) | `enableEducationCloud` |
| Student Success | `enableStudentSuccess` |
| Academic Operations | `enableAcademicOperations` |
| Mentoring | `enableMentoring` |
| Alumni Relations | `enableAlumniRelations` |
| Recruitment & Admissions | `enableRNADynamicApplications` |
| Student Management | `enableStudentManagement` |
| Financial Aid | `enableFinancialAid` |
| Fundraising | `enableFundraising` |
| Corporate Relations | `enableCorporateRelations` |
| Outcomes | `enableOutcomes` |
| Program Cohorts | `enableProgramCohorts` |
| Student Goals | `enableStudentGoals` |
| Care Plans | `enableCarePlansPreference` (NOT `enableCarePlans` → `FIELD_INTEGRITY_EXCEPTION`); verify `IsCarePlansPreferenceEnabled` |
| Support Programs — Benefit Management | `enableBenefitManagementPreference` |
| Support Programs — Benefit/Goal Sharing | `enableBenefitAndGoalSharingPref` |
| Support Programs — Assign w/ inactive enrollment | `allowBenefitAssignmentWithInactiveProgramEnrollment` |
| Scheduler — Event Management | `enableEventManagementOrgPref` |
| Scheduler — Share SA with AR | `enableShareSaWithArOrgPref` |
| Academic Operations | `enableAcademicOperations`; verify `IsAcademicOperationsEnabled` |
| Validate Pathway Selections | `enablePathwayPlannerRealTimeValidation`; verify `IsPathwayPlannerRealTimeValidationEnabled` |
| Advanced Academic Operations | `enableEduAdvncdAcadOper`; verify `IsEduAdvncdAcadOperEnabled` (needs Adv Acad Ops PSL + BRE/quota — see Step 5) |
| Enforce Time Conflicts | `enableCosConflicts`; verify `IsCosConflictsEnabled` |

(~28 `enableXXX` fields total on `IndustriesSettings`.)

**Records (not toggles) — created via sObject/Tooling POST:**

| Record | Endpoint / shape | Gotcha |
|--------|------------------|--------|
| Support Process | `POST sobjects/BusinessProcess {Name, TableEnumOrId:"Case", Description}` | Do NOT send `IsActive` (INVALID_FIELD_FOR_INSERT_UPDATE); active by default |
| Case Record Type | `POST tooling/sobjects/RecordType {FullName:"Case.X", Metadata:{label,active,businessProcess,description}}` | `businessProcess` = BP **Name**; profile perms NOT applied via API |
| Case Team Template | `POST sobjects/CaseTeamTemplate {Name, Description}` | Prereq for SuccessTeam; reference by **Name** |
| Success Team | `POST sobjects/SuccessTeam {Name, CaseRecordTypeId, DefaultUnassignedCaseTeam, IsActive}` | `IsActive` IS writable; `DefaultUnassignedCaseTeam` = CaseTeamTemplate Name |

---

