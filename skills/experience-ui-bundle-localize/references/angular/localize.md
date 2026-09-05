# Angular reference — Localize an Angular UI Bundle

Framework-specific companion to `SKILL.md` for the **Angular** path. `SKILL.md` owns the
neutral workflow + guardrail spine (Step 0 routing, preconditions, the five steps, and the
guardrails); this file owns everything Angular/ngx-translate-specific: the runtime library, the
call convention, the wiring shape, and the framework depth doc. The shared engine and the
framework-neutral depth docs live in [`../common/`](../common/).

## Library & call convention

An Angular UI Bundle can't use `@salesforce/label/*` the way LWC does — those imports resolve at
compile time inside the platform's compiler, which your standalone Angular bundle doesn't go
through. Instead the app **fetches labels at runtime** through the Salesforce GraphQL UI API and
hands them to **[ngx-translate](https://ngx-translate.org/)** (`@ngx-translate/core`) to render.

The engine that does the fetching is the same one React uses — see
[`../common/platform-sdk-i18n.md`](../common/platform-sdk-i18n.md). What's Angular-specific is
that ngx-translate loads translations through a **`TranslateLoader`**, so instead of React's
shipped `SalesforceBackend` you write a small custom loader that issues the same
`uiapi.platform.labels` GraphQL query.

```html
<!-- template: pipe form (most common) -->
<h1>{{ 'Welcome_Text' | translate }}</h1>

<!-- template: directive form -->
<h1 [translate]="'Welcome_Text'"></h1>
```

```typescript
// component/service: imperative form
constructor(private translate: TranslateService) {}
label = this.translate.instant("Welcome_Text");   // sync (translations already loaded)
this.translate.get("Welcome_Text").subscribe(v => …);  // async Observable
```

- **Call sites:** the `translate` pipe / directive in templates, and
  `TranslateService.instant / get / stream("Key")` in code. The key is the bare `<fullName>`
  (the `c` namespace is the default).
- **Files scanned for user-facing strings / call sites:** `.html` (templates) and `.ts`
  (inline templates + service calls).
- **To use `t`-style translation in a component:** import ngx-translate's `TranslatePipe` (and/or
  `TranslateDirective`) into the standalone component's `imports`, and/or inject
  `TranslateService`.

## Step 2 (Extract) — Angular specifics

Replace the template literal with the `translate` pipe and import `TranslatePipe` into the
component's `imports` array:

```html
<!-- Before: <h1>Welcome</h1> -->
<!-- After:  <h1>{{ 'Welcome_Text' | translate }}</h1> -->
```

```typescript
import { TranslatePipe } from "@ngx-translate/core";

@Component({
  selector: "app-welcome",
  standalone: true,
  imports: [TranslatePipe],   // ← add
  templateUrl: "./welcome.html",
})
export class Welcome {}
```

For strings built in TypeScript (dynamic messages, `aria-label` bindings), inject
`TranslateService` and call `instant(...)` / `get(...)`.

## Step 4 (Wire) — Angular specifics

Install ngx-translate (tell the user to run, from the UI bundle dir — pick a `@ngx-translate/core`
release compatible with the bundle's Angular version; the standalone `provideTranslateService`
API is v16+):

```bash
npm install @ngx-translate/core
```

Then scaffold the two files — the custom `SalesforceTranslateLoader` (`src/i18n/salesforce-translate-loader.ts`)
and the label manifest (`src/i18n/label-manifest.ts`) — register the loader via
`provideTranslateService(...)` in `src/app/app.config.ts`, and at boot fetch the i18n context and
call `TranslateService.use(lang)` before the app renders. Full loader code and the B2E vs B2C
configuration are in [i18n-setup.md](./i18n-setup.md).

## Scripts

Run them from the UI bundle dir (they scan `src/` relative to the current directory). The first
three are framework-neutral and live in the skill's shared `scripts/` folder; `check-i18n-wired.sh`
is Angular-specific (ngx-translate `provideTranslateService` / `TranslateLoader` detection) and
ships here in the Angular reference folder.

| Script | Purpose |
|--------|---------|
| [`check-org-api-version.sh`](../../scripts/check-org-api-version.sh) | Precondition 4 — org supports API v68.0+ |
| [`detect-bundle-type.sh`](../../scripts/detect-bundle-type.sh) | Precondition 5 — classify B2E / B2C / internal |
| [`check-manifest-registered.sh --framework angular`](../../scripts/check-manifest-registered.sh) | Step 3 — every `translate` key is registered in the manifest (`--framework angular` selects the `.html` pipe/directive + `.ts` service-call grammar) |
| [`check-i18n-wired.sh`](./check-i18n-wired.sh) | Step 4 — the loader + `provideTranslateService` are wired, called at boot, and the manifest reaches the loader |

## Depth docs

Framework-neutral (shared with React), in [`../common/`](../common/):
- [platform-sdk-i18n.md](../common/platform-sdk-i18n.md) — the shared runtime engine: the Labels GraphQL query, `fetchI18nContext`, the manifest format, batching, and fallback
- [label-xml.md](../common/label-xml.md) — Custom Labels and translation metadata XML shapes; the `namespace:Key` rules
- [verifying.md](../common/verifying.md) — serve URL, locale flip, and verifying labels render
- [gotchas.md](../common/gotchas.md) — the silent-fail traps: unregistered manifest keys, API-version bake-in, stale label cache

Angular-specific (this folder):
- [i18n-setup.md](./i18n-setup.md) — the two files you write: the custom `TranslateLoader` + the label manifest
- [interpolation.md](./interpolation.md) — positional `{0}/{1}` placeholder interpolation with ngx-translate
