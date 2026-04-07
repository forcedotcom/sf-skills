<!-- Parent: adlc-author/SKILL.md -->

# Feature Validity by Context

> **Key distinction**: Many action metadata properties are valid on **action definitions with targets** (`flow://`, `apex://`) but NOT on **utility actions** (`@utils.transition`).

| Feature | On `@utils.transition` | On action definitions with `target:` | Notes |
|---------|------------------------|---------------------------------------|-------|
| `label:` on topics | ❌ | ✅ | Valid on topic blocks |
| `label:` on actions | ❌ | ✅ | Valid on Level 1 action definitions |
| `label:` on I/O fields | ❌ | ✅ | Valid on inputs/outputs |
| `require_user_confirmation:` | ❌ | ✅ | Compiles; runtime no-op |
| `include_in_progress_indicator:` | ❌ | ✅ | Shows spinner during action execution |
| `progress_indicator_message:` | ❌ | ✅ | Works on both `flow://` and `apex://` |
| `output_instructions:` | ❌ | ❓ Untested | Not tested on target-backed actions |
| `always_expect_input:` | ❌ | ❌ | NOT implemented anywhere |

**What works on `@utils.transition` actions:**
```yaml
actions:
   go_next: @utils.transition to @topic.next
      description: "Navigate to next topic"   # ✅ ONLY description works
```

**What works on action definitions with `target:`:**
```yaml
actions:
   process_order:
      label: "Process Order"                            # ✅ Display label
      description: "Process the customer's order"       # ✅ LLM description
      require_user_confirmation: True                   # ✅ Compiles (runtime issue)
      include_in_progress_indicator: True               # ✅ Shows spinner
      progress_indicator_message: "Processing..."       # ✅ Custom spinner message
      inputs:
         order_id: string
            label: "Order ID"                           # ✅ I/O display label
            description: "The order identifier"
      outputs:
         status: string
            label: "Order Status"                       # ✅ I/O display label
            description: "Current order status"
      target: "apex://OrderProcessor"
```