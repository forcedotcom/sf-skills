# Lightning Base Components — Full API Reference

Per-component API docs (Properties, Methods, Events, Slots) for every Lightning Base Component, rendered verbatim from the same source the legacy `explore_lbc_components` MCP tool returned. Each component below is a self-contained block delimited by `---`. The first non-blank line of each block is `# Component API Structure`; the component name lives in the `**Name:**` field a few lines below. To find a specific component, grep for `**Name:** <name>` (e.g. `**Name:** datatable`).

## Component index

- accordion
- accordionSection
- alert
- avatar
- badge
- barcodeScanner
- breadcrumb
- breadcrumbs
- button
- buttonGroup
- buttonIcon
- buttonIconStateful
- buttonMenu
- buttonStateful
- card
- checkboxGroup
- clickToDial
- combobox
- confirm
- datatable
- dualListbox
- dynamicIcon
- fileUpload
- formattedAddress
- formattedDateTime
- formattedEmail
- formattedLocation
- formattedName
- formattedNumber
- formattedPhone
- formattedRichText
- formattedText
- formattedTime
- formattedUrl
- helptext
- icon
- input
- inputAddress
- inputField
- inputLocation
- inputName
- inputRichText
- layout
- layoutItem
- menuDivider
- menuItem
- menuSubheader
- messageService
- modal
- modalBody
- modalFooter
- modalHeader
- navigation
- outputField
- pageReferenceUtils
- pill
- pillContainer
- progressBar
- progressRing
- prompt
- radioGroup
- recordEditForm
- recordForm
- recordPicker
- recordViewForm
- refresh
- relativeDateTime
- richTextToolbarButton
- richTextToolbarButtonGroup
- select
- slider
- spinner
- tab
- tabset
- textarea
- tile
- toast
- toastContainer
- tree
- treeGrid
- verticalNavigation
- verticalNavigationItem
- verticalNavigationItemBadge
- verticalNavigationItemIcon

# Component API Structure

## Basic Information

- **Name:** accordion
- **Namespace:** lightning
- **Tag Name:** lightning-accordion
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A collection of vertically stacked sections with multiple content areas. Users can expand and collapse sections to control how much content is visible at once.

## API Reference

### Properties

| Name                      | Type            | Default   | Description                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------- | --------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| title                     | string          | undefined | Displays tooltip text when the mouse moves over the element.                                                                                                                                                                                                                                                                                                                                                             |
| activeSectionName         | string \| array | undefined | Expands the specified accordion sections. Pass in a string for a single section or a list of section names. Section names are case-sensitive. To support multiple expanded sections, include allow-multiple-sections-open in your markup. By default, only the first section in the accordion is expanded. Returns a string when allowMultipleSectionsOpen is false, or an array when allowMultipleSectionsOpen is true. |
| allowMultipleSectionsOpen | boolean         | false     | If present, the accordion allows multiple open sections. Otherwise, opening a section closes another that's currently open.                                                                                                                                                                                                                                                                                              |

### Methods

None

### Events

#### sectiontoggle

- **Description:** The event fired when an accordion loads with at least one active section or when a section is toggled.
- **Payload:**
  ```javascript
  {
    openSections: string | array; // The name of the active section. Returns a string or an array of strings for the active section names, depending on the allowMultipleSectionsOpen attribute. Returns a string when allowMultipleSectionsOpen is false, or an array when allowMultipleSectionsOpen is true.
  }
  ```

### Slots

#### default

- **Description:** Placeholder for accordion-section components.

---

# Component API Structure

## Basic Information

- **Name:** accordionSection
- **Namespace:** lightning
- **Tag Name:** lightning-accordion-section
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A single section that is nested in an accordion component. Each section can contain HTML markup or Lightning components.

## API Reference

### Properties

| Name         | Type             | Default   | Description                                                                                                                                                                                                           |
| ------------ | ---------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name         | string           | undefined | The unique section name to use with the active-section-name attribute in the accordion component. If you use the sectiontoggle event, provide a name for the accordion section to identify the section that's opened. |
| label        | string           | undefined | The text that displays as the title of the section.                                                                                                                                                                   |
| title        | string           | undefined | Reserved for internal use.                                                                                                                                                                                            |
| headingLevel | string \| number | undefined | Changes the 'aria-level' attribute value for the h2 markup tag in the section's title element. Supported values are 1, 2, 3, 4, 5, 6.                                                                                 |

### Methods

None

### Events

None

### Slots

#### actions

- **Description:** Placeholder for actionable components, such as lightning-button or lightning-button-menu. Actions are displayed at the top right corner of the accordion section.

#### default

- **Description:** Placeholder for your content in the accordion section.

---

# Component API Structure

## Basic Information

- **Name:** alert
- **Namespace:** lightning
- **Tag Name:** lightning-alert
- **Version:** 54.0
- **Type:** COMPONENT
- **Description:** Create an alert modal within your component that communicates a state that affects the entire system, not just a feature or page. Use `LightningAlert.open()` instead of the native `window.alert()` for a more consistent user experience. The alert modal implements the SLDS prompt blueprint with `role="alertdialog"` and is a focus trap.

## API Reference

### Properties

| Name    | Type   | Default              | Description                                                                                                                                                |
| ------- | ------ | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label   | string | "Alert" (translated) | Value to use for header text in "header" variant or aria-label in "headerless" variant                                                                     |
| message | string | ""                   | Text to display in the alert                                                                                                                               |
| variant | string | "header"             | Variant to use for alert. Valid values are "header" and "headerless"                                                                                       |
| theme   | string | "default"            | Theme to use when variant is "header". Valid values are "default", "shade", "inverse", "alt-inverse", "success", "info", "warning", "error", and "offline" |

### Methods

#### open

- **Description:** Static method to open an alert modal instance. Returns a Promise that resolves when the alert is closed.
- **Parameters:**
  - `apis` (Object, required): Object containing properties to set on the alert instance (label, message, variant, theme)
- **Returns:** Promise

#### close

- **Description:** Closes the alert modal and resolves the promise returned by open(). This method is public for testing only.
- **Parameters:**
  - `result` (any, optional): Value returned in the promise when the alert closes
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** avatar
- **Namespace:** lightning
- **Tag Name:** lightning-avatar
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A visual representation of an object.

## API Reference

### Properties

| Name             | Type   | Default   | Description                                                                                                                                                                                                                                                                                                                                                           |
| ---------------- | ------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| alternativeText  | string | ''        | The alternative text used to describe the avatar, which is displayed as hover text on the image.                                                                                                                                                                                                                                                                      |
| fallbackIconName | string | undefined | The Lightning Design System name of the icon used as a fallback when the image fails to load. The initials fallback relies on this for its background color. Names are written in the format 'standard:account' where 'standard' is the category, and 'account' is the specific icon to be displayed. Only icons from the standard and custom categories are allowed. |
| initials         | string | undefined | If the record name contains two words, like first and last name, use the first capitalized letter of each. For records that only have a single word name, use the first two letters of that word using one capital and one lower case letter.                                                                                                                         |
| size             | string | 'medium'  | The size of the avatar. Valid values are x-small, small, medium, and large.                                                                                                                                                                                                                                                                                           |
| src              | string | ''        | The URL for the image.                                                                                                                                                                                                                                                                                                                                                |
| variant          | string | 'square'  | The variant changes the shape of the avatar. Valid values are circle and square. The avatar is always a circle in SLDS 2 themes.                                                                                                                                                                                                                                      |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** badge
- **Namespace:** lightning
- **Tag Name:** lightning-badge
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Represents a label which holds a small amount of information, such as the number of unread notifications. A badge can be used to display unread notifications, or to label a block of text. Badges don't work for navigation because they can't include a hyperlink.

## API Reference

### Properties

| Name                | Type   | Default | Description                                                                                                                                                                                                     |
| ------------------- | ------ | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label               | string | null    | (Required) The text to be displayed inside the badge.                                                                                                                                                           |
| iconName            | string | null    | The Lightning Design System name of the icon to be displayed inside the badge. Names are written in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed. |
| iconAlternativeText | string | null    | The alternative text used to describe the icon, which is displayed as tooltip text.                                                                                                                             |
| iconPosition        | string | 'start' | The position for the icon. Possible values: 'start' (displayed before the text) and 'end' (displayed after the text).                                                                                           |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** barcodeScanner
- **Namespace:** lightning
- **Tag Name:** lightning-barcode-scanner
- **Version:** 57.0
- **Type:** COMPONENT
- **Description:** Scans barcodes on a mobile device. The component embeds a barcode scanning function displayed as an icon, which launches the barcode scanner when the user clicks it.

## API Reference

### Properties

| Name                    | Type    | Default                                                                                                                   | Description                                                                                                                                                                      |
| ----------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| scannerOptions          | object  | `{ barcodeTypes: ['code128', 'code39', 'code93', 'datamatrix', 'ean13', 'ean8', 'itf', 'upca', 'upce', 'pdf417', 'qr'] }` | An object representing configuration details for a barcode scanning session. Supports properties like `barcodeTypes` (array of barcode type strings) and `scannerSize` (string). |
| enableContinuousScan    | boolean | false                                                                                                                     | Enables continuous scanning when set to `true`. When false, the scanner automatically closes after one successful scan. When true, the scanner remains open for multiple scans.  |
| enabledIconSrc          | string  | ''                                                                                                                        | The URL of a custom image for the enabled icon. When not specified, uses the default `action:scan_enabled` icon.                                                                 |
| disabledIconSrc         | string  | ''                                                                                                                        | The URL of a custom image for the disabled icon. When not specified, uses the default `action:scan_disabled` icon.                                                               |
| iconSize                | string  | 'medium'                                                                                                                  | The size of the barcode scanner icon. Supported values are `xx-small`, `x-small`, `small`, `medium`, and `large`.                                                                |
| enabledAlternativeText  | string  | 'Scanner enabled'                                                                                                         | Assistive technology text to describe the enabled barcode scanner icon.                                                                                                          |
| disabledAlternativeText | string  | 'Scanner disabled'                                                                                                        | Assistive technology text to describe the disabled barcode scanner icon.                                                                                                         |
| disabled                | boolean | false                                                                                                                     | Disables the barcode scanner button when set to `true`.                                                                                                                          |

### Methods

None

### Events

#### scan

- **Description:** Triggered by a successful scan on a single scan component or by successfully closing the scanner window on a continuous scan component. The event does not bubble and does not propagate outside the template in which it was dispatched.
- **Payload:**
  ```javascript
  {
    scannedBarcodes: string[] // An array of scanned barcode values. Duplicate scans are automatically filtered out.
  }
  ```

#### errors

- **Description:** Triggered if there is an error during the scan. The event does not bubble and does not propagate outside the template in which it was dispatched. Not triggered when the user manually closes the scanner (in that case, the `scan` event is triggered instead).
- **Payload:**
  ```javascript
  {
    error: object; // An object containing error details including code and message properties.
  }
  ```

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** breadcrumb
- **Namespace:** lightning
- **Tag Name:** lightning-breadcrumb
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** An item in the hierarchy path of the page the user is on. Displays a clickable link that represents a single breadcrumb in a navigation path. Must be nested within a lightning-breadcrumbs component. Automatically sets role="listitem" and adds the CSS class 'slds-breadcrumb\_\_item'.

## API Reference

### Properties

| Name        | Type   | Default | Description                                                                                                                                                                |
| ----------- | ------ | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label       | string | null    | The text label for the breadcrumb (required).                                                                                                                              |
| name        | string | null    | Optional identifier that can be used to identify the breadcrumb in a callback (e.g., in an onclick handler).                                                               |
| href        | string | '#'     | The URL of the page that the breadcrumb navigates to. If not provided, defaults to '#'. The URL is sanitized for security when the ENABLE_SANITIZE_URL feature is enabled. |
| ariaCurrent | string | null    | Reserved for internal use. Automatically managed by the parent lightning-breadcrumbs component to mark the current page.                                                   |

### Methods

#### focus

- **Description:** Sets focus on the breadcrumb link element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes focus from the breadcrumb link element.
- **Parameters:** None
- **Returns:** void

### Events

This component does not dispatch any custom events. Standard DOM events like `click` can be handled using the `onclick` attribute.

### Slots

This component has no slots.

---

# Component API Structure

## Basic Information

- **Name:** breadcrumbs
- **Namespace:** lightning
- **Tag Name:** lightning-breadcrumbs
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** An ordered list that displays the hierarchy path of the page you're currently visiting within the website or app. Each breadcrumb item is represented by a lightning-breadcrumb component. Breadcrumbs are actionable and separated by a greater-than sign. The component automatically sets aria-label="Breadcrumbs" and role="navigation" for accessibility, and marks the last breadcrumb with aria-current="page".

## API Reference

### Properties

This component does not expose any public properties.

### Methods

None

### Events

None

### Slots

#### default

- **Description:** Placeholder for lightning-breadcrumb components. The slot accepts multiple lightning-breadcrumb elements to form the breadcrumb navigation path.

---

# Component API Structure

## Basic Information

- **Name:** button
- **Namespace:** lightning
- **Tag Name:** lightning-button
- **Version:** GA
- **Type:** COMPONENT
- **Description:** A clickable element used to perform an action. Use lightning-button where users need to submit or reset a form, begin a new task, trigger a new UI element to appear on the page, or specify a new or next step in a process.

## API Reference

### Properties

| Name             | Type            | Default   | Description                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------- | --------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| name             | string          | undefined | The name for the button element. This value is optional and can be used to identify the button in a callback.                                                                                                                                                                                                                                                                  |
| value            | string          | undefined | The value for the button element. This value is optional and can be used when submitting a form.                                                                                                                                                                                                                                                                               |
| label            | string          | undefined | The text to be displayed inside the button.                                                                                                                                                                                                                                                                                                                                    |
| tabIndex         | number          | 0         | Reserved for internal use only. Use the global tabindex attribute instead. Set tab index to -1 to prevent focus on the button during tab navigation. The default value is 0, which makes the button focusable during tab navigation.                                                                                                                                           |
| variant          | string          | neutral   | The variant changes the appearance of the button. Accepted variants include base, neutral, brand, brand-outline, destructive, destructive-text, inverse, and success.                                                                                                                                                                                                          |
| iconName         | string          | undefined | The Lightning Design System name of the icon. Names are written in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed.                                                                                                                                                                                                 |
| iconPosition     | string          | left      | Describes the position of the icon with respect to the button label. Options include left and right.                                                                                                                                                                                                                                                                           |
| stretch          | boolean         | false     | Setting it to true allows the button to take up the entire available width.                                                                                                                                                                                                                                                                                                    |
| type             | string          | button    | Specifies the type of button. Valid values are button, reset, and submit.                                                                                                                                                                                                                                                                                                      |
| disableAnimation | boolean         | false     | Reserved for internal use. If present, disables button animation.                                                                                                                                                                                                                                                                                                              |
| disabled         | boolean         | false     | Specifies whether this button should be displayed in a disabled state. Disabled buttons can't be clicked.                                                                                                                                                                                                                                                                      |
| accessKey        | string          | undefined | Specifies a shortcut key to activate or focus an element.                                                                                                                                                                                                                                                                                                                      |
| title            | string          | undefined | Displays tooltip text when the mouse cursor moves over the element.                                                                                                                                                                                                                                                                                                            |
| ariaLabel        | string          | undefined | Label describing the button to assistive technologies.                                                                                                                                                                                                                                                                                                                         |
| ariaLabelledBy   | string          | undefined | Specifies the ID or list of IDs of the element or elements that contain visible descriptive text to describe the button.                                                                                                                                                                                                                                                       |
| ariaDescribedBy  | string          | undefined | A space-separated list of element IDs that provide descriptive labels for the button.                                                                                                                                                                                                                                                                                          |
| ariaControls     | string          | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaOwns         | string          | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaDetails      | string          | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaFlowTo       | string          | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaExpanded     | string\|boolean | undefined | Indicates whether an element that the button controls is expanded or collapsed. Valid values are 'true' or 'false'. The return value can be a string or null.                                                                                                                                                                                                                  |
| ariaPressed      | string          | undefined | Indicates the current "pressed" state of toggle buttons. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                                                   |
| ariaHidden       | string          | undefined | Indicates whether an element that the button controls is expanded or collapsed. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                            |
| ariaCurrent      | string          | undefined | Indicates the element that represents the current item within a container or set of related elements.                                                                                                                                                                                                                                                                          |
| ariaKeyShortcuts | string          | undefined | Indicates keyboard shortcuts that an author has implemented to activate or give focus to an element.                                                                                                                                                                                                                                                                           |
| ariaHasPopup     | string          | undefined | Indicates that the button has an interactive popup element. Valid values are 'true', 'dialog', 'menu', 'listbox', 'tree', and 'grid' based on ARIA 1.1 specifications.                                                                                                                                                                                                         |
| ariaRelevant     | string          | undefined | Indicates what user agent change notifications (additions, removals, text, all) should be made to the accessibility tree. Valid values are 'additions', 'removals', 'text', 'all'.                                                                                                                                                                                             |
| ariaLive         | string          | undefined | Indicates that the button can be updated when it doesn't have focus. Valid values are 'polite', 'assertive', or 'off'. The polite value causes assistive technologies to notify users of updates at a low priority, generally without interrupting. The assertive value causes assistive technologies to notify users immediately, potentially clearing queued speech updates. |
| ariaAtomic       | string          | undefined | Indicates whether assistive technologies present all, or only parts of, the changed region. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                |
| ariaBusy         | string          | undefined | Indicates an element is being modified and that assistive technologies MAY want to wait until the modifications are complete before exposing them to the user. Valid values are 'true' or 'false'.                                                                                                                                                                             |
| groupOrder       | string          | ''        | Reserved for internal use only. Describes the order of this element (first, middle or last) inside lightning-button-group.                                                                                                                                                                                                                                                     |

### Methods

#### focus

- **Description:** Sets focus on the button.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a mouse click on the button.
- **Parameters:** None
- **Returns:** void

### Events

#### click

- **Description:** Fired when the button is clicked. This is a native DOM event that bubbles.
- **Payload:** Standard DOM click event

#### focus

- **Description:** Fired when the button receives focus.
- **Payload:** Standard DOM focus event

#### blur

- **Description:** Fired when the button loses focus.
- **Payload:** Standard DOM blur event

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** buttonGroup
- **Namespace:** lightning
- **Tag Name:** lightning-button-group
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A component that represents a set of buttons displayed together to create a navigational bar. It applies SLDS button group styling and manages the visual grouping of contained button components.

## API Reference

### Properties

This component has no public properties.

### Methods

None

### Events

None

### Slots

#### default

- **Description:** Accepts one or more button components. Supported components include lightning-button, lightning-button-icon, lightning-button-icon-stateful, lightning-button-menu, and lightning-button-stateful. The component automatically manages the groupOrder property on slotted elements to apply appropriate styling based on their position in the group (first, middle, last, or single).

---

# Component API Structure

## Basic Information

- **Name:** buttonIcon
- **Namespace:** lightning
- **Tag Name:** lightning-button-icon
- **Version:** 0.0
- **Type:** COMPONENT
- **Description:** An icon-only HTML button that executes an action in a controller. Only utility icons can be used in this component.

## API Reference

### Properties

| Name                        | Type              | Default   | Description                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------- | ----------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| name                        | string            | undefined | The name for the button element. This value is optional and can be used to identify the button in a callback.                                                                                                                                                                                                                                                                  |
| value                       | string            | undefined | The value for the button element. This value is optional and can be used when submitting a form.                                                                                                                                                                                                                                                                               |
| variant                     | string            | 'border'  | The variant changes the appearance of button-icon. Accepted variants include bare, container, brand, border, border-filled, bare-inverse, and border-inverse.                                                                                                                                                                                                                  |
| iconName                    | string            | undefined | The Lightning Design System name of the icon. Names are written in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed. Only utility icons can be used in this component.                                                                                                                                               |
| iconClass                   | string            | undefined | The class to be applied to the contained icon element. Only Lightning Design System utility classes are currently supported.                                                                                                                                                                                                                                                   |
| size                        | string            | 'medium'  | The size of the button-icon. For the bare variant, options include x-small, small, medium, and large. For non-bare variants, options include xx-small, x-small, small, and medium.                                                                                                                                                                                             |
| type                        | string            | 'button'  | Specifies the type of button. Valid values are button, reset, and submit.                                                                                                                                                                                                                                                                                                      |
| alternativeText             | string            | undefined | The alternative text used to describe the icon. This text should describe what happens when you click the button, for example 'Upload File', not what the icon looks like, 'Paperclip'.                                                                                                                                                                                        |
| tooltipType                 | string            | 'info'    | Reserved for internal use only. Specifies the type of tooltip to be used. Use info in cases where target already has click handlers. Use toggle in cases where target only shows a tooltip, such as helptext.                                                                                                                                                                  |
| disableAlternativeTextTitle | boolean           | false     | Reserved for internal use only. Disables the alternative text being used for the button title when the title has not been provided.                                                                                                                                                                                                                                            |
| tooltip                     | string            | undefined | Text to display when the user mouses over or focuses on the button. The tooltip is auto-positioned relative to the button and screen space.                                                                                                                                                                                                                                    |
| disabled                    | boolean           | false     | Specifies whether this button should be displayed in a disabled state. Disabled buttons can't be clicked.                                                                                                                                                                                                                                                                      |
| accessKey                   | string            | undefined | Specifies a shortcut key to activate or focus an element.                                                                                                                                                                                                                                                                                                                      |
| title                       | string            | undefined | Displays tooltip text when the mouse cursor moves over the element.                                                                                                                                                                                                                                                                                                            |
| ariaLabel                   | string            | undefined | Label describing the button to assistive technologies.                                                                                                                                                                                                                                                                                                                         |
| ariaLabelledBy              | string            | undefined | Specifies the ID or list of IDs of the element or elements that contain visible descriptive text to describe the button.                                                                                                                                                                                                                                                       |
| ariaDescribedBy             | string            | undefined | A space-separated list of element IDs that provide descriptive labels for the button.                                                                                                                                                                                                                                                                                          |
| ariaControls                | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaOwns                    | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaDetails                 | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaFlowTo                  | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaExpanded                | string \| boolean | undefined | Indicates whether an element that the button controls is expanded or collapsed. Valid values are 'true' or 'false'. The return value can be a string or null.                                                                                                                                                                                                                  |
| ariaPressed                 | string            | undefined | Indicates the current "pressed" state of toggle buttons. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                                                   |
| ariaHidden                  | string            | undefined | Indicates whether an element that the button controls is expanded or collapsed. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                            |
| ariaCurrent                 | string            | undefined | Indicates the element that represents the current item within a container or set of related elements.                                                                                                                                                                                                                                                                          |
| ariaKeyShortcuts            | string            | undefined | Indicates keyboard shortcuts that an author has implemented to activate or give focus to an element.                                                                                                                                                                                                                                                                           |
| ariaHasPopup                | string            | undefined | Indicates that the button has an interactive popup element. Valid values are 'true', 'dialog', 'menu', 'listbox', 'tree', and 'grid' based on ARIA 1.1 specifications.                                                                                                                                                                                                         |
| ariaRelevant                | string            | undefined | Indicates which types of changes to a live region are relevant. Valid values are 'additions', 'removals', 'text', 'all'.                                                                                                                                                                                                                                                       |
| ariaLive                    | string            | undefined | Indicates that the button can be updated when it doesn't have focus. Valid values are 'polite', 'assertive', or 'off'. The polite value causes assistive technologies to notify users of updates at a low priority, generally without interrupting. The assertive value causes assistive technologies to notify users immediately, potentially clearing queued speech updates. |
| ariaAtomic                  | string            | undefined | Indicates whether assistive technologies present all, or only parts of, the changed region. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                |
| ariaBusy                    | string            | undefined | Indicates an element is being modified and that assistive technologies MAY want to wait until the modifications are complete before exposing them to the user. Valid values are 'true' or 'false'.                                                                                                                                                                             |
| tabIndex                    | number            | 0         | Reserved for internal use only. Use the global tabindex attribute instead. Set tab index to -1 to prevent focus on the button during tab navigation. The default value is 0, which makes the button focusable during tab navigation.                                                                                                                                           |
| groupOrder                  | string            | ''        | Reserved for internal use only. Describes the order of this element (first, middle or last) inside lightning-button-group.                                                                                                                                                                                                                                                     |

### Methods

#### focus

- **Description:** Sets focus on the button.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a mouse click on the button.
- **Parameters:** None
- **Returns:** void

### Events

#### focus

- **Description:** Fired when the button receives focus.
- **Payload:** None

#### blur

- **Description:** Fired when the button loses focus.
- **Payload:**
  ```javascript
  {
    detail: {
      relatedTarget: Element; // The element receiving focus
    }
  }
  ```

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** buttonIconStateful
- **Namespace:** lightning
- **Tag Name:** lightning-button-icon-stateful
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** An icon-only button that retains state and can toggle between selected and unselected states. The button displays utility icons and supports various sizes and border variants. When selected, the button renders with aria-pressed="true", making it accessible to screen readers.

## API Reference

### Properties

| Name             | Type              | Default   | Description                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------- | ----------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| name             | string            | undefined | The name for the button element. This value is optional and can be used to identify the button in a callback.                                                                                                                                                                                                                                                                  |
| value            | string            | undefined | The value for the button element. This value is optional and can be used when submitting a form.                                                                                                                                                                                                                                                                               |
| variant          | string            | 'border'  | The variant changes the appearance of the button. Accepted variants include 'border', 'border-filled', and 'border-inverse'.                                                                                                                                                                                                                                                   |
| iconName         | string            | undefined | The Lightning Design System name of the icon. Names are written in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed. Only utility icons can be used in this component.                                                                                                                                               |
| size             | string            | 'medium'  | The size of the button-icon component. Options include 'xx-small', 'x-small', 'small', and 'medium'.                                                                                                                                                                                                                                                                           |
| alternativeText  | string            | undefined | The alternative text used to describe the icon. This text should describe what happens when you click the button, for example 'Upload File', not what the icon looks like, 'Paperclip'.                                                                                                                                                                                        |
| selected         | boolean           | false     | Specifies whether the button is in a selected state.                                                                                                                                                                                                                                                                                                                           |
| tooltip          | string            | undefined | Text to display when the user mouses over or focuses on the button. The tooltip is auto-positioned relative to the button and screen space.                                                                                                                                                                                                                                    |
| disabled         | boolean           | false     | Specifies whether this button should be displayed in a disabled state. Disabled buttons can't be clicked.                                                                                                                                                                                                                                                                      |
| accessKey        | string            | undefined | Specifies a shortcut key to activate or focus the button.                                                                                                                                                                                                                                                                                                                      |
| title            | string            | undefined | Displays tooltip text when the mouse cursor moves over the element.                                                                                                                                                                                                                                                                                                            |
| ariaLabel        | string            | undefined | Label describing the button to assistive technologies.                                                                                                                                                                                                                                                                                                                         |
| ariaLabelledBy   | string            | undefined | Specifies the ID or list of IDs of the element or elements that contain visible descriptive text to describe the button.                                                                                                                                                                                                                                                       |
| ariaDescribedBy  | string            | undefined | A space-separated list of element IDs that provide descriptive labels for the button.                                                                                                                                                                                                                                                                                          |
| ariaControls     | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaOwns         | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaDetails      | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaFlowTo       | string            | undefined | A space-separated list of element IDs whose presence or content is controlled by this button.                                                                                                                                                                                                                                                                                  |
| ariaExpanded     | string \| boolean | undefined | Indicates whether an element that the button controls is expanded or collapsed. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                            |
| ariaPressed      | string            | undefined | Indicates the current "pressed" state of toggle buttons. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                                                   |
| ariaHidden       | string            | undefined | Indicates whether an element that the button controls is expanded or collapsed. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                            |
| ariaCurrent      | string            | undefined | Indicates the element that represents the current item within a container or set of related elements.                                                                                                                                                                                                                                                                          |
| ariaKeyShortcuts | string            | undefined | Indicates keyboard shortcuts that an author has implemented to activate or give focus to an element.                                                                                                                                                                                                                                                                           |
| ariaHasPopup     | string            | undefined | Indicates that the button has an interactive popup element. Valid values are 'true', 'dialog', 'menu', 'listbox', 'tree', and 'grid' based on ARIA 1.1 specifications.                                                                                                                                                                                                         |
| ariaRelevant     | string            | undefined | Indicates what notifications the user agent will trigger when the accessibility tree within a live region is modified. Valid values are 'additions', 'removals', 'text', and 'all'.                                                                                                                                                                                            |
| ariaLive         | string            | undefined | Indicates that the button can be updated when it doesn't have focus. Valid values are 'polite', 'assertive', or 'off'. The polite value causes assistive technologies to notify users of updates at a low priority, generally without interrupting. The assertive value causes assistive technologies to notify users immediately, potentially clearing queued speech updates. |
| ariaAtomic       | string            | undefined | Indicates whether assistive technologies present all, or only parts of, the changed region. Valid values are 'true' or 'false'.                                                                                                                                                                                                                                                |
| ariaBusy         | string            | undefined | Indicates an element is being modified and that assistive technologies may want to wait until the modifications are complete before exposing them to the user. Valid values are 'true' or 'false'.                                                                                                                                                                             |
| groupOrder       | string            | ''        | Reserved for internal use only. Describes the order of this element (first, middle or last) inside lightning-button-group.                                                                                                                                                                                                                                                     |

### Methods

#### focus

- **Description:** Sets focus on the button.
- **Parameters:** None
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** buttonMenu
- **Namespace:** lightning
- **Tag Name:** lightning-button-menu
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Represents a dropdown menu with a list of actions or functions. The menu closes when you click away from it, and it also closes and puts the focus back on the button when you select a menu item.

## API Reference

### Properties

| Name                         | Type    | Default      | Description                                                                                                                                                                                                                 |
| ---------------------------- | ------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| internalDatatableActionsMenu | boolean | false        | For internal use only. If present, the dropdown arrow is removed when 'utility:threedots' is used. This is used when the button-menu is on a datatable.                                                                     |
| iconSize                     | string  | medium       | The size of the icon. Options include xx-small, x-small, small, medium, or large.                                                                                                                                           |
| iconName                     | string  | utility:down | The name of the icon to be used in the format 'utility:down'. If an icon other than 'utility:down' or 'utility:chevrondown' is used, a utility:down icon is appended to the right of that icon.                             |
| value                        | string  | ''           | The value for the button element. This value is optional and can be used when submitting a form.                                                                                                                            |
| alternativeText              | string  | 'Show menu'  | The assistive text for the button.                                                                                                                                                                                          |
| loadingStateAlternativeText  | string  | 'Loading'    | Message displayed while the menu is in the loading state.                                                                                                                                                                   |
| label                        | string  | null         | Optional text to be shown on the button.                                                                                                                                                                                    |
| draftAlternativeText         | string  | null         | Describes the reason for showing the draft indicator. This is required when is-draft is true.                                                                                                                               |
| groupOrder                   | string  | ''           | Reserved for internal use only. Describes the order of this element (first, middle or last) inside lightning-button-group.                                                                                                  |
| tabIndex                     | number  | undefined    | Reserved for internal use only. Should be set to -1 if button should not be focused when navigating with tab.                                                                                                               |
| variant                      | string  | border       | The variant changes the look of the button. Accepted variants include bare, container, border, border-filled, bare-inverse, and border-inverse.                                                                             |
| menuAlignment                | string  | left         | Determines the alignment of the menu relative to the button. Available options are: auto, left, center, right, bottom-left, bottom-center, bottom-right. The auto option aligns the dropdown menu based on available space. |
| disabled                     | boolean | false        | If present, the menu cannot be opened by users.                                                                                                                                                                             |
| nubbin                       | boolean | false        | If present, a nubbin is present on the menu. A nubbin is a stub that protrudes from the menu item towards the button menu. The nubbin position is based on the menu-alignment.                                              |
| title                        | string  | null         | Displays tooltip text when the mouse moves over the button menu.                                                                                                                                                            |
| isDraft                      | boolean | false        | If present, the menu trigger shows a draft indicator.                                                                                                                                                                       |
| isLoading                    | boolean | false        | If present, the menu is in a loading state and shows a spinner.                                                                                                                                                             |
| accessKey                    | string  | null         | The keyboard shortcut for the button menu.                                                                                                                                                                                  |
| tooltip                      | string  | undefined    | Text to display when the user mouses over or focuses on the button. The tooltip is auto-positioned relative to the button and screen space.                                                                                 |

### Methods

#### focus

- **Description:** Sets focus on the button.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a mouse click on the button.
- **Parameters:** None
- **Returns:** void

### Events

#### select

- **Description:** The event fired when a menu item is selected.
- **Payload:**
  ```javascript
  {
    value: string; // The value of the selected menu item
  }
  ```

#### open

- **Description:** The event fired when the dropdown menu is opened by clicking the button or pressing Enter while the button has focus.
- **Payload:** None

#### close

- **Description:** The event fired when the dropdown menu is closed by selecting a menu item, clicking the button again, or removing focus from the dropdown menu.
- **Payload:** None

#### focus

- **Description:** The event fired when the button receives focus.
- **Payload:** None

#### blur

- **Description:** The event fired when the button loses focus.
- **Payload:** None

### Slots

#### default

- **Description:** Placeholder for menu-item components. Use lightning-menu-item components nested in lightning-button-menu to specify the menu items for the button menu. You can also use lightning-menu-divider to create dividing lines and lightning-menu-subheader to create subheadings in the list of menu items.

---

# Component API Structure

## Basic Information

- **Name:** buttonStateful
- **Namespace:** lightning
- **Tag Name:** lightning-button-stateful
- **Version:** GA
- **Type:** COMPONENT
- **Description:** A button that toggles between states, similar to a Like button on social media. Stateful buttons can show a different label and icon based on their selected states.

## API Reference

### Properties

| Name              | Type    | Default   | Description                                                                                                                                                      |
| ----------------- | ------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| disabled          | boolean | undefined | If present, the button is disabled and users cannot interact with it.                                                                                            |
| iconNameWhenOn    | string  | undefined | The name of the icon to be used in the format 'utility:check' when the state is true.                                                                            |
| iconNameWhenOff   | string  | undefined | The name of the icon to be used in the format 'utility:add' when the state is false.                                                                             |
| iconNameWhenHover | string  | undefined | The name of the icon to be used in the format 'utility:close' when the state is true and the button receives focus. If not provided, defaults to iconNameWhenOn. |
| labelWhenOff      | string  | undefined | Required. The text to be displayed inside the button when state is false.                                                                                        |
| labelWhenOn       | string  | undefined | Required. The text to be displayed inside the button when state is true.                                                                                         |
| labelWhenHover    | string  | undefined | The text to be displayed inside the button when state is true and the button receives focus. If not provided, defaults to labelWhenOn.                           |
| groupOrder        | string  | ''        | Reserved for internal use only. Describes the order of this element (first, middle or last) inside lightning-button-group.                                       |
| variant           | string  | 'neutral' | The variant changes the appearance of the button. Accepted variants include brand, destructive, inverse, neutral, success, and text.                             |
| selected          | boolean | false     | If present, the button is in the selected state.                                                                                                                 |

### Methods

#### focus

- **Description:** Sets focus on the button.
- **Parameters:** None
- **Returns:** void

### Events

#### blur

- **Description:** Fired when the button loses focus.
- **Payload:** None

#### focus

- **Description:** Fired when the button receives focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** card
- **Namespace:** lightning
- **Tag Name:** lightning-card
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Cards apply a container around a related grouping of information.

## API Reference

### Properties

| Name         | Type             | Default   | Description                                                                                                                                                                                                                         |
| ------------ | ---------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| title        | string           | undefined | The title can include text, and is displayed in the header. To include additional markup or another component, use the title slot.                                                                                                  |
| iconName     | string           | undefined | The Lightning Design System name of the icon. Specify the name in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed. The icon is displayed in the header before the title. |
| variant      | string           | base      | The variant changes the appearance of the card. Accepted variants include base or narrow. This value defaults to base.                                                                                                              |
| headingLevel | string \| number | 2         | The headingLevel changes the 'aria-level' attribute value of the h2 tag in the markup for the card's title element. It can take values of 1, 2, 3, 4, 5, or 6.                                                                      |
| label        | string           | undefined | Assistive label for the card header. Only shown if `hideHeader` attribute is set to `true`.                                                                                                                                         |
| hideHeader   | boolean          | false     | Hides the header chunk of the card when set to `true`. Requires you to set the `label` attribute to supplement a non-rendered header. If `label` isn't set, you get a `console.warn` error.                                         |

### Methods

None

### Events

None

### Slots

#### default

- **Description:** Placeholder for your content in the card body.

#### title

- **Description:** Placeholder for the card title, which can be represented by a header or h1 element. The title is displayed at the top of the card, after the icon. Alternatively, use the title attribute if you don't need to pass in extra markup in your title.

#### actions

- **Description:** Placeholder for actionable components, such as lightning-button or lightning-button-menu. Actions are displayed on the top corner of the card after the title.

#### footer

- **Description:** Placeholder for the card footer, which is displayed at the bottom of the card and is usually optional. For example, the footer can display a "View All" link to navigate to a list view.

---

# Component API Structure

## Basic Information

- **Name:** checkboxGroup
- **Namespace:** lightning
- **Tag Name:** lightning-checkbox-group
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A checkbox group that enables selection of single or multiple options.

## API Reference

### Properties

| Name                    | Type    | Default  | Description                                                                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| label                   | string  | null     | Text label for the checkbox group. Required.                                                                                                                                                                                                                                                                                                                       |
| options                 | array   | null     | Array of label-value pairs for each checkbox. Each option object should contain `label` (string) and `value` (string) properties. Required.                                                                                                                                                                                                                        |
| name                    | string  | null     | The name of the checkbox group. Required.                                                                                                                                                                                                                                                                                                                          |
| value                   | array   | null     | The list of selected checkboxes. Each array entry contains the value of a selected checkbox. The value of each checkbox is set in the options attribute. Required.                                                                                                                                                                                                 |
| disabled                | boolean | false    | If present, the checkbox group is disabled. Checkbox selections can't be changed for a disabled checkbox group.                                                                                                                                                                                                                                                    |
| required                | boolean | false    | If present, at least one checkbox must be selected.                                                                                                                                                                                                                                                                                                                |
| variant                 | string  | standard | The variant changes the appearance of the checkbox group. Accepted variants include standard, label-hidden, label-inline, and label-stacked. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and checkbox group. Use label-stacked to place the label above the checkbox group. |
| messageWhenValueMissing | string  | null     | Optional message to be displayed when no checkbox is selected and the required attribute is set.                                                                                                                                                                                                                                                                   |
| validity                | object  | null     | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation. Returns the ValidityState object for the checkbox group.                                                                                                                                                                                               |

### Methods

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the checkbox group meets all constraint validations.

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when the checkbox value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### showHelpMessageIfInvalid

- **Description:** Displays an error message if the checkbox value is required and no option is selected.
- **Parameters:** None
- **Returns:** void

#### focus

- **Description:** Sets focus on the first checkbox input element.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** Fired when the selection of checkboxes changes. The event bubbles and is composed.
- **Payload:**
  ```javascript
  {
    value: array; // Array of values of all selected checkboxes
  }
  ```

#### focus

- **Description:** Fired when the checkbox group receives focus.
- **Payload:** None

#### blur

- **Description:** Fired when the checkbox group loses focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** clickToDial
- **Namespace:** lightning
- **Tag Name:** lightning-click-to-dial
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Renders a formatted phone number as click-to-dial enabled or disabled for Open CTI and Voice. The component respects any existing click-to-dial commands for computer-telephony integrations (CTI) with Salesforce. Phone numbers are automatically formatted following the North American format (123 456 7890).

## API Reference

### Properties

| Name     | Type   | Default | Description                                                                                                                                                                                                                                                                                                 |
| -------- | ------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value    | string | null    | The phone number to be dialed. This property is required.                                                                                                                                                                                                                                                   |
| recordId | string | null    | The Salesforce record Id that's associated with the phone number. This Id is passed by the component and does not get validated. If provided, the payload passed to the Open CTI method `onClickToDial` contains the record information associated with this record ID (e.g., record name and object type). |
| params   | string | null    | Comma-separated list of parameters to pass to the third-party phone system.                                                                                                                                                                                                                                 |

### Methods

#### click

- **Description:** Dials the phone number by passing the parameters and recordId to the phone system if they are provided. Only an enabled phone number can be clicked.
- **Parameters:** None
- **Returns:** void

### Events

This component does not dispatch any public events.

### Slots

This component does not support any slots.

---

# Component API Structure

## Basic Information

- **Name:** combobox
- **Namespace:** lightning
- **Tag Name:** lightning-combobox
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A widget that provides an input field that is readonly, accompanied by a dropdown list of selectable options.

## API Reference

### Properties

| Name                    | Type     | Default            | Description                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------- | -------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| autocomplete            | string   | undefined          | Reserved for internal use. Controls auto-filling of the field.                                                                                                                                                                                                                                                                                                                    |
| ariaInvalid             | boolean  | undefined          | A Boolean value for aria-invalid.                                                                                                                                                                                                                                                                                                                                                 |
| label                   | string   | undefined          | Text label for the combobox.                                                                                                                                                                                                                                                                                                                                                      |
| dropdownAlignment       | string   | 'left'             | Specifies where the drop-down list is aligned with or anchored to the selection field. By default the list is aligned with the selection field at the top left so the list opens down. Use bottom-left to make the selection field display at the bottom so the list opens above it. Use auto to let the component determine where to open the list based on space available.     |
| placeholder             | string   | 'Select an Option' | Text that is displayed before an option is selected, to prompt the user to select an option.                                                                                                                                                                                                                                                                                      |
| messageWhenValueMissing | string   | undefined          | Error message to be displayed when the value is missing and input is required.                                                                                                                                                                                                                                                                                                    |
| name                    | string   | undefined          | Specifies the name of the combobox.                                                                                                                                                                                                                                                                                                                                               |
| ariaLabelledBy          | string   | ''                 | Reserved for internal use. Use the standard aria-labelledby instead. A space-separated list of element IDs that provide labels for the combobox.                                                                                                                                                                                                                                  |
| ariaDescribedBy         | string   | ''                 | Reserved for internal use. Use the standard aria-describedby instead. A space-separated list of element IDs that provide descriptive labels for the combobox.                                                                                                                                                                                                                     |
| fieldLevelHelp          | string   | undefined          | Help text detailing the purpose and function of the combobox.                                                                                                                                                                                                                                                                                                                     |
| variant                 | string   | 'standard'         | The variant changes the appearance of the combobox. Accepted variants include standard, label-hidden, label-inline, and label-stacked. This value defaults to standard. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and combobox. Use label-stacked to place the label above the combobox. |
| value                   | object   | undefined          | Specifies the value of an input element.                                                                                                                                                                                                                                                                                                                                          |
| options                 | object[] | []                 | A list of options that are available for selection. Each option has the following attributes: label and value.                                                                                                                                                                                                                                                                    |
| disabled                | boolean  | false              | If present, the combobox is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                                           |
| readOnly                | boolean  | false              | If present, the combobox is read-only. A read-only combobox is also disabled.                                                                                                                                                                                                                                                                                                     |
| required                | boolean  | false              | If present, a value must be selected before the form can be submitted.                                                                                                                                                                                                                                                                                                            |
| spinnerActive           | boolean  | false              | If present, a spinner is displayed below the menu items to indicate loading activity.                                                                                                                                                                                                                                                                                             |
| validity                | object   | undefined          | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                                       |

### Methods

#### focus

- **Description:** Sets focus on the combobox.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes focus from the combobox.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the combobox has any validity errors.

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the combobox.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when the combobox value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### showHelpMessageIfInvalid

- **Description:** Shows the help message if the combobox is in an invalid state.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** The event fired when an item is selected in the combobox.
- **Payload:**
  ```javascript
  {
    value: string; // The value of the selected option
  }
  ```

#### focus

- **Description:** The event fired when the combobox receives focus.
- **Payload:** None

#### blur

- **Description:** The event fired when the combobox loses focus.
- **Payload:** None

#### open

- **Description:** The event fired when the dropdown is opened.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** confirm
- **Namespace:** lightning
- **Tag Name:** lightning-confirm
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Create a confirm modal within your component that asks the user to respond before they continue. Use `LightningConfirm.open()` instead of the native `window.confirm()` for a more consistent user experience. Returns a Promise that resolves to true when OK is clicked and false when Cancel is clicked.

## API Reference

### Properties

| Name    | Type   | Default                | Description                                                                                                                                                 |
| ------- | ------ | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label   | string | "Confirm" (translated) | Value to use for header text in "header" variant or aria-label in "headerless" variant.                                                                     |
| message | string | ''                     | Text to display in the confirm modal.                                                                                                                       |
| variant | string | 'header'               | Variant to use for the confirm modal. Valid values are "header" and "headerless".                                                                           |
| theme   | string | 'default'              | Theme to use when variant is "header". Valid values are "default", "shade", "inverse", "alt-inverse", "success", "info", "warning", "error", and "offline". |

### Methods

#### open

- **Description:** Opens a confirm modal instance with the specified configuration. This is a static method called on the LightningConfirm class rather than an instance.
- **Parameters:**
  - `apis` (Object, optional): Configuration object containing properties to set on the modal instance (label, message, variant, theme)
- **Returns:** Promise that resolves to true when OK is clicked and false when Cancel is clicked

#### close

- **Description:** Closes the confirm modal and returns the result. This method is public for testing only.
- **Parameters:**
  - `result` (any, optional): Value to be returned in the promise
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** datatable
- **Namespace:** lightning
- **Tag Name:** lightning-datatable
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A table that displays rows and columns of data. Supports features including displaying and formatting of columns with appropriate data types, infinite scrolling of rows, inline editing for some data types, header actions, header wrapping, row-level actions, resizing of columns, selecting of rows, sorting of columns by ascending and descending order, text wrapping and clipping, row numbering column, and cell content alignment.

## API Reference

### Properties

| Name                   | Type            | Default   | Description                                                                                                                                                                                                                            |
| ---------------------- | --------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ariaLabel              | string          | null      | Aria-label attribute passed down to the child table element                                                                                                                                                                            |
| ariaLabelledBy         | string          | null      | Aria-labelledby attribute passed down to the child table element                                                                                                                                                                       |
| columnWidthsMode       | string          | 'fixed'   | Specifies how column widths are calculated. Valid values: 'fixed' (columns with equal widths) or 'auto' (column widths based on content and table width)                                                                               |
| columns                | array           | []        | Array of the columns object that defines the data types. Required properties include 'label', 'fieldName', and 'type'. The default type is 'text'                                                                                      |
| data                   | array           | []        | The array of data to be displayed                                                                                                                                                                                                      |
| defaultSortDirection   | string          | 'asc'     | Specifies the default sorting direction on an unsorted column. Valid values: 'asc' or 'desc'                                                                                                                                           |
| disabledRows           | array           | []        | List of key-field values for rows to disable programmatically                                                                                                                                                                          |
| draftValues            | array           | []        | The current values per row that are provided during inline edit                                                                                                                                                                        |
| enableInfiniteLoading  | boolean         | false     | If present, you can load a subset of data and display more when users scroll to the end of the table. Use with the loadmore event handler                                                                                              |
| errors                 | object          | {}        | Object containing information about cell level, row level, and table level errors. When set, error messages are displayed on the table accordingly                                                                                     |
| hideBorders            | boolean         | false     | If present, the table borders are hidden. Only valid when hide-table-header is true                                                                                                                                                    |
| hideCheckboxColumn     | boolean         | false     | If present, the checkbox or radio button column for row selection is hidden                                                                                                                                                            |
| hideTableHeader        | boolean         | false     | If present, the table header is hidden                                                                                                                                                                                                 |
| isLoading              | boolean         | false     | If present, a spinner is shown to indicate that more data is loading                                                                                                                                                                   |
| keyField               | string          | undefined | Required for better performance. Associates each row with a unique ID. Key-field is case sensitive and must match the value in the data array                                                                                          |
| loadMoreOffset         | number          | 20        | Determines when to trigger infinite loading based on how many pixels the table's scroll position is from the bottom of the table                                                                                                       |
| maxColumnWidth         | number          | 1000      | The maximum width for all columns in pixels                                                                                                                                                                                            |
| maxEditLimit           | number          | null      | Reserved for internal use. The maximum number of distinct rows that can have draft values (be edited) at the time of a save                                                                                                            |
| maxRowSelection        | number          | undefined | The maximum number of rows that can be selected. Value should be a positive integer. Checkboxes are used for selection by default, and radio buttons are used when maxRowSelection is 1 unless overridden using singleRowSelectionMode |
| minColumnWidth         | number          | 50        | The minimum width for all columns in pixels                                                                                                                                                                                            |
| renderConfig           | object          | undefined | Reserved for internal use. Enables and configures advanced rendering modes. Valid properties are 'bufferSize', 'rowHeight', 'viewportRendering', and 'virtualize'                                                                      |
| renderMode             | string          | 'default' | Opts-in to a more performant table rendering mode. Valid values: 'default' (traditional DOM structure) or 'inline' (simplified DOM structure that improves performance but may break some custom styling)                              |
| resizeColumnDisabled   | boolean         | false     | If present, column resizing is disabled                                                                                                                                                                                                |
| resizeStep             | number          | 10        | The width to resize the column when a user presses left or right arrow in pixels                                                                                                                                                       |
| rowNumberOffset        | number          | 0         | Determines where to start counting the row number                                                                                                                                                                                      |
| rowToggleIcon          | object          | {}        | Reserved for internal use                                                                                                                                                                                                              |
| selectedRows           | array           | []        | List of key-field values for rows to select programmatically                                                                                                                                                                           |
| showActionsMenu        | boolean         | false     | If present, the actions menu is displayed to enable users to do advanced sorting                                                                                                                                                       |
| showRowNumberColumn    | boolean         | false     | If present, the row numbers are shown in the first column                                                                                                                                                                              |
| singleRowSelectionMode | string          | 'radio'   | Specifies whether to render checkboxes instead of radio buttons when max-row-selection is 1. Valid values: 'radio' or 'checkbox'                                                                                                       |
| sortedBy               | string or array | undefined | The column key or fieldName(s) that controls the sorting order. Sort the data using the sort event handler                                                                                                                             |
| sortedDirection        | string or array | undefined | Specifies the sorting direction. Valid values: 'asc' or 'desc' or an array of such values. Sort the data using the sort event handler                                                                                                  |
| suppressBottomBar      | boolean         | false     | If present, the footer that displays the Save and Cancel buttons is hidden during inline editing                                                                                                                                       |
| wrapTableHeader        | string          | 'none'    | Specifies how the table header is wrapped. Valid values: 'all' (wrap all column headers), 'none' (clip all column headers), or 'by-column' (wrap/clip column headers based on the wrap/clip setting for that individual column)        |
| wrapTextMaxLines       | number          | undefined | The number of lines after which the content will be cut off and hidden. Must be at least 1 or more. The text in the last line is truncated and shown with an ellipsis                                                                  |

### Methods

#### focus

- **Description:** Focuses the current active cell in the datatable
- **Parameters:** None
- **Returns:** void

#### getSelectedRows

- **Description:** Returns data in each selected row
- **Parameters:** None
- **Returns:** array - An array of data in each selected row

#### openInlineEdit

- **Description:** Opens the inline edit panel for the datatable's currently active cell. If the active cell is not editable, then the panel is opened for the first editable cell in the table. If there is no data or no editable cells, this results in a no-op
- **Parameters:** None
- **Returns:** void

#### scrollToTop

- **Description:** Scrolls to the top of the datatable
- **Parameters:** None
- **Returns:** void

### Events

#### cancel

- **Description:** The event fired when the cancel button is pressed during inline editing
- **Payload:** None

#### cellchange

- **Description:** The event fired when a cell value changes during inline editing
- **Payload:**
  ```javascript
  {
    draftValues: array; // The current values provided during inline editing
  }
  ```

#### headeraction

- **Description:** The event fired when a header action is selected, such as text wrapping, text clipping, or a custom header action
- **Payload:**
  ```javascript
  {
    action: object, // The action definition
    columnDefinition: object // The column definition specified in the columns property
  }
  ```

#### loadmore

- **Description:** The event fired when you scroll to the bottom of the table to load more data, until there are no more data to load
- **Payload:**
  ```javascript
  {
    enableInfiniteLoading: boolean, // Specifies whether infinite loading is available on the table
    isLoading: boolean, // Specifies that data is loading and displays a spinner on the table
    loadMoreOffset: number // The number of pixels between the bottom of the table and the current scroll position
  }
  ```

#### resize

- **Description:** The event fired when a table column is resized. In fixed width mode, fires on initial render, manual resize, or when the number of columns changes. In auto width mode, fires only on manual resize
- **Payload:**
  ```javascript
  {
    columnWidths: array, // The width of all columns in pixels
    isUserTriggered: boolean // Specifies whether the column resize is caused by a user action
  }
  ```

#### rowaction

- **Description:** The event fired when a row-level action is triggered from the action column
- **Payload:**
  ```javascript
  {
    action: object, // The action object that was selected
    row: object // The data in the row where the action was triggered
  }
  ```

#### rowselection

- **Description:** The event fired when a row is selected via checkbox or radio button
- **Payload:**
  ```javascript
  {
    selectedRows: array, // The data in the rows that are selected
    config: {
      action: string, // The type of selection event: 'selectAllRows', 'deselectAllRows', 'rowSelect', or 'rowDeselect'
      value: string // The id value of the row that was toggled (available for rowSelect and rowDeselect actions)
    }
  }
  ```

#### save

- **Description:** The event fired when data is saved during inline editing
- **Payload:**
  ```javascript
  {
    draftValues: array; // The current values provided during inline editing
  }
  ```

#### sort

- **Description:** The event fired when a column is sorted
- **Payload:**
  ```javascript
  {
    fieldName: string, // The fieldName that controls the sorting
    columnKey: string, // The column key
    sortDirection: string, // The sorting direction: 'asc' or 'desc'
    fieldNames: array, // Array of fieldNames
    sortDirections: array, // Array of sort directions
    isMultiColumnSort: boolean // Reserved for internal use, defaults to false
  }
  ```

### Slots

#### customdatatypes

- **Description:** Slot for defining custom data types. Allows extending the datatable with custom cell types beyond the built-in types

---

# Component API Structure

## Basic Information

- **Name:** dualListbox
- **Namespace:** lightning
- **Tag Name:** lightning-dual-listbox
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A pair of listboxes that enables multiple options to be selected and reordered.

## API Reference

### Properties

| Name                      | Type     | Default                      | Description                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------- | -------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| label                     | string   | null                         | (Required) Label for the dual listbox.                                                                                                                                                                                                                                                                                                                       |
| sourceLabel               | string   | null                         | (Required) Label for the source options listbox.                                                                                                                                                                                                                                                                                                             |
| selectedLabel             | string   | null                         | (Required) Label for the selected options listbox.                                                                                                                                                                                                                                                                                                           |
| options                   | object[] | null                         | (Required) A list of options that are available for selection. Each option has the following attributes: label and value.                                                                                                                                                                                                                                    |
| name                      | string   | null                         | Specifies the name of an input element.                                                                                                                                                                                                                                                                                                                      |
| value                     | list     | []                           | A list of default options that are included in the selected options listbox. This list is populated with values from the options attribute.                                                                                                                                                                                                                  |
| requiredOptions           | list     | []                           | A list of required options that cannot be removed from selected options listbox. This list is populated with values from the options attribute.                                                                                                                                                                                                              |
| min                       | number   | 0                            | Minimum number of options required in the selected options listbox.                                                                                                                                                                                                                                                                                          |
| max                       | number   | null                         | Maximum number of options allowed in the selected options listbox.                                                                                                                                                                                                                                                                                           |
| disabled                  | boolean  | false                        | If present, the listbox is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                       |
| required                  | boolean  | false                        | If present, the user must add an item to the selected listbox before submitting the form.                                                                                                                                                                                                                                                                    |
| variant                   | string   | standard                     | The variant changes the appearance of the dual listbox. Accepted variants include standard, label-hidden, label-inline, and label-stacked. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and dual listbox. Use label-stacked to place the label above the dual listbox. |
| size                      | number   | null                         | Number of items that display in the listboxes before vertical scrollbars are displayed. Determines the vertical size of the listbox.                                                                                                                                                                                                                         |
| fieldLevelHelp            | string   | null                         | Help text detailing the purpose and function of the dual listbox.                                                                                                                                                                                                                                                                                            |
| disableReordering         | boolean  | false                        | If present, the Up and Down buttons used for reordering the selected list items are hidden.                                                                                                                                                                                                                                                                  |
| showActivityIndicator     | boolean  | false                        | If present, a spinner is displayed in the first listbox to indicate loading activity.                                                                                                                                                                                                                                                                        |
| messageWhenValueMissing   | string   | "An option must be selected" | Error message to be displayed when the value is missing and input is required.                                                                                                                                                                                                                                                                               |
| messageWhenRangeOverflow  | string   | (computed)                   | Error message to be displayed when a range overflow is detected.                                                                                                                                                                                                                                                                                             |
| messageWhenRangeUnderflow | string   | (computed)                   | Error message to be displayed when a range underflow is detected.                                                                                                                                                                                                                                                                                            |
| addButtonLabel            | string   | (computed)                   | Label for add button. Default: "Move to {selectedLabel}".                                                                                                                                                                                                                                                                                                    |
| removeButtonLabel         | string   | (computed)                   | Label for remove button. Default: "Move to {sourceLabel}".                                                                                                                                                                                                                                                                                                   |
| upButtonLabel             | string   | "Move selection up"          | Label for up button.                                                                                                                                                                                                                                                                                                                                         |
| downButtonLabel           | string   | "Move selection down"        | Label for down button.                                                                                                                                                                                                                                                                                                                                       |
| validity                  | object   | null                         | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                  |

### Methods

#### focus

- **Description:** Sets focus on the first option from either list. If the source list doesn't contain any options, the first option on the selected list is focused on.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the dual listbox meets all constraint validations.

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when the dual listbox value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### showHelpMessageIfInvalid

- **Description:** Displays an error message if the dual listbox value is required.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** The event fired when an item is selected in the combobox. The change event is triggered when you click the left and right buttons to move options from one list to another or when you change the order of options in the selected options list.
- **Payload:**
  ```javascript
  {
    value: string[] // An array of selected option values
  }
  ```

#### focus

- **Description:** The event fired when the component receives focus.
- **Payload:** None

#### blur

- **Description:** The event fired when the component loses focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** dynamicIcon
- **Namespace:** lightning
- **Tag Name:** lightning-dynamic-icon
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Represents various animated icons with different states. Visually indicates an event that's in progress, such as a graph that's loading.

## API Reference

### Properties

| Name            | Type   | Default        | Description                                                                                                                                                                                                                                                                                                                                                  |
| --------------- | ------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| alternativeText | string | undefined      | The alternative text used to describe the dynamic icon. This text should describe what's happening (e.g., 'Graph is refreshing'), not what the icon looks like.                                                                                                                                                                                              |
| type            | string | undefined      | The Lightning Design System name of the dynamic icon. Valid values are: ellie, eq, score, strength, trend, and waffle. This property is required.                                                                                                                                                                                                            |
| option          | string | varies by type | Changes the appearance of the dynamic icon. The options available depend on the type: eq supports "play" (default) or "stop"; score supports "positive" (default) or "negative"; strength supports "-3", "-2", "-1", "0" (default), "1", "2", "3"; trend supports "neutral" (default), "up", or "down". The ellie and waffle types do not use this property. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** fileUpload
- **Namespace:** lightning
- **Tag Name:** lightning-file-upload
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A file uploader for uploading and attaching files to records.

## API Reference

### Properties

| Name           | Type    | Default   | Description                                                                                                            |
| -------------- | ------- | --------- | ---------------------------------------------------------------------------------------------------------------------- |
| name           | string  | undefined | Specifies the name of the input element. Required.                                                                     |
| label          | string  | undefined | The text label for the file uploader. Required.                                                                        |
| accept         | list    | undefined | Comma-separated list of file extensions that can be uploaded in the format ['.ext'], such as ['.pdf', '.jpg', '.png']. |
| recordId       | string  | undefined | The record Id of the record that the uploaded file is associated to.                                                   |
| disabled       | boolean | false     | Specifies whether this component should be displayed in a disabled state. Disabled components can't be clicked.        |
| multiple       | boolean | false     | Specifies whether a user can upload more than one file simultaneously.                                                 |
| fileFieldName  | string  | undefined | Name of a custom field on the ContentVersion object. Set its value with the file-field-value attribute.                |
| fileFieldValue | string  | undefined | Value to store in the custom field specified by file-field-name for the uploaded file.                                 |
| required       | boolean | false     | If present, the file-upload field is set to required as true.                                                          |
| ariaInvalid    | boolean | undefined | A Boolean value for aria-invalid.                                                                                      |

### Methods

#### focus

- **Description:** Focuses on the lightning-input when called.
- **Parameters:** None
- **Returns:** void

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - Returns true if the input field is valid.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when a form is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

### Events

#### uploadfinished

- **Description:** The event fired when files are uploaded successfully.
- **Payload:**
  ```javascript
  {
    files: array; // The list of files that are uploaded. Each file contains name (string) and documentId (string). If a guest user performed the file upload, the documentId isn't returned.
  }
  ```

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedAddress
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-address
- **Version:** 42.0
- **Type:** COMPONENT
- **Description:** Displays a formatted address in a format and field order determined by the user's Salesforce locale. By default, the address is displayed as a link that opens the location in Google Maps in a new tab. The component can optionally display a static map image using Google Maps.

## API Reference

### Properties

| Name          | Type    | Default    | Description                                                                                                                                                                                                                       |
| ------------- | ------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| street        | string  | ''         | The street detail for the address                                                                                                                                                                                                 |
| city          | string  | ''         | The city detail for the address                                                                                                                                                                                                   |
| province      | string  | ''         | The province detail for the address                                                                                                                                                                                               |
| country       | string  | ''         | The country detail for the address                                                                                                                                                                                                |
| postalCode    | string  | ''         | The postal code detail for the address                                                                                                                                                                                            |
| latitude      | number  | ''         | The latitude of the location if known. Latitude values must be within -90 and 90. When provided with longitude, the map link uses coordinates instead of the address string for faster rendering                                  |
| longitude     | number  | ''         | The longitude of the location if known. Longitude values must be within -180 and 180. When provided with latitude, the map link uses coordinates instead of the address string for faster rendering                               |
| disabled      | boolean | false      | If present, the address is displayed as plain text and cannot be clicked or focused on                                                                                                                                            |
| variant       | string  | 'truncate' | Whether the slds-truncate class is assigned to each address line. Accepted values are 'truncate' and 'plain'. The 'truncate' variant applies the slds-truncate class to each line, while 'plain' renders lines without truncation |
| showStaticMap | boolean | false      | Displays a static map of the location using Google Maps                                                                                                                                                                           |
| locale        | string  | 'en-US'    | The locale of the address. Determines the format and field order of the displayed address                                                                                                                                         |

### Methods

#### click

- **Description:** Simulates a mouse click on the address and navigates to Google Maps in a new tab
- **Parameters:** None
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedDateTime
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-date-time
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Displays formatted date and time using the Intl.DateTimeFormat JavaScript object. The locale set in the Salesforce user preferences determines the default formatting. Supports Date objects, ISO8601 formatted strings, and timestamps as input values.

## API Reference

### Properties

| Name         | Type    | Default   | Description                                                                                                                                                                                                                                                                                                                                                |
| ------------ | ------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value        | object  | undefined | The value to be formatted, which can be a Date object, timestamp, or an ISO8601 formatted string.                                                                                                                                                                                                                                                          |
| weekday      | string  | undefined | Specifies how to display the day of the week. Allowed values are narrow, short, or long.                                                                                                                                                                                                                                                                   |
| era          | string  | undefined | Specifies how to display the era. Allowed values are narrow, short, or long.                                                                                                                                                                                                                                                                               |
| year         | string  | undefined | Specifies how to display the year. Allowed values are numeric or 2-digit.                                                                                                                                                                                                                                                                                  |
| month        | string  | undefined | Specifies how to display the month. Allowed values are 2-digit, numeric, narrow, short, or long.                                                                                                                                                                                                                                                           |
| day          | string  | undefined | Specifies how to display the day. Allowed values are numeric or 2-digit.                                                                                                                                                                                                                                                                                   |
| hour         | string  | undefined | Specifies how to display the hour. Allowed values are numeric or 2-digit.                                                                                                                                                                                                                                                                                  |
| minute       | string  | undefined | Specifies how to display the minute. Allowed values are numeric or 2-digit.                                                                                                                                                                                                                                                                                |
| second       | string  | undefined | Specifies how to display the second. Allowed values are numeric or 2-digit.                                                                                                                                                                                                                                                                                |
| timeZoneName | string  | undefined | Specifies how to display the time zone name. Allowed values are short or long. For example, the Pacific time zone would display as 'PST' if you specify 'short', or 'Pacific Standard Time' if you specify 'long.'                                                                                                                                         |
| timeZone     | string  | undefined | The time zone for date and time display. Use this attribute only if you want to override the default, which is the time zone set on the user device. Specify a time zone from the IANA time zone database (https://www.iana.org/time-zones). For example, set the value to 'Pacific/Honolulu' to display Hawaii time. The short code UTC is also accepted. |
| hour12       | boolean | undefined | Determines whether time is displayed as 12-hour. If false, time displays as 24-hour. The default setting is determined by the user's locale. Set the value using a variable. If set to any string directly, the component interprets its value as true. If set to undefined, the locale default is used.                                                   |
| dateStyle    | string  | medium    | The date formatting style to use. Allowed values are short, medium, or long. Use with the time-zone, time-zone-name, or hour12 attributes only.                                                                                                                                                                                                            |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedEmail
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-email
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Displays an email address as a hyperlink with the mailto: URL scheme. Clicking on the email address opens the default mail application for the desktop or mobile device.

## API Reference

### Properties

| Name     | Type    | Default   | Description                                                                                                                                                                                                                                |
| -------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| value    | string  | undefined | The email address that's displayed if a label is not provided. Can be a single email or multiple emails separated by commas. Can include query parameters for cc, subject, and body.                                                       |
| label    | string  | undefined | The text label for the email address. If not provided, the value is displayed as the label.                                                                                                                                                |
| tabIndex | number  | undefined | Indicates if an element should be focusable. A value of 0 means the element is focusable and participates in sequential keyboard navigation. A value of -1 means the element is focusable but does not participate in keyboard navigation. |
| hideIcon | boolean | false     | If present, the email icon is hidden and only the email address is displayed.                                                                                                                                                              |

### Methods

#### focus

- **Description:** Sets focus on the element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the element.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a mouse click on the email address and opens the default email app.
- **Parameters:** None
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedLocation
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-location
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Displays a read-only representation of a geolocation in decimal degrees using the format [latitude, longitude]. If one of the values is invalid or outside the allowed range, this component doesn't display anything.

## API Reference

### Properties

| Name      | Type   | Default   | Description                                                                                                |
| --------- | ------ | --------- | ---------------------------------------------------------------------------------------------------------- |
| latitude  | number | undefined | The latitude of the geolocation. Latitude values must be within -90 and 90. This property is required.     |
| longitude | number | undefined | The longitude of the geolocation. Longitude values must be within -180 and 180. This property is required. |

### Methods

No public methods.

### Events

No custom events.

### Slots

No slots.

---

# Component API Structure

## Basic Information

- **Name:** formattedName
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-name
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Displays a formatted name that can include a salutation and suffix. The locale set in the app's user preferences determines how names are formatted and the order they are presented.

## API Reference

### Properties

| Name         | Type   | Default   | Description                                                                                                              |
| ------------ | ------ | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| format       | string | long      | The format to use to display the name. Valid values include short, medium, and long. This value defaults to long.        |
| salutation   | string | undefined | The value for the salutation, such as Dr. or Mrs.                                                                        |
| firstName    | string | undefined | The value for the first name.                                                                                            |
| lastName     | string | undefined | The value for the last name.                                                                                             |
| middleName   | string | undefined | The value for the middle name.                                                                                           |
| suffix       | string | undefined | The value for the suffix, such as Jr. or Esq.                                                                            |
| informalName | string | undefined | The value for the informal name.                                                                                         |
| locale       | string | en-US     | Specifies the locale used to determine the order of name components of the formatted name. This value defaults to en-US. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedNumber
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-number
- **Version:** GA
- **Type:** COMPONENT
- **Description:** Displays formatted numbers for decimals, currency, and percentages. Uses the Intl.NumberFormat JavaScript object to format numerical values. The locale set in Salesforce user settings determines where to display spaces, commas, and periods in numbers, and the currency used by default.

## API Reference

### Properties

| Name                     | Type   | Default   | Description                                                                                                                                                    |
| ------------------------ | ------ | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value                    | number | undefined | The value to be formatted. Required.                                                                                                                           |
| formatStyle              | string | 'decimal' | The number formatting style to use. Possible values are 'decimal', 'currency', 'percent', and 'percent-fixed'.                                                 |
| currencyCode             | string | undefined | Only used if formatStyle='currency'. Determines which currency is displayed. Possible values are the ISO 4217 currency codes, such as 'USD' for the US dollar. |
| currencyDisplayAs        | string | 'symbol'  | Determines how currency is displayed. Possible values are 'symbol', 'code', and 'name'.                                                                        |
| minimumIntegerDigits     | number | undefined | The minimum number of integer digits that are required. Possible values are from 1 to 21.                                                                      |
| minimumFractionDigits    | number | undefined | The minimum number of fraction digits that are required.                                                                                                       |
| maximumFractionDigits    | number | undefined | The maximum number of fraction digits that are allowed.                                                                                                        |
| minimumSignificantDigits | number | undefined | The minimum number of significant digits that are required. Possible values are from 1 to 21.                                                                  |
| maximumSignificantDigits | number | undefined | The maximum number of significant digits that are allowed. Possible values are from 1 to 21.                                                                   |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedPhone
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-phone
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Displays a phone number as a hyperlink with the tel: URL scheme. Clicking the phone number opens the default VOIP call application on desktop or calls the number on mobile devices. For US/Canada locales, 10 or 11 digit numbers starting with 1 are formatted as (999) 999-9999. Numbers with a "+" prefix are displayed without formatting.

## API Reference

### Properties

| Name     | Type    | Default   | Description                                                                                                                                                                                                                                                                                            |
| -------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| value    | number  | undefined | Sets the phone number to display.                                                                                                                                                                                                                                                                      |
| disabled | boolean | false     | If present, the phone number displays as plain text instead of a link. The number cannot be clicked or receive focus.                                                                                                                                                                                  |
| tabIndex | number  | undefined | Reserved for internal use. Use tabindex instead to indicate if an element should be focusable. A value of 0 means that the element is focusable and participates in sequential keyboard navigation. A value of -1 means that the element is focusable but does not participate in keyboard navigation. |

### Methods

#### focus

- **Description:** Sets focus on the element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the element.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a mouse click on the phone number and opens the default phone app.
- **Parameters:** None
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedRichText
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-rich-text
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A read-only component that displays rich text formatted with HTML tags. The component sanitizes HTML content to prevent XSS vulnerabilities and automatically creates links for URLs and email addresses unless disabled. Supports server-side rendering.

## API Reference

### Properties

| Name           | Type    | Default | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| -------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value          | string  | ''      | Sets the rich text to display. The value is converted to a string if it's not already. Undefined or null values are converted to empty strings. The component sanitizes HTML tags and attributes, removing unsupported ones while preserving text content. Supported HTML tags include: a, abbr, acronym, address, br, big, blockquote, caption, cite, code, col, colgroup, del, div, dl, dd, dt, em, font, h1-h6, hr, img, ins, kbd, li, ol, mark, p, param, pre, q, s, samp, small, span, strong, sub, sup, table, tbody, td, tfoot, th, thead, tr, tt, u, ul, var, strike. The b tag is converted to strong and i tag to em for accessibility. |
| disableLinkify | boolean | false   | If present, the component does not automatically create links for URLs and email addresses in the rich text. When false (default), linkable text such as 'salesforce.com' and email addresses are automatically converted to clickable links.                                                                                                                                                                                                                                                                                                                                                                                                     |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedText
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-text
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Displays text, replaces newlines with line breaks, and linkifies if requested. Converts `\r` and `\n` characters into `<br />` tags. Supports linkifying URLs and email addresses with protocols: `http`, `https`, `ftp`, and `mailto`.

## API Reference

### Properties

| Name    | Type    | Default | Description                                                                                                                                                                                                                                                                                               |
| ------- | ------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value   | string  | ''      | Sets the text to display.                                                                                                                                                                                                                                                                                 |
| linkify | boolean | false   | If present, URLs and email addresses are displayed in anchor tags with `target="_blank"`. They are displayed in plain text by default. If the URL protocol isn't specified, the link's `href` uses `https://` or `http://` to match the host domain's protocol. Email addresses use `mailto://` protocol. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedTime
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-time
- **Version:** 42.0
- **Type:** COMPONENT
- **Description:** Displays a formatted time in user's locale format. Accepts a valid ISO8601 formatted time string and displays it in the user's locale format. Time is always displayed in Universal Time (UTC). Supported patterns: HH:mm, HH:mm:ss, HH:mm:ss.SSS. Offsets are ignored.

## API Reference

### Properties

| Name  | Type   | Default | Description                                                                                                                                                                                      |
| ----- | ------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| value | string | null    | Time value to format. Must be a valid ISO8601 formatted time string (e.g., "22:12:30.999", "14:30", "10:15:45"). The component formats the time in medium format according to the user's locale. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** formattedUrl
- **Namespace:** lightning
- **Tag Name:** lightning-formatted-url
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Displays a URL as a hyperlink using an anchor tag with an href attribute. Supports both absolute and relative URLs with automatic protocol handling.

## API Reference

### Properties

| Name     | Type   | Default   | Description                                                                                                                                                                                                                                                                                            |
| -------- | ------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| value    | string | undefined | The URL to format. Can be an absolute URL (with protocol like http://, https://) or relative URL (starting with /, ./, ../, or a filename). URLs without a protocol are prefixed with http:// by default, unless they use the host domain's protocol.                                                  |
| label    | string | undefined | The text to display in the link. If not provided, the value property is used as the displayed text.                                                                                                                                                                                                    |
| tooltip  | string | undefined | The text to display when the mouse hovers over the link. A link doesn't display a tooltip unless a text value is provided.                                                                                                                                                                             |
| target   | string | \_self    | Specifies where to open the link. Options include \_blank, \_parent, \_self, and \_top.                                                                                                                                                                                                                |
| tabIndex | number | undefined | Reserved for internal use. Use tabindex instead to indicate if an element should be focusable. A value of 0 means that the element is focusable and participates in sequential keyboard navigation. A value of -1 means that the element is focusable but does not participate in keyboard navigation. |

### Methods

#### focus

- **Description:** Sets focus on the element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the element.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a mouse click on the url and navigates to it using the specified target.
- **Parameters:** None
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** helptext
- **Namespace:** lightning
- **Tag Name:** lightning-helptext
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** An icon with a text popover used for tooltips. Displays an icon with a popover containing a small amount of text describing an element on screen. The popover is displayed when you hover or focus on the icon. On iOS devices, the helptext popover opens when you tap on the icon and closes with a second tap on the popover or the icon.

## API Reference

### Properties

| Name            | Type   | Default        | Description                                                                                                                                                                                                                                                                                                                                      |
| --------------- | ------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| content         | string | undefined      | Text to be shown in the popover. For readability, provide a small amount of text. HTML markup is not supported in the tooltip content.                                                                                                                                                                                                           |
| tabIndex        | number | 0              | Reserved for internal use only. Use the global tabindex attribute instead. Set tab index to -1 to prevent focus on the button during tab navigation. The default value is 0, which makes the button focusable during tab navigation.                                                                                                             |
| iconName        | string | 'utility:info' | The Lightning Design System name of the icon used as the visible element. Names are written in the format 'utility:info' where 'utility' is the category, and 'info' is the specific icon to be displayed. Only utility icons can be used in lightning-helptext.                                                                                 |
| iconVariant     | string | 'bare'         | Changes the appearance of the icon. Accepted variants include 'bare' (default, no classes applied), 'error' (red fill for user or system errors), 'inverse' (white fill for dark backgrounds), and 'warning' (yellow fill to advise caution).                                                                                                    |
| alternativeText | string | 'Help'         | The assistive text for the button icon. Screen readers announce the assistive text and help text content as {alternativeText} button {content}. The text should describe the function of the icon, for example, "Show help text". Must be a non-empty string; invalid values will trigger a console warning and the default "Help" will be used. |

### Methods

#### focus

- **Description:** Sets focus on the button.
- **Parameters:** None
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** icon
- **Namespace:** lightning
- **Tag Name:** lightning-icon
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Represents a visual element that provides context and enhances usability. Icons can be used inside the body of another component or on their own.

## API Reference

### Properties

| Name            | Type   | Default   | Description                                                                                                                                                                                                                                                                |
| --------------- | ------ | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| alternativeText | string | undefined | The alternative text used to describe the icon. This text should describe what happens when you click the button, for example 'Upload File', not what the icon looks like, 'Paperclip'.                                                                                    |
| iconName        | string | undefined | The Lightning Design System name of the icon. Names are written in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed. This property is required unless src is provided.                                           |
| src             | string | undefined | A uri path to a custom svg sprite, including the name of the resource, for example: /assets/icons/standard-sprite/svg/test.svg#icon-heart. When this attribute is present, the component attempts to load an icon from the provided resource.                              |
| size            | string | 'medium'  | The size of the icon. Options include xx-small, x-small, small, medium, or large. xx-small creates a 14px by 14px icon, x-small creates a 16px by 16px icon, small creates a 24px by 24px icon, medium creates a 32px by 32px icon, and large creates a 48px by 48px icon. |
| variant         | string | ''        | The variant changes the appearance of a utility icon. Accepted variants include inverse, success, warning, and error. Use the inverse variant to implement a white fill in utility icons on dark backgrounds. Variants are only supported for utility icons.               |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** input
- **Namespace:** lightning
- **Tag Name:** lightning-input
- **Version:** GA
- **Type:** COMPONENT
- **Description:** Represents interactive controls that accept user input depending on the type attribute. Supports multiple input types including text, number, date, datetime, time, email, file, password, search, tel, url, checkbox, checkbox-button, toggle, color, and range.

## API Reference

### Properties

| Name                       | Type            | Default      | Description                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------------- | --------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| placeholder                | string          | null         | Text that is displayed when the field is empty, to prompt the user for a valid entry. Use this attribute with date, email, number, password, search, tel, text, time, and url input types only.                                                                                                                                                                                                                                     |
| name                       | string          | null         | Specifies the name of an input element.                                                                                                                                                                                                                                                                                                                                                                                             |
| label                      | string          | null         | Text label for the input. This is required.                                                                                                                                                                                                                                                                                                                                                                                         |
| messageWhenBadInput        | string          | null         | Error message to be displayed when a bad input is detected. The badInput error can be returned for invalid input for any input type.                                                                                                                                                                                                                                                                                                |
| messageWhenPatternMismatch | string          | null         | Error message to be displayed when a pattern mismatch is detected. The patternMismatch error can be returned when you specify a pattern for email, password, search, tel, text, or url input types.                                                                                                                                                                                                                                 |
| messageWhenRangeOverflow   | string          | null         | Error message to be displayed when a range overflow is detected. The rangeOverflow error can be returned when you specify a max value for number or range input types.                                                                                                                                                                                                                                                              |
| messageWhenRangeUnderflow  | string          | null         | Error message to be displayed when a range underflow is detected. The rangeUnderflow error can be returned when you specify a min value for number or range input types.                                                                                                                                                                                                                                                            |
| messageWhenStepMismatch    | string          | null         | Error message to be displayed when a step mismatch is detected. The stepMismatch error can be returned when you specify a step value for number and range input types.                                                                                                                                                                                                                                                              |
| messageWhenTooShort        | string          | null         | Error message to be displayed when the value is too short. The tooShort error can be returned when you specify a min-length value for email, password, search, tel, text, and url input types.                                                                                                                                                                                                                                      |
| messageWhenTooLong         | string          | null         | Error message to be displayed when the value is too long. The tooLong error can be returned when you specify a max-length value for email, password, search, tel, text, and url input types.                                                                                                                                                                                                                                        |
| messageWhenTypeMismatch    | string          | null         | Error message to be displayed when a type mismatch is detected. The typeMismatch error can be returned for the email and url input types.                                                                                                                                                                                                                                                                                           |
| messageWhenValueMissing    | string          | null         | Error message to be displayed when the value is missing. The valueMissing error can be returned when you specify the required attribute for any input type.                                                                                                                                                                                                                                                                         |
| messageToggleActive        | string          | "Active"     | Text shown for the active state of a toggle. The default is "Active".                                                                                                                                                                                                                                                                                                                                                               |
| messageToggleInactive      | string          | "Inactive"   | Text shown for the inactive state of a toggle. The default is "Inactive".                                                                                                                                                                                                                                                                                                                                                           |
| ariaLabel                  | string          | null         | Describes the input to assistive technologies.                                                                                                                                                                                                                                                                                                                                                                                      |
| autocomplete               | string          | undefined    | Controls auto-filling of the field. Use this attribute with email, search, tel, text, and url input types only. Set the attribute to pass through autocomplete values to be interpreted by the browser. When type='date' or type='datetime' or type='time' the value of autocomplete is 'off'.                                                                                                                                      |
| dateStyle                  | string          | "medium"     | The display style of the date when type='date' or type='datetime'. Valid values are short, medium (default), and long. The format of each style is specific to the locale. On mobile devices this attribute has no effect.                                                                                                                                                                                                          |
| timeStyle                  | string          | "short"      | The display style of the time when type='time' or type='datetime'. Valid values are short (default), medium, and long. Currently, medium and long styles look the same. On mobile devices this attribute has no effect.                                                                                                                                                                                                             |
| dateAriaLabel              | string          | null         | Describes the date input to assistive technologies when type='datetime'. On mobile devices, this label is merged with aria-label and time-aria-label to describe the native date time input.                                                                                                                                                                                                                                        |
| timeAriaLabel              | string          | null         | Describes the time input to assistive technologies when type='datetime'. On mobile devices, this label is merged with aria-label and date-aria-label to describe the native date time input.                                                                                                                                                                                                                                        |
| dateAccessKey              | string          | null         | Sets a key that can be used to access the date picker when you use the datetime type.                                                                                                                                                                                                                                                                                                                                               |
| timeAccessKey              | string          | null         | Sets a key that can be used to access the time picker when you use the datetime type.                                                                                                                                                                                                                                                                                                                                               |
| timeStepMinutes            | number          | 15           | Specifies the time interval in minutes for the dropdown options. Any positive integer above or equal to 5 is valid. The default is 15 minutes.                                                                                                                                                                                                                                                                                      |
| inputmode                  | string          | null         | Controls the virtual keyboard type on mobile devices.                                                                                                                                                                                                                                                                                                                                                                               |
| formatFractionDigits       | number          | null         | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                                                                                          |
| timeAriaControls           | string          | null         | A space-separated list of element IDs whose presence or content is controlled by the time input when type='datetime'. On mobile devices, this is merged with aria-controls and date-aria-controls to describe the native date time input.                                                                                                                                                                                           |
| timeAriaDetails            | string          | null         | A space-separated list of IDs of elements that provide details of the date input when type='datetime'.                                                                                                                                                                                                                                                                                                                              |
| dateAriaErrorMessage       | string          | null         | A space-separated list of element IDs that provide error messages for the date input when type='datetime'.                                                                                                                                                                                                                                                                                                                          |
| timeAriaErrorMessage       | string          | null         | A space-separated list of element IDs that provide error messages for the time input when type='datetime'.                                                                                                                                                                                                                                                                                                                          |
| dateAriaLabelledBy         | string          | null         | A space-separated list of element IDs that provide labels for the date input when type='datetime'. On mobile devices, this is merged with aria-labelled-by and time-aria-labelled-by to describe the native date time input.                                                                                                                                                                                                        |
| timeAriaLabelledBy         | string          | null         | A space-separated list of element IDs that provide labels for the time input when type='datetime'. On mobile devices, this is merged with aria-labelled-by and date-aria-labelled-by to describe the native date time input.                                                                                                                                                                                                        |
| timeAriaDescribedBy        | string          | null         | A space-separated list of element IDs that provide descriptive labels for the time input when type='datetime'. On mobile devices, this is merged with aria-described-by and date-aria-described-by to describe the native date time input.                                                                                                                                                                                          |
| dateAriaControls           | string          | null         | A space-separated list of element IDs whose presence or content is controlled by the date input when type='datetime'. On mobile devices, this is merged with aria-controls and time-aria-controls to describe the native date time input.                                                                                                                                                                                           |
| dateAriaDetails            | string          | null         | A space-separated list of IDs of elements that provide details of the date input when type='datetime'.                                                                                                                                                                                                                                                                                                                              |
| dateAriaDescribedBy        | string          | null         | A space-separated list of element IDs that provide descriptive labels for the date input when type='datetime'. On mobile devices, this is merged with aria-described-by and time-aria-described-by to describe the native date time input.                                                                                                                                                                                          |
| ariaControls               | string          | null         | A space-separated list of element IDs whose presence or content is controlled by the input.                                                                                                                                                                                                                                                                                                                                         |
| ariaDetails                | string          | null         | A space-separated list of IDs of elements that provide details for the input.                                                                                                                                                                                                                                                                                                                                                       |
| ariaLabelledBy             | string          | null         | A space-separated list of element IDs that provide labels for the input.                                                                                                                                                                                                                                                                                                                                                            |
| ariaDescribedBy            | string          | null         | A space-separated list of element IDs that provide descriptive labels for the input.                                                                                                                                                                                                                                                                                                                                                |
| ariaErrorMessage           | string          | null         | A space-separated list of element IDs that provide descriptive error message for input.                                                                                                                                                                                                                                                                                                                                             |
| ariaInvalid                | boolean         | undefined    | A Boolean value for aria-invalid.                                                                                                                                                                                                                                                                                                                                                                                                   |
| ariaHasPopup               | string          | null         | Specifies the value of the aria-haspopup attribute.                                                                                                                                                                                                                                                                                                                                                                                 |
| ariaKeyShortcuts           | string          | null         | Specifies the value of the aria-keyshortcuts attribute.                                                                                                                                                                                                                                                                                                                                                                             |
| ariaDisabled               | boolean         | null         | Specifies the value of the aria-disabled attribute.                                                                                                                                                                                                                                                                                                                                                                                 |
| ariaRoleDescription        | string          | null         | Specifies the value of the aria-roledescription attribute.                                                                                                                                                                                                                                                                                                                                                                          |
| ariaExpanded               | string          | null         | Specifies the value of the aria-expanded attribute, only valid on type simple.                                                                                                                                                                                                                                                                                                                                                      |
| ariaAutoComplete           | string          | null         | Specifies the value of the aria-autocomplete, only valid on type simple.                                                                                                                                                                                                                                                                                                                                                            |
| formatter                  | string          | "decimal"    | String value with the formatter to be used for number input. Valid values include decimal, percent, percent-fixed, and currency.                                                                                                                                                                                                                                                                                                    |
| type                       | string          | "text"       | The type of the input. Valid values are checkbox, checkbox-button, color, date, datetime, time, email, file, password, range, search, tel, url, number, and toggle. This value defaults to text.                                                                                                                                                                                                                                    |
| isLoading                  | boolean         | false        | For the search type only. If present, a spinner is displayed to indicate that data is loading.                                                                                                                                                                                                                                                                                                                                      |
| pattern                    | string          | null         | Specifies the regular expression that the input's value is checked against. This attribute is supported for email, password, search, tel, text, and url types. For color type, returns '^#([A-Fa-f0-9]{6}                                                                                                                                                                                                                           | [A-Fa-f0-9]{3})$'. |
| maxLength                  | number          | null         | The maximum number of characters allowed in the field. Use this attribute with email, password, search, tel, text, and url input types only.                                                                                                                                                                                                                                                                                        |
| accept                     | string          | null         | Specifies the types of files that the server accepts. Use this attribute with file input type only.                                                                                                                                                                                                                                                                                                                                 |
| minLength                  | number          | null         | The minimum number of characters allowed in the field. Use this attribute with email, password, search, tel, text, and url input types only.                                                                                                                                                                                                                                                                                        |
| max                        | decimal\|string | null         | The maximum acceptable value for the input. Use this attribute with number, range, date, time, and datetime input types only. For number and range type, the max value is a decimal number. For the date, time, and datetime types, the max value must use a valid string for the type.                                                                                                                                             |
| min                        | decimal\|string | null         | The minimum acceptable value for the input. Use this attribute with number, range, date, time, and datetime input types only. For number and range types, the min value is a decimal number. For the date, time, and datetime types, the min value must use a valid string for the type.                                                                                                                                            |
| step                       | decimal\|string | "1"          | Granularity of the value, specified as a positive floating point number. Use this attribute with number and range input types only. Use 'any' when granularity is not a concern. This value defaults to 1. For datetime and time types, returns 'any'.                                                                                                                                                                              |
| checked                    | boolean         | false        | If present, the checkbox is selected.                                                                                                                                                                                                                                                                                                                                                                                               |
| multiple                   | boolean         | false        | Specifies that a user can enter more than one value. Use this attribute with file and email input types only.                                                                                                                                                                                                                                                                                                                       |
| value                      | object          | ""           | Specifies the value of an input element.                                                                                                                                                                                                                                                                                                                                                                                            |
| variant                    | string          | "standard"   | The variant changes the appearance of an input field. Accepted variants include standard, label-inline, label-hidden, and label-stacked. This value defaults to standard, which displays the label above the field. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and input field. Use label-stacked to place the label above the input field. |
| disabled                   | boolean         | false        | If present, the input field is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                                                                                          |
| readOnly                   | boolean         | false        | If present, the input field is read-only and cannot be edited by users.                                                                                                                                                                                                                                                                                                                                                             |
| required                   | boolean         | false        | If present, the input field must be filled out before the form is submitted.                                                                                                                                                                                                                                                                                                                                                        |
| timezone                   | string          | userTimeZone | Specifies the time zone used when type='datetime' only. This value defaults to the user's Salesforce time zone setting.                                                                                                                                                                                                                                                                                                             |
| fieldLevelHelp             | string          | null         | Help text detailing the purpose and function of the input. This attribute isn't supported for file, toggle, and checkbox-button types.                                                                                                                                                                                                                                                                                              |
| accessKey                  | string          | null         | Specifies a shortcut key to activate or focus an element.                                                                                                                                                                                                                                                                                                                                                                           |
| files                      | object          | null         | A FileList that contains selected files. Use this attribute with the file input type only. When setting the files property, the value must be a FileList, an array of File objects, or a single File object.                                                                                                                                                                                                                        |
| validity                   | object          | null         | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                                                                                         |
| selectionStart             | number          | undefined    | Specifies the index of the first character to select in the input element. This attribute is supported only for text type. Use with selection-end to programmatically set or read the position of selected text.                                                                                                                                                                                                                    |
| selectionEnd               | number          | undefined    | Specifies the index of the last character to select in the input element. This attribute is supported only for text type. Use with selection-start to programmatically set or read the position of selected text.                                                                                                                                                                                                                   |
| role                       | string          | null         | The role set on lightning-primitive-input-simple to allow external developers to have a type="text" and role="combobox" if lightning-combobox does not meet their requirements. Valid value is 'combobox'.                                                                                                                                                                                                                          |

### Methods

#### checkValidity

- **Description:** Checks if the input is valid.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the element meets all constraint validations.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when a form is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### showHelpMessageIfInvalid

- **Description:** Displays error messages on invalid fields. An invalid field fails at least one constraint validation and returns false when checkValidity() is called.
- **Parameters:** None
- **Returns:** void

#### focus

- **Description:** Sets focus on the input element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the input element.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** The event fired when a value is changed in the input field. For input types checkbox and checkbox-button, the event returns checked attribute. For input type file, the event returns the list of selected files in a FileList object. For other input types, returns the input value.
- **Payload:**
  ```javascript
  {
    checked: boolean, // For checkbox and checkbox-button types only
    files: Object, // For file type only - FileList object containing File objects
    value: string // For other input types
  }
  ```

#### commit

- **Description:** The event fired when you press Enter after interacting with the input, or move away from the input so it loses focus. For the input type search, the event is fired when focus leaves the entire component or when the user clicks the X button to clear the search. For the input type number, the event is also fired when you press Up/Down arrow keys to change the number.
- **Payload:** None

#### focus

- **Description:** The event fired when the input receives focus.
- **Payload:** None

#### blur

- **Description:** The event fired when the input loses focus.
- **Payload:** None

### Slots

#### label-end

- **Description:** Slot for content to be placed at the end of the label. Only available for simple input types (text, number, email, tel, url, search, password, range, month, week, date, time, datetime on mobile).

---

# Component API Structure

## Basic Information

- **Name:** inputAddress
- **Namespace:** lightning
- **Tag Name:** lightning-input-address
- **Type:** COMPONENT
- **Description:** A compound field component that creates an address input form with multiple constituent fields including street, city, province, country, and postal code. The component supports flexible layouts, validation, address lookup via Google Maps API, dropdown menus for country and province selection, and locale-based field ordering.

## API Reference

### Properties

| Name                     | Type    | Default      | Description                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------ | ------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| addressLabel             | string  | undefined    | The label for the address compound field.                                                                                                                                                                                                                                                                                                                                                                                        |
| streetLabel              | string  | undefined    | The label for the street field.                                                                                                                                                                                                                                                                                                                                                                                                  |
| subpremiseLabel          | string  | undefined    | The label for the subpremise field. Use this attribute with show-compact-address.                                                                                                                                                                                                                                                                                                                                                |
| cityLabel                | string  | undefined    | The label for the city field.                                                                                                                                                                                                                                                                                                                                                                                                    |
| provinceLabel            | string  | undefined    | The label for the province field.                                                                                                                                                                                                                                                                                                                                                                                                |
| countryLabel             | string  | undefined    | The label for the country field.                                                                                                                                                                                                                                                                                                                                                                                                 |
| postalCodeLabel          | string  | undefined    | The label for the postal code field.                                                                                                                                                                                                                                                                                                                                                                                             |
| streetPlaceholder        | string  | undefined    | The placeholder for the street field.                                                                                                                                                                                                                                                                                                                                                                                            |
| subpremisePlaceholder    | string  | undefined    | The placeholder for the subpremise field. Use this attribute with show-compact-address.                                                                                                                                                                                                                                                                                                                                          |
| cityPlaceholder          | string  | undefined    | The placeholder for the city field.                                                                                                                                                                                                                                                                                                                                                                                              |
| provincePlaceholder      | string  | undefined    | The placeholder for the province field.                                                                                                                                                                                                                                                                                                                                                                                          |
| countryPlaceholder       | string  | undefined    | The placeholder for the country field.                                                                                                                                                                                                                                                                                                                                                                                           |
| postalCodePlaceholder    | string  | undefined    | The placeholder for the postal code field.                                                                                                                                                                                                                                                                                                                                                                                       |
| addressLookupPlaceholder | string  | undefined    | The placeholder for the address lookup field option. Visible only when using show-address-lookup.                                                                                                                                                                                                                                                                                                                                |
| addressLookupLabel       | string  | undefined    | The label for the address lookup field option. Only visible when show-address-lookup is set to true and label string is passed.                                                                                                                                                                                                                                                                                                  |
| provinceOptions          | array   | undefined    | The array of label-value pairs for the province. Displays a dropdown menu of options.                                                                                                                                                                                                                                                                                                                                            |
| hideProvince             | boolean | false        | If present, the province field is hidden from the UI and users cannot interact with it.                                                                                                                                                                                                                                                                                                                                          |
| countryOptions           | array   | undefined    | The array of label-value pairs for the country. Displays a dropdown menu of options.                                                                                                                                                                                                                                                                                                                                             |
| countryDisabled          | boolean | false        | If present, the country field is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                                                                                     |
| locale                   | string  | en-US        | Specifies the locale used to determine the layout of the address fields. This value defaults to en-US.                                                                                                                                                                                                                                                                                                                           |
| street                   | string  | empty string | The value for the street field. Maximum length is 255 characters when rendered as a textarea. Maximum length is 80 characters when rendered as an input using show-compact-address.                                                                                                                                                                                                                                              |
| subpremise               | string  | empty string | The value for the subpremise field. Maximum length is 80 characters. Use this attribute with show-compact-address.                                                                                                                                                                                                                                                                                                               |
| city                     | string  | empty string | The value for the city field. Maximum length is 40 characters.                                                                                                                                                                                                                                                                                                                                                                   |
| province                 | string  | empty string | The province field for the address. If province-options is provided, this province value is selected by default. Maximum length is 80 characters.                                                                                                                                                                                                                                                                                |
| country                  | string  | empty string | The country field for the address. If country-options is provided, this country value is selected by default. Maximum length is 80 characters.                                                                                                                                                                                                                                                                                   |
| postalCode               | string  | empty string | The value for postal code field. Maximum length is 20 characters.                                                                                                                                                                                                                                                                                                                                                                |
| disabled                 | boolean | false        | If present, the address fields are disabled and users cannot interact with them.                                                                                                                                                                                                                                                                                                                                                 |
| showAddressLookup        | boolean | false        | If present, an address lookup field using Google Maps is displayed. When used with show-compact-address, the first street field functions as the address lookup field.                                                                                                                                                                                                                                                           |
| countryLookupFilter      | array   | []           | A list of ISO 3166-1 Alpha-2 country codes to filter the address with. Country codes are case-insensitive. Use with the show-address-lookup attribute. Specify up to five country codes.                                                                                                                                                                                                                                         |
| showCompactAddress       | boolean | false        | If present, the street field is rendered as two separate inputs instead of a single textarea. To provide a label for the first street field, use street-label. To provide a label for the second street field, use subpremise-label.                                                                                                                                                                                             |
| readOnly                 | boolean | false        | If present, the address fields are read-only and cannot be edited.                                                                                                                                                                                                                                                                                                                                                               |
| required                 | boolean | false        | If present, the address fields must be filled before the form is submitted.                                                                                                                                                                                                                                                                                                                                                      |
| variant                  | string  | standard     | The variant changes the appearance of an input address field. Accepted variants include standard, label-hidden, label-inline, and label-stacked. This value defaults to standard. Use label-hidden to hide the compound field label but make it available to assistive technology. Use label-inline to horizontally align the label and input address field. Use label-stacked to place the label above the input address field. |
| fieldLevelHelp           | string  | undefined    | Help text detailing the purpose and function of the input.                                                                                                                                                                                                                                                                                                                                                                       |
| validity                 | object  | undefined    | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                                                                                      |

### Methods

#### checkValidity

- **Description:** Checks if the input is valid.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the element meets all constraint validations.

#### showHelpMessageIfInvalid

- **Description:** Displays error messages on the address fields if the values are invalid.
- **Parameters:** None
- **Returns:** void

#### setCustomValidityForField

- **Description:** Sets a custom error message to be displayed for the specified fieldName when the input address value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
  - `fieldName` (string, required): Name of the field, which must be one of the following: street, city, province, postalCode, country.
- **Returns:** void

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### focus

- **Description:** Sets focus on the first input element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes focus from all input fields.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** The event fired when an item is changed in the lightning-input-address component.
- **Payload:**
  ```javascript
  {
    street: string, // The number and name of street
    subpremise: string, // The subpremise information (apartment, unit, floor number)
    city: string, // The name of the city
    province: string, // The name of the province/state
    country: string, // The name of the country
    postalCode: string, // The postal code for the address
    validity: object // The validity state of the element
  }
  ```
- **Properties:**
  - bubbles: true
  - cancelable: false
  - composed: true

#### focus

- **Description:** Fired when the component receives focus.
- **Payload:** None

#### blur

- **Description:** Fired when the component loses focus and validation is reported.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** inputField
- **Namespace:** lightning
- **Tag Name:** lightning-input-field
- **Type:** COMPONENT
- **Description:** Represents an editable input for a field on a Salesforce object. Must be used as a direct child of `lightning-record-edit-form`. Automatically displays the appropriate input type based on the field's data type (text, number, picklist, lookup, address, etc.).

## API Reference

### Properties

| Name         | Type    | Default  | Description                                                                                                                                                                                                                                                                             |
| ------------ | ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| fieldName    | string  | null     | The API name of the field to be displayed.                                                                                                                                                                                                                                              |
| value        | string  | null     | The field value, which overrides the existing value.                                                                                                                                                                                                                                    |
| disabled     | boolean | false    | If present, the field is grayed out and users can't interact with it. Disabled fields don't receive focus and are skipped in tabbing navigation.                                                                                                                                        |
| readOnly     | boolean | false    | Specifies whether an input field is read-only. Not supported for the following field types: rich text, picklist, multi-select picklist, and lookup. A read-only field is not disabled by default.                                                                                       |
| required     | boolean | false    | If present, the input field must be filled out before the form is submitted.                                                                                                                                                                                                            |
| variant      | string  | standard | The variant changes the label position of an input field. Accepted variants include standard, label-hidden, label-inline, and label-stacked. The variant, if specified, determines the label position. Otherwise, the density setting of the parent form determines the label position. |
| autocomplete | string  | null     | Controls auto-filling of the input field based on the value. Supported field types: 'text', 'email', 'textarea', and 'single select picklist'. Additional field types supported on mobile: 'date', 'time', and 'date-time'.                                                             |
| ariaInvalid  | boolean | false    | A boolean value that controls whether assistive technologies read empty required textboxes as invalid.                                                                                                                                                                                  |
| dirty        | boolean | false    | (Readonly) Reserved for internal use. If present, the field has been modified by the user but not saved or submitted.                                                                                                                                                                   |

### Methods

#### wireRecordUi

- **Description:** Reserved for internal use.
- **Parameters:**
  - `data` (any, required): Reserved for internal use.
- **Returns:** void

#### wirePicklistValues

- **Description:** Reserved for internal use.
- **Parameters:**
  - `picklistValues` (any, required): Reserved for internal use.
- **Returns:** void

#### reset

- **Description:** Resets the form fields to their initial values.
- **Parameters:** None
- **Returns:** void

#### updateDependentField

- **Description:** Reserved for internal use.
- **Parameters:**
  - `fieldName` (string, required): Reserved for internal use.
  - `options` (any, required): Reserved for internal use.
- **Returns:** void

#### setErrors

- **Description:** Reserved for internal use.
- **Parameters:**
  - `errors` (any, required): Reserved for internal use.
- **Returns:** void

#### focus

- **Description:** Focus underlying input.
- **Parameters:** None
- **Returns:** void

#### reportValidity

- **Description:** Reserved for internal use.
- **Parameters:** None
- **Returns:** boolean - Returns true if the input field is valid.

#### clean

- **Description:** Reserved for internal use. Clean up the field dirty state.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** Fires when the value of the input field changes. The event bubbles up from the underlying input component.
- **Payload:**
  ```javascript
  {
    value: any, // The new value of the field
    checked: boolean // For checkbox fields, the checked state
  }
  ```

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** inputLocation
- **Namespace:** lightning
- **Tag Name:** lightning-input-location
- **Type:** COMPONENT
- **Description:** Represents a geolocation compound field that accepts user input for a latitude and longitude value. The latitude field accepts values within -90 and 90, and the longitude field accepts values within -180 and 180.

## API Reference

### Properties

| Name           | Type    | Default   | Description                                                                                                                                                                                                                                                                                                                                                                            |
| -------------- | ------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label          | string  | undefined | The label of the geolocation compound field.                                                                                                                                                                                                                                                                                                                                           |
| fieldLevelHelp | string  | undefined | Help text detailing the purpose and function of the input.                                                                                                                                                                                                                                                                                                                             |
| latitude       | string  | ''        | The latitude value. Latitude values must be within -90 and 90. Accepts numeric values which are converted to strings.                                                                                                                                                                                                                                                                  |
| longitude      | string  | ''        | The longitude value. Longitude values must be within -180 and 180. Accepts numeric values which are converted to strings.                                                                                                                                                                                                                                                              |
| disabled       | boolean | false     | If present, the geolocation fields are disabled and users cannot interact with them.                                                                                                                                                                                                                                                                                                   |
| readOnly       | boolean | false     | If present, the geolocation fields are read-only and cannot be edited.                                                                                                                                                                                                                                                                                                                 |
| required       | boolean | false     | If present, the geolocation fields must be filled out before the form is submitted. An error message is displayed if a user interacts with the field and does not provide a value.                                                                                                                                                                                                     |
| variant        | string  | standard  | The variant changes the appearance of the geolocation compound field. Accepted variants include standard, label-hidden, label-inline, and label-stacked. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and geolocation fields. Use label-stacked to place the label above the geolocation fields. |
| validity       | object  | N/A       | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                                            |

### Methods

#### focus

- **Description:** Sets focus on the latitude field.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the latitude and longitude fields.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the latitude and longitude fields meet all constraint validations.

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### showHelpMessageIfInvalid

- **Description:** Displays error messages on the latitude or longitude field if the coordinates are invalid.
- **Parameters:** None
- **Returns:** void

#### setCustomValidityForField

- **Description:** Sets a custom error message to be displayed for the latitude or longitude field when the value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
  - `fieldName` (string, required): Name of the field, which must be "latitude" or "longitude".
- **Returns:** void

### Events

#### change

- **Description:** The event fired when a value is changed in the lightning-input-location component. This event bubbles and is composed, allowing it to cross the shadow DOM boundary.
- **Payload:**
  ```javascript
  {
    latitude: string, // The latitude of the location
    longitude: string // The longitude of the location
  }
  ```

#### focus

- **Description:** The event fired when the component receives focus (when interacting state is entered).
- **Payload:** None

#### blur

- **Description:** The event fired when the component loses focus (when interacting state is left). The component also performs validation when this event fires.
- **Payload:** None

### Slots

This component does not support any slots.

---

# Component API Structure

## Basic Information

- **Name:** inputName
- **Namespace:** lightning
- **Tag Name:** lightning-input-name
- **Type:** COMPONENT
- **Description:** A name compound field represented by HTML input elements of type text. The Salutation field is a dropdown menu that accepts an array of label-value pairs. By default, displays Salutation, First Name, and Last Name fields.

## API Reference

### Properties

| Name              | Type    | Default                                 | Description                                                                                                                                                                                                                                                                                                                                                     |
| ----------------- | ------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label             | string  | undefined                               | The label of the input name field.                                                                                                                                                                                                                                                                                                                              |
| locale            | string  | en-US                                   | Specifies the locale used to determine the layout of the name fields. Supports both hyphens and underscores (e.g., en-US or en_US). If an invalid locale is provided, defaults to en-US.                                                                                                                                                                        |
| options           | array   | undefined                               | Displays a list of salutation options, such as Dr. or Mrs., provided as label-value pairs.                                                                                                                                                                                                                                                                      |
| fieldsToDisplay   | array   | ['firstName', 'salutation', 'lastName'] | List of fields to be displayed on the component. Other field values include middleName, informalName, suffix.                                                                                                                                                                                                                                                   |
| salutation        | string  | ''                                      | Displays the Salutation field as a dropdown menu. Use the options attribute to provide salutations in an array of label-value pairs.                                                                                                                                                                                                                            |
| firstName         | string  | ''                                      | Displays the First Name field.                                                                                                                                                                                                                                                                                                                                  |
| middleName        | string  | ''                                      | Displays the Middle Name field.                                                                                                                                                                                                                                                                                                                                 |
| informalName      | string  | ''                                      | Displays the Informal Name field.                                                                                                                                                                                                                                                                                                                               |
| lastName          | string  | ''                                      | Displays the Last Name field.                                                                                                                                                                                                                                                                                                                                   |
| suffix            | string  | ''                                      | Displays the Suffix field.                                                                                                                                                                                                                                                                                                                                      |
| disabled          | boolean | false                                   | If present, the input name field is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                 |
| readOnly          | boolean | false                                   | If present, the input name field is read-only and cannot be edited.                                                                                                                                                                                                                                                                                             |
| required          | boolean | false                                   | If present, the input name field must be filled out before the form is submitted. A red asterisk is displayed on the Last Name field. An error message is displayed if a user interacts with the Last Name field and does not provide a value.                                                                                                                  |
| variant           | string  | standard                                | The variant changes the appearance of a name compound field. Accepted variants include standard, label-hidden, label-inline, and label-stacked. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and name fields. Use label-stacked to place the label above the name fields. |
| fieldLevelHelp    | string  | undefined                               | Help text detailing the purpose and function of the input.                                                                                                                                                                                                                                                                                                      |
| validity          | object  | undefined                               | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                     |
| salutationLabel   | string  | undefined                               | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                      |
| firstNameLabel    | string  | undefined                               | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                      |
| middleNameLabel   | string  | undefined                               | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                      |
| lastNameLabel     | string  | undefined                               | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                      |
| suffixLabel       | string  | undefined                               | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                      |
| informalNameLabel | string  | undefined                               | Reserved for internal use.                                                                                                                                                                                                                                                                                                                                      |

### Methods

#### focus

- **Description:** Sets focus on the first input field.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the input element.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Returns the valid property value (Boolean) on the ValidityState object to indicate whether input name fields have validity errors.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the element meets all constraint validations.

#### showHelpMessageIfInvalid

- **Description:** Displays error messages on the input fields if the entries are invalid.
- **Parameters:** None
- **Returns:** void

#### setCustomValidityForField

- **Description:** Sets a custom error message to be displayed for the input name fields when the input value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
  - `fieldName` (string, required): The name of the input name field. Valid field names are: salutation, firstName, middleName, lastName, suffix, informalName.
- **Returns:** void

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

### Events

#### change

- **Description:** The event fired when an item is changed in the lightning-input-name component.
- **Payload:**
  ```javascript
  {
    salutation: string, // The value of the salutation field
    firstName: string, // The value of the first name field
    middleName: string, // The value of the middle name field
    lastName: string, // The value of the last name field
    informalName: string, // The value of the informal name field
    suffix: string, // The value of the suffix field
    validity: object // The validity state of the element
  }
  ```
- **Properties:**
  - bubbles: true
  - cancelable: false
  - composed: true

#### focus

- **Description:** The event fired when the component receives focus.
- **Payload:** None
- **Properties:**
  - bubbles: false
  - cancelable: false
  - composed: false

#### blur

- **Description:** The event fired when the component loses focus.
- **Payload:** None
- **Properties:**
  - bubbles: false
  - cancelable: false
  - composed: false

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** inputRichText
- **Namespace:** lightning
- **Tag Name:** lightning-input-rich-text
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A WYSIWYG editor with a customizable toolbar for entering rich text. Based on the Quill JS library, it enables users to add, edit, format, and delete rich text content. The editor provides toolbar buttons for text formatting, alignment, lists, links, images, and more. Supports customization through disabled categories and format lists.

## API Reference

### Properties

| Name                | Type    | Default   | Description                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------- | ------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label               | string  | undefined | The label of the rich text editor.                                                                                                                                                                                                                                                                                                                                                                  |
| fieldLevelHelp      | string  | undefined | Help text detailing the purpose and function of the rich text editor. The text is displayed in a tooltip above the rich text editor when you provide a label value. To display the label next to the tooltip, use the label-visible attribute.                                                                                                                                                      |
| labelVisible        | boolean | false     | If present, the label on the rich text editor is visible.                                                                                                                                                                                                                                                                                                                                           |
| required            | boolean | false     | If present, users must enter content in the editor. An asterisk is displayed before the label when label-visible is present.                                                                                                                                                                                                                                                                        |
| placeholder         | string  | undefined | Text that is displayed when the field is empty, to prompt the user for a valid entry.                                                                                                                                                                                                                                                                                                               |
| disabledCategories  | string  | ''        | A comma-separated list of button categories to remove from the toolbar. Valid categories: FORMAT_FONT, FORMAT_TEXT, FORMAT_BACKGROUND, FORMAT_BODY, ALIGN_TEXT, INSERT_CONTENT, REMOVE_FORMATTING.                                                                                                                                                                                                  |
| formats             | Array   | []        | A list of allowed formats. By default, the list is computed based on enabled categories. The 'table' format is always enabled to support copying and pasting of tables if formats are not provided. Valid formats include: font, size, bold, italic, underline, strike, list, indent, align, link, image, clean, table, header, color, background, code, code-block, script, blockquote, direction. |
| variant             | string  | undefined | The variant changes the appearance of the toolbar. Accepted variant is 'bottom-toolbar' which causes the toolbar to be displayed below the text box.                                                                                                                                                                                                                                                |
| messageWhenBadInput | string  | undefined | Error message to be displayed when invalid input is detected.                                                                                                                                                                                                                                                                                                                                       |
| customButtons       | object  | undefined | Reserved for internal use. Custom buttons to add to the toolbar.                                                                                                                                                                                                                                                                                                                                    |
| shareWithEntityId   | string  | undefined | Entity ID to share the image with. When specified, uploaded images are shared with the entity (record, org, group, or user) that corresponds to this ID.                                                                                                                                                                                                                                            |
| value               | string  | undefined | The HTML content in the rich text editor.                                                                                                                                                                                                                                                                                                                                                           |
| ariaDescribedBy     | string  | ''        | Reserved for internal use. Use the standard aria-describedby instead.                                                                                                                                                                                                                                                                                                                               |
| valid               | boolean | true      | Specifies whether the editor content is valid. If set to false, the slds-has-error class is added. This value defaults to true.                                                                                                                                                                                                                                                                     |
| disabled            | boolean | false     | If present, the editor is disabled and users cannot interact with it. This value defaults to false.                                                                                                                                                                                                                                                                                                 |

### Methods

#### focus

- **Description:** Sets focus on the rich text editor. Activates the editor if not already initialized.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes focus from the rich text editor.
- **Parameters:** None
- **Returns:** void

#### setFormat

- **Description:** Sets a format in the editor from the cursor point onwards. The format also applies to currently selected content. Valid formats are font, size, and align.
- **Parameters:**
  - `formats` (object, required): A key-value pair with format names and values. Supported format keys: align (values: left, right, center), background (color name or hex value), bold (true/false), code (true/false), code-block (true/false), color (color name or hex value), font (default, sans-serif, courier, verdana, tahoma, garamond, serif), header (1-6), italic (true/false), link (url), size (8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72), strike (true/false), underline (true/false).
- **Returns:** void

#### getFormat

- **Description:** Returns an object representing the formats applied to the current selection. Formats supported are align, background, bold, code, code-block, color, font, header, italic, link, size, strike, underline.
- **Parameters:** None
- **Returns:** object - An object representing the formats applied to the selection or editor.

#### insertTextAtCursor

- **Description:** Reserved for internal use. Insert text in the rich text editor at cursor position.
- **Parameters:**
  - `text` (string, required): Text to insert.
- **Returns:** void

#### setRangeText

- **Description:** Replaces a range of text in the rich text editor with a new string. Follows the API of the standard HTMLInputElement.setRangeText() method.
- **Parameters:**
  - `replacement` (string, required): The string to insert. HTML markup is not supported.
  - `start` (number, required): The 0-based index of the first character to replace.
  - `end` (number, required): The 0-based index of the character after the last character to replace.
  - `selectMode` (string, optional): Defines how the selection is set after the text is replaced. Valid values are 'select', 'start', 'end', and 'preserve' (default).
- **Returns:** void

### Events

#### change

- **Description:** Fired when the editor content changes.
- **Payload:**
  ```javascript
  {
    value: string; // The HTML content in the rich text editor
  }
  ```

#### focus

- **Description:** Fired when the editor receives focus.
- **Payload:** None

#### blur

- **Description:** Fired when the editor loses focus.
- **Payload:** None

### Slots

#### toolbar

- **Description:** Placeholder for lightning-rich-text-toolbar-button-group. Used to add custom buttons to the toolbar. Custom buttons are contained in a button group that displays at the end of the toolbar.

---

# Component API Structure

## Basic Information

- **Name:** layout
- **Namespace:** lightning
- **Tag Name:** lightning-layout
- **Version:** 0.0
- **Type:** COMPONENT
- **Description:** A flexible grid system for arranging containers within a page or inside another container. The default layout is mobile-first and can be easily configured to work on different devices. Create the content of the layout by including lightning-layout-item components within lightning-layout.

## API Reference

### Properties

| Name            | Type    | Default   | Description                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| horizontalAlign | string  | undefined | Determines how to spread the layout items horizontally. Valid values are 'center', 'space', 'spread', and 'end'. 'center' orders layout items into a horizontal line without spacing and places the group in the center. 'space' distributes items horizontally with space before, between, and after. 'spread' distributes items with space between but not at edges. 'end' groups items together and aligns them on the right side. |
| verticalAlign   | string  | undefined | Determines how to align the layout items vertically in the container. Valid values are 'start', 'center', 'end', and 'stretch'. 'start' aligns items at the top. 'center' aligns items in the center. 'end' aligns items at the bottom. 'stretch' extends items vertically to fill the container.                                                                                                                                     |
| pullToBoundary  | string  | undefined | Pulls layout items to the layout boundaries and corresponds to the padding size on the layout item. Valid values are 'small', 'medium', or 'large'. Choose the size that corresponds to the padding on your layout items.                                                                                                                                                                                                             |
| multipleRows    | boolean | false     | If present, layout items wrap to the following line when they exceed the layout width.                                                                                                                                                                                                                                                                                                                                                |

### Methods

None

### Events

None

### Slots

#### default

- **Description:** The default slot holds lightning-layout-item components that define the columns of the layout. You can place HTML tags and text between the lightning-layout-item components, but you can't place other components or expressions between them.

---

# Component API Structure

## Basic Information

- **Name:** layoutItem
- **Namespace:** lightning
- **Tag Name:** lightning-layout-item
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** The basic element in a lightning-layout component. A layout item groups information together to define visual grids, spacing, and sections.

## API Reference

### Properties

| Name             | Type   | Default   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------------- | ------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| flexibility      | object | undefined | Make the item fluid so that it absorbs any extra space in its container or shrinks when there is less space. Allowed values are: auto (columns grow or shrink equally as space allows), shrink (columns shrink equally as space decreases), no-shrink (columns don't shrink as space reduces), grow (columns grow equally as space increases), no-grow (columns don't grow as space increases), no-flex (columns don't grow or shrink as space changes). Use a comma-separated value for multiple options, such as 'auto, no-shrink'. |
| alignmentBump    | string | undefined | Specifies a direction to bump the alignment of adjacent layout items. Allowed values are left, top, right, bottom.                                                                                                                                                                                                                                                                                                                                                                                                                    |
| padding          | string | undefined | Sets padding to either the right and left sides of a container, or all sides of a container. Allowed values are horizontal-small, horizontal-medium, horizontal-large, around-small, around-medium, around-large.                                                                                                                                                                                                                                                                                                                     |
| size             | number | undefined | If the viewport is divided into 12 parts, size indicates the relative space the container occupies. Size is expressed as an integer from 1 through 12. This applies for all device-types.                                                                                                                                                                                                                                                                                                                                             |
| smallDeviceSize  | number | undefined | If the viewport is divided into 12 parts, this attribute indicates the relative space the container occupies on device-types larger than mobile. It is expressed as an integer from 1 through 12.                                                                                                                                                                                                                                                                                                                                     |
| mediumDeviceSize | number | undefined | If the viewport is divided into 12 parts, this attribute indicates the relative space the container occupies on device-types larger than tablet. It is expressed as an integer from 1 through 12.                                                                                                                                                                                                                                                                                                                                     |
| largeDeviceSize  | number | undefined | If the viewport is divided into 12 parts, this attribute indicates the relative space the container occupies on device-types larger than desktop. It is expressed as an integer from 1 through 12.                                                                                                                                                                                                                                                                                                                                    |

### Methods

None

### Events

None

### Slots

#### default

- **Description:** Placeholder for your content in lightning-layout-item.

---

# Component API Structure

## Basic Information

- **Name:** menuDivider
- **Namespace:** lightning
- **Tag Name:** lightning-menu-divider
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Creates a dividing line after a menu item in a lightning-button-menu component. Use a menu divider to introduce a break between item categories or separate items into groups. The component should be used as a sibling of lightning-menu-item, not as a child component.

## API Reference

### Properties

| Name    | Type   | Default    | Description                                                                                                                                               |
| ------- | ------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| variant | string | 'standard' | The variant changes the spacing above and below the divider. Accepted variants include 'standard' and 'compact'. The compact variant decreases the space. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** menuItem
- **Namespace:** lightning
- **Tag Name:** lightning-menu-item
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Represents a list item in a menu. A menu item component is used within the lightning-button-menu dropdown component. It can hold state such as checked or unchecked, and can contain icons.

## API Reference

### Properties

| Name                 | Type              | Default    | Description                                                                                                                                                                                                                                                                                                                                                         |
| -------------------- | ----------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value                | string            | undefined  | A value associated with the menu item.                                                                                                                                                                                                                                                                                                                              |
| label                | string            | undefined  | Text of the menu item.                                                                                                                                                                                                                                                                                                                                              |
| download             | string            | undefined  | The name of a file that's downloaded when clicking a link in the menu item. Used with the href attribute.                                                                                                                                                                                                                                                           |
| href                 | string            | undefined  | URL for a link to use for the menu item.                                                                                                                                                                                                                                                                                                                            |
| draftAlternativeText | string            | undefined  | Describes the reason for showing the draft indicator. This is required when is-draft is present on the lightning-menu-item tag.                                                                                                                                                                                                                                     |
| iconName             | string            | undefined  | The name of an icon to display after the text of the menu item.                                                                                                                                                                                                                                                                                                     |
| prefixIconName       | string            | undefined  | The name of an icon to display before the text of the menu item.                                                                                                                                                                                                                                                                                                    |
| iconType             | string            | 'standard' | The iconType changes the appearance of the icons in the menu item. Accepted values include 'standard' and 'color'. This value defaults to 'standard'. Use 'color' to display action and object icons with their background colors.                                                                                                                                  |
| isDraft              | boolean           | false      | If present, a draft indicator is shown on the menu item. A draft indicator is denoted by blue asterisk on the left of the menu item. When you use a draft indicator, include alternative text for accessibility using draft-alternative-text.                                                                                                                       |
| accessKey            | string            | undefined  | The keyboard shortcut for the menu item.                                                                                                                                                                                                                                                                                                                            |
| tabIndex             | number            | -1         | Reserved for internal use. Use tabindex instead to indicate if an element should be focusable. tabindex can be set to 0 or -1. The default tabindex value is 0, which means that the menu item is focusable and participates in sequential keyboard navigation. The value -1 means that the menu item is focusable but does not participate in keyboard navigation. |
| target               | string            | null       | Determines how a link in the href attribute is opened. Valid values include '\_self' and '\_blank'. The default is '\_self', which opens the link in the current browser tab. '\_blank' opens the link in a new browser tab.                                                                                                                                        |
| disabled             | boolean           | false      | If present, the menu item is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                            |
| checked              | boolean \| string | undefined  | If present, a check mark displays on the left of the menu item if it's selected. Can accept boolean values or string values 'true' and 'false'.                                                                                                                                                                                                                     |

### Methods

#### focus

- **Description:** Sets focus on the anchor element in the menu item.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Clicks the anchor element in the menu item.
- **Parameters:** None
- **Returns:** void

### Events

#### blur

- **Description:** Fired when the menu item loses focus.
- **Payload:** None

#### focus

- **Description:** Fired when the menu item receives focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** menuSubheader
- **Namespace:** lightning
- **Tag Name:** lightning-menu-subheader
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Creates a subheader in the list of items in lightning-button-menu. The heading appears in bold text and is slightly larger than menu item text. Subheaders can help categorize items and improve usability for long lists. Use as a sibling of lightning-menu-item, not as a child component.

## API Reference

### Properties

| Name  | Type   | Default   | Description                          |
| ----- | ------ | --------- | ------------------------------------ |
| label | string | undefined | The text displayed in the subheader. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** messageService
- **Namespace:** lightning
- **Tag Name:** N/A (Library)
- **Version:** 47.0
- **Type:** LIBRARY
- **Description:** Lightning message service provides functions and wire adapters to communicate across the DOM between Visualforce pages, Aura components, and Lightning web components. Use Lightning message service to publish and subscribe to messages over Lightning message channels.

## API Reference

### Wire Adapters

#### MessageContext

- **Description:** A wire adapter that provides component context for a LightningElement. Annotate a component's property with @wire(MessageContext) and pass that context value to the first parameter of the subscribe and publish functions. When subscribing with a @wire(MessageContext) context value, all listeners associated with that component get automatically cleaned up on disconnectedCallback.
- **Returns:** MessageContext object

### Functions

#### subscribe

- **Description:** Subscribes a listener function to be invoked when a message is published on the provided channel.
- **Parameters:**
  - `messageContext` (Object, required): The MessageContext object
  - `messageChannel` (Object, required): MessageChannel object
  - `listener` (Function, required): Function to be invoked when messages are published on the channel
  - `subscriberOptions` (Object, optional): Options to influence message channel subscription. Current subscriber options include `scope` - the scope that a component is subscribed to. Setting this to APPLICATION_SCOPE subscribes in the application scope.
- **Returns:** Subscription object used to unsubscribe the listener, if no longer interested

#### unsubscribe

- **Description:** Unregisters the listener associated with the subscription.
- **Parameters:**
  - `subscription` (Object, required): Subscription object returned when subscribing
- **Returns:** void

#### publish

- **Description:** Send a message to listeners subscribed to the channel.
- **Parameters:**
  - `messageContext` (Object, required): The MessageContext object
  - `messageChannel` (Object, required): MessageChannel object
  - `message` (Object, optional): Serializable object to be sent to subscribers
  - `publisherOptions` (Object, optional): Options to influence message delivery
- **Returns:** void

#### createMessageChannel

- **Description:** Creates an anonymous MessageChannel object for use with Message Service.
- **Parameters:** None
- **Returns:** Anonymous MessageChannel object

#### createMessageContext

- **Description:** Creates a message context for an LWC library. Use this function in a service component that doesn't extend LightningElement where @wire(MessageContext) cannot be used.
- **Parameters:** None
- **Returns:** MessageContext object for use by LWC Library

#### releaseMessageContext

- **Description:** Releases a message context associated with LWC library and unsubscribes all associated subscriptions.
- **Parameters:**
  - `messageContext` (Object, required): MessageContext for use by LWC Library
- **Returns:** void

### Constants

#### APPLICATION_SCOPE

- **Description:** When using subscribe, APPLICATION_SCOPE is passed in as a value to the scope property of the subscriberOptions. This specifies that the subscriber wants to subscribe to messages on a message channel no matter where the subscriber is in the entire application.
- **Type:** Symbol
- **Usage:** Pass as `{ scope: APPLICATION_SCOPE }` to the subscriberOptions parameter of subscribe function

---

# Component API Structure

## Basic Information

- **Name:** modal
- **Namespace:** lightning
- **Tag Name:** N/A (Extended class, not used as a tag)
- **Version:** 55.0
- **Type:** COMPONENT
- **Description:** A base class to create modal window overlays on top of the current app window. This component is extended rather than used directly as a tag. Modal windows interrupt user workflow and block interaction with the rest of the page until the user acts upon or dismisses the modal. Use with helper components `lightning-modal-header`, `lightning-modal-body`, and `lightning-modal-footer` to provide the modal structure.

## API Reference

### Properties

| Name         | Type    | Default | Description                                                                                                                                                                                                                                     |
| ------------ | ------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| size         | string  | medium  | How much of the viewport width the modal uses. Supported values are small, medium, large, or full. Cannot be changed after the modal is opened.                                                                                                 |
| label        | string  | ''      | Sets the modal's title and assistive device label. Required for accessibility. If the modal has a header, set label in the lightning-modal-header component. If the modal doesn't have a header, set the label property when opening the modal. |
| description  | string  | ''      | Sets the modal's accessible description. Uses aria-description attribute where supported, or falls back to aria-describedby. If setting a custom description value, include the label name at the beginning of the description.                 |
| disableClose | boolean | false   | Prevents closing the modal by normal means like the ESC key, the close button, or .close(). Should only be used temporarily (less than 5 seconds) to avoid keyboard traps.                                                                      |

### Methods

#### open

- **Description:** Static method that opens a modal instance and returns a promise that resolves with the result of the user's interaction with the modal. Each invocation creates a unique instance of the modal. When closed, the modal instance is destroyed.
- **Parameters:**
  - `apis` (object, optional): Object containing property values to set on the modal instance. Can include size, label, description, disableClose, and any custom @api properties defined in the extended component. Can also include event handlers (e.g., onselect) to capture events from within the modal.
- **Returns:** Promise that resolves with the result passed to close() method, or undefined if closed without a result.

#### close

- **Description:** Closes the modal and resolves the promise returned by open() with an optional result. The close operation is asynchronous to display a fade out animation. If disableClose is true, calling this method will log an error and not close the modal.
- **Parameters:**
  - `result` (any, optional): Value returned to the caller of open(). If not provided, resolves with undefined.
- **Returns:** void

### Events

No public events are dispatched from this component.

### Slots

This component does not use traditional slots. Instead, use the following helper components within the modal template:

- **lightning-modal-header**: Optional. Provides the header section with a title and optional tagline content.
- **lightning-modal-body**: Required. Provides the main content area of the modal.
- **lightning-modal-footer**: Optional. Provides the footer section, typically containing action buttons.

---

# Component API Structure

## Basic Information

- **Name:** modalBody
- **Namespace:** lightning
- **Tag Name:** lightning-modal-body
- **Version:** 55.0
- **Type:** COMPONENT
- **Description:** The modal body component renders the main content area of a modal. It automatically handles scrolling when content exceeds the available space by calculating the maximum height to prevent content from exceeding the screen height and adding scroll bars as needed. The component should be placed after `lightning-modal-header` and before `lightning-modal-footer` in the modal structure.

## API Reference

### Properties

This component does not expose any public properties.

### Methods

None

### Events

None

### Slots

#### default

- **Description:** The default slot contains the main content to be displayed in the modal body. Content can be nested directly in the slot, and the component will automatically handle scrolling behavior when the content exceeds the available space.

---

# Component API Structure

## Basic Information

- **Name:** modalFooter
- **Namespace:** lightning
- **Tag Name:** lightning-modal-footer
- **Version:** 55.0
- **Type:** COMPONENT
- **Description:** Creates a footer at the bottom of a modal dialog. The footer is optional and typically contains action buttons. The component automatically hides when the slot is empty.

## API Reference

### Properties

This component has no public properties.

### Methods

None

### Events

None

### Slots

#### default

- **Description:** The default slot accepts footer content, typically `lightning-button` components or native button elements. The footer automatically hides when this slot is empty. Place this component after `lightning-modal-body` in your modal template.

---

# Component API Structure

## Basic Information

- **Name:** modalHeader
- **Namespace:** lightning
- **Tag Name:** lightning-modal-header
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Creates a header to display the heading and tagline at the top of a modal. Use of a header is optional, but when you provide a header you must specify the header text with the label attribute. The component must be used within a modal that extends LightningModal.

## API Reference

### Properties

| Name  | Type   | Default | Description                                                                                                   |
| ----- | ------ | ------- | ------------------------------------------------------------------------------------------------------------- |
| label | string | ''      | Text to display as the heading at the top of the modal. Required for accessibility when using this component. |

### Methods

None

### Events

None

### Slots

#### default

- **Description:** Optional tagline text that displays in smaller text below the heading. You can include links with `<a>` tags, which are the only HTML elements permitted. If the header text is too long to fit on one line, it wraps in the modal header.

---

# Component API Structure

## Basic Information

- **Name:** navigation
- **Namespace:** lightning
- **Tag Name:** N/A (Library)
- **Version:** 43.0
- **Type:** LIBRARY
- **Description:** Provides navigation service APIs to navigate between pages in Salesforce and get page references. Exports `CurrentPageReference` wire adapter to get the current page reference and `NavigationMixin` to add navigation capabilities to components.

## API Reference

### Wire Adapters

#### CurrentPageReference

- **Description:** Wire adapter that gets a reference to the current page in Salesforce. Page URL formats can change in future releases. To future proof apps, use page references instead of URLs. The key-value pairs of the PageReference `state` property are serialized to URL query parameters.
- **Returns:** PageReference object
- **Usage:**
  ```javascript
  import { CurrentPageReference } from 'lightning/navigation';
  @wire(CurrentPageReference)
  pageRef;
  ```

### Mixins

#### NavigationMixin

- **Description:** Mixin that adds navigation APIs to a component's base class. Apply this mixin to gain access to navigation methods. Invoking these methods before the element is connected to the DOM can have unexpected results.
- **Usage:**
  ```javascript
  import { NavigationMixin } from 'lightning/navigation';
  export default class MyCustomElement extends NavigationMixin(LightningElement) {}
  ```
- **Provides Methods:**
  - `[NavigationMixin.Navigate](pageReference, [replace])` - Navigates to another page in the application
  - `[NavigationMixin.GenerateUrl](pageReference)` - Returns a promise that resolves to a URL string for the given page reference

### Methods (via NavigationMixin)

#### [NavigationMixin.Navigate]

- **Description:** Navigates to another page in the application using a page reference
- **Parameters:**
  - `pageReference` (PageReference, required): The page reference object describing the target page
  - `replace` (boolean, optional): Whether to replace the current page in the browser history
- **Returns:** void

#### [NavigationMixin.GenerateUrl]

- **Description:** Generates a URL for a given page reference that can be used in anchor href attributes or window.open() calls
- **Parameters:**
  - `pageReference` (PageReference, required): The page reference object describing the target page
- **Returns:** Promise<string> - Promise that resolves to the resulting URL

---

# Component API Structure

## Basic Information

- **Name:** outputField
- **Namespace:** lightning
- **Tag Name:** lightning-output-field
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Represents a read-only display of a label, help text, and value for a field on a Salesforce object. Must be used as a child of lightning-record-view-form. Automatically formats field values based on field type and user locale settings.

## API Reference

### Properties

| Name       | Type   | Default                       | Description                                                                                                                                    |
| ---------- | ------ | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| fieldName  | string | null                          | The API name of the field to be displayed. Can be a string or an object with a fieldApiName property.                                          |
| fieldClass | string | 'slds-form-element\_\_static' | A CSS class for the outer element, in addition to the component's base classes.                                                                |
| variant    | string | 'standard'                    | Changes the appearance of the output. Accepted variants include standard, label-hidden, label-stacked, and label-inline. Defaults to standard. |

### Methods

#### wireRecordUi

- **Description:** Reserved for internal use. Wires record and object info data to the component.
- **Parameters:**
  - `data` (object, required): The record and objectInfo data
- **Returns:** void

#### wirePicklistValues

- **Description:** Reserved for internal use. Wires picklist values to the component.
- **Parameters:**
  - `picklistValues` (any, required): Reserved for internal use
- **Returns:** void

### Events

#### registeroutputfield

- **Description:** Fired during renderedCallback to notify containers when the component hasn't received uiField data yet.
- **Payload:**
  ```javascript
  {
    // No detail properties
  }
  ```

#### registerfielddependency

- **Description:** Fired when the field is a controller field for dependent picklist values.
- **Payload:**
  ```javascript
  {
    fieldName: string, // The field name
    fieldElement: {
      updateFieldOptions: function, // Function to update field options
      setFieldValue: function, // Function to set field value
      getFieldValue: function // Function to get the current field value
    }
  }
  ```

### Slots

#### default

- **Description:** Default slot for additional content within the form element control div.

---

# Library API Structure

## Basic Information

- **Name:** pageReferenceUtils
- **Namespace:** lightning
- **Tag Name:** N/A (Library)
- **Version:** 48.0+
- **Type:** LIBRARY
- **Description:** Provides utilities for encoding and decoding default field values to pass into the `pageReference.state.defaultFieldValues` attribute on `standard__objectPage` page reference types. Supported only in Lightning Experience in all editions. Not supported in Lightning Out, Experience Builder sites, or the Salesforce mobile app.

## API Reference

### Functions

#### encodeDefaultFieldValues

- **Description:** Encodes default field values from a JavaScript object into a serialized string format (comma-separated key-value pairs with URL encoding).
- **Parameters:**
  - `defaultFieldValues` (object, required): Non-null object containing key-value pairs for default field values. Values must be string, number, boolean, null, or undefined. Values of undefined are dropped from the output. Values of null result in a key with no value.
- **Returns:** string - Encoded string in format `key1=value1,key2=value2` with URL encoding applied
- **Throws:**
  - TypeError if input is not a non-null object
  - TypeError if any value is not a string, number, boolean, null, or undefined

#### decodeDefaultFieldValues

- **Description:** Decodes default field values from a serialized string into a standard object. Use this method when overriding a standard action only. All returned values are strings; field type is not preserved.
- **Parameters:**
  - `dfvString` (string, required): Encoded string of default field values in the format produced by `encodeDefaultFieldValues`
- **Returns:** object - Decoded object with key-value pairs. Keys without values are set to null. Handles plus signs (+) as spaces in addition to standard URL decoding.
- **Throws:** TypeError if input is not a string

## Usage Notes

### Supported Objects

The following objects are NOT supported:

- ContractLineItem
- OpportunityLineItem
- OrderItem
- QuoteLineItem
- WorkOrderLineItem

### Field Restrictions

- `recordTypeId` is not supported in `defaultFieldValues`
- System-maintained fields (Id, modification timestamps) cannot be prepopulated
- Rich text fields cannot be prepopulated
- Date fields must use ISO 8601 format (e.g., 2017-07-18)
- Datetime fields must use ISO 8601 format in UTC (e.g., 2017-07-18T03:00:00Z)

### Field Visibility and Security

- Hidden fields (not on page layout) will be saved if specified in `defaultFieldValues`
- Fields without create access due to field-level security will cause save errors
- Perform access checks before using this utility to avoid user-facing errors

### Import Syntax

```javascript
import { encodeDefaultFieldValues } from 'lightning/pageReferenceUtils';
import { decodeDefaultFieldValues } from 'lightning/pageReferenceUtils';
```

---

# Component API Structure

## Basic Information

- **Name:** pill
- **Namespace:** lightning
- **Tag Name:** lightning-pill
- **Version:** 0.0
- **Type:** COMPONENT
- **Description:** A pill displays a label that can contain links and can be removed from view. Pills are useful for displaying read-only text that can be added and removed on demand, such as email addresses or keywords.

## API Reference

### Properties

| Name         | Type    | Default   | Description                                                                                                                                                                                                                                                                                                                              |
| ------------ | ------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| href         | string  | undefined | The URL of the page that the link goes to. URLs without a protocol use the host domain's protocol.                                                                                                                                                                                                                                       |
| label        | string  | undefined | The text label that displays in the pill. This property is required.                                                                                                                                                                                                                                                                     |
| name         | string  | undefined | The name for the pill. This value is optional and can be used to identify the pill in a callback.                                                                                                                                                                                                                                        |
| variant      | string  | 'link'    | The variant changes the appearance of the pill. Accepted variants include 'link', 'plain', and 'plainLink'. The 'link' variant creates a link in the pill when you specify the href attribute. The 'plain' variant renders the pill without a link and ignores the href attribute. The 'plainLink' variant is reserved for internal use. |
| hasError     | boolean | false     | If present, the pill is shown with a red border and an error icon on the left of the label.                                                                                                                                                                                                                                              |
| isPlainLink  | boolean | computed  | Reserved for internal use. Specifies whether the element variant is a plain link. Returns true if variant is 'plainLink'. This property is readonly.                                                                                                                                                                                     |
| tabIndex     | number  | undefined | Reserved for internal use. Use tabindex instead to indicate if an element should be focusable. A value of 0 means that the pill is focusable and participates in sequential keyboard navigation. A value of -1 means that the pill is focusable but does not participate in keyboard navigation.                                         |
| ariaSelected | boolean | undefined | Reserved for internal use. Specifies the aria-selected of an element.                                                                                                                                                                                                                                                                    |
| role         | string  | undefined | Reserved for internal use. Specifies the role of an element.                                                                                                                                                                                                                                                                             |

### Methods

#### focusLink

- **Description:** Reserved for internal use. Sets focus on the anchor element for a plainLink pill.
- **Parameters:** None
- **Returns:** void

#### focusRemove

- **Description:** Reserved for internal use. Sets focus on the remove button element for a plain pill.
- **Parameters:** None
- **Returns:** void

### Events

#### remove

- **Description:** The first event fired when you click the remove button. This event is cancelable. You can call preventDefault() on this event to prevent the click event from being fired when clicking the remove button.
- **Payload:**
  ```javascript
  {
    name: string; // The name of the pill that's removed
  }
  ```

#### focus

- **Description:** Fired when the pill receives focus.
- **Payload:** None

#### blur

- **Description:** Fired when the pill loses focus.
- **Payload:**
  ```javascript
  {
    relatedTarget: Element; // The element which will receive focus next
  }
  ```

### Slots

#### default

- **Description:** Placeholder for an image, such as an icon or avatar. Nest a lightning-icon or lightning-avatar component inside the lightning-pill component to display an icon or avatar representing the type of object.

---

# Component API Structure

## Basic Information

- **Name:** pillContainer
- **Namespace:** lightning
- **Tag Name:** lightning-pill-container
- **Version:** 42.0
- **Type:** COMPONENT
- **Description:** A list of pills grouped in a container. This component displays pills that can contain text, links, icons, or avatars. It provides keyboard navigation and supports various layout modes including single-line display and expandable/collapsible lists.

## API Reference

### Properties

| Name          | Type    | Default             | Description                                                                                                                                                                                                                                                                                               |
| ------------- | ------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label         | string  | "Selected Options:" | Aria label for the pill container to describe the list of options.                                                                                                                                                                                                                                        |
| variant       | string  | "standard"          | The variant changes the tab navigation behavior of the pill container. Accepted values are "standard" and "bare". The standard variant supports accessibility with arrow key navigation, while the bare variant only supports Tab key navigation.                                                         |
| singleLine    | boolean | false               | Specifies whether to limit pill display to one line. This attribute overrides the is-collapsible and is-expanded attributes.                                                                                                                                                                              |
| isCollapsible | boolean | false               | Specifies whether the pill list can be collapsed. Use is-collapsible with the is-expanded attribute to expand and collapse the list of pills.                                                                                                                                                             |
| isExpanded    | boolean | false               | Specifies whether the list of pills is expanded or collapsed, when is-collapsible is true. This attribute is ignored when is-collapsible is false, and the list of pills is expanded even if is-expanded is false or not set.                                                                             |
| items         | array   | undefined           | An array of pill attribute values that define pills to display in the container. Each item can have properties: label (required), name, href, type ("avatar" or "icon"), and type-specific properties (iconName, alternativeText for icons; src, fallbackIconName, variant, alternativeText for avatars). |

### Methods

#### focus

- **Description:** Sets focus on the pill list. If pills exist, focuses on the current pill (either the link or remove button). If no pills exist, focuses on the container's unordered list element.
- **Parameters:** None
- **Returns:** void

### Events

#### itemremove

- **Description:** The event fired when a pill is removed by clicking the remove button.
- **Payload:**
  ```javascript
  {
    item: object, // The pill item object that was removed
    index: number // The position of the pill in the items array
  }
  ```

#### focus

- **Description:** The event fired when the pill container or any pill within it receives focus. Also fires when the "+n more" button is clicked.
- **Payload:** None

#### blur

- **Description:** The event fired when focus leaves the pill container completely (not when moving between pills within the container).
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** progressBar
- **Namespace:** lightning
- **Tag Name:** lightning-progress-bar
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Displays a horizontal progress bar from left to right to indicate the progress of an operation.

## API Reference

### Properties

| Name      | Type   | Default   | Description                                                                                                                                                              |
| --------- | ------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| value     | number | 0         | The percentage value of the progress bar. Values are rounded and clamped between 0 and 100.                                                                              |
| ariaLabel | string | undefined | Describes the input to assistive technologies. When not provided, defaults to a localized "Progress Bar" label.                                                          |
| variant   | string | base      | The variant changes the appearance of the progress bar. Accepted variants include base or circular. The circular variant adds a border radius to give it a rounded look. |
| size      | string | medium    | The size of the progress bar. Valid values are x-small, small, medium, and large.                                                                                        |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** progressRing
- **Namespace:** lightning
- **Tag Name:** lightning-progress-ring
- **Version:** 48.0
- **Type:** COMPONENT
- **Description:** Displays a circular progress indicator to provide feedback about an action or process. Shows a value from 0 to 100 by filling the ring with color in a clockwise or counterclockwise direction. Supports multiple variants to change styling and provide contextual feedback.

## API Reference

### Properties

| Name      | Type   | Default   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --------- | ------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value     | number | 0         | The percentage value of the progress ring. Must be a number from 0 to 100. A value of 50 corresponds to a color fill of half the ring in a clockwise or counterclockwise direction, depending on the direction attribute.                                                                                                                                                                                                                     |
| variant   | string | 'base'    | Changes the appearance of the progress ring. Accepted variants include base, active-step, warning, expired, base-autocomplete. The base variant uses default green fill. The active-step variant uses blue fill. The warning variant uses yellow fill and displays a warning icon. The expired variant uses red fill and displays an error icon. The base-autocomplete variant uses green fill and displays a success icon when value is 100. |
| direction | string | 'fill'    | Controls which way the color flows from the top of the ring. Valid values include fill and drain. The fill value corresponds to a color flow in the clockwise direction. The drain value indicates a color flow in the counterclockwise direction.                                                                                                                                                                                            |
| ariaLabel | string | undefined | Descriptive label provided for assistive technologies. If not provided, defaults to a localized "Progress Ring" label.                                                                                                                                                                                                                                                                                                                        |
| size      | string | 'medium'  | The size of the progress ring. Valid values include medium and large.                                                                                                                                                                                                                                                                                                                                                                         |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** prompt
- **Namespace:** lightning
- **Tag Name:** lightning-prompt
- **Version:** 54.0
- **Type:** COMPONENT
- **Description:** Creates a prompt modal within your component that asks the user to provide information before they continue. Use `LightningPrompt.open()` instead of the native `window.prompt()` for a more consistent user experience. Unlike `window.prompt()`, `LightningPrompt.open()` doesn't halt execution on the page and returns a Promise. Works in cross-origin iframes where native `.prompt()` is no longer supported in Chrome and Safari.

## API Reference

### Properties

| Name         | Type   | Default               | Description                                                                                                                                                |
| ------------ | ------ | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label        | string | "Prompt" (translated) | Value to use for header text in "header" variant or aria-label in "headerless" variant                                                                     |
| message      | string | ''                    | Text to display in the prompt                                                                                                                              |
| defaultValue | string | ''                    | Default value for input                                                                                                                                    |
| variant      | string | 'header'              | Variant to use for the prompt. Valid values are "header" and "headerless"                                                                                  |
| theme        | string | 'default'             | Theme to use when variant is "header". Valid values are "default", "shade", "inverse", "alt-inverse", "success", "info", "warning", "error", and "offline" |

### Methods

#### open

- **Description:** Static method that opens a prompt modal instance. Returns a promise that resolves to the input text value if OK is clicked, or null if Cancel is clicked.
- **Parameters:**
  - `apis` (object, required): Object containing properties to set on the modal instance (e.g., label, message, defaultValue, variant, theme)
- **Returns:** Promise<string|null>

#### close

- **Description:** Closes the prompt modal and resolves the promise with the provided result. This method is public for testing only.
- **Parameters:**
  - `result` (any, required): Value to be returned in the promise
- **Returns:** void

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** radioGroup
- **Namespace:** lightning
- **Tag Name:** lightning-radio-group
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A radio button group that permits only one button to be selected at a time. The component renders radio button input elements and assigns the same value to the name attribute for each element, joining them in a group. When you select any radio button in the group, any previously selected button is deselected.

## API Reference

### Properties

| Name                    | Type    | Default        | Description                                                                                                                                                                                                                                                                                                                                               |
| ----------------------- | ------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type                    | string  | radio          | The style of the radio group. Options are radio or button.                                                                                                                                                                                                                                                                                                |
| label                   | string  | null           | Text label for the radio group. Required.                                                                                                                                                                                                                                                                                                                 |
| options                 | array   | null           | Array of label-value pairs for each radio button. Each object should have a label (string) and value (string) property. Required.                                                                                                                                                                                                                         |
| messageWhenValueMissing | string  | null           | Optional message displayed when no radio button is selected and the required attribute is set to true.                                                                                                                                                                                                                                                    |
| name                    | string  | auto-generated | Specifies the name of the radio button group. Only one button can be selected if a name is specified for the group. If not provided, a unique name is automatically generated.                                                                                                                                                                            |
| value                   | string  | null           | Specifies the value of the selected radio button.                                                                                                                                                                                                                                                                                                         |
| disabled                | boolean | false          | If present, the radio group is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                |
| required                | boolean | false          | If present, a radio button must be selected before the form can be submitted.                                                                                                                                                                                                                                                                             |
| variant                 | string  | standard       | The variant changes the appearance of the radio group. Accepted variants include standard, label-hidden, label-inline, and label-stacked. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and radio group. Use label-stacked to place the label above the radio group. |
| validity                | object  | null           | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                               |

### Methods

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the radio group has any validity errors.

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when the radio group value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### showHelpMessageIfInvalid

- **Description:** Shows the help message if the form control is in an invalid state.
- **Parameters:** None
- **Returns:** void

#### focus

- **Description:** Sets focus on the first radio input element.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** Dispatched when a radio button selection is changed. The event bubbles and is composed.
- **Payload:**
  ```javascript
  {
    value: string; // The value of the selected radio button
  }
  ```

#### focus

- **Description:** Dispatched when the radio group receives focus.
- **Payload:** None

#### blur

- **Description:** Dispatched when the radio group loses focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** recordEditForm
- **Namespace:** lightning
- **Tag Name:** lightning-record-edit-form
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Represents a record edit layout that displays one or more fields, provided by lightning-input-field. Use to create a form that adds a Salesforce record or updates fields in an existing record on an object. Supports editing a record's specified fields, creating a record using specified fields, customizing the form layout, and custom rendering of record data. Implements Lightning Data Service and handles field-level security automatically.

## API Reference

### Properties

| Name           | Type     | Default   | Description                                                                                                                                                                                                                                                                                                                                                                |
| -------------- | -------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| objectApiName  | string   | null      | The API name of the object. Required.                                                                                                                                                                                                                                                                                                                                      |
| recordId       | string   | null      | The ID of the record to be displayed. If provided, the form edits an existing record. If not provided, the form creates a new record.                                                                                                                                                                                                                                      |
| recordTypeId   | string   | null      | The ID of the record type, which is required if you created multiple record types but don't have a default.                                                                                                                                                                                                                                                                |
| formClass      | string   | undefined | A CSS class for the form element.                                                                                                                                                                                                                                                                                                                                          |
| fieldNames     | string[] | undefined | Reserved for internal use. Names of the fields to include in the form.                                                                                                                                                                                                                                                                                                     |
| layoutType     | string   | 'Full'    | Reserved for internal use. The type of layout to use to display the form fields. Possible values: Compact, Full.                                                                                                                                                                                                                                                           |
| optionalFields | string[] | []        | The optional fields of the record.                                                                                                                                                                                                                                                                                                                                         |
| density        | string   | 'auto'    | Sets the arrangement style of fields and labels in the form. Accepted values are compact, comfy, and auto (default). Use compact to display fields and their labels on the same line. Use comfy to display fields below their labels. Use auto to let the component dynamically set the density according to the user's Display Density setting and the width of the form. |

### Methods

#### submit

- **Description:** Submits the form using an array of record fields or field IDs. The field ID is provisioned from @salesforce/schema/. Invoke this method only after the load event.
- **Parameters:**
  - `fields` (string[]|FieldId[], required): Array of record field names or field IDs.
- **Returns:** void

### Events

#### load

- **Description:** The event fired when the record edit form loads record data. If you load the fields dynamically, load is fired before the child elements of lightning-record-edit-form finish loading. The load event is fired when the record-id value changes, the fields list changes, the form includes picklist fields, or the record type changes.
- **Payload:**
  ```javascript
  {
    // Returns the record UI and picklist values if picklist fields are included in the form
    // See https://developer.salesforce.com/docs/atlas.en-us.uiapi.meta/uiapi/ui_api_responses_record_ui.htm
  }
  ```

#### error

- **Description:** The event fired when the record edit form returns a server-side error.
- **Payload:**
  ```javascript
  {
    message: string, // General description of error
    detail: object, // Description of error details, if any
    output: object // Record exception errors with errors and fieldErrors properties
  }
  ```

#### submit

- **Description:** The event fired when the submit button is pressed. Client-side validation errors, if any, are displayed. The form is then submitted only when all fields in the form are valid. The form can be submitted only after it's loaded.
- **Payload:**
  ```javascript
  {
    fields: object; // The editable fields that are provided for submission during a record create or edit
  }
  ```

#### success

- **Description:** The event fired when the record data is updated successfully. The load event then fires to return the updated data.
- **Payload:**
  ```javascript
  {
    id: string; // The ID of the saved record
    // Additional record data - see https://developer.salesforce.com/docs/atlas.en-us.uiapi.meta/uiapi/ui_api_responses_record.htm
  }
  ```

### Slots

#### default

- **Description:** Placeholder for form components like lightning-messages, lightning-button, lightning-input-field and lightning-output-field. Use lightning-input-field to display an editable field.

---

# Component API Structure

## Basic Information

- **Name:** recordForm
- **Namespace:** lightning
- **Tag Name:** lightning-record-form
- **Version:** 43.0
- **Type:** COMPONENT
- **Description:** Creates an editable form or display form for a record. Provides automatic switching between view and edit modes, automatic Cancel and Save buttons, and uses the object's default record layout with support for multiple columns. Easier to use than building forms manually with lightning-record-edit-form or lightning-record-view-form, but less customizable.

## API Reference

### Properties

| Name          | Type     | Default   | Description                                                                                                                                                                                                                                                                                                                                                                |
| ------------- | -------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| recordId      | string   | null      | The ID of the record to be displayed. Required when editing or viewing a record. Not required when creating a new record.                                                                                                                                                                                                                                                  |
| objectApiName | string   | null      | The API name of the object. Required.                                                                                                                                                                                                                                                                                                                                      |
| layoutType    | string   | null      | The type of layout to use to display the form fields. Possible values: Compact, Full. When creating a new record, only the full layout is supported.                                                                                                                                                                                                                       |
| recordTypeId  | string   | null      | The ID of the record type, which is required if you created multiple record types but don't have a default.                                                                                                                                                                                                                                                                |
| fields        | string[] | []        | List of fields to be displayed. The fields display in the order you list them. Can also accept an array of field objects with fieldApiName and objectApiName properties.                                                                                                                                                                                                   |
| mode          | string   | undefined | Specifies the interaction and display style for the form. Possible values: view, edit, readonly. If a record ID is not provided, the default mode is edit. If a record ID is provided, the default mode is view.                                                                                                                                                           |
| density       | string   | auto      | Sets the arrangement style of fields and labels in the form. Accepted values are compact, comfy, and auto (default). Use compact to display fields and their labels on the same line. Use comfy to display fields below their labels. Use auto to let the component dynamically set the density according to the user's Display Density setting and the width of the form. |
| columns       | number   | 1         | Specifies the number of columns for the form. Must be a positive integer.                                                                                                                                                                                                                                                                                                  |

### Methods

#### submit

- **Description:** Submits the form using an array of record fields or field IDs. The field ID is provisioned from @salesforce/schema/. Invoke this method only after the load event.
- **Parameters:**
  - `fields` (string[]|FieldId[], required): Array of record field names or field IDs.
- **Returns:** void

### Events

#### load

- **Description:** The event fired when the record fields are loaded. Use this event to perform logic after the form loads, such as to modify the fields before they are displayed.
- **Payload:**
  ```javascript
  {
    objectInfos: object, // Object information containing field metadata
    records: object, // Record data
    record: object // Single record object (when recordId is provided)
  }
  ```

#### error

- **Description:** The event fired when an error occurs during loading or submission of the form. Errors are automatically handled by the component.
- **Payload:**
  ```javascript
  {
    // Error details from the underlying lightning-record-edit-form component
  }
  ```

#### cancel

- **Description:** The event fired when the user clicks the Cancel button. If the form includes the recordId attribute, pressing the Cancel button returns the user to view mode with initial values provided by the record. If you don't provide the recordId attribute, pressing the Cancel button resets the fields to blank values.
- **Payload:** None

#### submit

- **Description:** The event fired when the user clicks the Submit button or when the submit() method is called. Use this event to customize form submission behavior, such as to perform validation or modify field values before submission.
- **Payload:**
  ```javascript
  {
    fields: object; // The fields to be submitted
  }
  ```

#### success

- **Description:** The event fired when the form is successfully submitted and the record is created or updated. Use this event to perform actions after successful submission, such as displaying a toast message.
- **Payload:**
  ```javascript
  {
    id: string, // The ID of the created or updated record
    // Additional record information from the User Interface API
  }
  ```

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** recordPicker
- **Namespace:** lightning
- **Tag Name:** lightning-record-picker
- **Version:** 59.0
- **Type:** COMPONENT
- **Description:** A component that provides an input search field that can search for Salesforce records. It uses the GraphQL wire adapter to search for records, displays the records, and allows selection of a record.

## API Reference

### Properties

| Name                | Type    | Default | Description                                                                                                                                                                                                                                                         |
| ------------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label               | string  | null    | The text label for the component. Required.                                                                                                                                                                                                                         |
| placeholder         | string  | null    | The text displayed when the input is empty to prompt the user to enter a search term.                                                                                                                                                                               |
| objectApiName       | string  | null    | The API name of the object for the retrieved records. Required.                                                                                                                                                                                                     |
| value               | string  | null    | The ID of the record that is selected in the record picker.                                                                                                                                                                                                         |
| filter              | object  | null    | The filter applied to the retrieved records. Object with a `criteria` property (array of filter criteria objects) and an optional `filterLogic` property.                                                                                                           |
| displayInfo         | object  | null    | The display configuration used to customize the way retrieved records are presented. Object with optional `primaryField` (string) and `additionalFields` (array) properties.                                                                                        |
| matchingInfo        | object  | null    | The matching configuration to customize the fields used to match the search results to the search term entered by the user. Object with optional `primaryField` (object with `fieldPath` and optional `mode` properties) and `additionalFields` (array) properties. |
| required            | boolean | false   | If present, specifies that a user must select a record. If no record is selected, the record picker is in an invalid state.                                                                                                                                         |
| variant             | string  | null    | The variant changes the appearance of the component. The component displays the label above the combobox by default. Specify variant="label-hidden" to hide the label but make it available to assistive technology.                                                |
| fieldLevelHelp      | string  | null    | Help text detailing the purpose and function of the record picker, displayed on hover for desktop and on click for mobile.                                                                                                                                          |
| disabled            | boolean | false   | If present, the component is disabled and you can't interact with it.                                                                                                                                                                                               |
| messageWhenBadInput | string  | null    | The error message displayed when the user enters a search term in the input but doesn't select an option.                                                                                                                                                           |

### Methods

#### clearSelection

- **Description:** Clears the selected record. This method does not clear the search term or refresh the validity message.
- **Parameters:** None
- **Returns:** void

#### focus

- **Description:** Set the focus of the component.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Remove the focus of the component.
- **Parameters:** None
- **Returns:** void

#### reportValidity

- **Description:** Check if the component is in a valid state and refresh the validity message. If the component is valid, it clears the validity error message. If the component is invalid, it displays the validity error message.
- **Parameters:** None
- **Returns:** boolean - Returns true if the component is in a valid state.

#### checkValidity

- **Description:** Check if the component is in a valid state.
- **Parameters:** None
- **Returns:** boolean - Returns true if the component is in a valid state.

#### setCustomValidity

- **Description:** Set a custom validity error message.
- **Parameters:**
  - `message` (string, required): A custom validity message. Specify an empty string to reset the custom message.
- **Returns:** void

### Events

#### change

- **Description:** The event fired when a record has been selected or cleared.
- **Payload:**
  ```javascript
  {
    recordId: string; // The ID of the selected record or null if none
  }
  ```

#### error

- **Description:** The event fired when Lightning Data Service returns an error.
- **Payload:**
  ```javascript
  {
    error: {
      message: string, // The error message
      output: string, // The error details
      errorCode: string // The error code with format ERR_RP00x
    }
  }
  ```

#### focus

- **Description:** The event fired when the focus is set.
- **Payload:**
  ```javascript
  {
  }
  ```

#### blur

- **Description:** The event fired when the focus is removed.
- **Payload:**
  ```javascript
  {
  }
  ```

#### ready

- **Description:** The event fired when the component stops loading and is rendered. Use this event to call methods on the component after it finishes rendering.
- **Payload:**
  ```javascript
  {
  }
  ```

### Slots

This component does not define any slots.

---

# Component API Structure

## Basic Information

- **Name:** recordViewForm
- **Namespace:** lightning
- **Tag Name:** lightning-record-view-form
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** Represents a record view layout that displays one or more fields, provided by lightning-output-field. This component creates a form that displays Salesforce record data for specified fields associated with that record. The fields are rendered with their labels and current values as read-only. The component handles field-level security and sharing automatically, so users see only the data they have access to. It does not require additional Apex controllers or Lightning Data Service to display record data.

## API Reference

### Properties

| Name           | Type   | Default | Description                                                                                                                                                                                                                                                                                                                                                                            |
| -------------- | ------ | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| density        | string | 'auto'  | Sets the arrangement style of fields and labels in the form. Accepted values are 'compact', 'comfy', and 'auto' (default). Use 'compact' to display fields and their labels on the same line. Use 'comfy' to display fields below their labels. Use 'auto' to let the component dynamically set the density according to the user's Display Density setting and the width of the form. |
| recordId       | string | null    | The ID of the record to be displayed. This property is required.                                                                                                                                                                                                                                                                                                                       |
| objectApiName  | string | null    | The API name of the object. This property is required. The object API name must be appropriate for the use of the component and must agree with the record ID, otherwise the form does not display.                                                                                                                                                                                    |
| optionalFields | array  | []      | The optional fields of the record. Allows specifying additional fields to fetch beyond those explicitly defined in lightning-output-field components.                                                                                                                                                                                                                                  |

### Methods

None

### Events

#### load

- **Description:** Fired when the record view form loads record data. This event is fired when the form gets new data from Lightning Data Service, which can occur once or multiple times after the component is initialized. For example, the event is fired when the record-id value changes, the fields list changes, the form includes picklist fields, or the record type changes.
- **Payload:**
  ```javascript
  {
    detail: object; // Contains the record UI data including records, objectInfos, layout, and layoutUserState
  }
  ```
- **Properties:**
  - bubbles: false
  - cancelable: false
  - composed: false

#### error

- **Description:** Fired when an error occurs during record data loading or processing. This includes errors from invalid record IDs, API name mismatches, or data fetching failures.
- **Payload:**
  ```javascript
  {
    detail: object; // Contains error information including message and other error details
  }
  ```

### Slots

#### default

- **Description:** Placeholder for lightning-output-field components. Use lightning-output-field components inside this slot to specify which fields to display on the record. The component automatically fetches and displays the record data for the specified fields.

---

# Library API Structure

## Basic Information

- **Name:** refresh
- **Namespace:** lightning
- **Tag Name:** N/A (Library)
- **Version:** 55.0
- **Type:** LIBRARY
- **Description:** Provides a standard way to refresh component data in LWC. Enables updating data for a specific hierarchy of components (a "view"), without reloading an entire page. Implements a refresh tree system where components can register as refresh handlers or containers to participate in coordinated data refresh operations.

## API Reference

### Exported Functions

#### registerRefreshContainer

- **Description:** Register a component as a refresh container. The registered element will begin the refresh process when it receives a RefreshEvent. Containers initiate and coordinate the refresh process for their descendants.
- **Parameters:**
  - `contextElement` (HTMLElement | LightningElement, required): The component element to register as a refresh container
  - `providerMethod` (Function, required): The callback method that will be invoked when refresh is triggered. This method receives a Promise as a parameter that will be resolved when all descendant refresh handlers complete
- **Returns:** number - A refresh handle (ID) that can be used to unregister the container
- **Throws:**
  - Error if contextElement is not an HTMLElement or LightningElement
  - Error if providerMethod is not a function
  - Error if element is already registered with the same registration type

#### unregisterRefreshContainer

- **Description:** Unregister a component as a refresh container, removing it from the refresh tree.
- **Parameters:**
  - `refreshID` (number, required): The handle returned by registerRefreshContainer
- **Returns:** void

#### registerRefreshHandler

- **Description:** Register a refresh callback to be called at the appropriate time in a view refresh process. Handlers perform the actual data refresh operations and must return a Promise.
- **Parameters:**
  - `contextElement` (HTMLElement | LightningElement, required): The component element that wishes to participate in refresh
  - `providerMethod` (Function, required): The method responsible for performing refresh logic. Must return a Promise that resolves when refresh is complete
- **Returns:** number - A refresh handle (ID) that can be used to unregister the handler
- **Throws:**
  - Error if contextElement is not an HTMLElement or LightningElement
  - Error if providerMethod is not a function
  - Error if element is already registered with the same registration type

#### unregisterRefreshHandler

- **Description:** Remove a refresh handler's registration from the refresh tree.
- **Parameters:**
  - `refreshID` (number, required): The handle returned by registerRefreshHandler
- **Returns:** void

### Exported Classes

#### RefreshEvent

- **Description:** A CustomEvent that signals a refresh request to a container. Dispatching this event initiates the refresh process for the containing refresh tree.
- **Properties:**
  - `type` (string): Event type is 'lightning\_\_refresh'
  - `bubbles` (boolean): true
  - `composed` (boolean): true
  - `cancelable` (boolean): true
- **Constructor:** Takes no parameters

### Exported Constants

#### RefreshEventName

- **Type:** string
- **Value:** 'lightning\_\_refresh'
- **Description:** The event name used for refresh events

#### REFRESH_COMPLETE

- **Type:** number
- **Value:** 1
- **Description:** Status constant indicating the refresh process has completed successfully on all descendant refresh handler nodes

#### REFRESH_COMPLETE_WITH_ERRORS

- **Type:** number
- **Value:** 2
- **Description:** Status constant indicating the refresh process has completed on descendant refresh handler nodes, but some children have reported an error

#### REFRESH_ERROR

- **Type:** number
- **Value:** 0
- **Description:** Status constant indicating the refresh process was not able to run on descendant refresh handler nodes

## Usage Notes

- Components can register as both a refresh handler and a refresh container on the same element
- Refresh handlers must return a Promise from their providerMethod
- If a refresh handler takes longer than 20 seconds (REFRESH_TIMEOUT), it will be placed in a timeout state and the refresh process will continue without waiting for it
- The refresh process maintains a tree structure where containers coordinate refresh operations for their descendant handlers
- Refresh operations cascade through the tree from parent to child nodes
- The providerMethod for containers receives a Promise parameter that resolves with a status constant (REFRESH_COMPLETE, REFRESH_COMPLETE_WITH_ERRORS, or REFRESH_ERROR)
- The providerMethod for handlers receives no parameters and must return a Promise

---

# Component API Structure

## Basic Information

- **Name:** relativeDateTime
- **Namespace:** lightning
- **Tag Name:** lightning-relative-date-time
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Displays the relative time difference between the current date-time and the provided date-time. The component automatically updates the displayed value as time passes to keep the relative time accurate. It formats the relative time for the current locale following the rules from Unicode CLDR.

## API Reference

### Properties

| Name  | Type                 | Default   | Description                                                                                                                                                                                                                                                                                          |
| ----- | -------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| value | Date\|number\|string | undefined | The timestamp or JavaScript Date object to be formatted. Accepts a JavaScript Date object, a timestamp (number), or undefined/null/empty string (which displays nothing). The component displays the relative time between the current time and this value, such as "2 hours ago" or "in 5 minutes". |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** richTextToolbarButton
- **Namespace:** lightning
- **Tag Name:** lightning-rich-text-toolbar-button
- **Type:** COMPONENT
- **Description:** A custom button for the toolbar in lightning-input-rich-text. This component creates interactive buttons that can perform custom actions, format text, or open popups. Buttons must be placed inside lightning-rich-text-toolbar-button-group components.

## API Reference

### Properties

| Name                | Type    | Default   | Description                                                                                                                                                                                                |
| ------------------- | ------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| iconName            | string  | undefined | The Lightning Design System name of the icon for the button. Format: 'utility:down' where 'utility' is the category and 'down' is the specific icon.                                                       |
| iconAlternativeText | string  | undefined | Alternative text describing what happens when the button is clicked (e.g., 'Upload File'). Used for accessibility and button tooltips. Should describe the action, not the icon's appearance.              |
| disabled            | boolean | false     | Specifies whether the button is disabled. Disabled buttons cannot be clicked and appear with a light gray icon.                                                                                            |
| selected            | boolean | false     | Indicates whether the button is in a selected/pressed state. A selected button displays with a dark background color. Returns null if ariaHasPopup is set, as buttons with popups do not use aria-pressed. |
| ariaHasPopup        | string  | undefined | Value for the aria-haspopup attribute. Indicates the type of popup element the button opens (e.g., 'dialog', 'menu'). Buttons with this attribute do not use aria-pressed.                                 |
| groupOrder          | any     | undefined | Reserved for internal use only.                                                                                                                                                                            |

### Methods

#### showPopup

- **Description:** Displays a popup below the button. Content passed into the default slot is rendered inside the popup. The popup is positioned centered below the button.
- **Parameters:** None
- **Returns:** void

#### closePopup

- **Description:** Closes the popup that was displayed below the button.
- **Parameters:** None
- **Returns:** void

#### focus

- **Description:** Sets focus on the button element.
- **Parameters:** None
- **Returns:** void

#### click

- **Description:** Simulates a click on the button element.
- **Parameters:** None
- **Returns:** void

### Events

#### popupclickout

- **Description:** Fires when a popup is open and the user clicks outside of it. Can be prevented using preventDefault() to keep the popup open. If not prevented, the popup automatically closes.
- **Payload:** None

#### focus

- **Description:** Fires when the button receives focus.
- **Payload:** None

#### blur

- **Description:** Fires when the button loses focus.
- **Payload:** None

### Slots

#### default

- **Description:** Content to be displayed inside the popup. Any components nested within lightning-rich-text-toolbar-button are rendered as the popup content when showPopup() is called.

---

# Component API Structure

## Basic Information

- **Name:** richTextToolbarButtonGroup
- **Namespace:** lightning
- **Tag Name:** lightning-rich-text-toolbar-button-group
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Creates a custom button group in lightning-input-rich-text. This is a container component for custom buttons that is used in the toolbar slot of lightning-input-rich-text. The group is displayed at the end of the toolbar. A group is required for custom buttons, even if there is only one custom button. Multiple button groups can be included in lightning-input-rich-text, and each group can contain multiple lightning-rich-text-toolbar-button components.

## API Reference

### Properties

| Name      | Type   | Default   | Description                                                     |
| --------- | ------ | --------- | --------------------------------------------------------------- |
| ariaLabel | string | undefined | Describes the custom button category to assistive technologies. |

### Methods

None

### Events

None

### Slots

#### default

- **Description:** Placeholder for custom buttons. Use lightning-rich-text-toolbar-button components in this slot to define custom buttons.

---

# Component API Structure

## Basic Information

- **Name:** select
- **Namespace:** lightning
- **Tag Name:** lightning-select
- **Version:** 59.0
- **Type:** COMPONENT
- **Description:** A menu of options for single or multiple selection using the HTML select element.

## API Reference

### Properties

| Name                    | Type            | Default    | Description                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------- | --------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label                   | string          | null       | The text label for the component. To hide the label but make it available to assistive technologies, use the label-hidden variant.                                                                                                                                                                                                                                                                                                |
| name                    | string          | null       | The identifier for the component.                                                                                                                                                                                                                                                                                                                                                                                                 |
| messageWhenValueMissing | string          | null       | The error message that's displayed below the menu when a user interacts with the menu but does not select an option.                                                                                                                                                                                                                                                                                                              |
| accessKey               | string          | null       | A shortcut key that activates and focuses on the menu.                                                                                                                                                                                                                                                                                                                                                                            |
| autocomplete            | string          | null       | Reserved for internal use. Controls auto-filling of the field.                                                                                                                                                                                                                                                                                                                                                                    |
| fieldLevelHelp          | string          | null       | Help text detailing the purpose and function of the menu of options. The text is displayed in a tooltip above the menu.                                                                                                                                                                                                                                                                                                           |
| variant                 | string          | 'standard' | The variant changes the appearance of the dropdown menu. Accepted variants include standard, label-inline, label-hidden, and label-stacked. This value defaults to standard, which displays the label above the dropdown menu. label-hidden hides the label but makes it available to assistive technology. label-inline horizontally aligns the label and dropdown menu. label-stacked places the label above the dropdown menu. |
| multiple                | boolean         | false      | Specifies whether multiple options can be selected.                                                                                                                                                                                                                                                                                                                                                                               |
| size                    | number          | 4          | The number of rows in the list that should be visible at one time. Use this attribute with the multiple attribute. Returns null when multiple is false.                                                                                                                                                                                                                                                                           |
| required                | boolean         | false      | Specifies whether an option must be selected.                                                                                                                                                                                                                                                                                                                                                                                     |
| disabled                | boolean         | false      | Specifies whether the menu is disabled and users cannot interact with it.                                                                                                                                                                                                                                                                                                                                                         |
| value                   | string \| array | null       | The value of the selected option. If empty and a value is required, the component is in an invalid state. When multiple is true, this should be an array of strings. When multiple is false, this should be a string.                                                                                                                                                                                                             |
| options                 | array           | []         | An array of menu options with key-value pairs. Each option object should contain: label (string) - the text to display, value (string) - the value to identify the option, and disabled (boolean, optional) - whether the option is selectable.                                                                                                                                                                                   |
| ariaDescribedBy         | string          | null       | A space-separated list of element IDs whose content describes the select element.                                                                                                                                                                                                                                                                                                                                                 |
| ariaLabelledBy          | string          | null       | A space-separated list of element IDs that provide labels for the select element.                                                                                                                                                                                                                                                                                                                                                 |
| validity                | ValidityState   | null       | (Readonly) Represents the validity states that an element can be in, with respect to constraint validation.                                                                                                                                                                                                                                                                                                                       |

### Methods

#### focus

- **Description:** Sets focus on the select element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes focus from the select element.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Checks if the input is valid.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the element meets all constraint validations.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when a form is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the input fields.

#### showHelpMessageIfInvalid

- **Description:** Displays an error message on an invalid select field. An invalid field fails at least one constraint validation and returns false when checkValidity() is called.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** The event fired when an option is selected.
- **Payload:**
  ```javascript
  {
    value: string | array; // The value of the selected option. When multiple is true, this is an array of selected values. When multiple is false, this is a string.
  }
  ```

#### focus

- **Description:** The event fired when the select element receives focus.
- **Payload:** None

#### blur

- **Description:** The event fired when the select element loses focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** slider
- **Namespace:** lightning
- **Tag Name:** lightning-slider
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** An input range slider for specifying a value between two specified numbers. Supports horizontal and vertical orientations.

## API Reference

### Properties

| Name                       | Type    | Default      | Description                                                                                                                                       |
| -------------------------- | ------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| label                      | string  | undefined    | Text label to describe the slider. Required attribute.                                                                                            |
| value                      | number  | 0            | The numerical value of the slider.                                                                                                                |
| min                        | number  | 0            | The minimum value of the input range.                                                                                                             |
| max                        | number  | 100          | The maximum value of the input range.                                                                                                             |
| step                       | number  | 1            | The step increment value of the input range. Examples include 0.1, 1, or 10.                                                                      |
| type                       | string  | 'horizontal' | The type determines the orientation of the slider. Accepted values are 'vertical' and 'horizontal'.                                               |
| size                       | string  | ''           | The size of the slider. Empty string sets the slider to the width of the viewport. Accepted values are 'x-small', 'small', 'medium', and 'large'. |
| disabled                   | boolean | false        | If present, the slider is disabled and users cannot interact with it.                                                                             |
| variant                    | string  | 'standard'   | The variant changes the appearance of the slider. Accepted variants are 'standard' and 'label-hidden'.                                            |
| messageWhenRangeOverflow   | string  | undefined    | Error message to be displayed when a range overflow is detected.                                                                                  |
| messageWhenRangeUnderflow  | string  | undefined    | Error message to be displayed when a range underflow is detected.                                                                                 |
| messageWhenStepMismatch    | string  | undefined    | Error message to be displayed when a step mismatch is detected.                                                                                   |
| messageWhenValueMissing    | string  | undefined    | Error message to be displayed when the value is missing.                                                                                          |
| messageWhenTooLong         | string  | undefined    | Error message to be displayed when the value is too long.                                                                                         |
| messageWhenBadInput        | string  | undefined    | Error message to be displayed when a bad input is detected.                                                                                       |
| messageWhenPatternMismatch | string  | undefined    | Error message to be displayed when a pattern mismatch is detected.                                                                                |
| messageWhenTypeMismatch    | string  | undefined    | Error message to be displayed when a type mismatch is detected.                                                                                   |
| validity                   | object  | N/A          | (Readonly) Represents the validity states of the slider input, with respect to constraint validation.                                             |

### Methods

#### focus

- **Description:** Sets focus on the input element.
- **Parameters:** None
- **Returns:** void

#### blur

- **Description:** Removes keyboard focus from the input element.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the slider meets all constraint validations.

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the slider.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when the slider value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### showHelpMessageIfInvalid

- **Description:** Displays error messages on invalid fields. An invalid field fails at least one constraint validation and returns false when checkValidity() is called.
- **Parameters:** None
- **Returns:** void

### Events

#### change

- **Description:** Fired when the slider value changes. The event bubbles and is composed, propagating across shadow DOM boundaries.
- **Payload:**
  ```javascript
  {
    value: string; // The new value of the slider
  }
  ```

#### focus

- **Description:** Fired when the slider receives focus.
- **Payload:** None

#### blur

- **Description:** Fired when the slider loses focus.
- **Payload:** None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** spinner
- **Namespace:** lightning
- **Tag Name:** lightning-spinner
- **Type:** COMPONENT
- **Description:** Displays an animated spinner image to indicate that a feature is loading. Can be used when retrieving data or anytime an operation doesn't immediately complete.

## API Reference

### Properties

| Name            | Type   | Default   | Description                                                                                                                                                                       |
| --------------- | ------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| alternativeText | string | undefined | The alternative text used to describe the reason for the wait and need for a spinner. This attribute should not be empty; a console warning is displayed if no value is provided. |
| size            | string | medium    | The size of the spinner. Accepted sizes are xx-small, x-small, small, medium, and large.                                                                                          |
| variant         | string | base      | The variant changes the appearance of the spinner. Accepted variants include base, brand, and inverse.                                                                            |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** tab
- **Namespace:** lightning
- **Tag Name:** lightning-tab
- **Version:** 44.0
- **Type:** COMPONENT
- **Description:** A single tab in a tabset component. The tab content displays when a user clicks the tab. Use lightning-tab as a child of the lightning-tabset component. Tab content is lazy loaded, and you can only query the content for the active and previously active tabs.

## API Reference

### Properties

| Name                   | Type    | Default   | Description                                                                                                                                                                                                                                      |
| ---------------------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| value                  | string  | undefined | The optional string to identify which tab was clicked during the tab's active event. This string is also used by active-tab-value in tabset to open a tab.                                                                                       |
| label                  | string  | undefined | The text displayed in the tab header.                                                                                                                                                                                                            |
| title                  | string  | undefined | Specifies text that displays in a tooltip over the tab content.                                                                                                                                                                                  |
| iconName               | string  | undefined | The Lightning Design System name of an icon to display at the beginning of the tab label. Specify the name in the format 'utility:down' where 'utility' is the category, and 'down' is the icon to be displayed. Only utility icons can be used. |
| iconAssistiveText      | string  | undefined | The alternative text for the icon specified by icon-name.                                                                                                                                                                                        |
| endIconName            | string  | undefined | The Lightning Design System name of an icon to display at the end of the tab label. Specify the name in the format 'utility:check' where 'utility' is the category, and 'check' is the icon to be displayed.                                     |
| endIconAlternativeText | string  | undefined | The alternative text for the icon specified by end-icon-name.                                                                                                                                                                                    |
| showErrorIndicator     | boolean | false     | Specifies whether there's an error in the tab content. An error icon is displayed to the right of the tab label. If an end icon is present, the error indicator is displayed after the icon.                                                     |

### Methods

#### loadContent

- **Description:** Reserved for internal use. Loads the tab content and dispatches the active event.
- **Parameters:** None
- **Returns:** void

### Events

#### active

- **Description:** The event fired when a tab becomes active.
- **Payload:** None

### Slots

#### default

- **Description:** Placeholder for your content in lightning-tab.

---

# Component API Structure

## Basic Information

- **Name:** tabset
- **Namespace:** lightning
- **Tag Name:** lightning-tabset
- **Version:** 44.0
- **Type:** COMPONENT
- **Description:** Displays a tabbed container with multiple content areas, only one of which is visible at a time. Tabs are displayed horizontally inline with content shown below it, by default. Use tabs to separate information into logical sections based on functionality or use case.

## API Reference

### Properties

| Name           | Type         | Default    | Description                                                                                                                                                                                                                                                       |
| -------------- | ------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| title          | string       | undefined  | Displays tooltip text when the mouse moves over the tabset.                                                                                                                                                                                                       |
| headingLabel   | string\|null | null       | Specifies text to use as custom assistive text for the tabset heading. The text is placed in a div element with role="heading" and aria-level="2". When heading-label isn't specified, the default assistive text is "Tabs" in a div element with aria-level="2". |
| headingVisible | boolean      | false      | Determines whether the text that's passed with the heading-label attribute is visible above the tabset. This attribute isn't present by default so the assistive text is only read by screen readers.                                                             |
| headingLevel   | number       | 2          | Specifies the value to pass through to aria-level when you specify heading-label. Accepts values from 1 to 6. The default value is 2.                                                                                                                             |
| variant        | string       | 'standard' | The variant changes the appearance of the tabset. Accepted variants are standard, scoped, and vertical.                                                                                                                                                           |
| activeTabValue | string       | undefined  | Sets a specific tab to open by default using a string that matches a tab's value string. If not used, the first tab opens by default.                                                                                                                             |

### Methods

#### focus

- **Description:** Focus currently selected tab.
- **Parameters:** None
- **Returns:** void

### Events

This component does not dispatch any public events.

### Slots

#### default

- **Description:** Placeholder for lightning-tab components.

---

# Component API Structure

## Basic Information

- **Name:** textarea
- **Namespace:** lightning
- **Tag Name:** lightning-textarea
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Represents a multiline text input field. Creates an HTML textarea element for entering multi-line text input. A text area holds an unlimited number of characters.

## API Reference

### Properties

| Name                    | Type    | Default   | Description                                                                                                                                                                                                                                                                                                                                      |
| ----------------------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| accessKey               | string  | undefined | The keyboard shortcut for input field.                                                                                                                                                                                                                                                                                                           |
| ariaDescribedBy         | string  | undefined | A space-separated list of element IDs that provide descriptive labels for the textarea.                                                                                                                                                                                                                                                          |
| ariaLabelledBy          | string  | undefined | A space-separated list of element IDs that provide labels for the textarea.                                                                                                                                                                                                                                                                      |
| autocomplete            | string  | undefined | Controls auto-filling of the field. Set the attribute to pass through autocomplete values to be interpreted by the browser.                                                                                                                                                                                                                      |
| disabled                | boolean | false     | If present, the field is grayed out and users cannot interact with it. Values from disabled fields are excluded from form submissions. Applying both disabled and readonly attributes to the component can result in unexpected behavior.                                                                                                        |
| fieldLevelHelp          | string  | undefined | The help text that appears in a popover. Set field-level help to provide an informational tooltip on the textarea input field.                                                                                                                                                                                                                   |
| label                   | string  | undefined | Text that describes the textarea input field. This property is required.                                                                                                                                                                                                                                                                         |
| maxLength               | number  | undefined | The maximum number of characters allowed in the textarea.                                                                                                                                                                                                                                                                                        |
| messageWhenBadInput     | string  | undefined | Error message to be displayed when a bad input is detected.                                                                                                                                                                                                                                                                                      |
| messageWhenTooLong      | string  | undefined | Error message to be displayed when the value is too long.                                                                                                                                                                                                                                                                                        |
| messageWhenTooShort     | string  | undefined | Error message to be displayed when the value is too short.                                                                                                                                                                                                                                                                                       |
| messageWhenValueMissing | string  | undefined | Error message to be displayed when the value is missing.                                                                                                                                                                                                                                                                                         |
| minLength               | number  | undefined | The minimum number of characters allowed in the textarea.                                                                                                                                                                                                                                                                                        |
| name                    | string  | undefined | Specifies the name of an input element.                                                                                                                                                                                                                                                                                                          |
| placeholder             | string  | undefined | Text that is displayed when the field is empty, to prompt the user for a valid entry.                                                                                                                                                                                                                                                            |
| readOnly                | boolean | false     | If present, the field is read-only, cannot be edited, but can receive focus. The component determines the height based on the amount of content. Applying both disabled and read-only attributes can result in unexpected behavior.                                                                                                              |
| required                | boolean | false     | If present, the textarea field must be filled out before the form can be submitted.                                                                                                                                                                                                                                                              |
| validity                | object  | undefined | (Readonly) Represents the validity states of the textarea input, with respect to constraint validation.                                                                                                                                                                                                                                          |
| value                   | string  | undefined | The value of the textarea input, also used as the default value during init.                                                                                                                                                                                                                                                                     |
| variant                 | string  | standard  | The variant changes the appearance of the textarea. Accepted variants include standard, label-hidden, label-inline, and label-stacked. Use label-hidden to hide the label but make it available to assistive technology. Use label-inline to horizontally align the label and textarea. Use label-stacked to place the label above the textarea. |

### Methods

#### blur

- **Description:** Removes focus from the textarea field.
- **Parameters:** None
- **Returns:** void

#### checkValidity

- **Description:** Returns the valid attribute value (Boolean) on the ValidityState object.
- **Parameters:** None
- **Returns:** boolean - Indicates whether the textarea meets all constraint validations.

#### focus

- **Description:** Sets focus on the textarea field.
- **Parameters:** None
- **Returns:** void

#### reportValidity

- **Description:** Displays the error messages and returns false if the input is invalid. If the input is valid, reportValidity() clears displayed error messages and returns true.
- **Parameters:** None
- **Returns:** boolean - The validity status of the textarea.

#### setCustomValidity

- **Description:** Sets a custom error message to be displayed when the textarea value is submitted.
- **Parameters:**
  - `message` (string, required): The string that describes the error. If message is an empty string, the error message is reset.
- **Returns:** void

#### setRangeText

- **Description:** Replace a range of text in textarea with a new string.
- **Parameters:**
  - `replacement` (string, required): The string to insert.
  - `start` (number, optional): The 0-based index of the first character to replace.
  - `end` (number, optional): The 0-based index of the character after the last character to replace.
  - `selectMode` (string, optional): A string defining how the selection should be set after the text has been replaced. Possible values: 'select' (selects the newly inserted text), 'start' (moves the selection to just before the inserted text), 'end' (moves the selection to just after the inserted text), 'preserve' (attempts to preserve the selection, this is the default).
- **Returns:** void

#### showHelpMessageIfInvalid

- **Description:** Displays error messages on invalid fields. An invalid field fails at least one constraint validation and returns false when checkValidity() is called.
- **Parameters:** None
- **Returns:** void

### Events

#### blur

- **Description:** Fired when the textarea loses focus.
- **Payload:** None

#### change

- **Description:** Fired when the value of the textarea changes. The event bubbles and is composed, allowing it to cross shadow DOM boundaries.
- **Payload:**
  ```javascript
  {
    value: string; // The current value of the textarea
  }
  ```

#### focus

- **Description:** Fired when the textarea receives focus.
- **Payload:** None

### Slots

#### label-end

- **Description:** Slot positioned at the end of the label element, after the label text. Can be used to add additional content or components next to the label.

---

# Component API Structure

## Basic Information

- **Name:** tile
- **Namespace:** lightning
- **Tag Name:** lightning-tile
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A grouping of related information associated with a record. The information can be actionable and paired with a figure, such as an icon or avatar component.

## API Reference

### Properties

| Name    | Type   | Default    | Description                                                                                                                                                                                   |
| ------- | ------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label   | string | undefined  | The text label that displays in the tile as the heading and hover text. Required.                                                                                                             |
| href    | string | undefined  | The URL of the page that the link goes to.                                                                                                                                                    |
| type    | string | 'standard' | The tile type. Valid values are 'standard' and 'media'. The default is 'standard'.                                                                                                            |
| actions | array  | []         | A list of actions that's displayed in a dropdown menu. Each action object should have properties: label (string), value (any), iconName (string, optional), and disabled (boolean, optional). |

### Methods

None

### Events

#### actiontriggered

- **Description:** The event fired when an action on the dropdown menu is triggered.
- **Payload:**
  ```javascript
  {
    action: object; // The selected action object from the actions array
  }
  ```
- **Event Properties:**
  - bubbles: false
  - cancelable: false
  - composed: false

### Slots

#### default

- **Description:** Placeholder for your content that appears below the heading in the tile body.

#### media

- **Description:** Slot for a figure such as a lightning-icon or lightning-avatar component. Only available when type is 'media'.

---

# Component API Structure

## Basic Information

- **Name:** toast
- **Namespace:** lightning
- **Tag Name:** lightning-toast
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A notification element used to display toast messages with an icon, label, message, and optional links. Toast notifications convey small pieces of information to the user, such as feedback and confirmation after the user takes an action. Toasts can be configured to disappear after a certain duration or until the user clicks the close button.

## API Reference

### Properties

| Name         | Type            | Default   | Description                                                                                                                                                                                                                                                                                                             |
| ------------ | --------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| label        | string          | ''        | Title of the toast. Can contain placeholders in the form {0}, {1}, etc. for index-based links or {name} for name-based links that will be replaced with anchor tags. Required property.                                                                                                                                 |
| labelLinks   | array or object | undefined | An array of { url, label } which replaces the {0}...{N} placeholders in label string, or a map of { name: { url, label } } which replaces the {name}...{anotherName} placeholders in label string.                                                                                                                      |
| message      | string          | ''        | Message of the toast. Can contain placeholders in the form {0}, {1}, etc. for index-based links or {name} for name-based links that will be replaced with anchor tags.                                                                                                                                                  |
| messageLinks | array or object | undefined | An array of { url, label } which replaces the {0}...{N} placeholders in message string, or a map of { name: { url, label } } which replaces the {name}...{anotherName} placeholders in message string.                                                                                                                  |
| variant      | string          | 'info'    | The variant of the toast element used to determine the icon, background color, and text color. Valid values: 'info', 'warning', 'success', 'error'.                                                                                                                                                                     |
| mode         | string          | varies    | The mode of the toast used to determine whether the toast can be closed by the user via a close button and whether the toast disappears after a set time period. Valid values: 'dismissible', 'sticky'. Default is 'sticky' for most cases, except for 'success' variant without links which defaults to 'dismissible'. |

### Methods

#### focus

- **Description:** Sets focus on the toast content element.
- **Parameters:** None
- **Returns:** void

#### show (static)

- **Description:** Static method to trigger a toast notification. Creates a single page-level toast container if one does not exist and dispatches a ShowToastEvent to display the toast.
- **Parameters:**
  - `config` (object, required): A map of toast attributes to values. Expected shape: { label: string (required), labelLinks: array or object, message: string, messageLinks: array or object, variant: string ('info'|'success'|'warning'|'error'), mode: string ('dismissible'|'sticky'), on<eventname>: function }
  - `source` (HTMLElement, optional): Source element which triggers the toast showing, typically 'this' from the local component. If not provided, the event is dispatched on document.body.
- **Returns:** void

### Events

#### close

- **Description:** Fired when the toast is closed, either by user clicking the close button or automatically after the timeout duration in dismissible mode. This event signals for removal of the toast element from the DOM.
- **Payload:**
  ```javascript
  {
    isFocused: boolean; // Indicates if the toast was focused when closed
  }
  ```

### Slots

#### default (label slot)

- **Description:** Default slot for the toast label/title content. If not provided via slot, the component will use the label property value.

#### message

- **Description:** Named slot for the toast message content. If not provided via slot, the component will use the message property value. Not displayed on smaller screens or mobile environments.

---

# Component API Structure

## Basic Information

- **Name:** toastContainer
- **Namespace:** lightning
- **Tag Name:** lightning-toast-container
- **Version:** 58.0
- **Type:** COMPONENT
- **Description:** Manages a list of toast components and their display position and order. Each site page supports a single toast container instance. The container listens for ShowToastEvent events dispatched from the page and manages the display queue of toast notifications.

## API Reference

### Properties

| Name              | Type   | Default      | Description                                                                                                                                                                                                                                                                                                                    |
| ----------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| containerPosition | string | 'fixed'      | Controls the position of the toast container div related to the containing element. Supported values are 'absolute' and 'fixed'. Value 'fixed' positions the container relative to the initial containing block established by the viewport. Value 'absolute' positions the container relative to a positioned parent element. |
| maxToasts         | number | 3            | Sets the maximum number of toast components shown at a given time. Must be at least 1.                                                                                                                                                                                                                                         |
| toastPosition     | string | 'top-center' | Controls the position of toast components inside the toast container. Supported values are 'top-left', 'top-center', 'top-right', 'bottom-left', 'bottom-center', and 'bottom-right'. The most recent toast displays at the top of the container, and the oldest toast notification displays at the bottom.                    |

### Methods

#### close

- **Description:** Closes the toast container and removes all displayed toasts. Resets the container state and removes event listeners.
- **Parameters:**
  - `result` (any, optional): Result value to be returned in the promise from the open call
  - `promise` (Promise, optional): Promise to resolve when closing
- **Returns:** void

#### ToastContainer.instance

- **Description:** Static factory method that creates a page-level toast container if it does not exist, or returns the existing one. Only one global toast container instance is supported per page.
- **Parameters:**
  - `config` (object, optional): Configuration object to set the toast container's public attributes. Can include containerPosition, maxToasts, and toastPosition properties.
- **Returns:** ToastContainer instance, or empty object in server-side rendering context

#### ToastContainer.open

- **Description:** Static method that creates and opens a new toast container instance.
- **Parameters:**
  - `config` (object, optional): Configuration object to set attributes directly on the container instance
- **Returns:** Promise that resolves to the toast container instance

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** tree
- **Namespace:** lightning
- **Tag Name:** lightning-tree
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Displays a nested tree with visualization of a structural hierarchy, such as a sitemap for a website or a role hierarchy in an organization. Items are displayed as hyperlinks and can be nested. Items with nested items are also known as branches.

## API Reference

### Properties

| Name         | Type             | Default   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------ | ---------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| header       | string           | undefined | The text that's displayed as the tree heading.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| headingLevel | string \| number | 2         | Changes the 'aria-level' attribute value for the h2 markup tag in the tree's title element. Supported values are 1, 2, 3, 4, 5, 6.                                                                                                                                                                                                                                                                                                                                                                                                          |
| items        | array            | []        | An array of key-value pairs that describe the tree. Each item can have the following properties: label (string, required) - the title and label for the hyperlink; name (string) - unique name for the item for the onselect event handler; metatext (string) - text to provide supplemental information; href (string) - URL for the link; expanded (boolean, default false) - whether a branch is expanded; disabled (boolean, default false) - whether an item is disabled; items (array) - nested items as an array of key-value pairs. |
| selectedItem | string           | undefined | Selects and highlights the specified tree item. Tree item names are case-sensitive. If the tree item is nested, selecting this item also expands the parent branches.                                                                                                                                                                                                                                                                                                                                                                       |

### Methods

None

### Events

#### change

- **Description:** The event fired when a branch is expanded or collapsed.
- **Payload:**
  ```javascript
  {
    items: array, // Deep copy of the current items array
    key: string, // The name of the branch that was expanded or collapsed
    expand: boolean // Whether the branch is now expanded (true) or collapsed (false)
  }
  ```

#### select

- **Description:** The event fired when a tree item is selected and before navigating to a given hyperlink. Event is cancelable using preventDefault(). Event bubbles and composes.
- **Payload:**
  ```javascript
  {
    name: string; // The name of the selected tree item
  }
  ```

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** treeGrid
- **Namespace:** lightning
- **Tag Name:** lightning-tree-grid
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** Displays hierarchical data in a table with expandable rows. Implements lightning-datatable internally to provide a tree-like structure with nested data.

## API Reference

### Properties

| Name                 | Type             | Default | Description                                                                                                                                                                                         |
| -------------------- | ---------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| columns              | array            | -       | Required. Array of column objects that define the data types. Each column must include 'label', 'fieldName', and 'type' properties. The first column is automatically transformed to a tree column. |
| data                 | array            | -       | Required. Array of hierarchical data to be displayed. Nested items must be defined using the `_children` key.                                                                                       |
| keyField             | string           | -       | Required. Associates each row with a unique ID for better performance. Used to identify rows for expansion, selection, and other operations.                                                        |
| expandedRows         | array            | []      | Array of unique row IDs for rows that are expanded. Updates when rows are toggled.                                                                                                                  |
| selectedRows         | array            | []      | Array of unique row IDs that are selected. Enables programmatic row selection.                                                                                                                      |
| disabledRows         | array            | []      | Array of key-field values for rows that should be disabled, preventing users from changing their selection status.                                                                                  |
| columnWidthsMode     | string           | 'fixed' | Specifies how column widths are calculated. Set to 'fixed' for equal widths or 'auto' for content-based widths.                                                                                     |
| defaultSortDirection | string           | 'asc'   | Specifies the default sorting direction on an unsorted column. Valid options are 'asc' and 'desc'.                                                                                                  |
| sortedBy             | string\|string[] | -       | Column key or fieldName(s) that controls the sorting order. Sort data using the onsort event handler.                                                                                               |
| sortedDirection      | string\|string[] | -       | Specifies the sorting direction. Valid options are 'asc' or 'desc', or an array of such values. Sort data using the onsort event handler.                                                           |
| hideCheckboxColumn   | boolean          | false   | If present, the checkbox column for row selection is hidden.                                                                                                                                        |
| hideTableHeader      | boolean          | false   | If present, the table header is hidden.                                                                                                                                                             |
| hideBorders          | boolean          | false   | If present, the table borders are hidden. Only valid when hide-table-header is true.                                                                                                                |
| isLoading            | boolean          | false   | If present, a spinner is displayed to indicate that more data is being loaded.                                                                                                                      |
| maxColumnWidth       | number           | 1000    | The maximum width for all columns in pixels.                                                                                                                                                        |
| minColumnWidth       | number           | 50      | The minimum width for all columns in pixels.                                                                                                                                                        |
| resizeColumnDisabled | boolean          | false   | If present, column resizing is disabled.                                                                                                                                                            |
| rowNumberOffset      | number           | 0       | Determines where to start counting the row number.                                                                                                                                                  |
| showRowNumberColumn  | boolean          | false   | If present, the row number column is shown in the first column.                                                                                                                                     |
| rowToggleIcon        | object           | -       | Configuration object to customize the tree icon. If not provided, the default tree icon 'utility:chevronright' is used.                                                                             |
| ariaLabel            | string           | ''      | Provides an assistive label to identify the table for accessibility. Passed down to the child table element.                                                                                        |

### Methods

#### getSelectedRows

- **Description:** Returns data in each selected row.
- **Parameters:** None
- **Returns:** array - An array of data in each selected row.

#### getCurrentExpandedRows

- **Description:** Returns an array of rows that are expanded.
- **Parameters:** None
- **Returns:** array - The IDs for all rows that are marked as expanded.

#### expandAll

- **Description:** Expands all rows with children content.
- **Parameters:** None
- **Returns:** void

#### collapseAll

- **Description:** Collapses all rows.
- **Parameters:** None
- **Returns:** void

### Events

#### toggle

- **Description:** Fired when a row is expanded or collapsed.
- **Payload:**
  ```javascript
  {
    name: string, // The unique ID for the row that's toggled
    isExpanded: boolean, // Specifies whether the row is expanded or not
    hasChildrenContent: boolean, // Whether the row has valid nested data in _children
    row: object // The toggled row data
  }
  ```

#### toggleall

- **Description:** Fired when all rows are expanded or collapsed.
- **Payload:**
  ```javascript
  {
    isExpanded: boolean; // Specifies whether rows are expanded or not
  }
  ```

#### sort

- **Description:** Fired when a column is sorted. Handle this event to update the table with sorted data.
- **Payload:**
  ```javascript
  {
    fieldName: string, // The fieldName that controls the sorting
    sortDirection: string, // The sorting direction ('asc' or 'desc')
    isMultiColumnSort: boolean // Reserved for internal use. Defaults to false
  }
  ```

#### rowselection

- **Description:** Fired when a row is selected or deselected. Triggered when a user interacts with the checkbox column.
- **Payload:**
  ```javascript
  {
    selectedRows: array, // Array of selected row data objects
    config: object // Internal configuration with action details
  }
  ```

#### headeraction

- **Description:** Fired when a header-level action is run from the dropdown menu on a column header.
- **Payload:**
  ```javascript
  {
    action: object, // The action object with name and label
    columnDefinition: object // The column definition where the action was triggered
  }
  ```

#### rowaction

- **Description:** Fired when a row-level action is run from the action column dropdown menu.
- **Payload:**
  ```javascript
  {
    action: object, // The action object with name and label
    row: object // The row data where the action was triggered
  }
  ```

### Slots

#### customdatatypes

- **Description:** Allows insertion of custom data type definitions. Used with static customTypes for defining custom column types that extend the default data types available in the tree grid.

---

# Component API Structure

## Basic Information

- **Name:** verticalNavigation
- **Namespace:** lightning
- **Tag Name:** lightning-vertical-navigation
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A vertical list of links that either take the user to another page or parts of the page the user is in. Used together with lightning-vertical-navigation-section, lightning-vertical-navigation-item, lightning-vertical-navigation-overflow, lightning-vertical-navigation-item-badge, and lightning-vertical-navigation-item-icon sub-components to create navigation menus that are one level deep with support for overflow sections.

## API Reference

### Properties

| Name         | Type    | Default | Description                                                                                                                                                                                                  |
| ------------ | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| compact      | boolean | false   | If present, spacing between navigation items is reduced.                                                                                                                                                     |
| shaded       | boolean | false   | If present, the vertical navigation is displayed on top of a shaded background. When true, selected items are highlighted in white instead of blue.                                                          |
| selectedItem | string  | ''      | Name of the navigation item to make active. An active item is highlighted in blue (or white when shaded is true). The value must match the name attribute of a lightning-vertical-navigation-item component. |

### Methods

None

### Events

#### beforeselect

- **Description:** The event fired before a navigation item is selected. This event is cancelable, allowing you to run validation or other actions before the selection occurs.
- **Payload:**
  ```javascript
  {
    name: string; // The name of the item to be selected, matching the name value on the vertical-navigation-item component
  }
  ```

#### select

- **Description:** The event fired when a navigation item is selected.
- **Payload:**
  ```javascript
  {
    name: string; // The name of the selected item, matching the name value on the vertical-navigation-item component
  }
  ```

### Slots

#### default

- **Description:** Placeholder for lightning-vertical-navigation-section and lightning-vertical-navigation-overflow components. The navigation menu requires at least one navigation section with navigation items.

---

# Component API Structure

## Basic Information

- **Name:** verticalNavigationItem
- **Namespace:** lightning
- **Tag Name:** lightning-vertical-navigation-item
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A text-only link within lightning-vertical-navigation-section or lightning-vertical-navigation-overflow. Used to create navigation items in a vertical navigation menu.

## API Reference

### Properties

| Name  | Type   | Default              | Description                                                                                                                                                        |
| ----- | ------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| label | string | undefined            | The text displayed for the navigation item. Required.                                                                                                              |
| name  | string | undefined            | A unique identifier for the navigation item. The name is used by the `select` event on lightning-vertical-navigation to identify which item is selected. Required. |
| href  | string | 'javascript:void(0)' | The URL of the page that the navigation item goes to.                                                                                                              |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** verticalNavigationItemBadge
- **Namespace:** lightning
- **Tag Name:** lightning-vertical-navigation-item-badge
- **Version:** 41.0
- **Type:** COMPONENT
- **Description:** A navigation item that displays a numerical badge to the right of the item label. This component is designed to be used within lightning-vertical-navigation-section or lightning-vertical-navigation-overflow. The badge is only shown when the badge count is greater than zero.

## API Reference

### Properties

| Name          | Type   | Default              | Description                                                                                                               |
| ------------- | ------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| label         | string | undefined            | The text displayed for this navigation item. (required)                                                                   |
| name          | string | undefined            | A unique identifier for this navigation item. (required)                                                                  |
| badgeCount    | number | 0                    | The number to show inside the badge. If this value is zero, the badge is hidden.                                          |
| assistiveText | string | "New Items"          | Assistive text describing the number in the badge, which enhances accessibility and is not displayed to the user.         |
| href          | string | "javascript:void(0)" | The URL of the page that the navigation item goes to. URLs are sanitized when the ENABLE_SANITIZE_URL feature is enabled. |

### Methods

None

### Events

None

### Slots

None

---

# Component API Structure

## Basic Information

- **Name:** verticalNavigationItemIcon
- **Namespace:** lightning
- **Tag Name:** lightning-vertical-navigation-item-icon
- **Version:** 1.0.0
- **Type:** COMPONENT
- **Description:** A navigation item that displays an icon to the left of the item label. Used within lightning-vertical-navigation-section or lightning-vertical-navigation-overflow to create navigation menus with icons.

## API Reference

### Properties

| Name     | Type   | Default              | Description                                                                                                                                                                    |
| -------- | ------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| label    | string | undefined            | The text displayed for this navigation item. Required.                                                                                                                         |
| name     | string | undefined            | A unique identifier for this navigation item. Required.                                                                                                                        |
| iconName | string | undefined            | The Lightning Design System name of the icon. Names are written in the format 'utility:down' where 'utility' is the category, and 'down' is the specific icon to be displayed. |
| href     | string | 'javascript:void(0)' | The URL of the page that the navigation item goes to.                                                                                                                          |

### Methods

None

### Events

None

### Slots

None
