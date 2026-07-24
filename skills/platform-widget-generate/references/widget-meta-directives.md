# Widget Meta Directives Reference

The `meta` object on a UEM block carries runtime directives for iteration (`forEach` / `forItem`) and conditional rendering (`if`). Read this file when a widget needs either.

---

## Iteration with forEach / forItem

`forEach` iterates over an array; the block and ALL its children repeat for each item.

### Rules

- Place `forEach` on the `meta` object of the REPEATING block (e.g. a row or card).
- The value is an expression referencing an array: `{!$attrs.<arrayAttr>}` (or `{!$<outerForItem>.<arrayField>}` for nested loops).
- `forItem` is required alongside `forEach`. It names the variable bound to the current item and must start with `$`.
- Inside the `forEach` block, reach the **current item** through the loop variable (`{!$item.X}`) — not by traversing the array path (`{!$attrs.items.X}`, which does not unfold to the current iteration). Top-level references for values that don't change across iterations (`{!$attrs.<unrelatedField>}`) are still valid.
- `forEach` blocks can be nested — inner loops use their own `forItem` name.

### Example — top-level list

```json
{
  "definition": "namespace/repeatingBlock",
  "meta": { "forEach": "{!$attrs.items}", "forItem": "$item" },
  "children": [
    { "definition": "namespace/childBlock1", "attributes": { "content": "{!$item.id}" } },
    { "definition": "namespace/childBlock2", "attributes": { "content": "{!$item.total}" } }
  ]
}
```

### Example — container holds repeating child

When a container holds repeating items, `forEach` goes on the child — not on the container.

```json
{
  "definition": "namespace/block",
  "children": [
    {
      "definition": "namespace/repeatingBlock",
      "meta": { "forEach": "{!$attrs.items}", "forItem": "$item" },
      "children": [
        { "definition": "namespace/childBlock", "attributes": { "content": "{!$item.name}" } }
      ]
    }
  ]
}
```

### Example — nested loops

The inner `forEach` references an array on the outer loop variable and uses a distinct `forItem` name.

```json
{
  "definition": "namespace/repeatingBlock",
  "meta": { "forEach": "{!$attrs.orders}", "forItem": "$order" },
  "children": [
    { "definition": "namespace/childBlock", "attributes": { "content": "{!$order.id}" } },
    {
      "definition": "namespace/repeatingChildBlock",
      "meta": { "forEach": "{!$order.lineItems}", "forItem": "$line" },
      "children": [
        { "definition": "namespace/childBlock1", "attributes": { "content": "{!$line.name}" } },
        { "definition": "namespace/childBlock2", "attributes": { "content": "{!$line.count}" } }
      ]
    }
  ]
}
```

---

## Conditional rendering with if

`if` conditionally renders a block. When the expression is `false`, the block and all its children are excluded from the rendered output.

### Rules

- Place `if` on the `meta` object of the block.
- Use `if` only when the schema has a `lightning__booleanType` property suited to the condition. Bind directly to that property (or to a loop variable holding such a value). If no suitable boolean exists in the schema, do not use `if` — render the block unconditionally instead.
- Do not lean on the truthiness of strings (`""` vs `"value"`), numbers (`0` vs `1`), or nullable fields — that may render today but is not guaranteed across surfaces. Comparisons, arithmetic, and string operations are not supported.
- `if` may coexist with `forEach` on the same `meta`. `if` is evaluated first — if `false`, the loop is skipped entirely.

### Example — top-level boolean

```json
{
  "definition": "namespace/block",
  "meta": { "if": "{!$attrs.isVerified}" },
  "attributes": { "label": "Verified user" }
}
```

### Example — boolean nested inside a schema object

```json
{
  "definition": "namespace/block",
  "meta": { "if": "{!$attrs.features.showBanner}" },
  "attributes": { "text": "Promo banner" }
}
```

### Example — boolean inside a forEach loop

```json
{
  "definition": "namespace/repeatingBlock",
  "meta": { "forEach": "{!$attrs.tasks}", "forItem": "$task" },
  "children": [
    { "definition": "namespace/block1", "attributes": { "content": "{!$task.title}" } },
    {
      "definition": "namespace/block2",
      "meta": { "if": "{!$task.completed}" },
      "attributes": { "label": "Done" }
    }
  ]
}
```

---

## Gotchas

| Issue | Resolution |
|---|---|
| `if` bound to a non-boolean (string or number) does not behave as expected | Use `if` only when the schema has a `lightning__booleanType` property; otherwise render the block unconditionally |
| Nested loops share the same `forItem` name | Pick distinct names (e.g. `$item` outer, `$line` inner) — there is no validation error on collision |
