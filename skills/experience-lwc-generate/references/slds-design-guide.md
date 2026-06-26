# SLDS Design

## Overview

**Use blueprints** when building custom HTML/CSS, targeting non-Salesforce platforms, or when no Lightning Base Component exists.

Refer to the SLDS blueprints in [slds-blueprints.json](slds-blueprints.json)

**Use Lightning Base Components** when working within Salesforce (LWC, Aura, Visualforce) — they handle accessibility, events, and framework integration automatically.

---

## Blueprints by Category

### Actions (4 components)

| Blueprint              | Description                      | Lightning Component      |
| ---------------------- | -------------------------------- | ------------------------ |
| **Buttons**            | Action triggers with text labels | `lightning-button`       |
| **Button Icons**       | Icon-only action triggers        | `lightning-button-icon`  |
| **Button Groups**      | Related buttons in a row         | `lightning-button-group` |

---

### Input (23 components)

| Blueprint                 | Description                                    | Lightning Component                 |
| ------------------------- | ---------------------------------------------- | ----------------------------------- |
| **Checkbox**              | Binary selection control                       | `lightning-input` (type="checkbox") |
| **Checkbox Button**       | Checkbox styled as a button                    | `lightning-checkbox-button`         |
| **Checkbox Button Group** | Set of checkbox buttons in a fieldset          | N/A                                 |
| **Checkbox Toggle**       | Toggle-style checkbox                          | N/A                                 |
| **Combobox**              | Text input with dropdown list                  | `lightning-combobox`                |
| **Counter**               | Number input with increment/decrement controls | `lightning-input`                   |
| **Datepickers**           | Calendar date selection                        | `lightning-input` (type="date")     |
| **Datetime Picker**       | Combined date and time selection               | N/A                                 |
| **Dueling Picklist**      | Multi-select with two lists                    | N/A                                 |
| **Expression**            | Formula builder interface                      | N/A                                 |
| **File Selector**         | File upload with drag-and-drop                 | `lightning-file-upload`             |
| **Form Element**          | Wrapper for form inputs                        | N/A                                 |
| **Input**                 | Text/number input                              | `lightning-input`                   |
| **Lookups**               | Search and select from a dataset               | N/A                                 |
| **Picklist**              | Dropdown from predefined options               | N/A                                 |
| **Radio Group**           | Single selection from exclusive options        | `lightning-radio-group`             |
| **Radio Button Group**    | Radio buttons in a styled group                | `lightning-radio-group`             |
| **Rich Text Editor**      | Text editor with formatting toolbar            | `lightning-input-rich-text`         |
| **Select**                | Native dropdown selection                      | `lightning-select`                  |
| **Slider**                | Numeric range input via draggable handle       | `lightning-slider`                  |
| **Textarea**              | Multi-line text input                          | `lightning-textarea`                |
| **Timepicker**            | Time selection interface                       | `lightning-input` (type="time")     |
| **Visual Picker**         | Visual tile-based selection                    | N/A                                 |

---

### Layout (12 components)

| Blueprint              | Description                          | Lightning Component    |
| ---------------------- | ------------------------------------ | ---------------------- |
| **Accordion**          | Collapsible stacked sections         | `lightning-accordion`  |
| **Brand Band**         | Visual header with branding          | `lightning-brand-band` |
| **Builder Header**     | Header for app builder interfaces    | N/A                    |
| **Cards**              | Container with header/body/footer    | `lightning-card`       |
| **Carousel**           | Slideshow with navigation controls   | `lightning-carousel`   |
| **Docked Form Footer** | Fixed bottom footer for form actions | N/A                    |
| **Expandable Section** | Collapsible content block            | N/A                    |
| **Page Headers**       | Page title, metadata, and actions    | N/A                    |
| **Panels**             | Structured side or overlay container | `lightning-panel`      |
| **Split View**         | Resizable two-pane layout            | N/A                    |
| **Summary Detail**     | Collapsible key-value layout         | N/A                    |
| **Tiles**              | Card-like grid content items         | `lightning-tile`       |

---

### Navigation (12 components)

| Blueprint               | Description                    | Lightning Component             |
| ----------------------- | ------------------------------ | ------------------------------- |
| **App Launcher**        | Grid for app discovery         | N/A                             |
| **Breadcrumbs**         | Hierarchical location trail    | `lightning-breadcrumbs`         |
| **Dynamic Menu**        | Contextual menu in popover     | `lightning-menu`                |
| **Global Header**       | Primary application header     | N/A                             |
| **Global Navigation**   | Main navigation bar            | N/A                             |
| **Menus**               | Contextual action lists        | `lightning-menu-item`           |
| **Path**                | Linear process stage indicator | N/A                             |
| **Scoped Tabs**         | Tabs scoped to a context       | `lightning-tabset`              |
| **Tabs**                | Switchable content panels      | `lightning-tabset`              |
| **Trees**               | Hierarchical list              | `lightning-tree`                |
| **Vertical Navigation** | Vertical nav menu              | `lightning-vertical-navigation` |
| **Vertical Tabs**       | Vertical tab interface         | `lightning-tabset`              |

---

### Display (9 components)

| Blueprint             | Description                      | Lightning Component |
| --------------------- | -------------------------------- | ------------------- |
| **Activity Timeline** | Chronological event list         | N/A                 |
| **Avatar**            | User or entity image placeholder | `lightning-avatar`  |
| **Avatar Group**      | Stacked avatar collection        | N/A                 |
| **Badges**            | Small status label               | `lightning-badge`   |
| **Dynamic Icons**     | Animated contextual icons        | N/A                 |
| **Files**             | File attachment card             | N/A                 |
| **Icons**             | SVG icons from SLDS sprite       | `lightning-icon`    |
| **Illustration**      | Empty/error state graphic        | N/A                 |
| **Pills**             | Removable tag or filter token    | `lightning-pill`    |

---

### Data (2 components)

| Blueprint       | Description             | Lightning Component   |
| --------------- | ----------------------- | --------------------- |
| **Data Tables** | Sortable tabular data   | `lightning-datatable` |
| **Tree Grid**   | Hierarchical data table | `lightning-tree-grid` |

---

### Feedback (9 components)

| Blueprint                | Description                         | Lightning Component            |
| ------------------------ | ----------------------------------- | ------------------------------ |
| **Alert**                | Page-level status banner            | N/A                            |
| **Notifications**        | System notification messages        | N/A                            |
| **Progress Bar**         | Linear completion indicator         | `lightning-progress-bar`       |
| **Progress Indicator**   | Multi-step process tracker          | `lightning-progress-indicator` |
| **Progress Ring**        | Circular progress indicator         | `lightning-progress-ring`      |
| **Scoped Notifications** | Notification scoped to a container  | N/A                            |
| **Spinners**             | Loading state indicator             | `lightning-spinner`            |
| **Toast**                | Temporary notification message      | N/A                            |
| **Trial Bar**            | Trial status and call-to-action bar | N/A                            |

---

### Overlay (6 components)

| Blueprint           | Description                            | Lightning Component |
| ------------------- | -------------------------------------- | ------------------- |
| **Docked Composer** | Bottom-docked content creation panel   | N/A                 |
| **Modals**          | Blocking dialog overlay                | N/A                 |
| **Popovers**        | Contextual overlay anchored to trigger | N/A                 |
| **Prompt**          | Confirmation or input dialog           | N/A                 |
| **Tooltips**        | Hover-triggered label                  | N/A                 |
| **Welcome Mat**     | Onboarding introduction overlay        | N/A                 |

---

### Complex Components (8 components)

| Blueprint           | Description                           | Lightning Component      |
| ------------------- | ------------------------------------- | ------------------------ |
| **Chat**            | Chronological chat message display    | N/A                      |
| **Color Picker**    | Color selection with hex/swatch input | N/A                      |
| **Drop Zone**       | Drag-and-drop target area             | N/A                      |
| **Feeds**           | Chronological activity feed           | N/A                      |
| **List Builder**    | Drag-and-drop list ordering           | `lightning-dual-listbox` |
| **Map**             | Interactive map display               | `lightning-map`          |
| **Publishers**      | Content creation panel                | N/A                      |
| **Setup Assistant** | Guided onboarding checklist           | N/A                      |

---

## Framework Notes

- **LWC / Aura**: Prefer the mapped Lightning component when listed — it handles accessibility and events.
- **React / Vue / Angular / plain HTML**: Use the blueprint HTML structure and CSS classes directly.
- **Customization**: Apply styling hooks (CSS custom properties) to theme components without overriding base styles.