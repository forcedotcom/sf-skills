---
name: platform-agentexchange-partner-offers-configure
description: "Enable or disable the org preference that controls whether a Salesforce org can receive partner offers from the Transactable Marketplace. Use this skill when the user wants to turn partner offer reception on or off for an org. TRIGGER when: user asks to enable or disable partner offers, configure TransactableMarketplaceReceivePartnerOffers, configure enableTransactableMarketplaceReceivePartnerOffers, set up marketplace partner offer reception, toggle the TM partner offers setting, edit a TransactableMarketplacePrivateOffer.settings file, or configure org preferences related to transactable marketplace. DO NOT TRIGGER when: user needs to create or manage the partner offer records themselves, configure marketplace listing settings, or work with SfdcPartnerOffer objects (use platform-metadata-deploy or platform-apex-generate instead)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
---

# Enabling Transactable Marketplace Receive Partner Offers Org Preference

This skill configures the `enableTransactableMarketplaceReceivePartnerOffers` org preference via the `TransactableMarketplacePrivateOfferSettings` Metadata API type, which controls whether a Salesforce org is eligible to receive partner offers through the Transactable Marketplace. It is required for subscriber orgs that participate in the TM partner offer flow.

## Scope

- **In scope**: Reading the current value of the pref, enabling or disabling it via Metadata API (`TransactableMarketplacePrivateOfferSettings`), and verifying the change took effect.
- **Out of scope**: Creating or managing partner offer records, configuring marketplace listings, or any Apex/trigger changes related to offer processing.

---

## Required Inputs

- **Target org alias or username**: The org where the pref should be set. Ask if not provided.
- **Desired state**: `true` (enable) or `false` (disable). Default: `true`.

---

## Workflow

### Phase 1 — Check current state

1. **Query the current preference value** by running:
   ```bash
   sf data query -q "SELECT Preference, Value FROM OrgPreference WHERE Preference = 'TransactableMarketplaceReceivePartnerOffers'" --target-org <alias> --use-tooling-api
   ```
   If the record exists and `Value = true`, the pref is already enabled — confirm with the user before proceeding.
   If the query returns no rows, the pref is not yet set (defaults to `false`).

2. **Resolve the org's package directory** to determine where to write metadata. Run this and use its output as `<packageDir>`:
   ```bash
   jq -r '.packageDirectories[0].path // "force-app/main/default"' sfdx-project.json
   ```

### Phase 2 — Apply the preference

3. **Write the TransactableMarketplacePrivateOfferSettings metadata file** — load `assets/org-pref-template.md` for the exact XML structure, then write the file at:
   ```text
   <packageDir>/settings/TransactableMarketplacePrivateOffer.settings
   ```
   Set `<enableTransactableMarketplaceReceivePartnerOffers>true</enableTransactableMarketplaceReceivePartnerOffers>` (or `false` if disabling).

4. **Deploy the metadata** to the target org. Before running the deploy, confirm with the user:
   - [ ] Confirmed the target org alias with the user (deploying to the wrong org is not easily reversible)
   - [ ] Confirmed the desired state (`true`/`false`) matches the user's intent
   ```bash
   sf project deploy start --metadata TransactableMarketplacePrivateOfferSettings --target-org <alias>
   ```

### Phase 3 — Verify

5. **Confirm the change** by re-running the Tooling API query from step 1 and verifying the `Value` column matches the desired state.

6. **Report to the user** — see Output Expectations below.

---

## Rules / Constraints

| Rule | Rationale |
|------|-----------|
| Always query the current value before writing metadata | Avoids unnecessary deploys and detects conflicting changes |
| Use `TransactableMarketplacePrivateOfferSettings` as the metadata type | This is the concrete type registered in the platform for this pref, not the generic `OrgPreferenceSettings` |
| The settings file must be named `TransactableMarketplacePrivateOffer.settings` | Metadata API requires the filename to match the settings node name |
| Do not hardcode `force-app/main/default/` | Always read `sfdx-project.json` for the actual package directory |
| Never deploy without confirming the org alias with the user | Deploying to the wrong org is not easily reversible |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Tooling API query returns no rows | Pref is unset (defaults to `false`). Safe to create a new settings file. |
| Deploy fails with `INVALID_TYPE` | The metadata type name is `TransactableMarketplacePrivateOfferSettings` — check the `--metadata` flag value. |
| Deploy succeeds but value doesn't change | Another settings file in the project may be overriding this one. Search for other `TransactableMarketplacePrivateOffer.settings` files in the project. |
| `INSUFFICIENT_ACCESS_OR_READONLY` on deploy | User running the deploy must have the "Modify All Data" or org preference admin permission in the target org. |
| Pref not visible in UI | `enableTransactableMarketplaceReceivePartnerOffers` is not surfaced in Setup UI — the Tooling API query is the only way to verify it. |
| Available from API version 67.0+ only | The type is available from API v67.0 — deploying against an older API version will fail. |

---

## Output Expectations

After completing all phases, report:

```text
Org: <alias>
Preference: enableTransactableMarketplaceReceivePartnerOffers
Previous value: <true|false|unset>
New value: <true|false>
File written: <packageDir>/settings/TransactableMarketplacePrivateOffer.settings
Deploy status: Success
```

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/org-pref-template.md` | Phase 2, step 3 — use as the exact XML structure for the settings file |
| `examples/org-preference-settings.xml` | To verify the generated file matches expected format |
