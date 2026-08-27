# Conditional Rendering Compatibility (`lwc:if` → `if:true`/`if:false`)

## Framework for the analysis

The Komaci offline static analysis engine used by Salesforce Mobile App Plus and Field Service Mobile App does not support modern conditional rendering directives (`lwc:if={property}`, `lwc:elseif={property}`, `lwc:else`). These directives must be replaced with `if:true={property}` and `if:false={property}` to ensure compatibility with offline data priming.

Your task:

1. Inspect HTML.
2. Identify any usage of `lwc:if={property}`, `lwc:elseif={property}`, or `lwc:else`.
3. Recommend exactly how to replace them with `if:true` / `if:false` directives, preserving the original branching logic.

**FOCUS:**

- Only analyze and provide feedback on occurrences of `lwc:if={property}`, `lwc:elseif={property}`, and `lwc:else`.
- Ignore any other directives or potential issues unrelated to those three.

## Conversion rules

- **`lwc:if={property}`** → replace with `if:true={property}`.
- **`lwc:elseif={property}`** → typically requires a nested `if:false={previousCondition}` that wraps an `if:true={property}`.
- **`lwc:else`** → has no condition of its own, so it must be wrapped by `if:false={previousCondition}` (the inverse of the relevant condition chain).
- **Standalone `lwc:if`** (not followed by `lwc:elseif`/`lwc:else`) → still must be replaced with `if:true={property}`.
- **Multiple condition chains** → review every template; do not stop at the first occurrence.

## Conversion example

`before.html`:

```html
<template>
  <template lwc:if="{conditionOne}">
    <div>show condition one</div>
  </template>
  <template lwc:elseif="{conditionTwo}">
    <div>show condition two</div>
  </template>
  <template lwc:else>
    <div>show default condition</div>
  </template>
</template>
```

`after.html`:

```html
<template>
  <template if:true="{conditionOne}">
    <div>show condition one</div>
  </template>
  <template if:false="{conditionOne}">
    <template if:true="{conditionTwo}">
      <div>show condition two</div>
    </template>
    <template if:false="{conditionTwo}">
      <div>show default condition</div>
    </template>
  </template>
</template>
```

The proper review feedback for the example above:

- replace `lwc:if={conditionOne}` with `if:true={conditionOne}`
- replace `lwc:elseif={conditionTwo}` with `if:false={conditionOne}`, then create a nested template with `if:true={conditionTwo}` wrapping the remainder of the component
- replace `lwc:else` with `if:false={conditionTwo}`

Rules to follow:

- If no action is required, return an empty list. Do not return null or any other value — return an empty array.
- Keep issues concise; avoid duplicated issues or unnecessary analysis for things that are not real violations.
- Stick to the instructions for the specific reviewer in scope. Issues outside that scope will be analyzed by other reviewers.
- For each violation, provide:
  - The exact violation type as defined by the reviewer in scope.
  - A description of why it is a problem in the context of mobile offline priming.
  - An intent analysis explaining what the developer likely intended.
  - A suggested action with concrete code-level remediation.
- Do not make assumptions about other components that may be referenced.
