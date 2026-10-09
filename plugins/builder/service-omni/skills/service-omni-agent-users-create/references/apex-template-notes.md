# `create-users.apex.template` notes

Anonymous Apex template for creating agent demo users. `run-create.sh` resolves the tokens
before execution and submits the rendered Apex.

## Tokens

| token | meaning |
| --- | --- |
| `__COUNT__` | integer 1..10 — number of user slots |
| `__PROFILE_ID__` | 18-char Profile Id (e.g. `00eRZ00000012tKYAQ`) |
| `__SUFFIX__` | 8-char lowercase hex string derived from `Organization.Id` |

## Idempotency

The block re-queries existing users inside the transaction and inserts only the truly
missing indexes. Two concurrent runs can both pass the pre-query before either commits;
Salesforce's `DUPLICATE_USERNAME` constraint is the authoritative deduplicator, and
`run-create.sh` treats `DUPLICATE_USERNAME` as "another agent won the race" and retries a
re-detect.

## Security note (password / TraceFlag)

This block only creates the `User` rows and never emits a password via `System.debug`. The
caller (`run-create.sh`) sets each password with a SEPARATE Anonymous Apex
`System.setPassword(id, pw)` submission per newly-created user. That plaintext lives in the
submitted Apex source, which appears in the inline `executeAnonymous` debug log and — ONLY
when a debug-log TraceFlag is active for the running user — in a queryable `ApexLog` row.
`run-create.sh` proves no active TraceFlag exists before calling `System.setPassword` and
otherwise fails closed (no password set), so plaintext never reaches a queryable log.

## Output contract

For every user created this run, `System.debug` emits one line:

```text
AGENT_USER_CREATED|<userId>|<username>|<email>
```

which `run-create.sh` greps from the log to build the skill's JSON return value.
