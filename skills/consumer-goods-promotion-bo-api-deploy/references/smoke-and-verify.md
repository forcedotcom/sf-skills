# Phase 6 — Smoke test through the REST endpoints

Prove the interview's chosen workflows all reach the org and that the generated
step actually applied the interview's writes. `SKILL.md` Phase 6 links here.

The **shape** of the payload varies by interview:
- `entity` decides which nested entity the writes go on (`Tactic`, `Promotion`, etc.).
- `inputPaths` decide what keys the payload must carry.
- `outputWrites` decide what the verification SOQL should assert.

The **flow** is fixed: `initialize → ingest(create) → verify → ingest(update) →
verify → ingest(copy) → verify`, but the update and copy legs only run if the
interview included them in `workflows`.

## 6.-1 — Derive the payload contract from the workflow (schema-first)

Do this BEFORE composing any request body. The workflow itself declares the
accepted paths — read them, don't guess. See
`references/conventions-and-payload-rules.md` ("Payload contract derivation")
for the canonical SOQL; run it once per invoked workflow (`create`, `update`,
`copy`), producing three contracts.

**Additionally**, apply the eight cross-workflow rules (R1..R8) in
`references/conventions-and-payload-rules.md` ("Promotion payload — cross-workflow
rules"). These are the constraints the schema alone cannot express and every one
has caused a smoke-test failure historically. Summary of what the skill MUST do
on top of the derived contract:

- **R1** — force `DateFrom`, `DateThru`, `Slogan` into the create payload. If the user gave duration-in-weeks intent, compute `DateThru = DateFrom + weeks*7 - 1` client-side.
- **R2** — poll for `Status__c = 'Calculated'` (NOT `Processed`, which does not exist in the picklist).
- **R3** — send level NAMES verbatim as `ProductFilter.Criteria` keys (`Category`, `Brand`, ...), NOT Product2 field API names.
- **R4** — pre-flight the anchor account has a `Plan` `Account_Extension__c` row valid for `DateFrom..DateThru` in this sales org.
- **R5** — restrict `ManualInputs[].KPI` values to `editable` / `editable_calculated` `KPI_Definition__c.Name` on the template's `KPI_Set__c`.
- **R6** — for `copy`, derive requireds the same way, then layer the Apex-only preconditions (`Is_Copyable__c`, template type, anchor).
- **R7** — reject any `Tactics[*].TacticTemplate` not linked to the chosen `PromotionTemplate` in this sales org.
- **R8** — reject any `PromotionTemplate` whose `Promotion_Type__c != 'Promotion'` (fail-fast before ingest — otherwise it surfaces as a misleading `/productfilter` error).

For each derived contract, compute:
- `requiredPaths` = union of `Path__c` where `Required__c = true`.
- `optionalPaths` = every other declared path.
- `arrayPaths` = any `Path__c` starting with or containing `[*]` (bind to `Tactics[]` / `ManualInputs[]` in the request).

Emit `./out/contracts/<workflow>.json`:
```json
{
  "workflow": "create",
  "salesOrg": "<salesOrg>",
  "required": [{"path": ".PromotionTemplate", "step": "loadPromotionDefaults2"}, ...],
  "optional": [...],
  "arrayPaths": ["Tactics[*].TacticTemplate", ...]
}
```

Then reconcile against user input (three possible sources; skill picks the first non-empty):

1. `--intent-file <path>` — a JSON object whose keys mirror the payload shape. Validate every top-level key against the derived contract; any key not in `required ∪ optional` → stop, print `"Property '<key>' is not declared in the <workflow> contract"`.
2. `--mass-upload <path>` — a JSONL or CSV file, one promotion per row. Column headers MUST match the contract's `required` and `optional` path list verbatim; missing any required column → stop with the list of missing columns.
3. Interactive prompt — print the required list, ask for each in turn, then offer the optional list. Interview text is `./out/prompts/<workflow>.txt` (generated, not hard-coded).

Reference-data resolution (still schema-first, but the schema alone cannot
express these — do it AFTER contract validation and BEFORE any REST call):

- `PromotionTemplate` value → resolve name against `${PREFIX_UNDER}Promotion_Template__c` with `${PREFIX_UNDER}Sales_Org__c = <salesOrg>`. Miss → stop with "Promotion Template <name> not found in sales org <salesOrg>".
- Each `Tactics[*].TacticTemplate` value → resolve against `${PREFIX_UNDER}Tactic_Template__c` scoped to sales org, AND confirm linkage to the chosen `PromotionTemplate` via `${PREFIX_UNDER}Promotion_Template_Tactic_Template__c`. Miss → stop with the concrete failure.
- `AnchorAccount` value → resolve against `Account` where `${PREFIX_UNDER}ExternalId__c = <value> AND ${PREFIX_UNDER}Sales_Org__c = <salesOrg>`. Never pass a Salesforce Id — the packaged Apex looks up by external id.
- `ProductFilter.Criteria.{Brand,Category,Subcategory,Flavor,Package}[*]` → resolve each name against the packaged product-attribute lookups, scoped to the sales org.
- `ProductFilter.{Included,Excluded}Products[*]` → resolve each SKU against `Product2` scoped to the sales org.

Template-conditional requireds (the two the schema cannot express):
- `setPromotionAnchor2` declares `.AnchorAccount` as OPTIONAL, but the packaged Apex enforces it for certain `PromotionTemplate` values (verified for `Customer Promotion`). Do NOT hard-code the list — if a pre-flight `POST /ingest` with a probe promotion returns `"AnchorAccount is required"`, re-prompt for `AnchorAccount` and retry.

## 6.0 — Materialize per-run payloads

Only reached once the derived contract, user input, and reference-data
resolution all pass. Emit three payload files under `./out/smoke/`:
`create.json`, `update.json`, `copy.json`. Each is composed from the contract:

1. Top-level: `{importId, workflow, salesOrg, promotions: [...]}`. All four keys are lower-camel in the wire format (see the "Wire-format quirks" note in `references/conventions-and-payload-rules.md`).
2. Each promotion carries every `requiredPaths` value the user supplied (or an interview-collected value), plus any `optionalPaths` opted into. No unrecognized keys.
3. Nested arrays (`Tactics[]`, `ManualInputs[]`) mirror the `arrayPaths` groups from the contract.
4. Any user-supplied lookup value has been REPLACED by its resolved-in-sales-org form before writing the file: template names remain as names (packaged Apex resolves per sales org), account external ids remain as external ids.
5. Probe values for interview-driven `outputWrites` assertions are written to `./out/smoke/expected.json`.

The reference example ships a working set for `SetCommentValue`
(`assets/set-comment-value/payloads/`); `--preset set-comment-value` copies
those directly instead of running the generator.

Setup — every REST call below goes through `sf api request rest`, which
authenticates with the CLI's stored session for `--target-org` and
mints/refreshes the token internally. **Never** extract the access token
(`sf org display` / `sf org auth show-access-token`) and hand-build a `curl`
request: a bearer token in shell output, traces, or agent context is a
credential exposure (S1). Do **not** add `--json` to `sf api request rest` — the
raw stdout body is already JSON. `${URL_NS}` is the namespace segment from
Phase 1 (`/cgcloud` / `/cgcloud_dev` / empty); the endpoint is instance-relative.

```bash
BASE="/services/apexrest${URL_NS}/promotions"
```

## 6a — Create

```bash
# 1. Initialize a transaction
INIT=$(sf api request rest "${BASE}/initialize" --method POST \
  --body '{"nrOfItems": 1, "salesOrg": "<salesOrg>", "timeout": 600}' \
  --target-org <alias>)
IMPORT_ID=$(echo "$INIT" | jq -r .importId)
```

Bounds (from `BeginPromotionImportService`): `nrOfItems >= 1` and
`nrOfItems <= BoApiPromotionsPerTransaction` application limit; `timeout in
[300, 3600]`. Smoke test uses 1 item and 600s.

```bash
# 2. Ingest the generated create payload
CREATE_JSON=$(jq --arg id "$IMPORT_ID" '.importId = $id' ./out/smoke/create.json)
CREATE_RESP=$(sf api request rest "${BASE}/ingest" --method POST \
  --body "$CREATE_JSON" \
  --target-org <alias>)
```

Non-2xx → stop, print the response body.

```bash
# 3. Poll status until every record is Calculated (terminal success) or Error.
#    Wire shape (verified against the running org): the endpoint returns an
#    object, not an array — {"txid":"...","details":[{"status":"Calculated",
#    "nrOfItems":1}]}. Note lowercase `status` and the `details[]` nesting.
for i in $(seq 1 60); do
  STATUS=$(sf api request rest "${BASE}/status?importId=${IMPORT_ID}" \
    --target-org <alias>)
  echo "$STATUS" | jq .
  DONE=$(echo "$STATUS" | jq '[.details[] | select(.status | test("^(Calculated|Error)$"))] | length')
  TOTAL=$(echo "$STATUS" | jq '.details | length')
  [ "$DONE" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ] && break
  sleep 5
done
```

## 6a-verify — transaction-log query + interview-driven write assertion

The status endpoint returns *counts*. To guarantee we never claim success while
a record failed, also query `BO_API_Transaction_Log__c` directly:

```bash
sf data query --target-org <alias> --json --query "
  SELECT Id, ${PREFIX_UNDER}Status__c, ${PREFIX_UNDER}Error_Type__c,
         ${PREFIX_UNDER}Error_Information__c,
         ${PREFIX_UNDER}Promotion__c, ${PREFIX_UNDER}Transaction_Id__c
    FROM ${PREFIX_UNDER}BO_API_Transaction_Log__c
   WHERE ${PREFIX_UNDER}Transaction_Id__c = '${IMPORT_ID}'
     AND ${PREFIX_UNDER}Status__c != 'Calculated'
"
```

Any rows returned → stop, print them, refuse to declare success.
`Error_Information__c` carries the actual transform/validation message (e.g.
`Properties other than those defined were not expected at #.<path>` or `Required
property missing at #.<path>`) — read it verbatim to fix the payload; it is the
ONLY error-detail field on this object (there is no `Error_Message__c`).

Once green, pull the created promotion and assert every field named in the
interview's `outputWrites` matches its expected probe value from
`./out/smoke/expected.json`:

```bash
PROMO_ID=$(sf data query --target-org <alias> --json --query "
  SELECT ${PREFIX_UNDER}Promotion__c
    FROM ${PREFIX_UNDER}BO_API_Transaction_Log__c
   WHERE ${PREFIX_UNDER}Transaction_Id__c = '${IMPORT_ID}'
     AND ${PREFIX_UNDER}Status__c = 'Calculated'
   LIMIT 1
" | jq -r ".result.records[0].${PREFIX_UNDER}Promotion__c")

# For each outputWrite {field}: SELECT ${PREFIX_UNDER}<field> FROM
# ${PREFIX_UNDER}<entity>__c WHERE (entity's parent linkage to PROMO_ID)
```

Every field's actual value must equal the expected probe value in
`expected.json`. Any mismatch → stop, print `(field, expected, actual)`, refuse
to declare success — the generated step didn't do what the interview said.

## 6b — Update (skip if `update` not in interview `workflows`)

Repeat 6a with `update.json`. The payload references the newly-created promotion
id + entity ids from 6a's create response and carries different probe values.
Verify every `outputWrites` field now equals the *update* probe values.

## 6c — Copy (skip if `copy` not in interview `workflows`)

Repeat 6a with `copy.json` (references the created promotion id as the copy
source). Verify:
- A new promotion id came back.
- Every `outputWrites` field on the *copied* record equals the source record's value at copy-time (proves the step fired inside the copy workflow too).

**Copy payload schema is *stricter* than create/update, and child inputs come
from the source record.** The BO API rejects `PromotionTemplate`, `DateFrom`,
`DateThru`, `AnchorAccount`, `Tactics[].Id`, `Tactics[].TacticTemplate` for the
`copy` workflow — those come from the source record. Copying `create.json`
verbatim and swapping `workflow` fails with `Properties other than those defined
were not expected at #.<field>` and the ATL row lands in `Error`.

Also — verified in-org — on `copy`, **per-child input paths come from the source
record, not the payload**. The payload's `Tactics[]` block is accepted by the
schema but has no effect on the cloned children; each cloned child runs its
`outputWrites` against the *source* child's value. That is why the 6c verify says
"copied == source-at-copy value": it checks the step fired, not that payload
child probes made it through. `copy.json` should therefore carry only the source
promotion `Id` plus top-level probe fields (e.g. `Slogan`); `Tactics[]` in the
copy payload is decorative.
