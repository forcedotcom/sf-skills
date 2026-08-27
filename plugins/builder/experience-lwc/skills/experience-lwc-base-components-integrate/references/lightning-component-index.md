# Lightning Base Components - Namespace Overview

## Summary

This namespace contains 84 Lightning Base Components for building Salesforce Lightning Web Components. Components cover UI elements, form inputs, data display, navigation, and utilities. This overview is being generated to provide concise descriptions of when each component should be used.

**Status:** Complete (84/84 components documented)

---

## Component Index

**accordion:** A vertically stacked collection of collapsible sections that lets users show or hide content areas. Supports single or multiple sections being open simultaneously through the allowMultipleSectionsOpen property. Fires events when sections are toggled, making it ideal for FAQs, settings panels, or any content that needs progressive disclosure.

**accordionSection:** A single collapsible section within an accordion component that contains content and optional action buttons in the header.

**alert:** A modal alert dialog for displaying system-wide notifications, used as a modern replacement for window.alert(). Supports themed variants (success, warning, error, info) and both header and headerless styles. Returns a Promise for better async handling.

**avatar:** Displays a visual representation of an object using an image, initials, or fallback icon with customizable size and shape.

**badge:** A label component that displays small amounts of information like notification counts or status indicators, optionally with an icon.

**barcodeScanner:** Launches a mobile device barcode scanner to read various barcode types including QR codes, UPC, EAN, and more. Supports both single-scan mode (auto-closes after one scan) and continuous-scan mode (stays open for multiple scans). Mobile-only functionality.

**breadcrumb:** A single clickable link item representing one level in a navigation hierarchy, used within a breadcrumbs component to show the user's current location.

**breadcrumbs:** A container component for displaying a hierarchical navigation path using multiple breadcrumb items, showing where the user is within the site structure.

**button:** A clickable button element for triggering actions like form submission, navigation, or UI state changes. Supports multiple variants (brand, destructive, neutral, success), icons in left or right positions, and extensive ARIA attributes for accessibility. Use for primary actions, form controls, or any clickable interaction that isn't a link.

**buttonGroup:** A container that groups multiple button components together into a visual navigational bar with proper SLDS styling and automatic position management.

**buttonIcon:** An icon-only button that executes actions in a controller, supporting only utility icons. Offers multiple variants (bare, container, brand, border, border-filled, bare-inverse, border-inverse) and extensive ARIA attributes for accessibility. Use for toolbar actions, inline controls, or anywhere an icon button without text is needed.

**buttonIconStateful:** An icon-only toggle button that maintains state and switches between selected and unselected states. Sets aria-pressed="true" when selected for screen reader accessibility. Use for toolbar toggles, favorite/like buttons, or any icon-only control that needs to show on/off state.

**buttonMenu:** A dropdown menu button that displays a list of actions or functions, closing automatically when users click away or select an item. Supports variants (bare, container, border, border-filled, bare-inverse, border-inverse), custom icons, loading states, and flexible menu alignment. Use for action menus, overflow menus, or any button that needs to reveal a list of options.

**buttonStateful:** A button that toggles between states with different labels and icons based on selection, similar to social media Like buttons. Supports variants (brand, destructive, inverse, neutral, success, text) and optional hover state customization. Use for toggle actions that need visual feedback like follow/unfollow, subscribe/unsubscribe, or save/saved.

**card:** A container component that applies styling around related groupings of information. Supports optional icon, title, actions slot, body content slot, and footer slot. Use for grouping related content into visually distinct sections on a page.

**checkboxGroup:** A form input component for selecting single or multiple options from a predefined list. Supports validation, required field handling, and multiple label variants (standard, label-hidden, label-inline, label-stacked). Use for multi-select forms, filter controls, or settings where users need to choose multiple options.

**clickToDial:** Renders a formatted phone number with click-to-dial functionality for Open CTI and Voice integrations. Automatically formats North American phone numbers and can pass record context to telephony systems. Use when displaying phone numbers that should trigger integrated phone systems.

**combobox:** A dropdown selection widget with a readonly input field and a list of selectable options. Supports validation, dropdown alignment control, loading states, and label variants. Use for single-select dropdowns where users pick from a predefined list of options.

**confirm:** A modal confirmation dialog that replaces native window.confirm() with a themed, accessible modal. Returns a Promise resolving to true (OK) or false (Cancel). Supports header and headerless variants with multiple themes (default, success, warning, error, etc.). Use for user confirmations before destructive or important actions.

**datatable:** A comprehensive data table component that displays rows and columns with extensive features including sorting, inline editing, row selection, column resizing, infinite scrolling, and row-level actions. Supports multiple column types, custom formatting, cell-level errors, and both fixed and auto column width modes. Use for displaying and manipulating tabular data with rich interactivity requirements.

**dualListbox:** A pair of listboxes for selecting and reordering multiple options between source and selected lists. Supports validation with min/max constraints, required options that cannot be removed, and optional up/down buttons for reordering. Use for multi-select forms where users need to choose and prioritize multiple options from a list.

**dynamicIcon:** Displays animated icons that visually indicate events in progress. Supports types including ellie, eq (equalizer with play/stop), score (positive/negative), strength (-3 to +3 levels), trend (neutral/up/down), and waffle. Use for loading indicators, status animations, or progress visualization.

**fileUpload:** A file uploader for attaching files to Salesforce records. Supports single or multiple file uploads, file extension filtering, custom ContentVersion field values, and validation. Use for allowing users to upload documents, images, or other files to records.

**formattedAddress:** Displays a formatted address in locale-appropriate format and field order, rendered as a clickable link to Google Maps. Supports optional static map display and can use coordinates for faster rendering. Use for displaying physical addresses with map integration.

**formattedDateTime:** Displays date and time values formatted according to user locale using Intl.DateTimeFormat. Accepts Date objects, ISO8601 strings, or timestamps, with extensive customization for weekday, era, year, month, day, hour, minute, second, time zone, and 12/24-hour format. Use for displaying dates and times in a locale-aware format.

**formattedEmail:** Displays an email address as a clickable mailto: hyperlink that opens the default mail application. Supports custom labels, optional icon display, and can handle multiple comma-separated emails with query parameters for cc, subject, and body. Use for displaying email addresses that users can click to compose messages.

**formattedLocation:** Displays a read-only geolocation in decimal degrees format [latitude, longitude]. Validates that latitude is within -90 to 90 and longitude is within -180 to 180. Use for displaying coordinate data.

**formattedName:** Displays a formatted name with locale-aware ordering of components including salutation, first name, middle name, last name, suffix, and informal name. Supports short, medium, and long format options. Use for displaying person names in culturally appropriate formats.

**formattedNumber:** Displays formatted numerical values for decimals, currency, and percentages using Intl.NumberFormat. Supports currency code specification, display style (symbol/code/name), and control over integer digits, fraction digits, and significant digits. Use for displaying numbers, prices, or percentages in locale-aware formats.

**formattedPhone:** Displays a phone number as a clickable tel: hyperlink that opens VOIP applications on desktop or initiates calls on mobile. Automatically formats US/Canada 10-11 digit numbers as (999) 999-9999. Use for displaying phone numbers that users can click to call.

**formattedRichText:** A read-only component that displays rich text formatted with HTML tags, automatically sanitizing content to prevent XSS vulnerabilities. Supports extensive HTML tags (a, div, p, h1-h6, table, lists, etc.) and automatically linkifies URLs and email addresses unless disabled. Use for displaying user-generated HTML content safely.

**formattedText:** Displays plain text while converting newlines (\r and \n) to line breaks. Optionally linkifies URLs and email addresses with protocols (http, https, ftp, mailto) into clickable anchor tags. Use for displaying multi-line text with optional automatic link creation.

**formattedTime:** Displays a formatted time value in the user's locale format, always showing time in UTC. Accepts ISO8601 formatted time strings (HH:mm, HH:mm:ss, HH:mm:ss.SSS) and ignores offsets. Use for displaying time-only values in a locale-appropriate format.

**formattedUrl:** Displays a URL as a clickable hyperlink supporting both absolute and relative URLs with automatic protocol handling. Supports custom labels, tooltips, and target specification (\_blank, \_parent, \_self, \_top). Use for displaying clickable links with optional display text different from the URL.

**helptext:** An icon button with a text popover for displaying contextual help information. Shows content on hover/focus (tap on iOS) using a customizable icon (default utility:info) with variants (bare, error, inverse, warning). Use for providing inline help text or tooltips explaining form fields or UI elements.

**icon:** A visual element that displays icons from the Lightning Design System. Supports utility, standard, action, custom, and doctype icon categories with customizable size (xx-small to large) and variant styling (inverse, success, warning, error for utility icons). Use for adding visual context throughout the UI.

**input:** A comprehensive input component supporting multiple types including text, number, date, datetime, time, email, file, password, search, tel, url, checkbox, checkbox-button, toggle, color, and range. Provides extensive validation, custom error messages, ARIA attributes, and formatting options. Use as the primary form input component for collecting user data with type-specific behavior.

**inputAddress:** A compound field component creating an address input form with fields for street, city, province, country, and postal code. Supports Google Maps address lookup, country/province dropdowns, compact address mode, locale-based field ordering, and per-field validation. Use for collecting physical addresses with optional autocomplete functionality.

**inputField:** An editable input for a Salesforce object field that must be used within lightning-record-edit-form. Automatically renders the appropriate input type based on field metadata (text, picklist, lookup, etc.) and handles field-level security. Use for editing Salesforce record fields with automatic type handling and validation.

**inputLocation:** A geolocation compound field for accepting latitude and longitude values. Validates latitude within -90 to 90 and longitude within -180 to 180, with support for validation, required fields, and per-field custom error messages. Use for collecting geographic coordinate data.

**inputName:** A compound field for collecting person names with configurable fields including salutation (dropdown), first name, middle name, last name, suffix, and informal name. Supports locale-based field ordering and per-field validation. Use for collecting structured name data in forms.

**inputRichText:** A WYSIWYG editor based on Quill JS with a customizable toolbar for entering rich text content. Supports text formatting, alignment, lists, links, images, and more, with customization through disabled categories, allowed formats, and custom buttons. Use for collecting formatted text input like descriptions, comments, or articles.

**layout:** A flexible grid system for creating responsive layouts that arrange containers within a page. Supports horizontal alignment (center, space, spread, end), vertical alignment (start, center, end, stretch), wrapping to multiple rows, and pull-to-boundary options. Use with lightning-layout-item children to create mobile-first responsive designs.

**layoutItem:** The basic element within lightning-layout that defines columns in a grid layout. Supports 12-column sizing with responsive breakpoints (size, small/medium/large device sizes), flexibility options (auto, shrink, grow, no-flex), padding, and alignment bumping. Use to create individual columns within a lightning-layout.

**menuDivider:** Creates a horizontal dividing line between menu items in lightning-button-menu. Supports standard and compact variants to control spacing. Use to visually separate menu items into groups or categories.

**menuItem:** A list item within lightning-button-menu that can display text, icons, checkmarks, draft indicators, and links. Supports checked state, prefix/suffix icons, href navigation, disabled state, and keyboard shortcuts. Use for creating individual selectable or actionable items in dropdown menus.

**menuSubheader:** Creates a bold subheader text in lightning-button-menu to categorize or label groups of menu items. Use as a sibling of lightning-menu-item to improve usability in long lists.

**modal:** A base class for creating modal window overlays that must be extended rather than used directly as a tag. Supports configurable size (small, medium, large, full), accessibility labels, optional close prevention, and returns a Promise when opened. Use with lightning-modal-header, lightning-modal-body, and lightning-modal-footer to create custom modal dialogs.

**modalBody:** The main content area component of a modal that automatically handles scrolling when content exceeds available space. Place between lightning-modal-header and lightning-modal-footer in modal templates. Use to contain the primary content of modal dialogs.

**modalFooter:** An optional footer component for modals that typically contains action buttons. Automatically hides when empty. Place after lightning-modal-body in modal templates. Use for modal action buttons like Save, Cancel, or Close.

**modalHeader:** Creates a header at the top of a modal displaying a heading and optional tagline. Requires a label attribute for accessibility. Place before lightning-modal-body in modal templates. Use to provide titles and context for modal dialogs.

**navigation:** A library providing navigation service APIs including the CurrentPageReference wire adapter for getting the current page reference and NavigationMixin for adding navigation methods (Navigate, GenerateUrl) to components. Use for page navigation and URL generation in Lightning applications.

**outputField:** A read-only display component for Salesforce object field labels, help text, and formatted values. Must be used within lightning-record-view-form and automatically formats based on field type and locale. Use for displaying field data from Salesforce records without editing capability.

**pageReferenceUtils:** A utility library providing encodeDefaultFieldValues and decodeDefaultFieldValues functions for encoding/decoding default field values in standard\_\_objectPage page references. Use for prepopulating field values when navigating to record creation pages in Lightning Experience.

**pill:** A label component that can contain text, links, icons, or avatars and can be removed by users. Supports variants (link, plain, plainLink) and error state display with red border and icon. Use for displaying removable tags, keywords, email addresses, or selected items.

**pillContainer:** A container for displaying and managing multiple pill components in a list. Supports keyboard navigation, single-line display, expandable/collapsible lists, and programmatic pill management through an items array. Use for managing collections of pills like multi-select values or tag lists.

**progressBar:** A horizontal progress indicator that displays operation progress from 0-100%. Supports base and circular variants, plus size options (x-small, small, medium, large). Use for showing linear progress of loading, processing, or completion tasks.

**progressRing:** A circular progress indicator showing 0-100% completion by filling a ring clockwise or counterclockwise. Supports variants (base, active-step, warning, expired, base-autocomplete) with different colors and icons. Use for displaying circular progress, status indicators, or step completion.

**prompt:** A modal prompt dialog that replaces native window.prompt() with a themed, accessible modal that returns a Promise. Supports header and headerless variants with multiple themes. Use for collecting single text input from users before continuing an operation.

**radioGroup:** A radio button group allowing only one selection at a time from a list of options. Supports radio and button type styles, validation, and label variants (standard, label-hidden, label-inline, label-stacked). Use for single-select forms where users must choose exactly one option.

**recordEditForm:** A record edit layout for creating or updating Salesforce records using lightning-input-field components. Implements Lightning Data Service, handles field-level security automatically, supports custom layouts, and provides events for load, submit, success, and error states. Use for building custom forms to edit or create Salesforce records with full control over layout and behavior.

**recordForm:** An all-in-one form component for viewing, editing, or creating Salesforce records with automatic mode switching and default layout. Simpler than recordEditForm with built-in Save/Cancel buttons and automatic field rendering from object layouts. Use for quick forms when you need basic CRUD functionality without extensive customization.

**recordPicker:** A search input field for finding and selecting Salesforce records using GraphQL. Supports filtering, custom display/matching configuration, validation, and required fields. Use for lookup functionality, allowing users to search and select records from specified objects.

**recordViewForm:** A read-only record display layout using lightning-output-field components to show Salesforce record data. Handles field-level security and sharing automatically with no Apex controllers needed. Use for displaying record information in view-only mode.

**refresh:** A library providing a standardized refresh system for coordinating data updates across component hierarchies. Exports registerRefreshContainer, registerRefreshHandler, unregisterRefreshContainer, unregisterRefreshHandler functions and RefreshEvent class. Use to implement coordinated refresh functionality where multiple components need to update data together.

**relativeDateTime:** Displays relative time difference between current time and a provided date-time, automatically updating as time passes. Formats according to locale rules (e.g., "2 hours ago", "in 5 minutes"). Use for showing human-readable relative timestamps that stay current.

**richTextToolbarButton:** A custom button for lightning-input-rich-text toolbar that can perform actions, format text, or display popups. Must be placed inside lightning-rich-text-toolbar-button-group. Use for adding custom formatting or functionality to rich text editors.

**richTextToolbarButtonGroup:** A container for custom buttons in lightning-input-rich-text toolbar. Multiple groups can be included, each containing multiple toolbar buttons. Use to organize custom buttons into logical groups at the end of the rich text editor toolbar.

**select:** A dropdown menu for single or multiple selection using HTML select element. Supports validation, disabled options, custom error messages, and label variants. Use for dropdown selection forms with native HTML select behavior.

**slider:** An input range slider for selecting numeric values between min and max bounds with configurable step increments. Supports horizontal and vertical orientations, size variants, and validation. Use for allowing users to select numeric values through a visual slider interface.

**spinner:** An animated loading indicator showing that a feature or operation is in progress. Supports multiple sizes (xx-small to large) and variants (base, brand, inverse) with required alternative text for accessibility. Use to indicate loading states during data retrieval or long-running operations.

**tab:** A single tab within a tabset component that displays content when clicked. Supports icons at both start and end positions, error indicators, and lazy-loaded content. Use as children of lightning-tabset to create individual tab panels.

**tabset:** A tabbed container displaying multiple content areas with only one visible at a time. Supports standard, scoped, and vertical variants with customizable headings and active tab control. Use to organize related content into separate, switchable panels.

**textarea:** A multiline text input field for entering unlimited text. Supports validation, character limits (min/max length), placeholder text, read-only and disabled states, and label variants. Use for collecting multi-line text input like comments, descriptions, or long-form content.

**tile:** A grouping component displaying related information with an optional figure (icon/avatar), heading, body content, and action dropdown menu. Supports standard and media types. Use for displaying record summaries or related information in a card-like format.

**toast:** A notification component displaying temporary messages with icons, labels, messages, and optional links. Supports variants (info, warning, success, error) and modes (dismissible, sticky) with placeholder-based link insertion. Use for showing feedback, confirmations, or notifications after user actions.

**toastContainer:** A container managing the display queue and positioning of toast notifications. Supports configurable position (top/bottom, left/center/right), max visible toasts, and container positioning (fixed/absolute). Use to manage page-level toast notifications with a single container instance per page.

**tree:** A hierarchical navigation component displaying nested items as expandable branches with hyperlinks. Supports programmatic selection, disabled items, metatext, and customizable heading levels. Use for sitemaps, role hierarchies, or any nested navigation structure.

**treeGrid:** A data table with expandable hierarchical rows displaying nested data in a tree structure. Built on lightning-datatable with support for sorting, row selection, column resizing, and custom actions. Use for displaying and manipulating hierarchical tabular data like org charts or nested lists.

**verticalNavigation:** A vertical list of navigation links for page or in-page navigation. Supports compact spacing, shaded backgrounds, active item highlighting, and cancelable beforeselect events. Use with vertical-navigation-section and vertical-navigation-item children to create sidebar navigation menus.

**verticalNavigationItem:** A text-only link within vertical navigation menus. Requires label and unique name for identification in select events, with optional href for navigation targets. Use as children of vertical-navigation-section or vertical-navigation-overflow for basic navigation items.

**verticalNavigationItemBadge:** A navigation item displaying a numerical badge to the right of the label, shown only when badge count exceeds zero. Supports custom assistive text for accessibility and href navigation. Use for navigation items that need to display counts like unread messages or notifications.

**verticalNavigationItemIcon:** A navigation item displaying an icon to the left of the label. Supports Lightning Design System icon names with href navigation. Use within vertical navigation menus when items need visual icons for better recognition.

**messageService:** A library providing pub/sub messaging across the DOM between Visualforce pages, Aura components, and Lightning web components. Exports MessageContext wire adapter, subscribe, unsubscribe, publish, createMessageChannel, createMessageContext, and releaseMessageContext functions with APPLICATION_SCOPE constant. Use for cross-framework communication via Lightning message channels.
