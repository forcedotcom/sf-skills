# Portal Templates Reference

This document describes how to choose the framework and template for a Digital Experience portal.

## Framework: always Experience Builder (Aura or LWR), never Visualforce

Experience Cloud sites come in two families:

- **Experience Builder sites** — built on **Aura** or **LWR** (Lightning Web Runtime). These have the drag-and-drop **Builder**, modern components, branding, and responsive layouts. This is what you want in almost all cases.
- **Salesforce Tabs + Visualforce sites** (a.k.a. the legacy "VF Template") — a standard-nav + Visualforce site with **no Experience Builder**. This is legacy. Do **not** create these for new portals.

**How to tell them apart:** the Metadata API `Network.enableSiteAsContainer` field is `true` for an Experience Builder site and `false` for a Salesforce Tabs + Visualforce site. In Setup → Digital Experiences → All Sites, the **Framework** column shows `Aura`, `LWR`, or `Visualforce`, and only Builder-based sites show a **Builder** workspace link.

> The bug this reference exists to prevent: creating a portal with `templateName: "VF Template"` (Salesforce Tabs + Visualforce). It produces a Visualforce-framework site with no Builder. Use the self-service site API with `siteType: AURA`, or a `communities` API Experience Builder `templateName`.

---

## Recommended path for employee service / ITSM / help desk portals

**Preferred (richest employee experience): the `Agentforce Employee Center` Aura template via the communities API.** This is a purpose-built employee-service portal — IT and HR ticket management, a self-service catalog, a knowledge base, enablement programs, and (optionally) an embedded **Agentforce** conversational assistant. Prefer it over the plainer `Employee Portal` / `Customer Service` templates whenever the org's live template list (`GET /connect/communities/templates`) includes `Agentforce Employee Center`.

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/communities",
  body:   { "name": "<portal name>", "urlPathPrefix": "<alphanumeric>", "templateName": "Agentforce Employee Center" }
)
```

The communities API takes only `{name, description, templateName, templateParams, urlPathPrefix}` — pass `Agentforce Employee Center` verbatim as `templateName`. This path needs **no** MIAW Embedded Service Deployment.

> **Two layers.** `POST /connect/communities` with `templateName: "Agentforce Employee Center"` provisions the **site** (pages, ticketing, catalog, knowledge). The **conversational assistant** is a *separate* Agentforce agent — the site alone does not create one. To add it, create the internal employee agent from its shipped template (see "Agentforce assistant" below); this skill provisions the site and points the user to that step. It does **not** activate an agent automatically.

### Alternative paths (when Agentforce Employee Center is not desired or not present)

- **MIAW at creation time + a guest ESD exists →** `POST /connect/self-service/site` with `siteType: "AURA"`. This deploys an Aura Experience Builder site and wires **MIAW** in at creation time via Embedded Service Deployment (ESD) config IDs. Key inputs: `siteName` (required); `guestEmbeddedServiceConfigId` (required) — guest MIAW ESD; `embeddedServiceConfigId` (optional) — authenticated MIAW ESD; `siteType` — `AURA` (default) or `LWR`; plus `enableForGuest`, `contentDocumentId` (logo), `brandColors` (optional).
- **A plainer employee portal, no Agentforce, no MIAW →** communities API with `Employee Portal` (if present), else `Customer Service` or `Help Center`. Needs no ESD.

> Note: an internal "ITSM Employee Service" seed template exists as an org/feature template for the ITSM product (associated with CMDB and the `ItSrvcDscvrMgrPsl` permission set license). That is **not** a `templateName` value for `POST /connect/communities` — do not pass it as `templateName`.

---

## Agentforce assistant for the Employee Center (optional, separate step)

The `Agentforce Employee Center` site can host an **Agentforce** conversational assistant, but the site-create call does not build one. The agent is created from a template that ships with the org:

```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/headless/invoke/einstein/genai-agentbuilder/create-copilot-from-template",
  body:   {
    "templateNameOrId": "EmployeeCopilot__AgentforceEmployeeAgent",
    "copilotContext": { "name": "<agent label>", "company": "<company name>", "newAgentUser": true }
  }
)
```

- `templateNameOrId` — `EmployeeCopilot__AgentforceEmployeeAgent` is the shipped **internal employee** agent template (the service-agent equivalent is `SvcCopilotTmpl__EinsteinServiceAgent`).
- `copilotContext.company` is **required** — omitting it returns `500 CONTROLLER_ERROR "Company is Mandatory in Agents"`. `companyName` is a distinct, non-substitute field.
- The agent is created **`Inactive`** with a v1 version; it must be activated and connected to the site's channel afterward. `newAgentUser: true` auto-provisions a runtime user.
- The Experience Builder AI-portal editor lists attachable agents via `GET /services/data/v67.0/headless/invoke/platform/communities/unified-aiportal-setup/get-service-agent-templates`.

> Agentforce setup (agent creation, activation, channel wiring, permissions) is broad and largely out of scope for this portal-create skill. This skill provisions the **site** and, when the user wants the conversational assistant, points them to the agent template above rather than fully configuring Agentforce.

---

## Community Templates (`POST /connect/communities`)

The communities API accepts an Experience Builder **display name** as `templateName`. Accepted strings can vary by org edition/version — **always validate against the live list** via headless-360:

```text
mcp__headless-360__dispatch_readonly(method: "GET", url: "/services/data/v67.0/connect/communities/templates")
```

Use a returned `templateName` verbatim. The most common Experience Builder templates:

### Agentforce Employee Center (preferred for employee service)
**Template name:** `Agentforce Employee Center` &nbsp;·&nbsp; **Framework:** Aura &nbsp;·&nbsp; **Publisher:** Salesforce

The richest employee-service template: **IT and HR ticket management**, a **self-service catalog**, a **knowledge base**, **enablement programs**, and an optional embedded **Agentforce** conversational assistant. This is the modern successor to the plainer `Employee Portal` / `Customer Service` experiences for internal help desks. Not Visualforce (`siteAsContainerEnabled = true`).

**Use when:** Building an employee service / IT help desk / HR service portal and the org's live template list (`GET /connect/communities/templates`) includes `Agentforce Employee Center`. Prefer it over `Employee Portal` and `Customer Service` for this use case.

**Note:** The `POST /connect/communities` call provisions the site only. The Agentforce conversational assistant is a **separate** step — create it from the `EmployeeCopilot__AgentforceEmployeeAgent` template (see "Agentforce assistant for the Employee Center" above). Do not assume the site-create call activates an agent.

---

### Employee Portal
**Template name:** `Employee Portal` &nbsp;·&nbsp; **Framework:** Aura

Purpose-built Aura Experience Builder template for **employee service / internal self-service** portals (IT help desk, HR service, ITSM). A plainer alternative to `Agentforce Employee Center` — use it when the richer Agentforce template is not present or not wanted. Not Visualforce (`siteAsContainerEnabled = true`).

**Use when:** Building an employee-facing service/self-service portal via the communities API without a pre-existing MIAW Embedded Service Deployment (the self-service site API requires a guest ESD; this template does not), and `Agentforce Employee Center` is unavailable or undesired.

---

### Customer Service (formerly "Napili")
**Template name:** `Customer Service` &nbsp;·&nbsp; **Framework:** Aura &nbsp;·&nbsp; internal developerName: `Service Community Template`

The main Aura self-service template: Knowledge articles, case deflection, case management, community/Q&A. Mobile-responsive.

**Use when:** Building a self-service support community for customers or employees.

> Do not pass the legacy brand name `Napili` or a snake_case guess like `customer_service`. The current API display value is `Customer Service`.

---

### Help Center
**Template name:** `Help Center` &nbsp;·&nbsp; **Framework:** Aura &nbsp;·&nbsp; internal developerName: `Help Center Template`

Public / self-service knowledge + case deflection help center. More focused on knowledge and deflection than the fuller Customer Service community.

**Use when:** Building a knowledge-first help center or an IT help desk self-service experience.

---

### Customer Account Portal
**Template name:** `Customer Account Portal` &nbsp;·&nbsp; **Framework:** Aura &nbsp;·&nbsp; internal developerName: `CPT Community Template`

Authenticated account self-service — view/pay invoices, manage account, access records.

**Use when:** Building an authenticated portal for customers to manage their account.

---

### Partner Central
**Template name:** `Partner Central` &nbsp;·&nbsp; **Framework:** Aura &nbsp;·&nbsp; internal developerName: `PRM Community Template`

Partner Relationship Management — channel sales, deal registration, lead distribution, partner account management.

**Use when:** Building a partner portal via the communities API (as opposed to the dedicated PRM API).

---

### Build Your Own
**Template name:** `Build Your Own` &nbsp;·&nbsp; **Framework:** Aura &nbsp;·&nbsp; internal developerName: `Starter Template`

Blank Aura starting point — full control over pages and components.

**Use when:** You want a custom Aura site without pre-built self-service pages.

---

### Build Your Own (LWR)
**Template name:** `Build Your Own (LWR)` &nbsp;·&nbsp; **Framework:** LWR &nbsp;·&nbsp; internal developerName: `talon-template-byo`

Blank modern Lightning Web Runtime site — fast, headless-friendly.

**Use when:** You want the most modern, performant framework and are comfortable building from a blank canvas.

---

### Microsite (LWR)
**Template name:** `Microsite (LWR)` &nbsp;·&nbsp; **Framework:** LWR &nbsp;·&nbsp; internal developerName: `microsite-template-marketing`

Lightweight LWR marketing microsite.

**Use when:** Building a small, fast marketing site.

---

### Legacy: Salesforce Tabs + Visualforce ("VF Template") — DO NOT USE
**Template name:** `Salesforce Tabs + Visualforce`

A standard-nav + Visualforce site with **no Experience Builder**. This is the source of the "created as Visualforce" bug. Not an Experience Builder site (`enableSiteAsContainer = false`). Avoid for all new portals.

---

## PRM Templates (`POST /connect/prm/setup/sites`)

PRM templates are org-specific and vary by:
- PRM package version installed
- Org configuration
- Industry-specific templates
- Custom templates added by admins

### How to Find Available PRM Templates

1. **Via headless-360:** the Aura PRM templates (`Partner Central`, `Partner Central (Enhanced)`) also appear in `mcp__headless-360__dispatch_readonly(method: "GET", url: "/services/data/v67.0/connect/communities/templates")`. Dedicated PRM-only templates are org-specific.
2. **Via Setup UI:** Setup → Digital Experiences → Settings → Partner Templates. Note the exact names (case-sensitive).
3. **Common names:** `Partner Central`, `Channel Management`, plus custom templates (varies by org).

**Important:** Template names are case-sensitive and must match exactly. If unsure, check the Setup UI or ask the user.

Alternatively, if the org does not have PRM enabled, build a partner portal via the communities API with the `Partner Central` template.

---

## MIAW (Messaging for In-App and Web)

- The **self-service site API** wires MIAW in at creation time via `guestEmbeddedServiceConfigId` / `embeddedServiceConfigId`. This is the recommended path when the portal needs messaging.
- For **general communities** (`POST /connect/communities`), MIAW is **not** part of the create call. Configure it separately — create a Messaging Channel + Embedded Service Deployment (Setup → Embedded Service Deployments), then add the Embedded Service (Messaging) component to the site's pages in Experience Builder.
- Embedded Service Deployments must **pre-exist**; this skill does not create them.

---

## Template Parameters (`templateParams`)

The `templateParams` object on the communities API accepts template-specific configuration. Parameters vary by template and are not well-documented.

**Best practice:** For standard Experience Builder templates (`Customer Service`, `Help Center`, `Partner Central`), omit `templateParams` unless you need specific customization — the defaults work well. To discover parameters, create a test site via the UI and inspect the resulting Network/ExperienceBundle metadata.

---

## Template Selection Guide

All rows dispatch through `mcp__headless-360__dispatch` / `dispatch_readonly`.

| Requirement | API | Framework | Template / `siteType` |
|-------------|-----|-----------|-----------------------|
| Employee service / ITSM / HR / help desk (richest; Agentforce-ready) | `communities` | Aura | `Agentforce Employee Center` |
| Employee service / ITSM / help desk (with MIAW, guest ESD exists) | `self-service/site` | Aura | `siteType: AURA` |
| Employee service / ITSM / help desk (plainer, no Agentforce / no MIAW) | `communities` | Aura | `Employee Portal` (fallback `Customer Service`) |
| Customer support / self-service community | `communities` | Aura | `Customer Service` |
| Knowledge base / case deflection | `communities` | Aura | `Help Center` |
| Authenticated account self-service | `communities` | Aura | `Customer Account Portal` |
| Partner portal (with PRM) | `prm/setup/sites` | Aura | Org-specific PRM template |
| Partner portal / channel (no PRM) | `communities` | Aura | `Partner Central` |
| Custom Aura site | `communities` | Aura | `Build Your Own` |
| Modern blank / headless-friendly site | `communities` | LWR | `Build Your Own (LWR)` |
| Marketing microsite | `communities` | LWR | `Microsite (LWR)` |

---

## Template Customization Post-Creation

After portal creation, customize via:

1. **Experience Builder** — visual page builder. Setup → Digital Experiences → [Your Site] → **Builder**. Drag-and-drop components, layouts, styling.
2. **Branding Editor** — colors, fonts, logo. Builder → Settings → Theme/Branding.
3. **Pages** — create or override pages in Builder.
4. **Custom components** — develop LWC (or Aura) components, deploy, and add them via Builder.

**Note:** Initial framework/template selection sets the foundation, but extensive customization is possible post-creation.

---

## Version Compatibility

### API Version Notes
- All calls go through `mcp__headless-360__dispatch` / `dispatch_readonly`, which do **not** resolve the API version — pass the full `/services/data/vXX.0` prefix in every `url` (e.g. `url: "/services/data/v67.0/connect/communities"`).
- **v67.0 (Summer '26)** is the current/latest API version verified against a live test org at time of writing.
- `POST /connect/self-service/site` is available in recent versions (min-version 262).
- `GET /connect/communities/templates` is available v46.0+.
- `POST /connect/communities` is available v48.0+.

### Framework guidance
- **Aura Experience Builder templates** (Customer Service, Help Center, Customer Account Portal, Partner Central, Build Your Own) — current best practice for most portals.
- **LWR templates** (Build Your Own (LWR), Microsite (LWR)) — the most modern framework; prefer for greenfield custom or headless-friendly sites.
- **Salesforce Tabs + Visualforce** ("VF Template") — legacy; **do not use** for new portals.
- **Deprecated templates** (e.g. Kokua, Koa) — avoid.

**Best practice:** For employee service / ITSM / HR / help-desk portals, prefer the **`Agentforce Employee Center`** Aura template via the communities API — it ships the fullest employee experience (ticketing, catalog, knowledge, Agentforce-ready). Fall back to the self-service site API with `siteType: AURA` when the portal needs MIAW wired in at creation time and a guest ESD exists, or to the `Employee Portal` template (then `Customer Service`) when a plainer, non-Agentforce site is wanted. Use `Customer Service` (or `Help Center`) for customer self-service communities. Always validate exact `templateName` strings via `mcp__headless-360__dispatch_readonly(method: "GET", url: "/services/data/v67.0/connect/communities/templates")` in the target org — template availability varies by edition/version. The Agentforce conversational assistant is a separate step (`EmployeeCopilot__AgentforceEmployeeAgent`).
