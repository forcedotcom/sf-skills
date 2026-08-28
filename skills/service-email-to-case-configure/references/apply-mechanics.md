# Email-to-Case Apply Mechanics (why the write is shaped this way)

Load-bearing design rationale behind `apply-casesettings.py`. Read this before changing
how the script builds or sequences its `updateMetadata` payloads. Do not substitute a
plain deploy or a minimal patch.

## Why two phases (and not a single file-based deploy)

Enabling On-Demand Email-to-Case provisions the org's internal email-service
infrastructure, and a routing address can only bind to that infrastructure in a
**subsequent** operation. A single file-based deploy (`sf project deploy`) that both
enables On-Demand and declares a routing address **fails on a freshly-configured org** —
verified on clean orgs. `apply-casesettings.py` therefore reads current settings, applies
the **complete `emailToCase` block** (toggles) plus Support Settings in one `updateMetadata`
call (Phase A), then re-reads and appends routing addresses in a second call (Phase B).

## Two load-bearing properties of the write

- **Send the whole `emailToCase` block, not a minimal patch.** Provisioning the On-Demand
  email service is driven by writing the full `emailToCase` block. A minimal field-level
  patch that just flips `enableOnDemandEmailToCase` to `true` does **not** trigger
  provisioning, so Phase B then fails with "We couldn't save your routing address... custom
  email services named EmailToCase." (Verified from scratch on a clean org.)
- **Send only the top-level fields this skill owns; strip the rest.** The platform
  re-validates any top-level `CaseSettings` field present in the payload, even at an
  unchanged value — and several (notably Case Feed) carry dependencies unrelated to
  Email-to-Case (Case Feed re-validation requires Chatter). `apply-casesettings.py` writes
  only the fields it sets (`emailToCase`, `enableDraftEmails`, and Support Settings) and
  drops every other top-level field, which keeps its current org value via field-level
  merge. This is why the skill needs **no Chatter prerequisite** and does not fail on
  unrelated org Case configuration. (Verified from scratch on a Chatter-off org: stripping
  all other top-level fields still provisioned and bound a routing address, and the omitted
  fields — e.g. `enableCaseFeed` — kept their values.)

This is the validated mechanism; do not substitute a plain deploy, do not reduce the
`emailToCase` write to a minimal patch, and do not echo the full record back verbatim.

## Support Settings are preserved per field, via field-level merge

Default Case Owner (`defaultCaseOwner` / `defaultCaseOwnerType`) and Automated Case User
(`defaultCaseUser` / `useSystemUserAsDefaultCaseUser`) are **independent** top-level
`CaseSettings` fields — an org can have one configured and the other not. Because top-level
fields merge at the field level (an omitted field keeps its current org value), the script
**preserves a configured field by simply not emitting it** in the payload, and writes only
the field(s) that are unset (or that the caller explicitly overwrites with
`--overwrite-support-settings`). It therefore requires — and validates — input **only** for
the field being written; supplying a value for an already-configured field without the
overwrite flag leaves the existing value untouched. This is why a single "both configured?"
gate is wrong: on a partially-configured org it would either demand the already-set value or
silently overwrite it. `apply_support_settings` branches the owner and automated-user fields
separately for exactly this reason.

## Routing-address ordering (multi-address preservation)

The `updateMetadata` call **replaces the `routingAddresses` collection wholesale**.
An already-provisioned address is **dropped** if a brand-new address follows it in
document order. Therefore the script **emits new addresses before** the carried-over
existing ones, so existing addresses always survive.

The platform-managed read-only fields (`emailServicesAddress` / `isVerified`) do **not**
affect this — only document order does. As defensive hygiene the script still strips those
read-only fields from the payload (the platform mints them), but stripping is not the
preservation mechanism; ordering is. A runtime **preservation guard** baselines the
expected address count (`initial address count + created count`) captured before Phase A and
**fails the run loudly** if any existing address is dropped anyway.

## API version derivation

The Metadata API version is `max(org apiVersion, 67.0)` — derived from the org and floored
at the skill's `minApiVersion` (`67.0`). This keeps every field the skill sets valid while
auto-adopting newer org features (e.g. a v68+ org that supports the `botEmailDefinition`
binding for Agentforce for Service on Email is picked up automatically). It never claims a
version the org doesn't report. `--api-version` forces a specific value.
