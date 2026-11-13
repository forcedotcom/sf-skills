# Input validation (before any command)

Every `{PLACEHOLDER}` in this skill's commands is pasted, unescaped, into a shell string, a SOQL literal, or metadata XML. A stray `'`, `;`, `$(...)`, or `<` in a value would rewrite the command or the deployed file. Check each value against its grammar before the first command that uses it. This covers values the user types and values read back from the org (Ids, `Address`, `Queue.Name`, the org's username and API version).

On a mismatch, stop and ask the user for a corrected value. Never escape and continue: an escaped value that reaches the org is still not the name the user meant. For a value read back from the org, say which record failed; when adopting an existing queue, offer to create a new one instead.

| Value | Grammar |
|---|---|
| DeveloperName / API name: `AGENT_DEVELOPER_NAME`, `CHANNEL_DEVELOPER_NAME`, `QUEUE_DEVELOPER_NAME`, and every flow or `BotEmailDefinition` name | `^[A-Za-z][A-Za-z0-9_]{0,79}$` |
| Record Id: `BOT_ID`, `BOT_USER_ID`, `CHAN_ID`, `QUEUE_ID`, `ROUTING_ADDRESS_ID`, `CASE_SETTINGS_ID` | `^[A-Za-z0-9]{15}([A-Za-z0-9]{3})?$` |
| Queue label: `QUEUE_NAME` (typed, or an existing queue's `Name`) | `^[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}$` |
| `CAPACITY_PERCENTAGE` | `^[0-9]{1,3}$` (an integer from the `queue-resolution.md` table) |
| `ORG_API_VERSION` | `^[0-9]{2}\.[0-9]$` |
| `SUPPORT_EMAIL` | `^[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}$` |
| `ORG` (alias or username), `ORG_USERNAME` | `^[A-Za-z0-9][A-Za-z0-9._@+-]*$` |

None of these grammars admits a quote, `;`, `$`, backtick, `|`, `&`, `<`, or `>`, and none lets a value start with `-`, so a matching value can't escape its shell, SOQL, `sed`, or XML context or be read as a CLI option. Only `QUEUE_NAME` admits a space, and every command quotes it.

`ORG_USERNAME` and `ORG_API_VERSION` are captured into a shell variable and used in the same block, so their commands check the grammar inline with `[[ ... =~ ... ]]` before first use.

## Free text

Values with no grammar above can't be passed through the shell: labels other than `QUEUE_NAME`, `legalDisclaimer`, `signature`, `routingName`, escalation messages, and the bot user's username (`BOT_USER_USERNAME`). Write them into the metadata file with the Edit/Write tools, XML-escaping `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`, and `'` → `&apos;`. A value that must reach a shell command needs a grammar in the table first.
