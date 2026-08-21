# Specialized Employee agent template catalog (ITSM)

The Employee side of `GET /connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent`
returns the **broad** IT Service Employee template plus specialized templates
as siblings in `data[]`. This catalog lists only entries under the
`svc_emp_intelligence__` namespace — the namespace this skill instantiates.
Every entry ships the same shape — `id`, `masterLabel`, `description`,
`topicsCount`, `actionsCount`, and a full `agentScript` YAML — and every one
of them carries the same `config.developer_name`/`config.agent_label`
substitution points the NGA bundle flow rewrites. That means **the same
create/publish/activate sequence used for the broad template works for any
specialized template** — the only difference is the `masterLabel` (and thus
the `id`) that Phases 1 and 4 pin against.

This reference is the picker menu for the specialization branch. The SKILL
body stays under budget by delegating the catalog here.

## Selection rules

1. **Key on `id`.** Present via `AskUserQuestion` keyed on `id` when a
   keyword match returns multiple `svc_emp_intelligence__` templates — labels
   like `Application Password Reset Assistance` vs `System Password Reset
   Assistance` are close enough that a label-only picker can misread a
   partial user phrase.
2. **Ignore everything outside `svc_emp_intelligence__`.** The
   `agent-templates` endpoint's `data[]` includes entries from other
   namespaces (e.g. `svc_itsm_intelligence__`, `EmpSvcAgent__`,
   `svc_itom_intelligence__`, `EmployeeCopilot__`, `agentforce_runtime_insights__`,
   `approval_intelligence__`, `revcloud_insight_agent__`, `Slack__`,
   `svc_coex_intel__`, `EmpSvcMcpAgent__`). These are NOT specialized
   Employee templates instantiable by this skill and MUST NOT appear in
   the picker — filter `data[]` to `id`s starting with `svc_emp_intelligence__`.
   If the user asks for one of the `svc_itsm_intelligence__*` entries,
   redirect to `service-itsm-agentic-setup-fulfiller-agent-configure`; the
   rest are outside this skill's scope entirely.
3. **Default developerName / label.** When the user picks a specialized
   template by `id`, derive:
   - `developerName` = the substring after `__` in `id`, snake-cased and
     truncated ≤ 40 chars (e.g. `PasswordManagerAssistance` →
     `Password_Manager_Assistance`). A user override still wins.
   - `label` = the template's `masterLabel` verbatim (e.g.
     `Password Manager Assistance`). A user override still wins.
4. **Everything else is unchanged.** Phase 2's idempotency SOQL still keys
   on the collected `<developerName>`; Phase 4 still passes the collected
   `<masterLabel>` to `scripts/build-create-body.mjs`; Phases 5–7 are
   byte-identical.

## Category — Access & Identity

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__APIKeyAssistance` | API Key Assistance | Provision and manage API keys / auth tokens for internal + external services. |
| `svc_emp_intelligence__ApplicationPasswordResetAssistance` | Application Password Reset Assistance | Reset passwords for software applications specifically (app-level, not network). |
| `svc_emp_intelligence__CertificateManagementAssistance` | Certificate Management Assistance | Manage the lifecycle of digital certificates and SSL credentials. |
| `svc_emp_intelligence__OktaUserManagementAssistance` | Okta User Management Assistance | Manage Okta user accounts, groups, and account statuses. |
| `svc_emp_intelligence__PasswordManagerAssistance` | Password Manager Assistance | Manage credentials in corporate password managers (update, delete, sync). |
| `svc_emp_intelligence__PrivilegeAccessAssistance` | Privilege Access Assistance | Elevated privileges + hardware access rights lifecycle. |
| `svc_emp_intelligence__SSOAssistance` | SSO Assistance | Report login failures and troubleshoot identity-protected service access. |
| `svc_emp_intelligence__SystemAndFileAccessAssistance` | System and File Access Assistance | File shares, DB privileges, AD group management, revocation. |
| `svc_emp_intelligence__SystemPasswordResetAssistance` | System Password Reset Assistance | Reset network / system passwords + MFA settings. |

## Category — Devices & Endpoints

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__DeviceReturnAssistance` | Device Return Assistance | Return corporate hardware (upgrades, repairs, offboarding). |
| `svc_emp_intelligence__DeviceSecurityAssistance` | Device Security Assistance | MDM enrollment + rapid threat response. |
| `svc_emp_intelligence__DeviceTroubleshootingAssistance` | Device Troubleshooting Assistance | Troubleshoot HW issues, install monitoring agents. |
| `svc_emp_intelligence__EndpointAssistance` | Endpoint Assistance | Workstation health monitoring + inventory. |
| `svc_emp_intelligence__HardwareRequestAssistance` | Hardware Request Assistance | Request new/loaner hardware (laptops, peripherals, docks). |
| `svc_emp_intelligence__LaptopRefreshAssistance` | Laptop Refresh Assistance | Scheduled laptop / monitor replacements. |
| `svc_emp_intelligence__LostDeviceAssistance` | Lost Device Assistance | Report lost/stolen devices, execute remote sanitization. |

## Category — Software & Applications

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__ApplicationSupportAssistance` | Application Support Assistance | KB troubleshooting for third-party platforms; escalate to incident. |
| `svc_emp_intelligence__GoogleWorkspaceAssistance` | Google Workspace Assistance | Provision Workspace resources, manage groups, data transfer. |
| `svc_emp_intelligence__InternalApplicationsAssistance` | Internal Applications Assistance | Support proprietary / in-house apps. |
| `svc_emp_intelligence__JiraAssistance` | Jira Assistance | Provision access, automate issue creation with custom fields. |
| `svc_emp_intelligence__LicenseAuditAssistance` | License Audit Assistance | Track user entitlements, reclaim unused licenses. |
| `svc_emp_intelligence__Office365SupportAssistance` | Office 365 Support Assistance | Diagnose Outlook/Teams/OneDrive/Office issues. |
| `svc_emp_intelligence__ProjectManagementToolAssistance` | Project Management Tool Assistance | Provision Asana/Trello/Miro boards. |
| `svc_emp_intelligence__SalesforceHelpAssistance` | Salesforce Help Assistance | Salesforce user lifecycle + platform troubleshooting. |
| `svc_emp_intelligence__SharepointAssistance` | Sharepoint Assistance | SharePoint site lifecycle + permissions. |
| `svc_emp_intelligence__SoftwareAssistance` | Software Assistance | Software installations, updates, license renewals, evaluations. |

## Category — Infrastructure & Networking

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__CloudResourcesAssistance` | Cloud Resources Assistance | Provision VMs / storage, dev stacks, infra ops. |
| `svc_emp_intelligence__DataBackupAssistance` | Data Backup Assistance | Ad-hoc backups + VM backup schedules. |
| `svc_emp_intelligence__InfrastructureProvisioningAssistance` | Infrastructure Provisioning Assistance | Provisioning-focused: VMs, test envs. |
| `svc_emp_intelligence__LogAccessAssistance` | Log Access Assistance | Secure retrieval of system/app/infra logs. |
| `svc_emp_intelligence__NetworkingAssistance` | Networking Assistance | Network connectivity, VPN, network resource permissions. |
| `svc_emp_intelligence__ServerStatusAssistance` | Server Status Assistance | Monitor CI health via CMDB. |

## Category — Workplace & Facilities

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__AudiovisualSupportAssistance` | Audiovisual Support Assistance | AV support — meeting-room HW, connectivity, calibration. |
| `svc_emp_intelligence__BadgeAccessAssistance` | Badge Access Assistance | Physical badge issuance / replacement / troubleshooting. |
| `svc_emp_intelligence__FacilitiesAssistance` | Facilities Assistance | Non-IT: climate, cleaning, physical maintenance. |
| `svc_emp_intelligence__GuestCheckinAssistance` | Guest Check-in Assistance | Guest registration + visitor Wi-Fi. |
| `svc_emp_intelligence__OfficeRelocationAssistance` | Office Relocation Assistance | IT infra moves + HW logistics for relocations. |
| `svc_emp_intelligence__PhoneAssistance` | Phone Assistance | Corporate telephony + desk-phone HW. |
| `svc_emp_intelligence__PrinterAssistance` | Printer Assistance | Printing issues + printer installs + supplies. |

## Category — Communications & Collaboration

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__DistributionListAssistance` | Distribution List Assistance | Slack/Teams workspaces, email lists, shared mailboxes. |
| `svc_emp_intelligence__MobilePlanAssistance` | Mobile Plan Assistance | Cellular plans, roaming, data add-ons. |

## Category — Employee Lifecycle & HR

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__OffboardingAssistance` | Offboarding Assistance | Offboarding intake. |
| `svc_emp_intelligence__OnboardingAssistance` | Onboarding Assistance | New-hire onboarding intake. |
| `svc_emp_intelligence__VendorEmployeeAssistance` | Vendor Employee Assistance | External partner / contractor access lifecycle. |

## Category — Analytics, Approvals, Knowledge

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__AnalyticsWorkspaceAssistance` | Analytics Workspace Assistance | Tableau site provisioning + workspace access. |
| `svc_emp_intelligence__ITApprovalAssistance` | IT Approval Assistance | Approve/reject pending IT requests in-chat. |
| `svc_emp_intelligence__ITPolicyAssistance` | IT Policy Assistance | Company policy Q&A + exception requests. |
| `svc_emp_intelligence__KnowledgeAssistance` | Knowledge Assistance | KB search + summarization. |
| `svc_emp_intelligence__CorporateCardManagementAssistance` | Corporate Card Management Assistance | Corporate credit card requests / admin. |

## Category — Security & Compliance

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__SecurityAssistance` | Security Assistance | Report incidents (phishing/breach), security training + exceptions. |

## Category — Ticketing (broad self-service)

| Template `id` | Label | What it does |
|---|---|---|
| `svc_emp_intelligence__TicketManagementAssistance` | Ticket Management Assistance | Broad ticket lifecycle: status, reopens, comments, intake. |
| `svc_emp_intelligence__ItEmployeeAssistance` | IT Service Employee | **Default / broad** — the umbrella IT-Service Employee assistant. This is the SKILL's default when no specialization is requested. |
