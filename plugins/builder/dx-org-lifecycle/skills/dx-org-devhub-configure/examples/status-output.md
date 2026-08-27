# Output examples

Sample `devhub.sh` transcripts to calibrate what to expect and how to relay it.
These are reference only — the script prints the authoritative output at runtime.

## Dev Hub is ON (status + allocation)

```text
Dev Hub status for 'MyDevHub':
  Dev Hub: ENABLED  (ScratchOrgInfo is queryable)
  Scratch org signup records: 3

Scratch org allocation for 'MyDevHub':
  Limit                        Used  Remaining        Max
  Active scratch orgs             0          3          3
  Daily scratch orgs              0          6          6

  Active = orgs alive right now; Daily = successful creations in a rolling 24h window.
  Allocation is set by the Dev Hub's edition (e.g. Developer/trial 3 & 6;
  Enterprise 40 & 80; Unlimited/Performance 100 & 200) plus any purchased add-on.
```

## Dev Hub is OFF (prints how to enable it)

```text
Dev Hub status for 'my-org':
  Dev Hub: NOT ENABLED

  Enable it (deploys enableScratchOrgManagementPref=true; irreversible):
    devhub.sh "my-org" --enable            # validate first (dry run)
    devhub.sh "my-org" --enable --apply    # actually enable
  Requires ModifyAllData or ModifyMetadata (System Administrator);
  not allowed in a sandbox or an org with a registered namespace.

  Manual alternative (Setup UI):
    1. Log in as a System Administrator.
    2. Setup > Quick Find > "Dev Hub" > Dev Hub > turn Enable Dev Hub On.
    Open it directly: sf org open --path "lightning/setup/DevHub/home" --target-org "my-org"
```
