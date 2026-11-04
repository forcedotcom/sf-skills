# Data Mapper and Integration Procedure Formula Functions

Functions available in **Data Mapper formulas** and **Integration Procedure formulas** (Set Values values prefixed with `=`, `executionConditionalFormula`, `failureConditionalFormula`, etc.). Data Mappers and Integration Procedures share this function set.

> These are **not** the OmniScript functions — OmniScript Formula/Aggregate elements have their own list (see `omnistudio-omniscript-generate` → `references/formula-functions.md`). For example `AND()`, `OR()`, `CASE()`, `CONCATENATE()` are OmniScript functions; in Data Mappers / IPs use the `&&` / `||` operators and `CONCAT()`.
>
> Source: Salesforce Help — [Supported Data Mapper and Integration Procedure Functions](https://help.salesforce.com/s/articleView?language=en_US&id=xcloud.os_omnistudio_data_mapper_and_integration_procedure_functions.htm&type=5)

**Path syntax in formulas**: JSON nodes are separated by `:`. Both `Contact:FirstName` and `%Contact:FirstName%` are accepted. Dates are strings in Day.js format (`"2025-01-31"`, `"01/31/2025"`, `"2025-01-31T12:00:00Z"`).

---

## Conditional Functions

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `IF(expression, trueResult, falseResult)` | Any | `IF(InputDate < "2000-01-01", "20th Century", "21st Century")`. **Both branches are always evaluated** — see Gotchas. |
| `ISBLANK(expression)` | Boolean | True if a string or list is blank/empty. `ISBLANK("")`, `ISBLANK([])`, `ISBLANK(%EmptyList%)` → `true` |
| `ISNOTBLANK(expression)` | Boolean | True if a string or list is not empty. `ISNOTBLANK(%NumberList%)` → `true` |

## Mathematical Functions

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `ABS(expression)` | Number | `ABS(-4.50)` → `4.5` |
| `ROUND(expression, precision, direction)` | Number | `precision` defaults to **2**; `0` returns an integer. `direction` (requires `precision`): `CEILING`, `DOWN`, `FLOOR`, `HALF_DOWN`, `HALF_EVEN`, `HALF_UP`, `UP`. `ROUND(4.115)` → `4.12`; `ROUND(2.119, 2, DOWN)` → `2.11` |
| `SQRT(expression)` | Number | `SQRT(3 * 12)` → `6`; negative input returns `{}` |

## Date and Time Functions

`NOW()` and `TODAY()` use **UTC**; use the `$Vlocity.NOW` environment variable for the user/org time zone. For `ADDDAY` / `ADDMONTH` / `ADDYEAR`, a `"YYYY-MM-DD"` input preserves the time; `"MM/DD/YYYY"` resets it to `00:00:00`.

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `ADDDAY(date, days)` | Datetime | Negative to subtract. `ADDDAY("2025-01-01", 31)` → `"2025-02-01T00:00:00.000Z"` |
| `ADDMONTH(date, months)` | Datetime | `ADDMONTH("2025-01-25T16:35:30Z", 15)` → `"2026-04-25T16:35:30.000Z"` |
| `ADDYEAR(date, years)` | Datetime | `ADDYEAR("2025-01-01", -10)` → `"2015-01-01T00:00:00.000Z"` |
| `AGE(birthDate)` | Integer | Age in years today. `AGE("2002-02-15")` |
| `AGEON(birthDate, date)` | Integer | Age in years on `date` (dates only; 0 if under a year or `date` is earlier). `AGEON("2002-02-15", "2030-02-28")` → `28` |
| `DATEDIFF(firstDate, secondDate)` | Integer | Days = `secondDate − firstDate` (**can be negative**; times and time zones count). `DATEDIFF("02/01/2000", "2001-02-01")` → `366` |
| `DATETIMETOUNIX(datetime)` | Integer | Milliseconds since the UNIX epoch. `DATETIMETOUNIX("2002-02-01")` → `1012521600000` |
| `DAY(date)` | Integer | Day of month. `DAY("2025-01-31")` → `31` |
| `EOM(date)` | Datetime | Last day of the month. `EOM("2024-02-01")` → `"2024-02-29T00:00:00.000Z"` |
| `FORMATDATETIME(datetime, format, timezone)` | String | Java SimpleDateFormat `format` (default `"MM/DD/YY HH:mm aaa"`); IANA `timezone` (default caller's; requires `format`). `FORMATDATETIME("01/31/2025T12:00:00", "yyyy-MM-dd'T'HH:mm:ssZ", "America/New_York")` → `"2025-01-31T07:00:00-0500"` |
| `FORMATDATETIMEGMT(datetime, timezone, format)` | String | Returns GMT. **Note the parameter order differs from `FORMATDATETIME`** (`timezone` before `format`; `format` requires `timezone`). `FORMATDATETIMEGMT("01/31/2025T12:00:00", "America/New_York", "yyyy-MM-dd'T'HH:mm:ssZ")` → `"2025-01-31T17:00:00+0000"` |
| `HOUR(time)` | Integer | `HOUR("2004-02-01T08:00:00Z")` → `8` |
| `MINUTE(time)` | Integer | `MINUTE("08:17:00")` → `17` |
| `MONTH(date)` | Integer | `MONTH("2025-01-01")` → `1` |
| `NOW(format)` | Datetime | Optional SimpleDateFormat. `NOW()` → `"2025-03-08T22:01:46.684Z"`; `NOW("yyyy-MM-dd")` |
| `SECOND(time)` | Integer | `SECOND("08:00:59")` → `59` |
| `TIMEDIFF(firstTime, secondTime)` | Integer | Milliseconds = `firstTime − secondTime` (**opposite order to `DATEDIFF`**). `TIMEDIFF("16:35:30", "08:00:15")` → `30915000` |
| `TODAY()` | Datetime | `"YYYY-MM-DD"` (UTC). `CONCAT(YEAR(ADDYEAR(TODAY(), 1)), "-01-01")` → first day of next year |
| `UNIXTODATETIME(timestamp)` | Datetime | Seconds or milliseconds. `UNIXTODATETIME(1012581330)` → `"2002-02-01T16:35:30.000Z"` |
| `YEAR(date)` | Integer | `YEAR("2025-01-01")` → `2025` |

## String Functions

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `BASE64ENCODE(data)` | String | Not null/empty. `BASE64ENCODE("Encode this string.")` |
| `CONCAT(string...)` | String | Numbers are coerced; nulls/empty strings ignored. `CONCAT(Contact:FirstName, " ", Contact:LastName)` → `"Mike Smith"` |
| `JOIN(string..., token)` | String | `JOIN(Contacts:id, ', ')` → `"0036ab, 2787kq, 3610xr"`. Without a token the last value is used as the token. |
| `MAXSTRING(string...)` | String | Lexicographically last (case-sensitive). `MAXSTRING("Amy", "Ziggy", "Michael")` → `"Ziggy"` |
| `SPLIT(string, token)` | String[] | Token is a **Java regex** — escape special characters with `\` (e.g. `\.` to split on a period). Returns the input unchanged if the token is not found. `SPLIT(%Name%, " ")` → `["Anne","Marie","Gupta"]` |
| `STRINGINDEXOF(string, substring)` | Integer | 0-based, case-sensitive, `-1` if not found. `STRINGINDEXOF("This is the test string.", "test")` → `12` |
| `SUBSTRING(string, startIndex, endIndex)` | String | 0-based, start inclusive, end exclusive. Indexes may also be a character/string (position of first occurrence). `SUBSTRING("The string.", 4, 10)` → `"string"` |
| `TOSTRING(data)` | String | `TOSTRING(3.0)` → `"3.0"`; objects become `"key, value"` (use `SERIALIZE` for JSON) |

## List and Array Functions

Functions marked † require an **anonymous JSON list** — wrap named arrays with `LIST(...)`.

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `AVG(list)` | Number | `AVG(List:Item)`. Nulls count toward the denominator. |
| `FILTER(LIST(list), condition)` † | JSON list | Condition is a quoted expression; string matching is case-insensitive. `FILTER(LIST(NameList), 'LastName == "Xavier"')`; with a variable: `FILTER(LIST(NameList), 'LastName == "' + FindName + '"')` |
| `LIST(expression)` | JSON list | Converts values or a named JSON array into an anonymous list. `LIST(NameList)`, `LIST("a", "b")` |
| `LISTMERGE(mergeKey..., LIST(list)...)` † | JSON list | Merges nodes whose merge-key values match (case-insensitive); later lists overwrite. `LISTMERGE("id", LIST(ContactNames), LIST(ContactAddresses))` |
| `LISTMERGEPRIMARY(mergeKey..., LIST(list)...)` † | JSON list | Like `LISTMERGE` but keeps only nodes from the first (primary) list. |
| `LISTSIZE(list)` | Number | `LISTSIZE(NameList)` → `3`. **An empty JSON array returns 1** — see Gotchas. |
| `MAPTOLIST(jsonObject)` | JSON list | Converts an object into a list of single-key objects. `MAPTOLIST(Contact:Parents)` |
| `MAX(list)` | Number | `MAX(List:Item)` |
| `MIN(list)` | Number | `MIN(List:Item)` |
| `SORTBY(LIST(list), key..., '[:DSC]')` † | JSON list | **Data Mappers only.** Ascending by default; add `'[:DSC]'` for descending. `SORTBY(LIST(NameList), 'LastName', 'FirstName')` |
| `SUM(list)` | Number | `SUM(List:Item)` → `13.5` |

## JSON Object Functions

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `DESERIALIZE(jsonString)` | JSON object | `DESERIALIZE(%SerializedContact%)` |
| `RESERIALIZE(jsonString)` | JSON string | Same as `DESERIALIZE(SERIALIZE())`; converts Apex Remote Action output to a generic `Map<String, Object>` that DMs/IPs accept. |
| `SERIALIZE(jsonObject)` | JSON string | `SERIALIZE(%Contact%)`; for arrays `SERIALIZE(LIST(%Contacts%))` |
| `VALUELOOKUP(startNode, node...)` | String | Dynamic node lookup. `VALUELOOKUP(Contact, GetNameGroup, GetLastNameField)` → `"Edison"` |

## Invocation Functions

| Signature | Returns | Details / Example |
|-----------|---------|-------------------|
| `COUNTQUERY(query)` | Integer | Runs a single-field SOQL query and returns the row count. Use `'{0}'` for a parameter: `COUNTQUERY("SELECT Name FROM Account WHERE BillingState = '{0}'", %State%)` |
| `QUERY(query)` | JSON list | Runs a single-field SOQL query. `QUERY("SELECT Name FROM Account WHERE BillingState LIKE '{0}'", %InputState%)` → `["GenePoint","Pyramid Construction"]`. No rows returns `{}`. |
| `FUNCTION(class, method, input...)` | Any | Calls a custom function on an Apex class that implements `Callable`. Pass lists with `LIST(...)`. `FUNCTION('MyCustomFunctions', 'replace', InputString, "-", "_")` |
| `GENERATEGLOBALKEY(prefix)` | String | UUID-style key, optional prefix. `GENERATEGLOBALKEY("SUB")` → `"SUB-f72b…"` |
| `GLOBALAUTONUMBER(name)` | String | Next number from an Omni Global Auto Number definition. `GLOBALAUTONUMBER("Loan Application Number")` |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `IF()` evaluates **both** branches — side effects in the unused branch (e.g. `InvokeIP`, DML, callouts) still run | Don't put side-effecting calls inside `IF()`. Use the element's `executionConditionalFormula` (or a Conditional Block) to decide whether the action runs. |
| `LISTSIZE` of an empty array returns `1` (also after a `QUERY` with no rows, which returns `{}`) | `IF(ISBLANK(MyList), 0, LISTSIZE(MyList))` — or just use `ISBLANK` to test for empty |
| `FILTER` / `SORTBY` / `LISTMERGE` on a named array returns nothing | Wrap the array: `FILTER(LIST(MyArray), ...)` |
| `SORTBY` in an Integration Procedure | Supported in Data Mappers only — sort in a Transform Data Mapper |
| `SPLIT` on `.`, `\|`, `(` etc. gives unexpected results | The token is a Java regex — escape special characters (`\.`) |
| `DATEDIFF` vs `TIMEDIFF` sign | `DATEDIFF(a, b)` = b − a (days); `TIMEDIFF(a, b)` = a − b (ms) |
| `NOW()` / `TODAY()` are UTC | Use `$Vlocity.NOW` for the user/org time zone |
| `AND()`, `OR()`, `CASE()`, `CONCATENATE()`, `CONTAINS()` from OmniScript | Not in the DM/IP function list — use `&&`, `\|\|`, `CONCAT()`, `STRINGINDEXOF(...) >= 0` |
