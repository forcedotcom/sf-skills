<!-- Parent: generating-visual-diagrams/SKILL.md -->
# Interview Questions Reference

This document defines the questions Claude should ask (via `AskUserQuestion`) before generating images with generating-visual-diagrams.

---

## How to Use This Reference

When a user requests an image, Claude should:

1. **Detect image type** from the request
2. **Find the matching question set** below
3. **Invoke AskUserQuestion** with those questions
4. **Build prompt** using the answers
5. **Generate image** with optimized parameters

### Skip Interview Triggers

Skip questions and use defaults when user says:
- "quick" - e.g., "Quick ERD of Account-Contact"
- "simple" - e.g., "Simple LWC mockup"
- "just generate" - e.g., "Just generate an architecture diagram"
- "fast" - e.g., "Fast ERD draft"

---

## ERD Diagram Questions

### When to Use
User mentions: ERD, entity relationship, data model, object relationships, schema diagram

### Questions

```json
{
  "questions": [
    {
      "question": "Which objects should be included in the ERD?",
      "header": "Objects",
      "multiSelect": false,
      "options": [
        {
          "label": "Core CRM (Recommended)",
          "description": "Account, Contact, Opportunity, Case - standard sales/service objects"
        },
        {
          "label": "Sales Cloud",
          "description": "Lead, Campaign, Quote, Order, PriceBook, Product"
        },
        {
          "label": "Service Cloud",
          "description": "Case, Knowledge, Entitlement, Asset, ServiceContract"
        },
        {
          "label": "Custom objects",
          "description": "I'll specify the custom objects to include"
        }
      ]
    },
    {
      "question": "What visual style do you prefer?",
      "header": "Style",
      "multiSelect": false,
      "options": [
        {
          "label": "Architect.salesforce.com (Recommended)",
          "description": "Official Salesforce style: dark border + light fill, header banner, legend bar"
        },
        {
          "label": "Whiteboard",
          "description": "Hand-drawn look, casual feel for brainstorming"
        },
        {
          "label": "Technical",
          "description": "Detailed with field names and data types"
        },
        {
          "label": "Minimalist",
          "description": "Simple boxes, focus on relationships only"
        }
      ]
    },
    {
      "question": "What's the primary purpose of this ERD?",
      "header": "Purpose",
      "multiSelect": false,
      "options": [
        {
          "label": "Documentation (4K)",
          "description": "High quality for wikis, docs, long-term reference"
        },
        {
          "label": "Quick draft (1K)",
          "description": "Fast iteration, refine the prompt first"
        },
        {
          "label": "Presentation",
          "description": "Slides for stakeholders, clean and simple"
        },
        {
          "label": "Architecture review",
          "description": "Technical discussion with developers/architects"
        }
      ]
    },
    {
      "question": "Any special requirements? (Select all that apply)",
      "header": "Extras",
      "multiSelect": true,
      "options": [
        {
          "label": "Include legend",
          "description": "Add a legend explaining colors and relationship types"
        },
        {
          "label": "Show field names",
          "description": "Display key fields inside each object box"
        },
        {
          "label": "Color-code by type",
          "description": "Standard=blue, Custom=orange, External=green"
        },
        {
          "label": "None",
          "description": "Use default styling without extras"
        }
      ]
    }
  ]
}
```

### Answer-to-Prompt Mapping

| Answer | Prompt Addition |
|--------|-----------------|
| Core CRM | "Account, Contact, Opportunity, Case with standard relationships" |
| Sales Cloud | "Lead, Campaign, Quote, Order, PriceBook, Product with conversion flows" |
| Service Cloud | "Case, Knowledge, Entitlement, Asset, ServiceContract hierarchy" |
| Architect.salesforce.com | "Official architect.salesforce.com style: page title, header banner with Salesforce logo, LEGEND bar (ENTITIES + RELATIONSHIPS), dark border + light translucent fill boxes (~25% opacity), labeled relationship lines, footer with copyright" |
| Whiteboard | "Hand-drawn sketch style, informal, whiteboard aesthetic" |
| Technical | "Include field names, data types, API names in each box" |
| Documentation (4K) | Use Python script with `-r 4K`, include full header + legend |
| Quick draft (1K) | Use CLI or Python with `-r 1K` |
| Include legend | "Include LEGEND bar at top with ENTITIES and RELATIONSHIPS sections" |
| Color-code | "Auto-detect cloud color: Sales=Teal #0B827C, Service=Magenta #9E2A7D, Platform=Purple #5A67D8" |

### Default Values (for Skip Mode)

- Objects: Core CRM
- Style: Architect.salesforce.com
- Purpose: Quick draft (1K)
- Extras: Include legend

---

## LWC Component Mockup Questions

### When to Use
User mentions: LWC, Lightning Web Component, component mockup, wireframe, UI mockup, form, table, card

### Questions

```json
{
  "questions": [
    {
      "question": "What type of component do you need?",
      "header": "Component",
      "multiSelect": false,
      "options": [
        {
          "label": "Data table (Recommended)",
          "description": "List view with columns, sorting, row actions"
        },
        {
          "label": "Record form",
          "description": "Create/edit form with fields and sections"
        },
        {
          "label": "Dashboard card",
          "description": "Metrics, charts, or KPI tiles"
        },
        {
          "label": "Custom layout",
          "description": "I'll describe the specific layout needed"
        }
      ]
    },
    {
      "question": "Which Salesforce object is this for?",
      "header": "Object",
      "multiSelect": false,
      "options": [
        {
          "label": "Account",
          "description": "Customer/company records"
        },
        {
          "label": "Contact",
          "description": "Individual person records"
        },
        {
          "label": "Opportunity",
          "description": "Sales deals and pipeline"
        },
        {
          "label": "Custom object",
          "description": "I'll specify the object name"
        }
      ]
    },
    {
      "question": "Where will this component be used?",
      "header": "Context",
      "multiSelect": false,
      "options": [
        {
          "label": "Lightning Record Page (Recommended)",
          "description": "Embedded on Account, Contact, etc. detail pages"
        },
        {
          "label": "Lightning App Page",
          "description": "Home page, dashboard, or custom app"
        },
        {
          "label": "Experience Cloud",
          "description": "Customer/partner portal (community)"
        },
        {
          "label": "Standalone app",
          "description": "Full-page Lightning app or utility bar"
        }
      ]
    },
    {
      "question": "Style preferences? (Select all that apply)",
      "header": "Style",
      "multiSelect": true,
      "options": [
        {
          "label": "SLDS standard",
          "description": "Standard Lightning Design System styling"
        },
        {
          "label": "Dense/compact",
          "description": "Reduced spacing for data-heavy views"
        },
        {
          "label": "Mobile-responsive",
          "description": "Adapts to mobile screen sizes"
        },
        {
          "label": "Card-based",
          "description": "Elevated card container with shadow"
        }
      ]
    }
  ]
}
```

### Answer-to-Prompt Mapping

| Answer | Prompt Addition |
|--------|-----------------|
| Data table | "Lightning datatable with columns, header with search, row actions menu" |
| Record form | "Lightning record form with sections, field labels, Save/Cancel buttons" |
| Dashboard card | "SLDS card component with metric value, label, trend indicator" |
| Lightning Record Page | "Component sized for record page sidebar or main content" |
| Experience Cloud | "Portal-friendly styling, user-facing design" |
| Dense/compact | "Compact spacing, reduced padding, data-dense layout" |
| Mobile-responsive | "Responsive design, single column on mobile" |

### Default Values (for Skip Mode)

- Component: Data table
- Object: Account
- Context: Lightning Record Page
- Style: SLDS standard

---

## Architecture/Integration Diagram Questions

### When to Use
User mentions: architecture, integration, system diagram, data flow, API flow, authentication flow

### Questions

```json
{
  "questions": [
    {
      "question": "What type of diagram do you need?",
      "header": "Diagram",
      "multiSelect": false,
      "options": [
        {
          "label": "Integration flow (Recommended)",
          "description": "System-to-system data synchronization"
        },
        {
          "label": "Data flow",
          "description": "Entity movement between systems"
        },
        {
          "label": "Authentication flow",
          "description": "OAuth, JWT, SSO sequence diagram"
        },
        {
          "label": "Event-driven",
          "description": "Platform Events, CDC, pub/sub architecture"
        }
      ]
    },
    {
      "question": "Which systems are involved?",
      "header": "Systems",
      "multiSelect": false,
      "options": [
        {
          "label": "Salesforce + ERP",
          "description": "SAP, Oracle, NetSuite, Microsoft Dynamics"
        },
        {
          "label": "Salesforce + Marketing",
          "description": "Marketo, Pardot, HubSpot, Marketing Cloud"
        },
        {
          "label": "Salesforce + Custom APIs",
          "description": "Internal services, microservices, legacy systems"
        },
        {
          "label": "Multiple systems",
          "description": "I'll specify the systems involved"
        }
      ]
    },
    {
      "question": "What protocols/patterns are used? (Select all that apply)",
      "header": "Protocols",
      "multiSelect": true,
      "options": [
        {
          "label": "REST APIs",
          "description": "JSON over HTTP, most common pattern"
        },
        {
          "label": "Platform Events / CDC",
          "description": "Salesforce event-driven integration"
        },
        {
          "label": "MuleSoft / iPaaS",
          "description": "Integration platform as middleware"
        },
        {
          "label": "SOAP / Legacy",
          "description": "XML-based, enterprise protocols"
        }
      ]
    },
    {
      "question": "What elements should be highlighted? (Select all that apply)",
      "header": "Elements",
      "multiSelect": true,
      "options": [
        {
          "label": "Auth badges",
          "description": "Show OAuth 2.0, JWT, API Key on connections"
        },
        {
          "label": "Error handling",
          "description": "Retry logic, dead letter queues, fallbacks"
        },
        {
          "label": "Data transforms",
          "description": "Mapping, conversion, enrichment steps"
        },
        {
          "label": "Timing/frequency",
          "description": "Sync intervals, batch schedules"
        }
      ]
    }
  ]
}
```

### Answer-to-Prompt Mapping

| Answer | Prompt Addition |
|--------|-----------------|
| Integration flow | "System integration diagram with bidirectional data flow arrows" |
| Authentication flow | "OAuth 2.0 sequence diagram with token exchange steps" |
| Salesforce + ERP | "Salesforce (cloud icon) connected to ERP (server icon)" |
| REST APIs | "REST/JSON labels on connection arrows" |
| Platform Events | "Platform Events pub/sub with event bus in center" |
| Auth badges | "OAuth 2.0 / JWT badges on integration arrows" |
| Error handling | "Error queue and retry logic shown as separate path" |

### Default Values (for Skip Mode)

- Diagram: Integration flow
- Systems: Salesforce + Custom APIs
- Protocols: REST APIs
- Elements: Auth badges

---

## Code Review Questions (Gemini Sub-Agent)

### When to Use
User mentions: review, code review, check my code, analyze, audit, best practices

### Questions for Apex Review

```json
{
  "questions": [
    {
      "question": "What type of Apex code is this?",
      "header": "Code Type",
      "multiSelect": false,
      "options": [
        {
          "label": "Trigger",
          "description": "Before/after trigger on an object"
        },
        {
          "label": "Batch job",
          "description": "Batch Apex for large data processing"
        },
        {
          "label": "Service class",
          "description": "Business logic, utility, or helper class"
        },
        {
          "label": "Controller",
          "description": "Aura/LWC controller or VF controller"
        }
      ]
    },
    {
      "question": "What should the review focus on?",
      "header": "Focus",
      "multiSelect": true,
      "options": [
        {
          "label": "Bulkification",
          "description": "SOQL/DML in loops, governor limits"
        },
        {
          "label": "Security",
          "description": "CRUD/FLS checks, injection vulnerabilities"
        },
        {
          "label": "Performance",
          "description": "Query optimization, caching, efficiency"
        },
        {
          "label": "Best practices",
          "description": "Naming, structure, patterns, testability"
        }
      ]
    }
  ]
}
```

---

## Quick Reference Card

| Image Type | Trigger Keywords | Questions |
|------------|-----------------|-----------|
| ERD | ERD, entity, data model, schema | Objects, Style, Purpose, Extras |
| LWC Mockup | LWC, component, mockup, wireframe | Component, Object, Context, Style |
| Architecture | architecture, integration, flow | Diagram, Systems, Protocols, Elements |
| Code Review | review, analyze, check, audit | Code Type, Focus |

---

## Example: Full Interview Flow

### User Says
"I need an ERD for my Service Cloud implementation"

### Claude Invokes AskUserQuestion
```
Objects: Core CRM / Sales Cloud / Service Cloud / Custom
Style: Professional / Whiteboard / Technical / Minimalist
Purpose: Documentation / Quick draft / Presentation / Review
Extras: Legend / Field names / Color-code / None
```

### User Selects
- Objects: Service Cloud
- Style: Professional
- Purpose: Documentation
- Extras: Legend, Color-code

### Claude Builds Prompt
```
Professional Salesforce ERD diagram showing Service Cloud objects:
- Case (blue, center): Main service object
- Knowledge (green, right): Linked articles
- Entitlement (yellow, left): Service level agreements
- Asset (orange, below): Customer-owned products
- ServiceContract (purple, top): Contract management

Relationships:
- Case → Knowledge (Lookup, dashed arrow)
- Case → Asset (Lookup, dashed arrow)
- Asset → ServiceContract (Master-Detail, solid arrow)

Color coding: Standard objects (blue), Service objects (green/yellow)
Include legend in bottom-right corner.
Clean white background, SLDS styling.
```

### Claude Generates
```bash
uv run scripts/generate_image.py \
  -p "[prompt above]" \
  -f "service-cloud-erd.png" \
  -r 4K
```
