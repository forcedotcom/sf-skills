### Document.createProcessingInstruction

#### How to Find the Issue

Flag ALL usage of `document.createProcessingInstruction` including:

- Direct calls, bracket notation, destructuring
- Variable-based or dynamically constructed method names
- String concatenation or template literals creating the method name
- All contexts: Loops, conditionals, event handlers, async callbacks, hidden by unicode escape sequences and Reflection APIs

#### How to report the Issue

**RuleId: lws-001**
**level: error**
**message: Usage of document.createProcessingInstruction creates XML injection vulnerabilities enabling XSS attacks**

---

### Document Event Handlers

#### How to Find the Issue

Flag ONLY actual event handler registrations for these THREE forbidden events (case-sensitive):

- `rejectionhandled`
- `securitypolicyviolation`
- `unhandledrejection`

Include all contexts: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences.

#### How to report the Issue

**RuleId: lws-002**
**level: error**
**message: Usage of forbidden document event handler ({eventName}) exposes sensitive information**

---

### Document.open

#### How to Find the Issue

Flag `document.open` based on argument count:

- `document.open()` with 0 args: **BLOCKED** - Clears document (security risk)
- `document.open(url)` with 1 arg: **BLOCKED** - Opens in same window (navigation hijacking)
- `document.open(url, name)` with 2 args: **BLOCKED** - Opens with target in same window (security risk)
- `document.open(url, name, features)` with 3+ args: **ALLOWED**

Include indirect access patterns: bracket notation (`document['open']`), destructuring (`const {open} = document`), and variable references in all contexts.

#### How to report the Issue

**RuleId: lws-003**
**level: error**
**message: Usage of document.open with {argCount} arguments is a security risk**

---

### Document.write/writeln

#### How to Find the Issue

Flag ALL uses of `document.write()` and `document.writeln()`:

- **document.write()**: ALL uses - allows HTML injection enabling XSS attacks
- **document.writeln()**: ALL uses - identical to document.write with newline
- **Indirect calls**: Bracket notation (`document['write']`), destructuring (`const {write} = document`), aliasing
- **All contexts**: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences and Reflection APIs

#### How to report the Issue

**RuleId: lws-004**
**level: error**
**message: Usage of document.write/writeln enables XSS attacks and violates LWS security policies**

---

### Eval and Dynamic Code Execution

#### How to Find the Issue

Flag these patterns:

- **eval**: ANY usage - code sent to JavaScript eval function is unsafe
- **Function** / **new Function**: ANY usage - code evaluated via string argument is unsafe
- **setInterval** / **setTimeout**: ONLY with string arguments (function arguments are safe)

#### How to report the Issue

**RuleId: lws-005**
**level: error**
**message: Usage of {functionName} enables arbitrary code execution**

---

### Event Properties

#### How to Find the Issue

Flag ALL usage of:

- `event.originalTarget`
- `event.explicitOriginalTarget`
- `Event.prototype.originalTarget`
- `Event.prototype.explicitOriginalTarget`

These properties bypass Lightning Web Security's shadow DOM isolation and expose elements outside the component's security boundary.

#### How to report the Issue

**RuleId: lws-006**
**level: error**
**message: Access to {propertyName} bypasses shadow DOM isolation**

---

### Fullscreen API

#### How to Find the Issue

Flag ALL usage of:

- `requestFullscreen()` - Standard method
- `webkitRequestFullscreen()` - WebKit prefix
- `mozRequestFullScreen()` - Mozilla prefix (note capital 'S' in 'Screen')
- `msRequestFullscreen()` - Microsoft prefix
- String property access containing 'fullscreen' or 'screen'
- All browser-prefixed versions and all access patterns (direct, dynamic, stored references)

#### How to report the Issue

**RuleId: lws-007**
**level: error**
**message: Fullscreen API usage can be exploited for phishing attacks**

---

### Global Object Property Assignment

#### How to Find the Issue

**CRITICAL PREREQUISITE**: Only analyze files that import from 'lwc'. If no 'lwc' import exists, return empty list. If a file has NO import statements at all, skip it entirely.

Flag property assignments to: `globalThis`, `window`, `window.top`, `window.parent`, `window.frames`, `document.defaultView`, `self`, or `this` (in global scope).

**Examples to Flag**:

- `globalThis.myVar = 'hello'`
- `window.config = { debug: true }`
- `window.top.config = { debug: true }`
- `self.data = []`
- `document.defaultView.property = value`

**Do NOT Flag**:

- Property reads: `const x = window.location`
- Local scope assignments: `function foo(window) { window.local = 1 }`
- Method calls: `window.alert('hello')`
- Document properties: `document.cookie = 'foo=bar'` (document is not in the flagged list)

#### How to report the Issue

**RuleId: lws-008**
**level: error**
**message: Direct property assignment to global object {objectName} pollutes global namespace**

---

### HTML Body Element Events

#### How to Find the Issue

Flag document.body event handler usage that creates security vulnerabilities:

- `document.body.addEventListener(...)` and `document.body.oneventname = ...` assignments
- Destructured references: `const { body } = document;` then `body.addEventListener` or `body.oneventname`
- Bracket notation: `document.body['on' + var]` or `body[eventName]`
- Unicode escapes: `document.body['\u006f\u006e...']`
- Reflect patterns: `Reflect.set(document.body, 'onevent', ...)` or `Reflect.apply(document.body.addEventListener, ...)`
- String concatenation for event names

Flag only the actual handler assignment line, not intermediate variable construction. Report ALL occurrences case-sensitively.

#### How to report the Issue

**RuleId: lws-009**
**level: error**
**message: document.body event handler usage leaks sensitive information**

---

### Nonce Access

#### How to Find the Issue

Flag ALL nonce access on HTMLElement/SVGElement objects. Nonce access enables CSP bypass attacks.

**What to Look For**:

- **Direct access**: `element.nonce`, `element['nonce']`
- **getAttribute methods**: `.getAttribute('nonce')`, `.getAttributeNode('nonce')`
- **Selectors**: `querySelector('[nonce]')`, `querySelectorAll('script[nonce]')`
- **Variable-based**: `element[prop]`, `getAttribute(attrName)`, string concat/templates
- **Storage**: `localStorage/sessionStorage.setItem()` with nonce values
- **Setting**: `element.nonce = value`, `setAttribute('nonce', value)`
- **Loops**: `forEach`, `map`, `for...of` accessing nonce
- **Destructuring**: `const { nonce } = element`
- **Conditionals**: `if (element.nonce)`, `element.nonce || default`

#### How to report the Issue

**RuleId: lws-010**
**level: error**
**message: Nonce access enables CSP bypass attacks**

---

### UIEvent Range Parent

#### How to Find the Issue

Flag ANY access to `rangeParent` property from event objects including:

- Direct access: `event.rangeParent`
- Chained access: `event.target.rangeParent`
- Destructuring, obfuscated patterns using unicode escapes, bracket notation, or Reflect APIs

#### How to report the Issue

**RuleId: lws-011**
**level: error**
**message: Access to rangeParent property is forbidden**

---

### XSLT Processor

#### How to Find the Issue

Flag ALL usage of:

- `new XSLTProcessor()` - direct instantiation
- `window.XSLTProcessor` or `const P = XSLTProcessor` - indirect references
- `Reflect.construct(XSLTProcessor, [])` - reflection-based instantiation
- `transformToFragment()` and `transformToDocument()` - transformation methods
- `processor['transformToFragment']` - bracket notation
- `Reflect.apply()`, `.apply()`, `.call()`, `.bind()` - reflection-based method calls

XSLT transformations can generate `<script>` tags, event handlers, and bypass CSP. There is NO safe usage.

#### How to report the Issue

**RuleId: lws-012**
**level: error**
**message: XSLTProcessor usage enables XSS attacks and CSP bypass**

---

### Context Vulnerability

#### How to Find the Issue

Flag security vulnerabilities where **imported framework classes** are exploited through context manipulation.

**CRITICAL**: Imported modules expose framework internals. Static resources via loadScript() are safe.

**Patterns to Flag**:

1. **Method Context Manipulation**: `.call()`, `.apply()`, `.bind()`, `Reflect.apply()` on imported methods with external context

2. **Crafted Fake Context**: Objects mimicking framework structures passed to framework methods

3. **Component Extension**: Extending imported framework components to access inherited internals

4. **Prototype Manipulation**: `__lookupSetter__()`, `__lookupGetter__()`, `Object.getPrototypeOf()`, `Object.setPrototypeOf()`

5. **Internal Property Access**: `.helper`, `.context`, `.owner`, `.navService` on DOM elements/components

6. **Hierarchy Traversal**: `getOwner()`, `getContext()` calls or loops traversing object hierarchies

7. **Dynamic Creation with Exploited Context**: Using stolen contexts for component creation

8. **Complex Invocation Chains**: `Function.prototype.call.apply()` or `Function.prototype.apply.call()`

9. **All contexts**: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences

**What to Ignore**:

- Standard LWC lifecycle methods
- Event handlers with proper this binding within same component
- Built-in JavaScript methods without external context manipulation
- Code loaded via loadScript() from static resources

#### How to report the Issue

**RuleId: lws-013**
**level: error**
**message: Context manipulation attack on imported framework class**

---

### Document.execCommand

#### How to Find the Issue

Flag `document.execCommand` with ONLY these dangerous commands:

- **insertHTML** - Enables HTML injection and XSS attacks
- **selectAll** - Can expose sensitive content via clipboard manipulation

**Detection Patterns**:

- Direct calls: `document.execCommand('insertHTML', ...)`
- Variables: `document.execCommand(cmdVar, ...)` where cmdVar could be dangerous
- String concatenation: `'insert' + 'HTML'`
- Bracket notation: `document['execCommand']('selectAll')`
- Unicode escape sequences

Do NOT flag safe commands (copy, cut, paste, bold, italic, underline, undo, redo).

#### How to report the Issue

**RuleId: lws-014**
**level: error**
**message: document.execCommand with {commandName} enables HTML injection or unauthorized data access**

---

### Insecure HTML Injection (DOM Sinks)

#### How to Find the Issue

Flag insecure HTML injection patterns through DOM sinks on any element, shadowRoot, or document objects:

**What to Look For**:

- **innerHTML assignments**: Direct assignment of untrusted content to innerHTML
- **outerHTML assignments**: Direct assignment of untrusted content to outerHTML
- **insertAdjacentHTML calls**: Using insertAdjacentHTML with untrusted content
- **setHTML/setHTMLUnsafe calls**: Using these methods with untrusted content
- **Dangerous content patterns**:
  - Strings containing iframe elements with srcdoc attributes
  - Strings containing script elements
  - Dynamic HTML construction from variables
- **textContent with HTML**: Setting textContent to content that contains HTML markup
- **Any pattern where user input or external data is directly inserted into DOM sinks without proper sanitization**

**What to Ignore**:

- Safe DOM methods like createElement, appendChild, removeChild
- Proper use of textContent with plain text (no HTML)
- LWC template rendering and data binding
- Standard Lightning component usage

#### How to report the Issue

**RuleId: lws-015**
**level: error**
**message: Insecure HTML injection through {sinkName} enables XSS attacks**

---

### Map and Set Misuse

#### How to Find the Issue

Flag Map and Set misuse patterns:

**Direct Property Access/Assignment (CRITICAL)**:

- Using bracket notation: `map[key]` or `set[index]`
- Assigning with brackets: `map[key] = value` or `set[index] = value`

**Serialization Issues**:

- Using `JSON.stringify()` on Map or Set directly
- Passing Map/Set in decorators (e.g., `@wire`, `@track`)
- Sending Map/Set in event payloads or to child components

**Prototype Modification (CRITICAL)**:

- Adding properties to `Map.prototype` or `Set.prototype`

**What to Ignore**: DOM API usage, code unrelated to Map/Set misuse.

#### How to report the Issue

**RuleId: lws-016**
**level: error**
**message: Improper Map/Set usage bypasses internal data structures**

---

### Mutating Unknown Objects

#### How to Find the Issue

Flag mutations to objects not owned by the component:

**What to Flag**:

- **Event object mutations**: `event.detail.value = 'x'`, `event.target.customProp = true`
- **Parameter mutations**: `processConfig(config) { config.newProp = 'value'; }`
- **API response mutations**: `wireData.processed = true`, `response.items.customField = 123`
- **Mutations to properties received via @api**: `this.recordData.processed = true` where recordData is from @api
- **Non-standard properties on DOM elements**: `element.customProp = 123` (use dataset API instead)
- **Tracked property mutations**: Mutating wire data or external objects after storing in @track
- **Prototype/Host Object mutations**: `Array.prototype.custom = fn`, `document.foo = 'x'`
- **Mutations to objects from inherited methods**: Methods not defined in this component

**What to Ignore**:

- Objects created and owned by this component (not received from external sources)
- Standard DOM operations (createElement, appendChild, querySelector, innerHTML, textContent, classList)
- Standard event handling (addEventListener, removeEventListener)
- Mutations to cloned/copied objects (`const local = { ...external }; local.prop = 'x';`)

#### How to report the Issue

**RuleId: lws-017**
**level: error**
**message: Mutation of object not owned by component**

---

### Trusted Type Policy Names

#### How to Find the Issue

Flag `trustedTypes.createPolicy()` with these forbidden names:

- `'default'`
- `''` (empty string)
- `'lwsInternal'`
- `'trusted'`

Include string literals, variables, string concatenation, computed via unicode escapes, or accessed via Reflect APIs. Ignore policy content (second argument).

#### How to report the Issue

**RuleId: lws-018**
**level: error**
**message: Forbidden Trusted Type policy name '{policyName}' used**

---

### URL.createObjectURL with Restricted MIME Types

#### How to Find the Issue

Flag `URL.createObjectURL()` with restricted MIME types:

**Critical (Blocked)**:

- `text/javascript`
- Empty or undefined MIME types

**Warning (Must Be Scanned)**:

- `text/html` - Must be scanned for malicious content (script tags, XSS)
- `image/svg+xml` - Can contain embedded JavaScript
- `text/xml` - Must be scanned for malicious payloads

Trace back to Blob/File creation to extract MIME type. Include variable-based types, string concatenation, and template literals.

**Safe MIME Types** (don't flag): `image/*`, `video/*`, `audio/*`, `application/pdf`

**Detect Obfuscation**: `'text/' + 'javascript'`, template literals, conditional assignments

#### How to report the Issue

**RuleId: lws-019a**
**level: error**
**message: URL.createObjectURL with blocked MIME type '{mimeType}'**

**RuleId: lws-019b**
**level: warning**
**message: URL.createObjectURL with MIME type '{mimeType}' requires content scanning**

---

### URL Schemes

#### How to Find the Issue

Only `http`, `https`, and `about:blank` are allowed. Flag all disallowed schemes:

**Disallowed Schemes**:

- **Code Execution**: `javascript:`, `vbscript:` - Code execution, XSS attacks
- **CSP Bypass**: `data:`, `blob:` - Bypasses CSP, executable content
- **File System**: `file:` - File system access
- **Insecure Protocols**: `ftp:`, `ws:` - Insecure protocols
- **Potentially Exploitable**: `tel:`, `mailto:`
- **Custom Schemes**: Any non-standard URI schemes

**Where to Check**: HTML attributes (href, src, action), JavaScript strings/template literals, URL constructors, window.location/open, element.setAttribute, fetch/XHR URLs.

**Important**:

- Case insensitive detection (JavaScript:, JAVASCRIPT:)
- Watch for obfuscated schemes (`'java' + 'script:'`)
- `about:blank` ONLY allowed as exact literal, not with additional content

#### How to report the Issue

**RuleId: lws-020**
**level: error**
**message: Disallowed URL scheme '{scheme}' detected**

---

### SVG Animate Element Attributes

#### How to Find the Issue

Flag SVGAnimateElement's `to`, `from`, and `values` attributes containing URL values (`url(...)`).

**What to Flag**:

- `setAttribute('to', ...)` or `setAttribute('from', ...)` or `setAttribute('values', ...)` where the value contains `url(...)`
- Variable or template literal values that resolve to strings containing `url(...)`

**Critical Rules**:

1. **ONLY flag SVGAnimateElement**: The element must be created with `createElementNS('http://www.w3.org/2000/svg', 'animate')`
2. **ONLY these 3 attributes**: `to`, `from`, `values` - ignore all other attributes
3. **URL pattern required**: The attribute value must contain `url(...)` pattern
4. **Empty array if none found**: Return [] if no matches

**Note**: Informational only - LWS automatically sanitizes these URL values.

#### How to report the Issue

**RuleId: lws-021**
**level: warning**
**message: SVGAnimateElement attribute '{attributeName}' contains URL value (auto-sanitized by LWS)**

---

### Script Elements

#### How to Find the Issue

Flag direct script element creation and manipulation that could enable XSS attacks or CSP bypasses:

**What to Look For**:

- `document.createElement('script')` or `new HTMLScriptElement()`
- Script injection via innerHTML/outerHTML/insertAdjacentHTML
- Setting script.src to dynamic/untrusted URLs, blob URLs, or data URLs
- Setting script.textContent, script.text, or script.innerHTML with code
- All contexts: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences

#### How to report the Issue

**RuleId: lws-022**
**level: error**
**message: Direct script element creation or manipulation enables XSS attacks**

---

### Iframe Security

#### How to Find the Issue

Flag insecure iframe usage that leads to XSS or mXSS attacks:

**BLOCKED - srcdoc Attribute**:

- All srcdoc usage is blocked (bypasses CSP)
- `element.innerHTML = '<iframe srcdoc="..."></iframe>'`
- `iframe.setAttribute('srcdoc', '<html>...</html>')`

**BLOCKED - Dangerous src Protocols** (only http/https allowed):

- `javascript:` - `iframe.src = 'javascript:alert(1)'`
- `data:` - `iframe.src = 'data:text/html,<script>alert(1)</script>'`
- `blob:` - `iframe.src = URL.createObjectURL(blob)`
- `vbscript:` - `iframe.src = 'vbscript:msgbox(1)'`
- `file:` - `iframe.src = 'file:///etc/passwd'`

**BLOCKED - mXSS Attacks**:

- MathML/SVG/CDATA contexts combined with iframe srcdoc
- `math.setHTMLUnsafe('<style><!--</style><img src="--><mi><iframe srcdoc=\'...\'></iframe>"/>')`
- `div.innerHTML = '<svg><desc><iframe srcdoc=\'<script>...</script>\'></iframe></desc></svg>'`

**BLOCKED - Obfuscated Protocols**:

- Unicode escapes: `iframe.src = '\u006a\u0061\u0076\u0061\u0073\u0063\u0072\u0069\u0070\u0074:alert(1)'`
- String concatenation: `iframe.src = ('java' + 'script:') + 'alert(1)'`

**ALLOWED**: Only http/https protocols

- `iframe.src = 'https://trusted-domain.com/content'`
- `div.innerHTML = '<iframe src="https://example.com"></iframe>'`

#### How to report the Issue

**RuleId: lws-023a**
**level: error**
**message: iframe srcdoc attribute usage bypasses CSP**

**RuleId: lws-023b**
**level: error**
**message: iframe src with disallowed protocol '{protocol}'**

---
