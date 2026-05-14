<!-- Parent: modeling-omnistudio-epc-catalog/SKILL.md -->

# CME EPC Naming Conventions

Use deterministic naming across products, attributes, and offer bundles. Names should remain stable across environments and releases.

## Product Name

Format:

```text
<Business Domain> <Tier/Variant> (<Channel or Variant Tag>)
```

Examples:

- `Business Internet Essential (VPL)`
- `Business Internet Premium (FTTC)`

## Product Code

Format:

```text
<PREFIX>_<ENTITY>_<DOMAIN>_<VARIANT>
```

Examples:

- `VEPC_OFFERING_BUSINESS_INTERNET_ESSENTIAL`
- `VEPC_SPEC_BUSINESS_ROUTER_ADVANCED`

Rules:

- Uppercase with underscores only
- No environment suffixes (`_DEV`, `_UAT`, `_PROD`)
- Stable after go-live

## Attribute Code

Format:

```text
VEPC_ATTR_<DOMAIN>_<ATTRIBUTE_NAME>
```

Examples:

- `VEPC_ATTR_DOWNLOAD_SPEED`
- `VEPC_ATTR_CONTRACT_TERM`

## Attribute Category Code

Format:

```text
VEPC_ATTRIBUTE_CATEGORY_<DOMAIN_BLOCK>
```

Examples:

- `VEPC_ATTRIBUTE_CATEGORY_INTERNET_DETAILS`
- `VEPC_ATTRIBUTE_CATEGORY_CONTRACT_DETAILS`

## Offer Bundle Composition

When naming bundles and child items:

- Bundle parent `ProductCode` should indicate offering intent (`VEPC_OFFERING_*`)
- Child product codes should represent reusable specs (`VEPC_SPEC_*` recommended)
- Sequence values (`SeqNumber`, `ChildLineNumber`) should be unique per parent and spaced for future inserts

## Anti-Patterns

| Bad pattern | Why to avoid |
|---|---|
| `Product1`, `Offer_New`, `CatalogItemA` | Non-descriptive and unstable |
| Mixed abbreviations without glossary | Hard to maintain and search |
| Date/version in `ProductCode` | Breaks long-term references |
| Same `ProductCode` in multiple products | Downstream ambiguity |
