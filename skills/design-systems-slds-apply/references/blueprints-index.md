---
id: slds.guidance.blueprints
title: SLDS Blueprints Index
description: Complete index of SLDS blueprints by category with Lightning component mapping
summary: "Index of SLDS blueprints across 9 categories (Actions, Input, Layout, Navigation, Display, Data, Feedback, Overlay, Complex Components). Covers when to use blueprints vs Lightning Base Components."

artifact_type: index
domain: blueprints
topic: blueprints

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, learn]

refs:
  - slds.guidance.development
  - slds.guidance.design
  - slds.guidance.icons

tags: [blueprints, components, html, css, implementation]
keywords: [SLDS blueprints, component implementation, HTML structure, CSS classes, Lightning components, custom components]
---

# SLDS Blueprints Index

## Overview

Blueprints provide HTML structure, CSS classes, ARIA requirements, and code examples for each SLDS component. Each blueprint includes:

- **HTML structure**: Element hierarchy and required markup
- **CSS classes**: Root, element, modifier, size, and state classes
- **Styling hooks**: CSS custom properties for theming
- **Accessibility**: ARIA attributes, keyboard patterns, screen reader guidance
- **Code examples**: Usage examples for variants
- **Lightning component mapping**: Corresponding LWC when available

**Use blueprints** when building custom HTML/CSS, targeting non-Salesforce platforms, or when no Lightning Base Component exists.

**Use Lightning Base Components** when working within Salesforce (LWC, Aura, Visualforce) — they handle accessibility, events, and framework integration automatically.

---

## Blueprints by Category

### Actions

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Buttons** | Action triggers with text labels | `lightning-button` |
| **Button Icons** | Icon-only action triggers | `lightning-button-icon` |
| **Button Groups** | Related buttons in a row | `lightning-button-group` |
| **Docked Utility Bar** | Persistent bottom utility panel | N/A |

---

### Input

Form controls for user input and data entry.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Checkbox** | Binary selection control | `lightning-checkbox` |
| **Checkbox Button** | Checkbox styled as a button | `lightning-checkbox-button` |
| **Checkbox Button Group** | Set of checkbox buttons in a fieldset | `lightning-checkbox-group` |
| **Checkbox Toggle** | Toggle-style checkbox | `lightning-input` (type="checkbox-button") |
| **Combobox** | Text input with dropdown list | `lightning-combobox` |
| **Counter** | Number input with increment/decrement controls | N/A |
| **Datepickers** | Calendar date selection | `lightning-input` (type="date") |
| **Datetime Picker** | Combined date and time selection | `lightning-input` (type="datetime") |
| **Dueling Picklist** | Multi-select with two lists | `lightning-dual-listbox` |
| **Expression** | Formula builder interface | N/A |
| **File Selector** | File upload with drag-and-drop | `lightning-file-upload` |
| **Form Element** | Wrapper for form inputs | N/A |
| **Input** | Text/number input | `lightning-input` |
| **Lookups** | Search and select from a dataset | `lightning-record-picker` |
| **Picklist** | Dropdown from predefined options | `lightning-combobox` |
| **Radio Group** | Single selection from exclusive options | `lightning-radio-group` |
| **Radio Button Group** | Radio buttons in a styled group | `lightning-radio-group` |
| **Rich Text Editor** | Text editor with formatting toolbar | `lightning-input-rich-text` |
| **Select** | Native dropdown selection | `lightning-combobox` |
| **Slider** | Numeric range input via draggable handle | `lightning-slider` |
| **Textarea** | Multi-line text input | `lightning-textarea` |
| **Timepicker** | Time selection interface | `lightning-input` (type="time") |
| **Visual Picker** | Visual tile-based selection | `lightning-radio-group` (with tiles) |

---

### Layout

Components for organizing and structuring content.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Accordion** | Collapsible stacked sections | `lightning-accordion` |
| **Brand Band** | Visual header with branding | N/A |
| **Builder Header** | Header for app builder interfaces | N/A |
| **Cards** | Container with header/body/footer | `lightning-card` |
| **Carousel** | Slideshow with navigation controls | `lightning-carousel` |
| **Docked Form Footer** | Fixed bottom footer for form actions | N/A |
| **Expandable Section** | Collapsible content block | N/A |
| **Page Headers** | Page title, metadata, and actions | `lightning-record-view-form` |
| **Panels** | Structured side or overlay container | N/A |
| **Split View** | Resizable two-pane layout | N/A |
| **Summary Detail** | Collapsible key-value layout | N/A |
| **Tiles** | Card-like grid content items | `lightning-tile` |

---

### Navigation

Components for navigation and wayfinding.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **App Launcher** | Grid for app discovery | N/A |
| **Breadcrumbs** | Hierarchical location trail | `lightning-breadcrumbs` |
| **Dynamic Menu** | Contextual menu in popover | N/A |
| **Global Header** | Primary application header | N/A |
| **Global Navigation** | Main navigation bar | `lightning-navigation` |
| **Menus** | Contextual action lists | `lightning-menu-item` |
| **Path** | Linear process stage indicator | `lightning-path` |
| **Scoped Tabs** | Tabs scoped to a context | `lightning-tabset` |
| **Tabs** | Switchable content panels | `lightning-tabset` |
| **Trees** | Hierarchical list | `lightning-tree` |
| **Vertical Navigation** | Vertical nav menu | `lightning-vertical-navigation` |
| **Vertical Tabs** | Vertical tab interface | `lightning-vertical-navigation` |

---

### Display

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Activity Timeline** | Chronological event list | `lightning-activity-timeline` |
| **Avatar** | User or entity image placeholder | `lightning-avatar` |
| **Avatar Group** | Stacked avatar collection | N/A |
| **Badges** | Small status label | `lightning-badge` |
| **Dynamic Icons** | Animated contextual icons | N/A |
| **Files** | File attachment card | N/A |
| **Icons** | SVG icons from SLDS sprite | `lightning-icon` |
| **Illustration** | Empty/error state graphic | N/A |
| **Pills** | Removable tag or filter token | `lightning-pill` |

---

### Data

Components for displaying structured data.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Data Tables** | Sortable tabular data | `lightning-datatable` |
| **Tree Grid** | Hierarchical data table | `lightning-tree-grid` |

---

### Feedback

Components for communicating status and feedback.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Alert** | Page-level status banner | N/A |
| **Notifications** | System notification messages | N/A |
| **Progress Bar** | Linear completion indicator | `lightning-progress-bar` |
| **Progress Indicator** | Multi-step process tracker | `lightning-progress-indicator` |
| **Progress Ring** | Circular progress indicator | `lightning-progress-ring` |
| **Scoped Notifications** | Notification scoped to a container | N/A |
| **Spinners** | Loading state indicator | `lightning-spinner` |
| **Toast** | Temporary notification message | N/A |
| **Trial Bar** | Trial status and call-to-action bar | N/A |

---

### Overlay

Components that appear above the main interface.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Docked Composer** | Bottom-docked content creation panel | N/A |
| **Modals** | Blocking dialog overlay | N/A |
| **Popovers** | Contextual overlay anchored to trigger | N/A |
| **Prompt** | Confirmation or input dialog | N/A |
| **Tooltips** | Hover-triggered label | N/A |
| **Welcome Mat** | Onboarding introduction overlay | N/A |

---

### Complex Components

Advanced components with rich functionality.

| Blueprint | Description | Lightning Component |
|-----------|-------------|---------------------|
| **Chat** | Chronological chat message display | N/A |
| **Color Picker** | Color selection with hex/swatch input | N/A |
| **Drop Zone** | Drag-and-drop target area | N/A |
| **Feeds** | Chronological activity feed | N/A |
| **List Builder** | Drag-and-drop list ordering | N/A |
| **Map** | Interactive map display | `lightning-map` |
| **Publishers** | Content creation panel | N/A |
| **Setup Assistant** | Guided onboarding checklist | N/A |

---

## Framework Notes

- **LWC / Aura**: Prefer the mapped Lightning component when listed — it handles accessibility and events.
- **React / Vue / Angular / plain HTML**: Use the blueprint HTML structure and CSS classes directly.
- **Customization**: Apply styling hooks (CSS custom properties) to theme components without overriding base styles.
