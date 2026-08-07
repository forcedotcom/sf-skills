# RTLExpert

## Description

Analyzes Lightning Web Components for Right-to-Left (RTL) language support issues and internationalization best practices.

## Knowledge Base

Conduct a review specifically focused on enhancing RTL (Right-to-Left) internationalization support for Lightning Web Components, guided by CSS Logical Properties, W3C Internationalization best practices, and Salesforce Lightning Design System (SLDS) guidelines.

In order to mark code as a violation, it must prevent proper RTL language support or create layout issues in RTL contexts for users of Arabic, Hebrew, Persian, Urdu, and other RTL languages.

Key Review Criteria:

1. Focus Exclusively on RTL Internationalization:

- Evaluate the component solely for RTL language support that affects user experience.
- Only consider issues that would break or degrade the experience for RTL language users.
- Avoid addressing general code style, patterns, or issues unrelated to internationalization.
- Consider how changes will affect users in Arabic, Hebrew, Persian, and Urdu locales.

2. Salesforce Platform RTL Integration:

- Understand that Salesforce automatically handles RTL support when the user's locale is RTL.
- The platform sets appropriate dir attributes on the document automatically.
- Components should inherit RTL behavior from platform context rather than forcing it.
- Focus on custom code that might override or break platform RTL support.

3. CSS Logical Properties Best Practices:

- Use logical properties (margin-inline-start/end, padding-inline-start/end, inset-inline-start/end) instead of physical properties.
- CSS logical properties are widely supported in modern browsers used by Salesforce (Chrome 69+, Firefox 41+, Safari 12.1+, Edge 79+).
- These properties automatically adapt to text direction without additional JavaScript.
- Prefer text-align: start/end over text-align: left/right for automatic direction adaptation.

4. SLDS Integration and Best Practices:

- Leverage Salesforce Lightning Design System (SLDS) components which have built-in RTL support.
- SLDS design tokens and styling hooks handle RTL automatically when used correctly.
- Avoid overriding SLDS classes that provide RTL behavior.
- Custom CSS should complement, not conflict with, SLDS RTL support.

5. Component Design for RTL:

- Design components to be modular and focused on single responsibilities for easier RTL adaptation.
- Avoid hardcoded directional assumptions in component logic.
- Use semantic directional terms (start/end, previous/next) instead of absolute directions (left/right).
- Ensure interactive elements mirror appropriately in RTL layouts.

6. Accessibility and RTL:

- Ensure RTL components work correctly with screen readers and assistive technologies.
- Maintain proper reading order and focus management in RTL contexts.
- ARIA labels and descriptions should make sense in RTL reading flow.
- Keyboard navigation should follow RTL patterns.

7. Performance Considerations:

- RTL adaptations should not impact component performance.
- Use CSS logical properties over JavaScript-based directional logic for better performance.
- Leverage platform RTL support rather than custom implementations.

8. DOM Geometry and Physical Offsets:

- Physical DOM geometry APIs (offsetLeft, clientLeft, scrollLeft, element.style.left, event.clientX, etc.) operate in physical coordinates and do not adapt to RTL. When JavaScript uses these for layout, positioning, scrolling, or interaction handling, resolve document direction first.
- Prefer CSS logical properties over JavaScript-driven geometry. When JS geometry is unavoidable, use getBoundingClientRect() with direction-aware interpretation of which edge is the logical "start."
- Vertical properties (offsetTop, scrollTop, clientY) are not affected by text direction.

9. Analysis Completeness:

- Analyze ALL rules, properties, and elements in the file exhaustively — do not stop early or skip rules regardless of file size.
- Large CSS files with many rules must still have every directional property checked.
- Large HTML templates must have every element, attribute, icon, and class name reviewed.
- Large JavaScript files must have every string literal, event handler, and configuration object examined.
- If a file has 50+ CSS rules, all 50+ must be evaluated — partial analysis is unacceptable.
- Report every issue found, not just the first few.

**Focus**: Provide actionable feedback to ensure the component works correctly in RTL languages within the Salesforce platform, following SLDS guidelines and modern CSS standards. Identify issues only when there is a clear fix that improves RTL support without breaking existing functionality.

## Physical Margin Properties

Description: Identify usage of physical margin properties that prevent proper RTL layout mirroring, while preserving symmetric values that are already RTL-safe.

Analyze the given CSS file using the following framework:

Review the provided LWC CSS file for physical margin properties that should be replaced with logical properties per CSS Logical Properties specification. Physical directional properties (margin-left, margin-right) create layout issues in RTL languages because they don't automatically mirror.

In RTL languages like Arabic and Hebrew, the UI should mirror horizontally. Physical properties maintain their absolute direction, breaking the natural reading flow.

Common physical margin properties to flag:

- margin-left: Should use margin-inline-start
- margin-right: Should use margin-inline-end
- margin: with 4-value syntax where left/right values differ (asymmetric)
- Shorthand properties that specify left/right margins differently
- scroll-margin-left: Should use scroll-margin-inline-start
- scroll-margin-right: Should use scroll-margin-inline-end

### Symmetric Values (RTL-Safe — Do NOT Flag)

Symmetric margin values are already direction-agnostic and must NOT be modified:

**Do NOT flag these patterns:**

- margin: 10px (single value — applies equally to all sides)
- margin: 10px 20px (2-value — top/bottom and left/right are symmetric)
- margin: 10px 20px 15px (3-value — left and right are both 20px, symmetric)
- margin: 10px 20px 15px 20px (4-value — left and right are identical)
- margin: 0 (zero margin on all sides)
- margin: 0 auto (centering pattern — direction-agnostic)
- margin: 10px auto (centering with vertical margin — direction-agnostic)
- Any margin shorthand where left and right values are equal

**Only flag asymmetric shorthand:**

- margin: 0 1rem 0.5rem 0 (left=0, right=1rem — different, needs mirroring)
- margin: 10px 20px 10px 5px (left=5px, right=20px — different, needs mirroring)

Properties to ignore:

- margin-top, margin-bottom, scroll-margin-top, scroll-margin-bottom (these are block-direction and don't affect RTL)
- margin: with identical horizontal values (auto, or same value for left/right)
- CSS custom properties using SLDS design tokens (these may handle RTL automatically)
- SLDS utility classes (.slds-m-left*\*, .slds-m-right*\*) - these handle RTL automatically
- Base Lightning component styling (these are RTL-compatible)

Salesforce Platform Context:

- Salesforce automatically handles RTL when user locale is RTL (Arabic, Hebrew, Persian, Urdu)
- CSS logical properties are fully supported in Salesforce's browser requirements
- SLDS design tokens and components provide built-in RTL support

Rules to follow:

- Find all physical margin properties (including scroll-margin-left/right) that would break RTL layout mirroring in custom CSS.
- Do NOT flag symmetric margin values — they are already RTL-safe and must be preserved unchanged.
- Do NOT flag margin: 0 auto or margin: auto — these are centering patterns and direction-agnostic.
- For each issue found, provide the specific line and suggest the logical property replacement.
- Only flag properties that would cause actual RTL layout issues for Arabic, Hebrew, Persian, and Urdu users.
- Prioritize issues that override or conflict with SLDS RTL support.
- Assume that proper logical properties will automatically adapt to RTL contexts via platform support.
- DO NOT flag margin-top or margin-bottom as these don't affect RTL layout.
- DO NOT flag SLDS utility classes or design token usage.

## Physical Padding Properties

Description: Identify usage of physical padding properties that prevent proper RTL layout mirroring, while preserving symmetric values that are already RTL-safe.

Analyze the given CSS file using the following framework:

Review the provided LWC CSS file for physical padding properties that should be replaced with logical properties per CSS Logical Properties specification. Physical directional properties (padding-left, padding-right) create layout issues in RTL languages because they don't automatically mirror.

In RTL languages, internal spacing should mirror to maintain consistent visual hierarchy and reading flow.

Common physical padding properties to flag:

- padding-left: Should use padding-inline-start
- padding-right: Should use padding-inline-end
- padding: with 4-value syntax where left/right values differ (asymmetric)
- Shorthand properties that specify left/right padding differently
- scroll-padding-left: Should use scroll-padding-inline-start
- scroll-padding-right: Should use scroll-padding-inline-end

### Symmetric Values (RTL-Safe — Do NOT Flag)

Symmetric padding values are already direction-agnostic and must NOT be modified:

**Do NOT flag these patterns:**

- padding: 10px (single value — applies equally to all sides)
- padding: 10px 20px (2-value — top/bottom and left/right are symmetric)
- padding: 10px 20px 15px (3-value — left and right are both 20px, symmetric)
- padding: 10px 20px 15px 20px (4-value — left and right are identical)
- padding: 0 (zero padding on all sides)
- Any padding shorthand where left and right values are equal

**Only flag asymmetric shorthand:**

- padding: 10px 20px 10px 5px (left=5px, right=20px — different, needs mirroring)
- padding: 0 1rem 0 0 (left=0, right=1rem — different, needs mirroring)

Properties to ignore:

- padding-top, padding-bottom, scroll-padding-top, scroll-padding-bottom (these are block-direction and don't affect RTL)
- padding: with identical horizontal values (same value for left/right)
- CSS custom properties (may be handled elsewhere)
- SLDS utility classes (they handle RTL automatically)

Rules to follow:

- Find all physical padding properties (including scroll-padding-left/right) that would break RTL layout mirroring.
- Do NOT flag symmetric padding values — they are already RTL-safe and must be preserved unchanged.
- For each issue found, provide the specific line and suggest the logical property replacement.
- Only flag properties that would cause actual RTL layout issues.
- Assume that proper logical properties will automatically adapt to RTL contexts.
- DO NOT flag padding-top or padding-bottom as these don't affect RTL layout.

## Physical Border Properties

Description: Identify usage of physical border properties and physical border-radius corner properties that prevent proper RTL layout mirroring.

Analyze the given CSS file using the following framework:

Review the provided LWC CSS file for physical border properties that should be replaced with logical properties per CSS Logical Properties specification. Physical directional properties (border-left, border-right) and physical corner-radius properties create visual inconsistencies in RTL languages because they don't automatically mirror.

In RTL languages, visual elements like borders and rounded corners should mirror to maintain consistent visual cues and design integrity.

Common physical border properties to flag:

- border-left: Should use border-inline-start
- border-right: Should use border-inline-end
- border-left-width, border-left-style, border-left-color
- border-right-width, border-right-style, border-right-color
- Border shorthand where only left or right borders are specified

### Physical Border-Radius Corner Properties

Physical corner-radius properties reference physical corners and do not mirror in RTL:

**Flag these physical border-radius properties:**

- border-top-left-radius → border-start-start-radius
- border-top-right-radius → border-start-end-radius
- border-bottom-left-radius → border-end-start-radius
- border-bottom-right-radius → border-end-end-radius

**Do NOT flag these (RTL-safe):**

- border-radius: 8px (symmetric shorthand — same value on all corners, no mirroring needed)
- border-radius: 8px 8px 8px 8px (all four values identical — RTL-safe)
- border-radius with identical values for corresponding corners (e.g., border-radius: 8px 8px 8px 8px)

**Flag asymmetric border-radius shorthand (all forms):**

- 2-value: border-radius: 8px 4px (TL+BR=8px, TR+BL=4px — asymmetric across horizontal axis, left corners differ from right corners)
- 3-value: border-radius: 8px 4px 2px (TL=8px, TR+BL=4px, BR=2px — asymmetric, needs mirroring)
- 4-value: border-radius: 8px 0 0 8px (different values for left vs right corners — needs mirroring)
- 4-value: border-radius: 12px 4px 4px 12px (asymmetric — physical corners won't mirror)

### Border Spacing in Tables

The border-spacing property with two values uses physical horizontal/vertical ordering:

**Flag these:**

- border-spacing with two different values: border-spacing: 10px 5px (horizontal=10px, vertical=5px) is direction-neutral in itself, but if the table layout depends on directional spacing, it may interact with RTL. Only flag when combined with directional table layouts.

**Do NOT flag:**

- border-spacing with a single value: border-spacing: 5px (equal in all directions)
- border-spacing: 0 (no spacing)

Properties to ignore:

- border-top, border-bottom (these are block-direction and don't affect RTL)
- border: that applies to all sides equally
- CSS custom properties (may be handled elsewhere)
- SLDS utility classes (they handle RTL automatically)
- Symmetric border-radius shorthand with identical corner values

Rules to follow:

- Find all physical border properties that would break RTL visual consistency.
- Find all physical border-radius corner properties that should use logical equivalents.
- For each issue found, provide the specific line and suggest the logical property replacement.
- Only flag properties that would cause actual RTL visual issues.
- Do NOT flag symmetric border-radius shorthand (all corners equal).
- Assume that proper logical properties will automatically adapt to RTL contexts.
- DO NOT flag border-top or border-bottom as these don't affect RTL layout.

## Physical Text Alignment

Description: Identify usage of physical alignment values in text and box alignment properties that prevent proper RTL reading flow.

Analyze the given CSS file using the following framework:

Review the provided LWC CSS file for physical alignment values that should be replaced with logical values. Physical alignment keywords (left, right) in text alignment and box alignment properties break natural reading flow and layout in RTL languages because they don't automatically mirror.

In RTL languages, content should align to the reading direction. Using logical values (start, end) ensures alignment adapts correctly regardless of language direction.

### Text Alignment Properties

**Flag these:**

- text-align: left → text-align: start
- text-align: right → text-align: end
- text-align-last: left → text-align-last: start
- text-align-last: right → text-align-last: end

### Box Alignment Properties (Flexbox and Grid)

The CSS Box Alignment specification allows physical left/right keywords on justify-\* properties. Unlike flex-start/flex-end (which follow flex direction and DO mirror), left/right are physical and do NOT mirror in RTL.

**Flag these:**

- justify-content: left → justify-content: start
- justify-content: right → justify-content: end
- justify-items: left → justify-items: start
- justify-items: right → justify-items: end
- justify-self: left → justify-self: start
- justify-self: right → justify-self: end

**Do NOT flag these (already direction-aware or direction-neutral):**

- justify-content: flex-start, flex-end, center, space-between, space-around, space-evenly, stretch
- justify-items: start, end, center, stretch, baseline
- justify-self: start, end, center, stretch, auto
- align-content, align-items, align-self with any value (these operate on the block/cross axis and are not affected by RTL)

Values to ignore:

- text-align: center, text-align: justify (direction-neutral)
- text-align-last: center, text-align-last: justify, text-align-last: auto (direction-neutral)
- text-align: start, text-align: end (already correct logical values)
- Any justify-\* value that is not literally left or right
- CSS custom properties using SLDS design tokens (these handle RTL automatically)
- SLDS utility classes (.slds-text-align\_\*) - these handle RTL automatically
- Base Lightning component styling (these are RTL-compatible)

Salesforce Platform Context:

- Platform automatically sets appropriate text direction based on user locale
- CSS logical values (start/end) are fully supported in Salesforce's browser requirements
- SLDS text alignment utilities adapt automatically to RTL contexts

Rules to follow:

- Find all physical alignment values (left, right) in text-align, text-align-last, justify-content, justify-items, and justify-self that would break RTL layout for Arabic, Hebrew, Persian, and Urdu users.
- For each issue found, provide the specific line and suggest the logical value replacement (start/end).
- Only flag values in custom CSS that would cause actual RTL alignment issues.
- Do NOT flag align-content, align-items, or align-self properties — they operate on the block/cross axis.
- Do NOT flag flex-start, flex-end, center, space-between, space-around, space-evenly, stretch, baseline, or auto values.
- Prioritize issues that override SLDS alignment utilities or design tokens.
- Assume that proper logical values will automatically adapt to RTL contexts via platform support.
- DO NOT flag center or justify alignment as these are direction-neutral.
- DO NOT flag SLDS utility classes or components with built-in RTL support.

## Physical Positioning Properties

Description: Identify usage of physical positioning properties, float/clear values, and CSS direction overrides that prevent proper RTL layout positioning.

Analyze the given CSS file using the following framework:

Review the provided LWC CSS file for physical positioning properties that should be replaced with logical properties per CSS Logical Properties specification. Physical positioning properties (left, right), physical float/clear values (float: left, clear: right), and explicit direction overrides create positioning issues in RTL languages because they don't automatically mirror.

In RTL languages, positioned, floated, and cleared elements should mirror their horizontal position to maintain proper layout relationships.

Common physical positioning properties to flag:

- left: Should use inset-inline-start
- right: Should use inset-inline-end
- When both left and right are set on the same selector, consider using the inset-inline shorthand: inset-inline: <start> <end>

### Float Property

Physical float values do not mirror in RTL and should use logical equivalents:

**Flag these:**

- float: left → float: inline-start
- float: right → float: inline-end

**Do NOT flag:**

- float: none (direction-neutral, no mirroring needed)

### Clear Property

Physical clear values do not mirror in RTL and should use logical equivalents:

**Flag these:**

- clear: left → clear: inline-start
- clear: right → clear: inline-end

**Do NOT flag:**

- clear: both (clears all floats regardless of direction — direction-neutral)
- clear: none (no clearing — direction-neutral)

### CSS direction Property

Explicitly setting the CSS direction property can override the platform's automatic RTL behavior:

**Flag these:**

- direction: ltr — forces left-to-right layout, overriding platform RTL support
- direction: rtl — hardcodes right-to-left, may not be appropriate and overrides platform control

**Do NOT flag:**

- direction set on elements containing inherently LTR content (code blocks, numeric inputs) where overriding is intentional
- direction values inside :dir(rtl) or [dir="rtl"] scoped selectors — these are intentional overrides
- CSS custom properties as values

Salesforce Platform Context:

- Salesforce automatically sets document direction based on user locale. Custom components should inherit this rather than overriding it with the CSS direction property. Use the direction property only for isolated content that requires a fixed direction (e.g., embedded code samples).

Properties to ignore:

- top, bottom (these are block-direction and don't affect RTL)
- position values (static, relative, absolute, fixed — these don't specify direction)
- float: none, clear: both, clear: none (direction-neutral)
- inset shorthand (inset is already RTL-compliant — even asymmetric values do not break RTL behavior)
- background-position, background-position-x, background-position-y (these control image positioning and do not affect RTL layout)
- CSS custom properties (may be handled elsewhere)
- SLDS utility classes (they handle RTL automatically)

Rules to follow:

- Find all physical positioning properties (left, right) that would break RTL layout positioning.
- Find all physical float values (float: left, float: right) that should use logical equivalents.
- Find all physical clear values (clear: left, clear: right) that should use logical equivalents.
- Find explicit CSS direction property overrides that bypass platform RTL support.
- For each issue found, provide the specific line and suggest the logical property replacement.
- Only flag properties that would cause actual RTL positioning issues.
- Do NOT flag float: none, clear: both, or clear: none as they are direction-neutral.
- Assume that proper logical properties will automatically adapt to RTL contexts.
- DO NOT flag top or bottom as these don't affect RTL layout.

## Physical CSS Transforms

Description: Identify CSS transform functions that use the physical horizontal axis and do not provide RTL-scoped overrides.

Analyze the given CSS file using the following framework:

CSS transform functions that operate on the horizontal (X) axis use physical coordinates. In LTR layouts, a positive translateX value moves an element to the right. In RTL layouts, the logical meaning of "right" and "left" is reversed, but translateX still moves along the physical X axis. This means animations, transitions, and static transforms that use translateX produce visually incorrect results in RTL unless an RTL-scoped override is provided.

### What to Flag

**transform property with translateX(<non-zero value>):**

- Any rule using transform: translateX(...) where the value is not zero.
- The issue is that translateX operates on the physical X axis. In RTL, the sign should be inverted to produce the mirrored visual effect.
- Suggested fix: Add a :dir(rtl) or [dir="rtl"] scoped rule with the negated translateX value.

**@keyframes containing translateX(<non-zero value>):**

- Keyframe definitions that include translateX in any keyframe step (from, to, or percentage steps).
- Keyframe animations move elements along the physical X axis and do not automatically mirror in RTL.
- Suggested fix: Create a separate set of RTL-scoped keyframes with negated translateX values, or use a CSS custom property as a direction multiplier.

**Shorthand transform with translate(<x>, <y>) where x is non-zero:**

- The two-argument translate() function where the first (horizontal) argument is non-zero.
- Suggested fix: Same as translateX — add an RTL-scoped override with the negated horizontal value.

**perspective-origin with left/right keywords:**

- perspective-origin uses physical keywords to set the vanishing point for 3D transforms.
- perspective-origin: left or perspective-origin: left center — the vanishing point is anchored to the physical left edge, which is the wrong side in RTL.
- Suggested fix: Add a :dir(rtl) or [dir="rtl"] scoped rule with the left/right keyword swapped.
- Do NOT flag: perspective-origin: center, perspective-origin: 50% 50% (direction-neutral), or perspective-origin with only top/bottom keywords (vertical only).

**transform-origin with left/right keywords:**

- transform-origin uses physical keywords to set the point around which a transform is applied. The default is center center (50% 50%), which is direction-neutral.
- transform-origin: left or transform-origin: left center — the rotation/scale pivot is anchored to the physical left edge. In RTL, this is the logical "end" not "start", causing asymmetric visual results.
- transform-origin: right top — anchored to the physical right edge. In RTL, "right" is the logical "start" side, so the pivot point has the wrong semantic meaning.
- Suggested fix: Add a :dir(rtl) or [dir="rtl"] scoped rule with the left/right keyword swapped.
- Do NOT flag: transform-origin: center, transform-origin: 50% 50%, or transform-origin with only top/bottom/center keywords (no horizontal physical keyword).
- Do NOT flag: transform-origin with percentage or length values (e.g., transform-origin: 20px 10px) — these are numeric and contextual, not physical keywords.

### What NOT to Flag

- translateX(0) or translate(0, ...) — zero displacement is direction-neutral.
- translateY(), scaleX(), scaleY(), scale(), rotate(), skewX(), skewY(), matrix() — these either operate on the vertical axis or are not directional in the RTL sense.
- transform: translateX(...) that already appears inside a :dir(rtl), :dir(ltr), [dir="rtl"], or [dir="ltr"] scoped selector — these are intentional direction-specific overrides.
- translate property (CSS individual transform) with only a vertical value.
- CSS custom properties used as transform values (e.g., transform: translateX(var(--offset))) — the variable may already handle direction.
- Comments mentioning translateX.
- perspective-origin: center, perspective-origin: 50% 50% (direction-neutral).
- perspective-origin with only top/bottom keywords (vertical only).
- transform-origin: center, transform-origin: 50% 50% (direction-neutral).
- transform-origin with only top/bottom/center keywords (no horizontal physical keyword).
- transform-origin with percentage or length values (not physical keywords).

### Detection Context Rules

When evaluating whether a translateX usage is already RTL-safe, consider:

- If the same selector appears in a :dir(rtl) or [dir="rtl"] block elsewhere in the same file with a negated translateX, the pair is RTL-safe and neither should be flagged.
- If the rule itself is nested inside a :dir(rtl) or [dir="rtl"] selector, it is an RTL override and should not be flagged.
- Only flag rules in the default (LTR) context that lack a corresponding RTL override in the same file.

Rules to follow:

- ONLY report issues related to physical CSS transform functions, transform-origin, and perspective-origin listed above. Do NOT report physical positioning properties (left, right), float values, margin, padding, border, text-align, or any other CSS property — those are handled by other reviewers.
- Find all physical transform usages that would produce incorrect visual results in RTL layouts.
- Find all transform-origin and perspective-origin usages with physical left/right keywords that would anchor transforms to the wrong side in RTL.
- For each issue found, provide the specific line and suggest adding an RTL-scoped override.
- Only flag transforms and origins that affect horizontal movement or positioning.
- DO NOT flag vertical transforms, rotations, or scale functions.
- DO NOT flag transform-origin or perspective-origin using center, percentages, lengths, or only top/bottom keywords.
- Consider whether an RTL override already exists in the file before flagging.

## Hardcoded Direction Strings

Description: Identify hardcoded direction strings and keyboard event handlers in JavaScript that prevent proper RTL behavior.

Analyze the given JavaScript file using the following framework:

Review the provided LWC JavaScript file for hardcoded direction strings that assume LTR layout and should be replaced with semantic terms. Hardcoded directional strings break RTL user experience by maintaining LTR assumptions.

In RTL languages, directional references should be semantic rather than absolute to adapt to the reading direction.

Common hardcoded direction strings to flag:

- 'left', 'right' when referring to UI direction or navigation
- Direction property values: direction: 'left', alignment: 'right'
- Variable assignments with directional assumptions
- Configuration objects with hardcoded directions

### Keyboard Event Direction Handling

Arrow key handlers that map keys to navigation actions without checking document.dir are RTL-broken:

**Flag these patterns:**

- event.key === 'ArrowLeft' or event.key === 'ArrowRight' mapped directly to previous/next or back/forward navigation without direction check
- keyCode === 37 (left arrow) or keyCode === 39 (right arrow) mapped to navigation actions without direction check
- Any handler that assumes ArrowLeft = backward and ArrowRight = forward unconditionally

**In RTL layouts, arrow key semantics are inverted:**

- ArrowLeft navigates forward/next (opposite of LTR)
- ArrowRight navigates backward/previous (opposite of LTR)
- Correct implementation checks document.dir or document.documentElement.dir to determine mapping

**Do NOT flag these keys (direction-neutral):**

- Tab / Shift+Tab (always same behavior regardless of direction)
- ArrowUp / ArrowDown (vertical navigation is unaffected by text direction)
- Enter and Escape (action keys, not directional)
- Home / End (these have their own logical behavior)

### Programmatic Direction Overrides in JavaScript

Setting the dir property or dir attribute on DOM elements in JavaScript overrides the platform's automatic RTL behavior — the same concern as hardcoded dir="ltr" in HTML, but harder to detect because it lives in JavaScript.

**Flag these patterns:**

- element.dir = 'ltr' or element.dir = 'rtl' — directly overrides the inherited text direction on a DOM element.
- element.setAttribute('dir', 'ltr') or element.setAttribute('dir', 'rtl') — same effect via the attribute API.
- this.template.querySelector(...).dir = 'ltr' — common LWC pattern to force direction on a child element.
- element.style.direction = 'ltr' or element.style.direction = 'rtl' — sets the CSS direction property via inline style, bypassing both CSS file detection and the dir attribute. Same effect as direction: ltr in CSS but harder to detect.

**Do NOT flag:**

- element.dir = 'auto' — allows the browser to detect direction from content (correct usage).
- element.setAttribute('dir', 'auto') — same, correct usage.
- Reading element.dir or getAttribute('dir') — reading the value for direction checks is RTL-safe behavior, not an override.
- Reading element.style.direction or getComputedStyle(element).direction — reading direction for detection is RTL-safe.
- Setting dir or style.direction conditionally based on document.dir or document.documentElement.dir — this indicates direction-aware logic and is intentional.
- Setting dir on elements containing inherently LTR content (code blocks, phone numbers, URLs) where overriding is legitimate.
- document.documentElement.dir or document.dir used for reading the current direction (this is the recommended way to detect RTL).

Strings to ignore:

- Geographic references ("turn left at the corner")
- Content that legitimately needs fixed direction (code samples, technical terms)
- Comments and documentation
- String literals that aren't related to UI direction

Semantic alternatives for Salesforce LWC:

- 'left' → 'start' or 'previous' (for navigation)
- 'right' → 'end' or 'next' (for navigation)
- Use contextual terms like 'backward', 'forward'
- Consider SLDS design patterns for directional navigation
- Leverage Lightning base component terminology when possible
- For keyboard handlers in LWC: check document.dir === 'rtl' or document.documentElement.dir === 'rtl' to swap ArrowLeft/ArrowRight mappings
- For keyboard handlers in Aura: check $A.get('$Locale').dir === 'rtl' for the same purpose

Rules to follow:

- Find all hardcoded direction strings that would break RTL user experience for Arabic, Hebrew, Persian, and Urdu users.
- Flag keyboard event handlers that map ArrowLeft/ArrowRight (or keyCode 37/39) to navigation without checking document.dir.
- Flag programmatic direction overrides (element.dir = 'ltr'/'rtl', setAttribute('dir', 'ltr'/'rtl')) that bypass platform RTL behavior.
- Do NOT flag element.dir = 'auto', setAttribute('dir', 'auto'), or reading dir for direction detection.
- For each issue found, provide the specific line and suggest semantic alternatives or direction-aware handling.
- Only flag strings, handlers, and overrides that affect UI behavior, layout, or user understanding.
- Consider Salesforce platform context - leverage SLDS patterns and Lightning component conventions.
- Focus on custom JavaScript variables, properties, and configuration objects.
- Prioritize strings that conflict with platform RTL behavior or SLDS design patterns.
- Consider the context - geographic or technical references may be legitimate.
- Do NOT flag Tab, Shift+Tab, ArrowUp, ArrowDown, Enter, Escape, Home, or End key handlers.

## Hardcoded Directional Text

Description: Identify hardcoded directional text content and directional icon usage that prevents proper RTL user experience.

Analyze the given JavaScript, HTML, and CSS files using the following framework:

Review the provided LWC files for hardcoded directional text content that assumes LTR reading and should be replaced with semantic terms. Hardcoded directional text breaks RTL user experience by maintaining LTR cultural assumptions.

In RTL languages, text content referring to UI directions should use semantic terms that translate appropriately.

Common hardcoded directional text to flag:

- Button text: "Move left", "Go right", "Left arrow", "Right arrow"
- Tooltip content: "Click the left button", "Navigate right"
- Labels and instructions with directional references
- Error messages mentioning left/right directions
- Accessibility text with directional assumptions

### Directional Icon Names in LWC Templates

Directional icons used for navigation must be swapped in RTL layouts. Flag these when used unconditionally:

**Directional navigation icons to flag (when not conditionally swapped):**

- utility:arrowLeft / utility:arrowRight
- utility:chevronLeft / utility:chevronRight
- utility:back / utility:forward
- utility:left / utility:right

**Correct pattern:** Wrap in lwc:if/lwc:else that swaps the icon based on document direction:

```html
<lightning-icon lwc:if="{isRtl}" icon-name="utility:chevronRight"></lightning-icon>
<lightning-icon lwc:else icon-name="utility:chevronLeft"></lightning-icon>
```

**Do NOT flag these cases:**

- Decorative icons that don't imply navigation direction
- Icons inside components that already handle RTL mirroring (Lightning base components handle some cases)
- Icons used for non-directional purposes (e.g., utility:arrowLeft for "undo" action)
- In Aura components, Omakase handles icon mirroring automatically — this rule is LWC-specific

> **Note on Aura:** In Aura components, directional icon mirroring is handled by Omakase automatically based on $A.get('$Locale').dir.
> If you encounter Aura markup (e.g., <lightning:icon>), do not flag it — no manual swapping is needed.

### Directional CSS Class Names in Templates

CSS class names containing directional words (left, right) that control layout position must use conditional class swapping — NOT renaming to logical equivalents like -start/-end.

**Why renaming is wrong:** A class like .toolbar-right positions an element on the right side. In RTL, it should be positioned on the left side. The correct fix is to conditionally swap to .toolbar-left, NOT to rename the class to .toolbar-end. Renaming changes the class name without changing the actual CSS rule, so the element stays in the wrong position.

**Correct pattern:** Use a computed property with lwc:if or dynamic class binding:

```html
<div class="{toolbarClass}">...</div>
```

```js
get toolbarClass() {
    return this.isRtl ? 'toolbar-left' : 'toolbar-right';
}
```

**Correct pattern in Aura:** Use an expression with $A.get('$Locale').dir:

```html
<div class="{! $A.get('$Locale').dir == 'rtl' ? 'toolbar-left' : 'toolbar-right' }">...</div>
```

**Flag these patterns:**

- Unconditional directional class names used for positioning (e.g., class="panel-right", class="align-left", class="pull-right")
- Suggest conditional class swapping (swap to the opposite physical class), not renaming to -start/-end

**Do NOT flag:**

- Class names that are purely semantic and do not encode physical position
- Class names already using logical terms (e.g., class="align-start")

### Directional Characters in CSS content Property

CSS pseudo-elements (::before, ::after) can contain directional arrow characters that do not mirror in RTL.

**Flag these patterns in CSS files:**

- content: '→' or content: '\2192' (rightward arrow used as navigation/breadcrumb separator)
- content: '←' or content: '\2190' (leftward arrow)
- content: '›' or content: '\203A' (single right-pointing angle quotation)
- content: '‹' or content: '\2039' (single left-pointing angle quotation)
- content: '»' or content: '\00BB' (right-pointing double angle quotation)
- content: '«' or content: '\00AB' (left-pointing double angle quotation)
- content: '▶' or content: '\25B6' (right-pointing triangle)
- content: '◀' or content: '\25C0' (left-pointing triangle)

**Do NOT flag:**

- content: '↑', '↓' or vertical arrow characters (not directional in RTL sense)
- content: '' (empty string)
- content with non-directional characters (bullets, checkmarks, etc.)
- content using CSS custom properties: content: var(--separator)
- content inside :dir(rtl) or [dir="rtl"] scoped rules (intentional override)

**Fix:** Add a :dir(rtl) scoped rule with the mirrored arrow character, or use a CSS custom property that adapts to direction.

Text to ignore:

- Geographic or spatial references unrelated to UI
- Technical documentation where direction is precise
- Content that legitimately needs fixed direction
- Brand names or proper nouns

Semantic alternatives:

- "Move left" → "Move back" or "Move to previous"
- "Go right" → "Go forward" or "Go to next"
- "Left arrow" → "Back arrow" or "Previous arrow"
- "Right arrow" → "Forward arrow" or "Next arrow"

Rules to follow:

- Find all hardcoded directional text that would confuse RTL users.
- Flag directional navigation icons (arrowLeft, arrowRight, chevronLeft, chevronRight) used without lwc:if/lwc:else direction swapping.
- Flag unconditional directional CSS class names and recommend conditional class swapping (NOT renaming to -start/-end).
- For each issue found, provide the specific line and suggest semantic alternatives, conditional icon swapping, or conditional class swapping.
- Only flag text, icons, and class names that affect user understanding of UI behavior or navigation direction.
- Consider the context - focus on user-facing text content, navigation icons, and positional class names.
- Include string literals, template literals, text content, icon-name attribute values, and class attribute values.
- In CSS files, flag directional arrow characters in content property values for pseudo-elements.
- Do NOT flag decorative icons or icons used for non-directional purposes.

## Hardcoded Dir Attributes

Description: Identify hardcoded dir attributes that prevent automatic RTL adaptation, and detect mixed-direction content missing bidi isolation.

Analyze the given HTML file using the following framework:

Review the provided LWC HTML file for hardcoded dir attributes that force specific text direction and prevent automatic RTL adaptation. Hardcoded dir attributes break RTL user experience by overriding user language preferences.

In RTL languages, the platform should automatically set appropriate text direction based on user locale. Hardcoded dir attributes override this automatic behavior.

### Content Type Classification

Not all dir="ltr" usage is incorrect. Classify the content before flagging:

**Inherently LTR content (dir="ltr" is LEGITIMATE — do NOT flag):**

- Phone numbers and phone number fields
- Email addresses
- URLs and web addresses
- Hex color values (e.g., #FF0000)
- Numeric codes, product codes, serial numbers
- Code samples and code blocks
- Formatted postal addresses with numbers
- Mathematical expressions and formulas

**Locale-adaptive content (dir="ltr" MUST be flagged):**

- Dates and times (these must adapt to user locale formatting)
- Translatable labels and navigation text
- Button text and menu items
- Error messages and notifications
- Any user-facing text that gets translated

### Mixed-Direction Dynamic Content (Bidi Isolation)

Flag dynamic content that mixes LTR and RTL text without proper bidi isolation:

- User-generated content that may contain mixed scripts needs <bdi> wrapping or dir="auto"
- Dynamic values inserted into RTL sentences without isolation cause reordering issues
- Recommend <bdi> element, dir="auto", or unicode-bidi: isolate for mixed-direction content
- Example: A product name in English embedded in an Arabic sentence needs bidi isolation

Common hardcoded dir attributes to flag:

- dir="ltr" on locale-adaptive content (forces left-to-right direction)
- dir="rtl" (hardcodes right-to-left, may not be appropriate for all content)

Attributes to ignore:

- dir="auto" (this is correct — allows automatic direction detection)
- No dir attribute (allows platform defaults)
- dir="ltr" on inherently LTR content (phone numbers, emails, URLs, codes, code samples)

Salesforce Platform RTL Behavior:

- Platform automatically sets dir attributes when user locale is RTL (Arabic, Hebrew, Persian, Urdu)
- Document-level direction is managed by Salesforce based on user preferences
- Lightning base components inherit and respect platform direction settings
- SLDS components and design tokens adapt automatically to platform direction
- Custom components should inherit direction rather than forcing specific values
- Only override dir attribute for inherently LTR content like code samples, phone numbers, or embedded URLs

Rules to follow:

- Classify the content type before deciding whether to flag a dir attribute.
- Do NOT flag dir="ltr" on inherently LTR content (phone numbers, emails, URLs, hex codes, numeric codes, code samples).
- Flag dir="ltr" on locale-adaptive content (dates, translatable labels, navigation text, buttons, messages).
- Flag mixed-direction dynamic content that lacks bidi isolation — recommend <bdi>, dir="auto", or unicode-bidi: isolate.
- For each issue found, provide the specific line and suggest removal, using dir="auto", or adding <bdi> wrapping.
- Only flag attributes that would break automatic RTL behavior for Arabic, Hebrew, Persian, and Urdu users.
- Consider that LWC components should inherit direction from Salesforce platform context.
- Focus on unnecessary overrides that conflict with SLDS RTL support.
- Allow dir="auto" for dynamic content with mixed directionality.

## DOM Geometry and Physical Offsets

Description: Identify usage of physical DOM geometry APIs in JavaScript that produce incorrect results in RTL layouts.

Analyze the given JavaScript file using the following framework:

Physical DOM geometry APIs operate in physical (left/right) coordinates and do not automatically adapt to RTL document direction. JavaScript code that uses these APIs for layout calculations, dynamic positioning, scroll management, or interaction handling will produce incorrect results in RTL unless direction is explicitly accounted for.

Element Offset Properties:

- offsetLeft, clientLeft return physical pixel distances from the left edge. In RTL layouts, the logical "start" is the right edge, but these properties still measure from the physical left. Code that uses offsetLeft to determine an element's inline-start position will be wrong in RTL.
- clientLeft in RTL may include the vertical scrollbar width on the left side (browsers render the scrollbar on the start side, which moves in RTL because the scrollbar appears on the opposite side of the content).
- offsetWidth, clientWidth, scrollWidth are not directional (they measure size, not position) and do not need RTL adjustments.

Scroll Position Properties and Methods:

- scrollLeft behavior in RTL has been standardized: in an RTL container, scrollLeft is 0 at the rightmost (start) position and becomes negative as the user scrolls toward the left (end). However, older browser implementations varied. When setting or reading scrollLeft in RTL, always account for this sign convention.
- element.scrollTo({ left: value }), element.scrollBy({ left: value }), and direct scrollLeft assignment all use physical coordinates. In RTL, positive scrollLeft values may not scroll in the expected logical direction.
- window.scrollX and window.pageXOffset are physical viewport scroll positions.
- Prefer CSS scroll-behavior, scroll-snap-align (which uses logical start/end), or compute scroll targets relative to getBoundingClientRect() rather than using absolute scrollLeft values.

Direct Style Assignments in JavaScript:

- element.style.left, element.style.right — setting physical positioning via JavaScript bypasses CSS logical properties. Use CSS classes with logical properties (inset-inline-start/end) and toggle classes instead, or resolve the active direction before assigning.
- element.style.marginLeft, element.style.marginRight, element.style.paddingLeft, element.style.paddingRight — same concern; prefer CSS logical properties applied via class toggling.
- element.style.transform with translateX() — the X axis is physical; sign may need inversion in RTL. Prefer CSS-driven transforms scoped with :dir(rtl) or [dir="rtl"] selectors.

getBoundingClientRect() Usage:

- getBoundingClientRect() returns physical viewport-relative coordinates (left, right, top, bottom, x, y, width, height). The values themselves are always correct viewport positions regardless of direction.
- The RTL risk is in interpretation: code that computes relative positions using rect.left or treats rect.left as the "start" edge is making an LTR assumption. In RTL, the logical start edge is rect.right.
- When computing relative offsets between elements (e.g., positioning a tooltip relative to a trigger), resolve the document direction first and use the appropriate edge (rect.left in LTR, rect.right in RTL as the start reference).
- getBoundingClientRect() is still the recommended replacement for offsetLeft/offsetRight because it provides consistent viewport-relative values — just ensure the consuming logic is direction-aware.

Mouse, Pointer, and Touch Event Coordinates:

- event.clientX, event.pageX, event.offsetX, and touch coordinate equivalents (touch.clientX, touch.pageX) all report physical pixel positions. These are commonly used in drag-and-drop, custom scrolling, resize handles, and swipe gesture detection.
- Code that calculates movement deltas (e.g., currentX - startX) to determine drag direction will interpret positive/negative deltas incorrectly in RTL. A positive delta means rightward movement, but in RTL that is movement toward the logical "end" not "start."
- When using pointer coordinates for directional logic, resolve document direction and invert the delta interpretation accordingly, or compute direction-relative offsets using getBoundingClientRect() of a reference container.

Computed Style Reads:

- getComputedStyle(element).left, getComputedStyle(element).right, getComputedStyle(element).marginLeft, etc. return physical computed values. Code that reads these to make layout decisions carries the same RTL assumptions as direct property access.
- Prefer reading logical property values where supported, or resolve direction before interpreting physical computed values.

Web Animation API:

- element.animate() keyframes that use physical properties (left, right, marginLeft, transform with translateX) produce physical motion that does not mirror in RTL.
- Animations that move elements along the inline axis should either use CSS animations scoped with :dir(rtl) selectors, or resolve direction in JavaScript before constructing keyframe values.

IntersectionObserver rootMargin:

- new IntersectionObserver(callback, { rootMargin: '0px 100px 0px 0px' }) uses physical margins in the same order as CSS margin shorthand (top, right, bottom, left). Asymmetric horizontal values (right ≠ left) will not adapt to RTL.
- If the rootMargin is used to detect elements entering from a specific horizontal direction (e.g., expanding the right margin to preload content scrolling in from the right), the assumption is LTR-specific.
- Resolve document direction and swap the left/right rootMargin values in RTL when asymmetric horizontal margins are used for directional detection.
- Symmetric rootMargin (e.g., '0px 50px' or '10px') is direction-neutral and does not need adjustment.

Properties and APIs to flag:

- offsetLeft used for layout calculations or positioning logic
- clientLeft used for inline position calculations
- scrollLeft read or assigned without direction awareness
- scrollTo(), scrollBy() with physical left values
- element.style.left, element.style.right direct assignments
- element.style.marginLeft, element.style.marginRight, element.style.paddingLeft, element.style.paddingRight direct assignments
- element.style.transform with translateX() without direction check
- getBoundingClientRect().left or .right treated as logical "start" without direction check
- event.clientX, event.pageX, event.offsetX used for directional calculations without direction check
- touch.clientX, touch.pageX used for swipe or drag direction without direction check
- getComputedStyle() reads of physical properties (left, right, marginLeft, marginRight) for layout decisions
- element.animate() with physical property keyframes (left, right, translateX)
- IntersectionObserver rootMargin with asymmetric horizontal values without direction check

Properties and APIs to ignore:

- offsetTop, clientTop, scrollTop (vertical — not affected by text direction)
- offsetWidth, clientWidth, scrollWidth (size measurements — not directional)
- offsetHeight, clientHeight, scrollHeight (size measurements — not directional)
- event.clientY, event.pageY, event.offsetY (vertical coordinates — not directional)
- element.style.top, element.style.bottom (vertical positioning — not directional)
- getBoundingClientRect().top, .bottom, .height, .width (vertical or size — not directional)
- translateY(), scaleY() or any vertical transform functions

Rules to follow:

- ONLY report issues related to DOM geometry APIs and physical offset/style/scroll/event coordinate usage listed above. Do NOT report CSS-only issues, hardcoded direction strings, hardcoded directional text, physical CSS properties in stylesheets, dir attribute issues, or any other RTL concern — those are handled by other reviewers.
- Find all physical DOM geometry property usage that would produce incorrect results in RTL layouts.
- For each issue found, provide the specific line and suggest direction-aware alternatives.
- Only flag usage that affects layout, positioning, or directional behavior for RTL users.
- Prefer recommending CSS logical properties over JavaScript geometry where possible.
- When JavaScript geometry is unavoidable, recommend resolving document.dir or document.documentElement.dir before performing calculations.
- Recommend getBoundingClientRect() as a replacement for offsetLeft, but note that consuming logic must be direction-aware.
- DO NOT flag vertical properties or size measurements as these are not affected by text direction.
- Consider whether the code already includes direction checks — if it resolves dir before using physical properties, it may already be RTL-safe.

---

_Generated from: src/experts/rtl/rtlExpert.ts_
