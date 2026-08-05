# `<category>` Values — `ReportTypeCategory` Enumeration

The `category` value determines where the CRT appears in the report builder's "Create New Report Type" wizard. Use one of these Salesforce-defined values from the Metadata API `ReportTypeCategory` enum.

| Category value | Typical use |
|----------------|-------------|
| `accounts` | Accounts & Contacts |
| `opportunities` | Opportunities |
| `forecasts` | Forecasts |
| `cases` | Customer Support Reports |
| `leads` | Leads |
| `campaigns` | Campaigns |
| `activities` | Activities |
| `busop` | Business operations |
| `products` | Price Books, Products and Assets |
| `admin` | Administrative Reports |
| `territory` | Territory management |
| `territory2` | Territory management (Enterprise Territory Management) — API 31.0+ |
| `usage_entitlement` | Usage entitlements |
| `wdc` | Work.com / Calibration — API 29.0+ |
| `calibration` | Calibration — API 29.0+ |
| `other` | Other Reports (default for custom-object-based CRTs without a natural home) |
| `content` | Content |
| `quotes` | Quotes |
| `individual` | Individual (privacy) — API 45.0+ |
| `employee` | Employee — API 46.0+ |
| `data_cloud` | Data Cloud — API 55.0+ |
| `commerce` | Commerce — API 60.0+ |
| `flow` | Flow — API 60.0+ |
| `semantic_model` | Semantic model — API 60.0+ |

**When in doubt:** Use `other` for custom-object-based CRTs.
