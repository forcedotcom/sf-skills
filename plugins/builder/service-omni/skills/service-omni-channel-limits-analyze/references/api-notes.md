# Omni-Channel limits API notes

## Supported value

`SELECT COUNT() FROM PendingServiceRouting` provides a live, point-in-time PSR row count when Omni-Channel is enabled and the running user can access the object.

## Values not exposed by a supported API

The read-only Omni-Channel Limits Setup page also displays the org's effective maximum PSR count and a rolling hourly enqueue meter. Those values are read by Salesforce's internal page controller and are not exposed as fields on `PendingServiceRouting`, Tooling objects, Metadata types, Connect resources, or the standard REST org-limits response.

The skill therefore uses these values only as labeled references:

| Routing model | Reference maximum PSRs |
|---|---:|
| Enhanced | 300,000 |
| Legacy | 200,000 |

The reference hourly maximum is 45,000. Actual org values can differ, and live hourly usage is not retrievable. An administrator can supply a known PSR maximum with `--max-psrs`, but the script still records that it was not verified through an API.

## Full-fidelity product path

Exact reporting requires a Salesforce Core product API that exposes both maximums and the rolling hourly meter, ideally through the standard REST org-limits resource. Until that contract exists, do not scrape Setup HTML or model a fictional limits sObject.
