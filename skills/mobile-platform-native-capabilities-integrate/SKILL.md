---
name: mobile-platform-native-capabilities-integrate
description: "Build a Salesforce LWC that uses native mobile device capabilities — barcode scanner, biometrics, location, NFC, calendar, contacts, document scanner, geofencing, AR space capture, app review, and payments. Use this skill when the user asks for an LWC that scans a barcode, captures a photo of a document, reads location or geofences, prompts for biometrics, reads/writes the device calendar or contacts, taps NFC, takes a payment, prompts for an app review, or scans an AR space. Also triggers on \"lightning/mobileCapabilities\", \"mobile capability\", \"Nimbus\", \"device capability\". Do not use for mobile offline / Komaci priming reviews (use `mobile-platform-offline-validate`) or for picking generic Lightning base components (use `design-systems-slds-apply`)."
metadata:
  version: "1.0"
---

# Using Mobile Native Capabilities

The `lightning/mobileCapabilities` module exposes a set of factory functions
that return service objects for native device features (barcode scanning,
biometrics, location, etc.). Each service extends a common
[BaseCapability](references/base-capability.md) with an `isAvailable()`
method, so an LWC can degrade gracefully on surfaces where the capability is
not present (desktop, mobile web).

This skill routes an agent through (1) picking the right capability, (2)
loading the authoritative type definitions, and (3) wiring the service into
an LWC with the correct availability gating, error handling, and
deprecation-aware API choice.

## When to Use This Skill

- User asks for an LWC that uses a device capability listed in the index
  below.
- User mentions `lightning/mobileCapabilities`, "mobile capability", or
  "Nimbus" by name.
- User wants to know which mobile native APIs are available, or which one
  fits their feature.

Do NOT use this skill for:

- Mobile-offline review of an LWC (lwc:if, inline GraphQL, Komaci-priming
  violations) — use `mobile-platform-offline-validate`.
- Choosing or styling generic Lightning Base Components / SLDS blueprints —
  use `design-systems-slds-apply`.

## Prerequisites

- Knowledge that the LWC will run inside a supported mobile container
  (Salesforce Mobile App, Field Service Mobile App). These capabilities are
  unavailable on desktop and mobile web; gate every call behind
  `isAvailable()`.
- Familiarity with the `lightning/mobileCapabilities` module declaration
  (see [mobile-capabilities](references/mobile-capabilities.md)).

## Capability Index

| Capability | Reference | One-line use |
| --- | --- | --- |
| App Review | [App Review](references/app-review.md) | Prompt the user for a native in-app review. |
| AR Space Capture | [AR Space Capture](references/ar-space-capture.md) | Capture a 3D scan of a physical space using AR. |
| Barcode Scanner | [Barcode Scanner](references/barcode-scanner.md) | Read QR / UPC / EAN / Code-128 / etc. from the camera. |
| Biometrics | [Biometrics](references/biometrics.md) | Authenticate via Face ID / fingerprint. |
| Calendar | [Calendar](references/calendar.md) | Read or create events on the device calendar. |
| Contacts | [Contacts](references/contacts.md) | Read or create entries in the device address book. |
| Document Scanner | [Document Scanner](references/document-scanner.md) | Scan paper documents using the camera with edge detection. |
| Geofencing | [Geofencing](references/geofencing.md) | Trigger logic when the device crosses a geographic boundary. |
| Location | [Location](references/location.md) | Read GPS coordinates and watch for updates. |
| NFC | [NFC](references/nfc.md) | Read or write NFC tags. |
| Payments | [Payments](references/payments.md) | Take an Apple Pay / Google Pay payment. |

## Workflow

### Step 1 — Identify the capability

Map the user's feature ask to one row of the capability index. If the ask
spans multiple capabilities (e.g. "scan a barcode and store it on a
contact"), plan for **each** capability separately — there is one factory
function per capability.

### Step 2 — Load the shared and capability-specific references

Read these two shared references **once** per session — they apply to every
capability and are not duplicated in the per-capability files:

- [BaseCapability](references/base-capability.md) — the common interface
  with `isAvailable()` that every service extends.
- [mobile-capabilities](references/mobile-capabilities.md) — the
  `lightning/mobileCapabilities` module declaration showing every
  re-exported service.

Then open the capability's reference file from the table above. Each
per-capability reference contains the service-specific TypeScript API
(factory function, service interface, options types, result types, error
types) and assumes the two shared references above are already in context.

Do not infer the API from memory — read it. The services evolve and some
methods are explicitly `@deprecated` in favor of newer alternatives.

### Step 3 — Wire the service into the LWC

For each capability:

1. Import the factory from `lightning/mobileCapabilities`:
   ```js
   import { getBarcodeScanner } from 'lightning/mobileCapabilities';
   ```
2. Get an instance: `const scanner = getBarcodeScanner();`
3. Gate the call behind `isAvailable()`:
   ```js
   if (!scanner.isAvailable()) {
     // graceful fallback or user message
     return;
   }
   ```
4. Call the **non-deprecated** entry point. Several services keep older
   methods marked `@deprecated` alongside the recommended one — always
   prefer the recommended method in the reference.
5. Wrap the promise in `try/catch` and handle the typed failure codes the
   service exposes (e.g. `BarcodeScannerFailureCode`,
   `LocationServiceFailureCode`). User-cancelled vs. permission-denied vs.
   service-unavailable are distinct UX states.

### Step 4 — Surface failure modes to the user

Each service defines its own failure-code enum. Translate codes into
user-actionable messages: a `USER_DENIED_PERMISSION` should ask the user to
grant permission; a `USER_DISABLED_PERMISSION` must direct them to the OS
settings; a `SERVICE_NOT_ENABLED` should be a developer-visible error, not
shown to the user.

### Step 5 — Stay inside the supported surface

Mobile capabilities are available **only** when the LWC runs inside a
supported Salesforce mobile app. If the same component is rendered on
desktop or mobile web, the factory will still return an object but
`isAvailable()` will return `false`. Never assume availability — gate every
call.


## Examples

### Example — "Scan a barcode and write it into a field"

1. Map to: Barcode Scanner.
2. Read [Barcode Scanner](references/barcode-scanner.md).
3. Use `scan(options)` (not the deprecated `beginCapture` / `resumeCapture`
   / `endCapture` triple).
4. In options, set the `barcodeTypes` to the symbologies needed (default is
   all supported types) and `enableMultiScan: false` for a single read.
5. On resolve, write `result[0].value` to the bound field. On reject,
   inspect `error.code` against `BarcodeScannerFailureCode`.

### Example — "Take an Apple Pay payment for an order total"

1. Map to: Payments.
2. Read [Payments](references/payments.md).
3. Gate on `isAvailable()`.
4. Build the payment request object per the reference.
5. On resolve, surface the transaction id to the calling flow. On reject,
   handle user-cancelled and payment-failed paths separately.


## Verification Checklist

- [ ] Every capability call is preceded by `isAvailable()`.
- [ ] The non-deprecated entry point is used (no `beginCapture` /
      `resumeCapture` / `endCapture` for barcode, etc.).
- [ ] Each rejection path is mapped to the typed failure code enum.
- [ ] Imports come from `lightning/mobileCapabilities`, not from a private
      path.
- [ ] No assumption that the capability runs on desktop or mobile web.


## Troubleshooting

- **`isAvailable()` returns `false` on a real device** — the device is
  running an unsupported app surface (not Salesforce Mobile or Field
  Service Mobile), or the service is gated by an org-level setting. The
  fix is org configuration, not code.
- **TypeScript can't find the import** — confirm the LWC has access to
  `lightning/mobileCapabilities`. The module is declared globally inside
  Salesforce mobile containers; outside that, the types must be installed
  separately.
- **Deprecated barcode methods still work** — yes, but new code must use
  `scan()` and `dismiss()`. Refactor any sample code the agent received
  before returning it.
- **Multiple capabilities in one component** — get separate instances per
  capability (they are independent service objects); do not try to share
  state between them.
