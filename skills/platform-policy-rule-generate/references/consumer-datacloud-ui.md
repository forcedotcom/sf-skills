# DATACLOUD Consumer: Data Governance UI

In normal author mode, `consumer=DATACLOUD` selects the Data Governance UI-renderability candidate contract. The policy must be representable by the Data Governance Policy Builder and must not rely on the UI silently dropping or rewriting unsupported content. The consumer value alone is not proof of UI validation.

Explicit evidence-recreation mode is the narrow exception. When the request names one of this skill's retrieved API 69.0 examples and asks for exact recreation, preserve that example's exact conjunction and persisted scalar-expression shape even when it is not accepted by the normal author-mode compiler. Do not describe the recreated policy as UI validated; MDAPI retrieval, dry run, deploy, or persistence cannot establish that claim.

## UI Conjunction and Section Grouping

The UI reconstructs policy sections through a custom-conjunction API/UI projection. `whenClauseConjunction=Custom` and `whenClauseCustomConjunction` are API/UI concepts, not XML elements or MDAPI enum values. The generated package still emits ordinary MDAPI XML: serialize the typed plan into a nested `<conjunctionExpression>` using `AND`/`OR` groups. Do not invent a `CUSTOM` XML wrapper or put condition indexes directly in the top-level expression.

- `DATA_SPACE`: `DATASPACE` or `SESSION_DATASPACE`.
- `TAG_CLASSIFICATION`: `TAG` or `CLASSIFICATION`.
- `PERMISSION`: `ASSIGNED_PERMISSIONS_PATH` for permission membership, and `SCALAR_ATTRIBUTE` (with a `SOQLTARGETLISTEXPR` `principalExpression`) for a supported principal-attribute comparison. Both are confirmed deployable; `SCALAR_ATTRIBUTE` is UI-renderable per DG UI source (this is how the builder itself authors the condition), not by a per-shape round-trip. Group them together in the `PERMISSION` section.
- `ENTITY_TYPE`: `ENTITYTYPE`.
- `RECORD_FIELD`: `RECORDFIELD` or `EXPRESSION`.

Build conditions first, classify them, build each local group with its requested `AND`/`OR`, then build the top-level custom `AND`. Serialize that plan to the MDAPI `conjunctionExpression`. Every condition identifier must appear exactly once, no group may be empty, and no bare condition may be used where the UI expects a group. RLS join `whereClauseConjunction` uses a separate nested index namespace. Validate the API/UI projection separately; MDAPI persistence alone does not prove UI behavior.

The grouping contract is:

| Section group | Conditions kept together | Local grouping |
|---|---|---|
| `DATA_SPACE` | Dataspace and session-dataspace conditions | `AND` or `OR` as required by the policy |
| `TAG_CLASSIFICATION` | Tag and classification conditions | `OR` for alternatives, `AND` for cumulative requirements |
| `PERMISSION` | Assigned-permission and supported principal-attribute conditions | `AND` or `OR` as required by the policy |
| `ENTITY_TYPE` | Object/field entity-type discriminator conditions | `OR` for object-versus-field alternatives |
| `RECORD_FIELD` | Direct record-field and RLS join-expression conditions | `AND` for cumulative RLS criteria |

Examples:

```text
Two alternative classifications + one required permission:
Custom conjunction API/UI object:
CUSTOM(AND,
  TAG_CLASSIFICATION(OR, 1, 2),
  PERMISSION(AND, 3))

The corresponding MDAPI XML expression is:
(AND (OR 1 2) (AND 3))
```

For an object-level TupleRead policy with two entity-type alternatives, two alternative classifications, and one permission gate:

```text
(AND (OR 1 2) (OR 3 4) (AND 5))
```

For a field-level (FLS) deny with alternative tags and a permission exemption, the single `FIELD` entity-type condition is persisted bare and every other section is grouped:

```text
(AND 1 (OR 2 3 4) (AND 5))
```

Here `1` is `ENTITYTYPE IS FIELD` (the only condition that may stay bare, as in `examples/FieldReadDeny`), `(OR 2 3 4)` is `TAG_CLASSIFICATION`, and `(AND 5)` is `PERMISSION`. A bare `5` is the common mistake: it persists but Policy Builder cannot open the rule.

In the OLS example above, `(OR 1 2)` is the `ENTITY_TYPE` group, `(OR 3 4)` is the `TAG_CLASSIFICATION` group, and `(AND 5)` is the `PERMISSION` group. If the policy is RLS, its direct field or `EXPRESSION` conditions form the `RECORD_FIELD` group instead of being mixed into the tag or permission group. The numbers are assigned only after final condition ordering.

## Shape Restrictions

- One rule per set.
- One action only; use only UI-supported `Read` or `TupleRead` combinations.
- At most one resource domain; the UI consumes only the first domain.
- Use only UI-supported categories, effects, scopes, and transforms.
- Do not emit `UNLESS` conditions or an `UNLESS` conjunction.
- Do not emit a plain `AND`/`OR` conjunction in place of the custom conjunction.
- Never author `PLACEHOLDER`; its recognition by the UI reader does not make it an authoring construct.

## Principal Attributes

Reject `PLURAL_ATTRIBUTE`; it remains unconfirmed. `SCALAR_ATTRIBUTE`/`SOQLTARGETLISTEXPR` is confirmed deployable and UI-compatible per DG UI source (this is how the builder itself authors the condition, not established by a per-shape round-trip) — generate it directly for any attribute the directional table below marks `yes`:

| Attribute | Principal path | Resource/RLS path |
|---|---:|---:|
| `CompanyName` | yes | yes |
| `Department` | yes | yes |
| `Division` | yes | yes |
| `Username` | no | yes |
| `Email` | no | yes |
| `Title` | yes | yes |
| `CallCenterId` | yes | yes |
| `ContactId` | no | yes |
| `ProfileId` | yes | yes |
| `UserRoleId` | no | no |

This table is intentionally extensible and reflects the current UI source, not a universal H360 enum.

## RLS

- Resolve the single resource domain and every referenced field in the target org.
- Resolve every join schema, alias, predicate field, and principal expression field.
- Reject unresolved value domains; never emit a null or guessed field reference.
- The UI currently exposes RLS target field types `Text`, `Number`, `Boolean`, `Date`, and `Percent`; currency is normalized as `Number`.
- Reject `Email`, `Phone`, `Url`, and array-valued target fields for UI-renderable RLS.
- Validate resource-domain containment when dataspace scope is present.
- Treat RLS plus tag/classification predicates as unsupported until a UI round-trip and runtime test proves their semantics.

## Evidence Boundary

The UI source confirms its reconstruction and serialization contract. MDAPI deploy/retrieve alone does not prove that a policy opens, saves, and preserves semantics in the UI. Claim UI compatibility only after open/save/retrieve validation.
