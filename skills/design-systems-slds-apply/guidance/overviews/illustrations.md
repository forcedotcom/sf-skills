---
id: slds.guidance.overview.illustrations
title: Illustrations Overview
description: Foundational guidance for implementing illustrations in SLDS interfaces
summary: "Comprehensive illustration guidance covering empty states, informational states, and error states. Includes placement rules, sizing guidelines, accessibility requirements, and the one-illustration-per-page principle."

artifact_type: overview
domain: overviews
topic: illustrations

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.accessibility.overview

tags: [illustrations, empty-states, visual-design, user-experience]
keywords: [illustrations, empty states, error states, informational states, visual messaging, actionable guidance]
---

# Illustrations Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and guidance for implementing illustrations in Salesforce Lightning Design System. When working with SLDS components and interfaces, follow these guidelines to ensure illustrations are used purposefully to enhance clarity, personality, and user engagement.

---

## About Illustrations

Illustrations are engaging visuals that guide, inform, and delight users. In the Salesforce Lightning Design System (SLDS), they help communicate complex ideas, reinforce brand identity, and guide users through key moments in their journey. Illustrations are approachable and inclusive, reflecting the diversity of our users while aligning with the Salesforce brand.

**Key Requirement:** To ensure accessibility best practices, illustrations must always enhance the textual content, not replace it. Use them sparingly and align with the purpose and tone of the screen or message.

---

## Core Principles

When working with illustrations in UI interfaces, adhere to these four foundational principles:

1. **Prioritize clarity and purpose.** Illustrations should soften negative impressions and provide context. Use them to help users understand the state of the system or to guide them through a workflow.
2. **Accessibility is mandatory.** Illustrations must enhance textual content, never replace it. Always provide meaningful text alongside illustrations to ensure the experience is accessible to all users.
3. **Maintain visual restraint.** Use illustrations sparingly to avoid distracting users. Follow the "one illustration per page" rule to maintain focus on the primary task.
4. **Include actionable guidance.** Pair illustrations with clear, actionable UI text. If a page is empty, provide a link or button to help the user take the next step.

---

## Illustration Types

Illustrations in SLDS generally communicate one of three conditions: empty, informational, or error. The specific illustration and accompanying text vary depending on the context.

### Empty States
Empty state illustrations provide context when a page or component has no data to display.

**Use for:**
- Empty object list views (opportunities, leads, cases, contacts)
- Empty feeds (activity feeds, Chatter feeds)
- Empty dashboards or reports
- Blank canvas states requiring user action

### Informational
Informational illustrations support users as they explore new features, learn workflows, or encounter maintenance states.

**Use for:**
- System maintenance or scheduled downtime
- Authentication or connection prompts
- Onboarding and setup workflows
- Feature discovery or walkthrough introductions

### Error States
Error state illustrations offer reassurance and guidance when something goes wrong.

**Use for:**
- Page not found (404 errors)
- Access denied or permission errors
- Data unavailable or loading failures
- Lightning Experience compatibility issues
- Broken links or deleted content
- System failures or service disruptions

---

## Mobile Guidelines

When using illustrations on mobile devices, adjustments are necessary to ensure a consistent experience within smaller viewports.

- **Maximum Width:** 300px
- **Maximum Height:** 180px
- **UI Text:** Labels and body text must be shorter and use smaller font scales.

---

## Layouts

Illustrations can surface within Salesforce products in three primary layout contexts:

### Full Page
Used for major system states like 404 errors or initial onboarding where the illustration is the primary focus of the entire viewport.

### Main Body
Used within the main content area of a page, often for empty states in list views or dashboards.

### Panel or Sidebar
Used in narrower containers like utility panels, sidebars, or docked composers.

---

## Recommended Specs

The following specifications define the typography and sizing constraints for illustrations across desktop and mobile platforms.

### Desktop Specs

| Description | Styling Hooks | Value |
|-------------|---------------|-------|
| Title text | `--slds-g-font-scale-4` | - |
| Body text | `--slds-g-font-scale-2` | - |
| Text color | `--slds-g-color-on-surface-1` | - |
| Maximum image width | - | 600px |
| Maximum image height | - | 360px |

### Mobile Specs

| Description | Styling Hooks | Value |
|-------------|---------------|-------|
| Title text | `--slds-g-font-scale-3` | - |
| Body text | `--slds-g-font-size-base` | - |
| Text color | `--slds-g-color-on-surface-1` | - |
| Maximum image width | - | 300px |
| Maximum image height | - | 180px |

---

## UI Text Guidelines

UI text for illustrations must be clear, concise, and helpful. While these examples serve as guidelines, text should always be adapted to the specific context.

| State | Title | Body |
|-------|-------|------|
| Empty | Hmm… | No opportunities to display. |
| Empty | Collaborate with others | No updates here yet. |
| Informational | We are down for maintenance | Sorry for the inconvenience. We’ll be back shortly. |
| Informational | You’re not connected to Google Drive | Let’s get you authenticated. [Connect to Google Drive] |
| Error | Page not available | Maybe the page was deleted, the URL is incorrect, or something else went wrong. |
| Error | You don’t have access to this page | If you think you should have access, ask your admin for help. |
| Error | Data not available | The data you’re trying to access isn’t available. It might be due to a system error. |

---

## Usage and Best Practices

### Recommended Usage (Where & Why)

Illustrations are used to enhance scannability and provide visual context in specific scenarios. They are typically implemented in:

- **Empty states:** To provide context and reduce the "dead end" feeling of a blank page, guiding users on how to populate data (e.g., list views, dashboards).
- **Informational moments:** To support users during system maintenance, exploration of new features, or onboarding/setup workflows.
- **Error states:** To soften the impact of system failures or restricted access and provide a clear path forward (e.g., 404 pages, lack of permissions).
- **Feeds:** To encourage collaboration within activity or Chatter feeds.

### Implementation Constraints

To maintain SLDS visual consistency and performance, adhere to these constraints:

- **One per page:** Use only one illustration per page. Multiple illustrations create visual clutter and distract from the primary task.
- **Avoid small containers:** Do not use illustrations inside related lists, cards, or narrow components. Use plain inline text or icons for these areas.
- **No direct action feedback:** Do not use illustrations as feedback for direct user actions. Toasts, popovers, or banners are better suited for these interactions.

### Visual Standards

#### Character Positioning

Characters add personality but must not dominate the visual hierarchy of an illustration.

#####  Do

- Keep characters in the background to maintain focus on the message and system state.
- Integrate characters as supporting elements that enhance the context without becoming the primary focal point.

#####  Don't

- Avoid placing characters at the forefront of an illustration, as it can distract from the functional purpose of the screen.
- Never use characters as the sole indicator of the illustration's meaning.

---

## Implementation Workflow

Follow this sequence when implementing illustrations in your components:

### Step 1: Identify Illustration Need
Determine the state you are communicating:
- **Is the container empty?** (list views, feeds, dashboards)
- **Is the state informational?** (maintenance, onboarding, configuration)
- **Is there an error?** (page not found, no access, system failure)

### Step 2: Select Illustration Type
Choose an illustration that matches the tone and purpose identified in Step 1. Ensure the visual style is consistent with SLDS standards.

### Step 3: Apply Recommended Specs
Use the appropriate styling hooks for typography and respect the maximum dimensions for the target platform (Desktop vs. Mobile).

### Step 4: Add Accompanying UI Text
Write clear, concise, and actionable text. Ensure the body text includes a resolution path (e.g., a link to create a record or contact support).

### Step 5: Validate Accessibility
Ensure the illustration enhances the text and that all essential information is available via text. Verify that the layout works across different screen sizes and density settings.

---

## Pre-Implementation Checklist

Before finalizing any illustration implementation, verify:

| Requirement | Status |
|-------------|--------|
| **Classification & Selection** | |
| Illustration type matches the system state (empty/informational/error) | [ ] |
| Illustration chosen aligns with Salesforce approachable/inclusive brand | [ ] |
| **Styling & Specs** | |
| Typography uses recommended styling hooks (`--slds-g-font-scale-*`) | [ ] |
| Maximum dimensions respected for target platform (600x360 desktop, 300x180 mobile) | [ ] |
| One illustration per page limit maintained | [ ] |
| **Content & Copy** | |
| UI text provides clear title and helpful body content | [ ] |
| Actionable resolution path provided (e.g., links or buttons) | [ ] |
| **Accessibility** | |
| Illustration enhances rather than replaces textual content | [ ] |
| Sufficient contrast between text and background | [ ] |
| **Context & Placement** | |
| Layout context correctly identified (full page, main body, panel) | [ ] |
| Illustration used outside of related lists and cards | [ ] |

**Target outcome:** Purposeful, engaging illustrations that guide users through the Salesforce experience while maintaining brand consistency and accessibility standards.
