---
name: experience-lwc-typescript-migrate
description: "Use when converting an existing JavaScript Lightning Web Component (.js, .html, .css) to TypeScript with full type annotations and a matching `.d.ts` file that exposes only the component's `@api` surface. TRIGGER when the user says \"convert LWC to TypeScript\", \"migrate LWC to TS\", \"rename .js to .ts for this component\", \"add types to my LWC\", \"generate .d.ts for this LWC\", \"type-annotate @api properties\", or \"produce declare module 'c/componentName' definitions\". DO NOT TRIGGER when the user is authoring a brand-new LWC from scratch (use experience-lwc-generate), generating Jest tests for an existing LWC (use experience-lwc-generate), or migrating an Aura component to LWC."
metadata:
  version: "1.0"
  relatedSkills:
    - "experience-lwc-generate"
  cliTools:
    - tool: ["git"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["tsc"]
      semver: ">=4.0.0"
---
<!-- adk-managed-skill -->
# Converting LWC to TypeScript

Convert a Lightning Web Component bundle from JavaScript to TypeScript. The
deliverable is a fully-typed `.ts` implementation **plus** a `.d.ts` file
that only exposes `@api` members (the public surface other LWCs consume).

## When to Use This Skill

- User wants to migrate a single component or a folder of components from
  `.js` to `.ts`.
- User needs a `.d.ts` for an existing LWC so other components (or an
  external TypeScript host) can import it safely.
- User is adding type annotations to an already-renamed `.ts` LWC that
  hasn't been properly typed yet.
- User wants JSDoc-style type hints upgraded to real TypeScript types.

## Prerequisites

- The component builds and runs correctly in JavaScript today.
- `git` is available (the rename must preserve history via `git mv`).
- A TypeScript compiler is wired into the build (either the SFDX TS
  pipeline or a standalone `tsc` step).

---

## Workflow

### Step 1 — Read the component

Open every file in the bundle:

```text
componentName/
├── componentName.js
├── componentName.html
├── componentName.css
└── (possibly) __tests__/, __utam__/, existing .d.ts
```

Understand:

- What extends `LightningElement`? What is the class name?
- Which fields and methods carry the `@api` decorator?
- Which properties/methods have existing JSDoc (use as a type hint
  starting point, but validate against actual usage — JSDoc lies).
- Which parameters / return types can you infer from how the code is
  called internally?

### Step 2 — Rename `.js` → `.ts` using `git mv`

```bash
git mv componentName/componentName.js componentName/componentName.ts
```

Repeat for any helper `.js` files in the bundle (unless they're already
`.ts`). **Never** plain `mv` — that loses the history link TypeScript
reviewers rely on.

### Step 3 — Add type annotations in the `.ts`

Apply types in this priority order so you stop as soon as the public
contract is solid:

1. **`@api` properties and methods first.** Generate JSDoc if it's
   missing, then translate JSDoc types to TS syntax (`string`, `number`,
   `boolean`, `Promise<T>`). Validate each JSDoc claim against the code
   before trusting it.
2. **Complex shapes become `interface` or `type` aliases** — not inline
   shapes repeated everywhere.
3. **Optional members use `?`** only when the value is genuinely allowed
   to be `undefined`. Do not sprinkle `?` defensively.
4. **Private/internal state** — still type it, but don't export the
   types. Use `private` for members that must never be touched by
   consumers.
5. **Event handlers** — prefer precise DOM event types:
   - `MouseEvent` for `onclick` (and other click-like handlers). `click`
     is dispatched as a `MouseEvent` — including keyboard-activated
     clicks — so typing it as `PointerEvent` would let handlers rely on
     pointer-only fields (`pointerType`, `pressure`, etc.) that are
     undefined in those cases.
   - `PointerEvent` for `onpointerdown` / `onpointerup` / `onpointermove`
     and other `pointer*` handlers where pointer-specific fields are
     actually meaningful.
   - `CustomEvent<{ detail: ... }>` for LWC custom events.
   - `Event` is the last resort; document why when using it.
6. **Async methods** always return `Promise<T>` — never bare `T`.
7. **Avoid `any`.** If you genuinely can't type something, use `unknown`
   and narrow with a type guard.

#### Reference patterns

Load [[assets/type-patterns.ts|assets/type-patterns.ts]] as an inline example
covering property types, method types, and event handler types.

### Step 4 — Generate the `.d.ts`

Create `componentName.d.ts` next to the `.ts`. It must:

- Contain **only `@api` members** — no private state, no internal
  methods, no lifecycle hooks unless they are themselves `@api`.
- Preserve `@api` JSDoc verbatim (including `@type`, `@required`,
  `@default`, `@param`, `@returns` tags) directly above each declaration.
- Declare the LWC module namespace `c/componentName` (or the org's
  namespace if different).

Template: load [[assets/dts-template.ts|assets/dts-template.ts]] as the
starting `.d.ts` shape.

If the component has **no** `@api` members, still produce the module
declaration with a comment explaining there's no public surface — don't
skip the file.

### Step 5 — Compile and test

- Run the TypeScript compiler (`tsc --noEmit` or the build's equivalent).
  Resolve every error before calling it done; no `@ts-ignore` patches.
- Run the component's existing Jest tests. The behavior should be
  identical.
- Run the bundled consumer-finder unconditionally — empty output is a
  valid result, not a reason to skip. The script resolves the search
  paths from `sfdx-project.json`'s `packageDirectories` (or falls back
  to `<project-root>`), rejects any entry that escapes the project root,
  and performs the LWC-import search internally so the invocation is
  fully deterministic:

```bash
"<skill_dir>/scripts/find-consumers.sh" "<project-root>" "<componentName>"
```

  For each match, confirm the consumer's expected types still align with
  the new `.d.ts` public surface.

### Step 6 — Expected final bundle shape

```text
componentName/
├── componentName.ts          # Main TypeScript implementation
├── componentName.html        # Template (unchanged)
├── componentName.css         # Styles (unchanged)
└── componentName.d.ts        # Type definitions (new)
```

---

## Verification Checklist

**Before conversion:**

- [ ] Component is valid JS and all tests pass.
- [ ] You've identified every `@api` member and its intended type.

**After conversion:**

- [ ] `git mv` was used so history is preserved.
- [ ] Every variable and parameter in the `.ts` has a concrete type
      (no implicit `any`).
- [ ] Complex object shapes live in `interface` / `type` aliases, not
      inline repeats.
- [ ] Optional `?` is only on genuinely optional fields.
- [ ] `.d.ts` exists, declares `c/componentName`, extends
      `LightningElement`, includes **only** `@api` members.
- [ ] Every `@api` JSDoc is preserved verbatim in the `.d.ts`.
- [ ] `tsc` passes with zero errors; no `@ts-ignore` or `any` used as a
      workaround.
- [ ] Jest tests still pass.

---

## Common Pitfalls

- **Using `any` to silence errors.** Solve the actual type instead.
  If the value is truly unknown, use `unknown` + a type guard.
- **Including private members in the `.d.ts`.** The `.d.ts` is the
  public contract. Internal lifecycle and helpers must not leak.
- **Losing JSDoc during the rename.** Scan before and after — JSDoc
  comments on `@api` members must appear in both the `.ts` and `.d.ts`.
- **Skipping `git mv`.** Makes review miserable and confuses blame.
- **Forgetting async return types.** `foo()` with an `async` keyword
  always returns a `Promise`. Declare it.
- **Typing `onclick` as `PointerEvent`.** `click` is a `MouseEvent`
  (keyboard-triggered clicks included), so `PointerEvent` fields like
  `pointerType` are undefined for those events. Type `onclick` as
  `MouseEvent`; reserve `PointerEvent` for `onpointer*` handlers. Use
  `MouseEvent | TouchEvent` only when the code branches on `TouchEvent`
  distinctly.

## Support Resources

- [LWC TypeScript docs](https://developer.salesforce.com/docs/platform/lwc/guide/ts.html)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [LWC Developer Guide](https://developer.salesforce.com/docs/component-library/documentation/en/lwc)
