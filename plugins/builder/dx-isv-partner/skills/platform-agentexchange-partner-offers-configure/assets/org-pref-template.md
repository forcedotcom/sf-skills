# TransactableMarketplacePrivateOfferSettings XML Template

Use this exact structure when writing the settings metadata file.

## File path

```text
<packageDir>/settings/TransactableMarketplacePrivateOffer.settings
```

## Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TransactableMarketplacePrivateOfferSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableTransactableMarketplaceReceivePartnerOffers>true</enableTransactableMarketplaceReceivePartnerOffers>
</TransactableMarketplacePrivateOfferSettings>
```

Replace `true` with `false` to disable.

## Notes

- The metadata type is `TransactableMarketplacePrivateOfferSettings`, available from API version 67.0+.
- This type is registered with `apiCreateAllowed="false"` and `apiDeleteAllowed="false"` — it can only be updated, not created or deleted via the API. This does NOT mean you should skip writing the file: the preference always exists in the org with a default value, so writing a new local settings file and deploying it is treated as an update by the Metadata API and is always valid.
- The `xmlns` attribute is required; omitting it causes a deploy parse error.
- The field name is `enableTransactableMarketplaceReceivePartnerOffers` (note the `enable` prefix).
