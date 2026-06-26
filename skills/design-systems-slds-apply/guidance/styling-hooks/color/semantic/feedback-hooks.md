---
id: slds.guidance.hooks.color.feedback
title: Feedback Color Styling Hooks
description: Semantic hooks for error, warning, success, info, and disabled states
summary: "Guidance for feedback color hooks that convey status and state. Covers error, warning, success, info, and disabled colors with their strict semantic meanings and proper usage contexts."

artifact_type: reference
domain: styling-hooks
topic: color
subtopic: semantic

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks.color
  - slds.guidance.hooks.color.accent
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.borders
tags: [styling-hooks, color, semantic, feedback, error, warning, success, info, disabled]
keywords: [error color, warning color, success color, info color, disabled color, status indicators, form validation, alerts]
---

# Feedback Color Styling Hooks

> **Hook Selection:** Semantic hooks like feedback are the first choice (85% of use cases). See [Hook Selection Hierarchy](ref:slds.guidance.hooks.color).

## Overview

Feedback or alert colors provide visual feedback to the user regarding the status of an action or event. These colors are intentionally reserved to convey specific associations throughout the Salesforce UI. Only use feedback colors for their intended meaning so users have clear color associations throughout all of Salesforce products.

| **Color**   | **Meaning**                                                                |
|-------------|---------------------------------------------------------------------------|
| Error       | An error that needs to be addressed before progressing                     |
| Warning     | A warning of potential issues the user needs to be aware of                |
| Success     | A positive or successful action or outcome                                 |
| Info        | Convey non-critical information to users                                   |
| Disabled    | Indicates that a component is unavailable                                  |

---

## Understanding Feedback Hook Variants

### The 1-2 Pattern
Feedback hooks that include `-1` and `-2` variants follow this pattern:
- **`-1`**: Default state (lighter color, lower emphasis)
- **`-2`**: Hover/active state OR higher emphasis state (darker color, higher emphasis)

### Why Some Feedback Types Lack Variants

Not all feedback categories have `-2` variants. This is **intentional** and based on component availability in SLDS2:

| Feedback Type | Has `-2` Variant? | Reason |
|--------------|-------------------|--------|
| Error |  Yes (container, border, on-error) | SLDS2 includes error/destructive buttons requiring hover states |
| Success |  Yes (container, border, on-success) | SLDS2 includes success buttons requiring hover states |
| Warning |  No (except border-1) | SLDS2 has no warning buttons; used for form validation and static alerts |
| Info |  No | SLDS2 has no info buttons; only static badges, icons, and alert containers |
| Disabled |  Yes (container, on-disabled) | Multiple disabled states for different visual weights |

**Future-proofing**: If interactive warning or info components (such as warning buttons) are added to SLDS2 in future releases, corresponding `-2` variants may be introduced for hover states.

---

## `--slds-g-color-error-1`

### Description
Primary error color that indicates errors requiring user attention before progressing.

### Usage

####  Do
- Use error-1 for indicating errors in forms and validation messages
- Use error-1 for critical error states requiring immediate attention
- Use error-1 for error icons and text on neutral backgrounds
- Use error-1 to signal blocking issues that prevent progression
- Use error-1 for destructive action text (delete, remove)

####  Don't
- Avoid using for large background areas (use error-container instead)
- Avoid using for non-error contexts or decorative purposes
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of an error (always pair with text or icons)
- Avoid using system colors or colors from another group like surface colors in combination with error colors

#### Context
- Form validation error text
- Error icons on neutral backgrounds
- Destructive action button text or icons
- Error message text on light backgrounds
- Critical system notification text

### Accessibility
- All error colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-error colors for foreground text and icons on error backgrounds. When used as foreground on neutral surfaces, ensure proper contrast is maintained

---

## `--slds-g-color-error-container-*`

### Description
Error background colors for containers that communicate error states with varying levels of emphasis.

### Available Hooks
- `--slds-g-color-error-container-1` - Light error background for subtle emphasis
- `--slds-g-color-error-container-2` - Medium error background for higher emphasis

### State Progression Logic

Error container variants follow a state progression pattern for interactive destructive elements:
- **`error-container-1`**: Light error background for non-interactive error messages, alerts, and banners
- **`error-container-2`**: Medium error background for destructive button default states, or hover states when starting from container-1

**Typical pattern for destructive buttons**: Use `error-container-2` as the default background, with darker borders or overlays for hover/active states (handled by component-level hooks).

### Usage

####  Do
- Use error container colors for error alert backgrounds and error message containers
- Use error container colors for error banners and toast notifications
- Use error-container-2 for destructive button backgrounds
- Use error container colors for hover/focus/active states of error-related containers

####  Don't
- Avoid using for non-error contexts
- Avoid using without specific error communication requirements
- Avoid mixing with non-error semantic colors
- Avoid using system colors or colors from another group like surface colors in combination with error container colors

#### Context
- Error alert backgrounds
- Error message containers
- Destructive button backgrounds
- Error banner backgrounds
- Error toast notifications

### Accessibility
- All container colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-error colors for foreground text and icons. Choose on-error level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-error-container-1` with `--slds-g-color-on-error-1` for consistency, though other on-error levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-border-error-*`

### Description
Error border colors for visual emphasis of error states with varying levels of emphasis.

### Available Hooks
- `--slds-g-color-border-error-1` - Primary error border color
- `--slds-g-color-border-error-2` - Darker error border for increased emphasis

### State Progression Logic

Border error variants follow standard emphasis patterns:
- **`border-error-1`**: Default error border for standard error states
- **`border-error-2`**: Higher emphasis error border for increased visual weight or interactive hover states

**Typical usage**: Use `-1` for default error borders, and `-2` when higher visual emphasis is needed or for interactive state changes.

### Usage

####  Do
- Use border-error hooks for error form field borders
- Use border-error hooks for error container outlines
- Use border-error hooks to create visual emphasis for error states
- Use border-error hooks for focus indicators on error elements
- Use border-error hooks independently or paired with an error container color
- Use border-error-2 for high-emphasis error borders and destructive actions

####  Don't
- Avoid using for large background areas (borders should define, not fill)
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of an error
- Avoid using non-border error colors on borders to achieve a border with an error color

#### Context
- Error form field borders
- Error container outlines
- Error element indicators
- Validation error borders
- Destructive button outlines (border-error-2)

### Accessibility
- All border error colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best on neutral backgrounds or paired with matching error container colors
- Maintains visibility and consistency when paired with `--slds-g-sizing-border-*` sizing hooks

---

## `--slds-g-color-on-error-*`

### Description
Foreground colors for content placed on error backgrounds, with varying emphasis levels.

### Available Hooks
- `--slds-g-color-on-error-1` - Foreground for error-container-1 backgrounds
- `--slds-g-color-on-error-2` - Darker foreground for error-container-2 backgrounds

### Usage

####  Do
- Use on-error colors for text placed on error container backgrounds
- Use on-error colors for icons displayed on error backgrounds
- Use on-error-1 as error text color on neutral surfaces
- Pair on-error colors with the corresponding error container color
- Use on-error-2 for destructive button text on error-container-2

####  Don't
- Avoid using on non-error backgrounds without verification
- Avoid using for decorative elements that don't require readability
- Avoid mixing on-error-1 with error-container-2 or vice versa
- Avoid mixing with non-matching error backgrounds

#### Context
- Text on error container backgrounds
- Icons on error surfaces
- Error message text
- Destructive button text

### Accessibility
- All on-error colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best paired with a corresponding error background color. Choose on-error level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-error-1` with `--slds-g-color-error-1` or `--slds-g-color-error-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-warning-1`

### Description
Primary warning color that indicates potential issues requiring user awareness.

> **Why no `-2` variant?** Warning hooks lack a `-2` variant because SLDS2 currently has no interactive warning button components. The `-1` variant serves non-interactive elements like static warning icons, badges, and alert containers. If warning buttons become interactive in future releases, a `-2` variant may be added for hover states.

### Usage

####  Do
- Use warning-1 for indicating warnings and cautions
- Use warning-1 for alerting users to potential issues
- Use warning-1 for warning icons and text on neutral backgrounds
- Use warning-1 to signal non-blocking issues requiring attention
- Use warning-1 for informing users of consequences before actions

####  Don't
- Avoid using for large background areas (use warning-container instead)
- Avoid using for non-warning contexts or decorative purposes
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of a warning (always pair with text or icons)
- Avoid using system colors or colors from another group like surface colors in combination with warning colors

#### Context
- Warning message text
- Caution indicators
- Warning icons on neutral backgrounds
- Pre-action warning text
- Non-critical system notification text
- **Note**: If a warning icon is interactive (clickable, shows tooltip), it should be treated as a **button icon** component and use button icon coloring for hover states, not these standalone warning hooks

### Accessibility
- All warning colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-warning colors when used on warning backgrounds

---

## `--slds-g-color-warning-container-1`

### Description
Light warning background color for containers that communicate warning states.

### Usage

####  Do
- Use warning-container-1 for warning alert backgrounds
- Use warning-container-1 for warning banners and toast notifications
- Use warning-container-1 for caution message containers
- Pair warning-container-1 with `--slds-g-color-on-warning-1` for foreground content

####  Don't
- Avoid using for non-warning contexts
- Avoid using without specific warning communication requirements
- Avoid mixing with non-warning semantic colors
- Avoid using system colors or colors from another group like surface colors in combination with warning container colors

#### Context
- Warning alert backgrounds
- Warning message containers
- Caution banner backgrounds
- Warning toast notifications

### Accessibility
- AA compliant when paired with on-warning-1
- Best paired with on-warning colors for foreground text and icons. Choose on-warning level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-warning-container-1` with `--slds-g-color-on-warning-1` for consistency, though other on-warning levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-border-warning-1`

### Description
Warning border color for visual emphasis of warning states.

### Usage

####  Do
- Use border-warning-1 for warning form field borders
- Use border-warning-1 for warning container outlines
- Use border-warning-1 to create visual emphasis for warning states
- Use border-warning-1 for focus indicators on warning elements
- Use border-warning-1 independently or paired with a warning container color

####  Don't
- Avoid using for large background areas (borders should define, not fill)
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of a warning
- Avoid using non-border warning colors on borders to achieve a border with a warning color

#### Context
- Warning form field borders
- Warning container outlines
- Warning element indicators
- Caution borders
- **Note**: This hook was added to support form validation patterns. Unlike error/success, there is no `border-warning-2` since warning states don't typically have interactive hover requirements in current SLDS2 components.

### Accessibility
- All border warning colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best on neutral backgrounds or paired with matching warning container colors
- Maintains visibility and consistency when paired with `--slds-g-sizing-border-*` sizing hooks

---

## `--slds-g-color-on-warning-1`

### Description
Foreground color for content placed on warning backgrounds or for warning text on light surfaces.

### Usage

####  Do
- Use on-warning-1 for text placed on `--slds-g-color-warning-container-1` backgrounds
- Use on-warning-1 for icons displayed on warning backgrounds
- Use on-warning-1 as warning text color on neutral surfaces
- Pair on-warning-1 with the corresponding warning background color

####  Don't
- Avoid using on non-warning backgrounds without verification
- Avoid using for decorative elements that don't require readability
- Avoid mixing with non-matching warning backgrounds

#### Context
- Text on warning-container-1 backgrounds
- Icons on warning surfaces
- Warning message text

### Accessibility
- AA compliant when paired with warning-container-1 backgrounds
- Works best paired with a corresponding warning background color. Choose on-warning level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-warning-1` with `--slds-g-color-warning-1` or `--slds-g-color-warning-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-success-1`

### Description
Primary success color that indicates positive outcomes and successful actions.

### Usage

####  Do
- Use success-1 for indicating successful operations and confirmations
- Use success-1 for positive feedback and completion states
- Use success-1 for success icons and text on neutral backgrounds
- Use success-1 to signal successful outcomes and achievements
- Use success-1 for confirming actions were completed

####  Don't
- Avoid using for large background areas (use success-container instead)
- Avoid using for non-success contexts or decorative purposes
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of success (always pair with text or icons)
- Avoid using system colors or colors from another group like surface colors in combination with success colors

#### Context
- Success message text
- Confirmation indicators
- Success icons on neutral backgrounds
- Completion state text
- Positive system notification text

### Accessibility
- All success colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-success colors when used on success backgrounds

---

## `--slds-g-color-success-container-*`

### Description
Success background colors for containers that communicate success states with varying levels of emphasis.

### Available Hooks
- `--slds-g-color-success-container-1` - Light success background for subtle emphasis
- `--slds-g-color-success-container-2` - Medium success background for higher emphasis

### State Progression Logic

Success container variants follow a state progression pattern for interactive confirmation elements:
- **`success-container-1`**: Light success background for non-interactive success messages, alerts, and banners
- **`success-container-2`**: Medium success background for confirmation button default states, or hover states when starting from container-1

**Typical pattern for confirmation buttons**: Use `success-container-2` as the default background, with darker borders or overlays for hover/active states (handled by component-level hooks).

### Usage

####  Do
- Use success container colors for success alert backgrounds and success message containers
- Use success container colors for success banners and toast notifications
- Use success-container-2 for confirmation button backgrounds
- Use success container colors for hover/focus/active states of success-related containers

####  Don't
- Avoid using for non-success contexts
- Avoid using without specific success communication requirements
- Avoid mixing with non-success semantic colors
- Avoid using system colors or colors from another group like surface colors in combination with success container colors

#### Context
- Success alert backgrounds
- Success message containers
- Confirmation button backgrounds
- Success banner backgrounds
- Success toast notifications

### Accessibility
- All container colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-success colors for foreground text and icons. Choose on-success level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-success-container-1` with `--slds-g-color-on-success-1` for consistency, though other on-success levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-border-success-*`

### Description
Success border colors for visual emphasis of success states with varying levels of emphasis.

### Available Hooks
- `--slds-g-color-border-success-1` - Primary success border color
- `--slds-g-color-border-success-2` - Darker success border for increased emphasis

### State Progression Logic

Border success variants follow standard emphasis patterns:
- **`border-success-1`**: Default success border for standard success states
- **`border-success-2`**: Higher emphasis success border for increased visual weight or interactive hover states

**Typical usage**: Use `-1` for default success borders, and `-2` when higher visual emphasis is needed or for interactive state changes.

### Usage

####  Do
- Use border-success hooks for success form field borders
- Use border-success hooks for success container outlines
- Use border-success hooks to create visual emphasis for success states
- Use border-success hooks for focus indicators on success elements
- Use border-success hooks independently or paired with a success container color
- Use border-success-2 for high-emphasis success borders

####  Don't
- Avoid using for large background areas (borders should define, not fill)
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of success
- Avoid using non-border success colors on borders to achieve a border with a success color

#### Context
- Success form field borders
- Success container outlines
- Success element indicators
- Confirmation borders
- Emphasized confirmation outlines (border-success-2)

### Accessibility
- All border success colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best on neutral backgrounds or paired with matching success container colors
- Maintains visibility and consistency when paired with `--slds-g-sizing-border-*` sizing hooks

---

## `--slds-g-color-on-success-*`

### Description
Foreground colors for content placed on success backgrounds, with varying emphasis levels.

### Available Hooks
- `--slds-g-color-on-success-1` - Foreground for success-container-1 backgrounds
- `--slds-g-color-on-success-2` - Darker foreground for success-container-2 backgrounds

### Usage

####  Do
- Use on-success colors for text placed on success container backgrounds
- Use on-success colors for icons displayed on success backgrounds
- Use on-success-1 as success text color on neutral surfaces
- Pair on-success colors with the corresponding success container color
- Use on-success-2 for confirmation button text on success-container-2

####  Don't
- Avoid using on non-success backgrounds without verification
- Avoid using for decorative elements that don't require readability
- Avoid mixing on-success-1 with success-container-2 or vice versa
- Avoid mixing with non-matching success backgrounds

#### Context
- Text on success container backgrounds
- Icons on success surfaces
- Success message text
- Confirmation button text

### Accessibility
- All on-success colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best paired with a corresponding success background color. Choose on-success level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-success-1` with `--slds-g-color-success-1` or `--slds-g-color-success-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-info-1`

### Description
Primary info color that conveys non-critical information to users.

> **Why no `-2` variant?** Info hooks lack a `-2` variant because SLDS2 currently has no interactive info button components. The `-1` variant serves non-interactive elements like static info badges, icons, and alert containers. If info buttons become interactive in future releases, a `-2` variant may be added for hover states.

### Usage

####  Do
- Use info-1 for indicating informational messages
- Use info-1 for helpful tips and guidance
- Use info-1 for info icons and text on neutral backgrounds
- Use info-1 to signal non-critical information
- Use info-1 for educational or contextual content

####  Don't
- Avoid using for large background areas (use info-container instead)
- Avoid using for non-informational contexts or decorative purposes
- Avoid using without ensuring proper contrast
- Avoid using as the only indicator of information (always pair with text or icons)
- Avoid using system colors or colors from another group like surface colors in combination with info colors

#### Context
- Informational message text
- Help text and tooltips
- Info icons on neutral backgrounds
- Contextual guidance text
- Educational notification text
- **Note**: If an info icon is interactive (clickable, shows tooltip), it should be treated as a **button icon** component and use button icon coloring for hover states, not these standalone info hooks

### Accessibility
- All info colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-info colors when used on info backgrounds

---

## `--slds-g-color-info-container-1`

### Description
Light info background color for containers that communicate informational states.

### Usage

####  Do
- Use info-container-1 for info alert backgrounds
- Use info-container-1 for info banners and toast notifications
- Use info-container-1 for help panel backgrounds
- Pair info-container-1 with `--slds-g-color-on-info-1` for foreground content

####  Don't
- Avoid using for non-informational contexts
- Avoid using without specific informational communication requirements
- Avoid mixing with non-info semantic colors
- Avoid using system colors or colors from another group like surface colors in combination with info container colors

#### Context
- Info alert backgrounds
- Info message containers
- Help panel backgrounds
- Info banner backgrounds
- Info toast notifications

### Accessibility
- AA compliant when paired with on-info-1
- Best paired with on-info colors for foreground text and icons. Choose on-info level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-info-container-1` with `--slds-g-color-on-info-1` for consistency, though other on-info levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-on-info-1`

### Description
Foreground color for content placed on info backgrounds or for info text on light surfaces.

### Usage

####  Do
- Use on-info-1 for text placed on `--slds-g-color-info-container-1` backgrounds
- Use on-info-1 for icons displayed on info backgrounds
- Use on-info-1 as info text color on neutral surfaces
- Pair on-info-1 with the corresponding info background color

####  Don't
- Avoid using on non-info backgrounds without verification
- Avoid using for decorative elements that don't require readability
- Avoid mixing with non-matching info backgrounds

#### Context
- Text on info-container-1 backgrounds
- Icons on info surfaces
- Info message text
- Help text on info backgrounds

### Accessibility
- AA compliant when paired with info-container-1 backgrounds
- Works best paired with a corresponding info background color. Choose on-info level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-info-1` with `--slds-g-color-info-1` or `--slds-g-color-info-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-disabled-1`

### Description
Primary disabled color that indicates components are unavailable for interaction.

### Usage

####  Do
- Use disabled-1 for indicating disabled or inactive elements
- Use disabled-1 for non-interactive states
- Use disabled-1 for disabled borders and backgrounds
- Use disabled-1 to signal unavailable functionality
- Use disabled-1 for inactive form fields and buttons

####  Don't
- Avoid using for active or interactive elements
- Avoid using for decorative purposes
- Avoid using without ensuring users understand the disabled state
- Avoid using as the only indicator of disabled state (pair with `aria-disabled` or `disabled` attributes)
- Avoid using system colors or colors from another group like surface colors in combination with disabled colors

#### Context
- Disabled form field borders
- Inactive button backgrounds
- Unavailable menu items
- Non-interactive element styling
- Grayed-out content

### Accessibility
- All disabled colors maintain proper contrast ratios, though they intentionally appear de-emphasized
- Always use proper ARIA attributes (`aria-disabled="true"` or `disabled` attribute) in addition to visual styling

---

## `--slds-g-color-disabled-container-*`

### Description
Disabled container background colors for unavailable states with varying levels of emphasis.

### Available Hooks
- `--slds-g-color-disabled-container-1` - Light disabled background
- `--slds-g-color-disabled-container-2` - Medium emphasis disabled background

### Understanding Disabled Container Variants

Disabled container variants provide different visual weights for unavailable states:
- **`disabled-container-1`**: Light disabled background for subtle de-emphasis
- **`disabled-container-2`**: Medium disabled background for stronger visual de-emphasis

**These are NOT state progressions**: Disabled elements have no interactive states. The variant numbers represent different levels of visual de-emphasis based on component needs, not hover/active states.

**Typical usage**: Choose based on desired visual weight—`disabled-container-1` for subtle de-emphasis (common in form fields and neutral buttons), `disabled-container-2` for stronger de-emphasis (common in filled branded buttons).

### Usage

####  Do
- Use disabled container colors for disabled button backgrounds
- Use disabled container colors for inactive form field backgrounds
- Use disabled container colors for unavailable container states
- Use disabled container colors for grayed-out panel backgrounds

####  Don't
- Avoid using for active or interactive containers
- Avoid for elements that should remain visually prominent
- Avoid using without proper disabled state indicators
- Avoid mixing with active state semantic colors
- Avoid using system colors or colors from another group like surface colors in combination with disabled container colors

#### Context
- Disabled button backgrounds
- Inactive form field backgrounds
- Unavailable container backgrounds
- Grayed-out panels
- Non-interactive element backgrounds

### Accessibility
- All container colors maintain proper contrast ratios appropriate for disabled states
- Best paired with on-disabled colors for foreground text and icons. Choose on-disabled level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-disabled-container-1` with `--slds-g-color-on-disabled-1` for consistency, though other on-disabled levels may be used based on emphasis needs while maintaining accessibility compliance
- Always include proper semantic HTML and ARIA attributes to communicate disabled state to assistive technologies

---

## `--slds-g-color-border-disabled-1`

### Description
Disabled border color for visual emphasis of unavailable states.

### Usage

####  Do
- Use border-disabled-1 for disabled form field borders
- Use border-disabled-1 for inactive container outlines
- Use border-disabled-1 to create visual emphasis for disabled states
- Use border-disabled-1 independently or paired with a disabled container color

####  Don't
- Avoid using for active or interactive elements
- Avoid using without proper disabled state communication
- Avoid using as the only indicator of disabled state
- Avoid using non-border disabled colors on borders

#### Context
- Disabled form field borders
- Inactive container outlines
- Unavailable element borders
- Grayed-out element borders

### Accessibility
- Maintains appropriate contrast for disabled states
- Works best on neutral backgrounds or paired with matching disabled container colors
- Maintains visibility and consistency when paired with `--slds-g-sizing-border-*` sizing hooks
- Must be accompanied by proper semantic HTML and ARIA attributes

---

## `--slds-g-color-on-disabled-*`

### Description
Foreground colors for content placed on disabled backgrounds, with varying emphasis levels.

### Available Hooks
- `--slds-g-color-on-disabled-1` - Foreground for disabled-container-1 backgrounds
- `--slds-g-color-on-disabled-2` - Darker foreground for disabled content requiring more emphasis

### Usage

####  Do
- Use on-disabled colors for text placed on disabled container backgrounds
- Use on-disabled colors for icons displayed on disabled backgrounds
- Pair on-disabled colors with the corresponding disabled container color
- Use on-disabled-2 for disabled content requiring better readability

####  Don't
- Avoid using on active or interactive backgrounds
- Avoid using without the corresponding disabled background
- Avoid using for elements that should appear fully interactive
- Avoid mixing with non-matching disabled backgrounds

#### Context
- Text on disabled container backgrounds
- Icons on disabled surfaces
- Disabled button text
- Inactive form field text

### Accessibility
- All on-disabled colors maintain appropriate contrast ratios for disabled states while appearing visually de-emphasized
- Works best paired with a corresponding disabled background color. Choose on-disabled level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-disabled-1` with `--slds-g-color-disabled-1` or `--slds-g-color-disabled-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance
- Always ensure proper semantic HTML and ARIA attributes are present to communicate disabled state to assistive technologies

