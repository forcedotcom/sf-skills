# Output Templates — service-catalog-template-coordinate

Emit these text blocks at the corresponding step in the workflow. Load this file before rendering the
menu so the rendered table and the `AskUserQuestion` options never diverge.

## Operations menu (Behavior step 3)

Emit this menu — paired with a single-select `AskUserQuestion` whose options mirror the rows — only when
the user's intent is ambiguous (they have not named an operation, a specific template, or a target). When
intent is already clear, route directly per Behavior step 2 and do not show the menu.

The menu lists the four **entry** operations. **Activate** and **Place under a catalog category** are not
cold-start rows — they are reached by direct routing when the user names them ("activate the X process",
"add X to the Y catalog") and are offered as the natural **next step** after a deploy or create. Keeping
the menu at four rows also matches the four-option limit of a single-select `AskUserQuestion`.

```text
Unified Catalog Service Processes (via service-catalog-template-coordinate)

┌───┬───────────────────────────────┬──────────────────────────────────────────────────────┐
│ # │ Operation                     │ What it does                                         │
├───┼───────────────────────────────┼──────────────────────────────────────────────────────┤
│ 1 │ Find a template               │ Browse the Unified Catalog and rank Service Process  │
│   │                               │ templates against your business need (read-only)     │
│ 2 │ Deploy a template             │ Set up a specific template you've already chosen,    │
│   │                               │ resolved by name against the live catalog            │
│ 3 │ Create from scratch           │ Build a new Service Process without a template        │
│ G │ Guided: find → deploy → set live │ Find the best template, deploy the one you pick,   │
│   │                               │ then activate it end to end                          │
└───┴───────────────────────────────┴──────────────────────────────────────────────────────┘

Reply with 1, 2, 3, or G.
```

## Next-step offer (Behavior step 5)

After an operation completes, offer the natural next step in plain language — never as a raw Id:

- after **Find** → "Want me to deploy **<Template Name>**?"
- after **Deploy** → "Deployed. Want me to activate **<Service Process Name>** so it's live?"
- after **Activate** → "**<Service Process Name>** is live. Want me to file it under a catalog category?"
- after **Create from scratch** → offer to activate, then to place under a category.

Stop offering once the user indicates they're done.
