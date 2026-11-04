# OmniScript Formula Functions

Functions available in OmniScript **Formula** and **Aggregate** elements (and in Set Values values prefixed with `=`). Reference element values with merge fields: `%ElementName%`.

> These are the **OmniScript** functions. Data Mappers and Integration Procedures use a different function set — see the `omnistudio-datamapper-generate` / `omnistudio-integration-procedure-generate` skills.
>
> Source: Salesforce Help — [Omniscript Functions](https://help.salesforce.com/s/articleView?id=xcloud.os_omniscript_functions.htm&type=5)

---

## Number Functions

| Function | Example | Details |
|----------|---------|---------|
| `ABS(number)` | `ABS(%Friends%) == 6.52534` | Returns the absolute value. |
| `BOOLEAN(value)` | | Returns true or false. |
| `CURRENCY(value)` | | Returns the value formatted for currency. `12345` displays as `12,345`. |
| `INTEGER(value)` | `INTEGER(%Friends%) == 6`<br>`INTEGER("12.5") == 12` | Converts the number to an integer with no decimal places. Does not round up. Also accepts a string. |
| `NULL` | | Renders an object's value null. |
| `NUMBER(value)` | `NUMBER(%Friends%) == 128` | Converts a string into a number. |
| `POW(number, exponent)` | `POW(%Friends%, 3) == 274.625` | Returns the exponent value. |
| `RANDOM()` | `RANDOM()` | Returns a random number between 0 and 1 (commonly used for A/B testing). Takes no parameters. |
| `ROUND(number, decimalPlaces)` | `ROUND(%Friends%, 3) == 6.525` | Rounds to the given number of decimal places. |

## Logical Functions

| Function | Example | Details |
|----------|---------|---------|
| `AND()` | `IF((%reset%="Yes" AND( %reboot%="Yes")), "Closed", "Escalated")` | Logical operator: true if all conditions are met. |
| `OR()` | `IF((%reset%="Yes" OR( %reboot%="Yes")), "Closed", "Escalated")` | Logical operator: true if any condition is met. |
| `IF(EXPRESSION, THEN, ELSE)` | `IF((%reset%="Yes" \|\| %reboot%="Yes"), "Closed", "Escalated")` | Returns THEN if EXPRESSION is true, otherwise ELSE. |
| `EQUALS(Field_Name, 'Condition')` | `IF(EQUALS(%Department%,'401(k)'), "Then Result", "Else Result")` | Compares a field to a value or another field. |
| `COUNTIF(values, expression_or_value)` | `COUNTIF(%MyArray%, >10)` | Counts the repeated elements that meet the condition. |
| `SUMIF(values, expression_or_value)` | `SUMIF(%MyArray%, >5)` | Sums the elements that meet the condition. |

## String Functions

| Function | Example | Details |
|----------|---------|---------|
| `CASE(value, $CASE)` | `CASE(%Name%, UPPER) == "TONY JONES"`<br>`CASE(%Name%, LOWER) == "tony jones"`<br>`CASE(%Name%, SENTENCE) == "Tony jones"`<br>`CASE(%Name%, TITLE) == "Tony Jones"` | Changes case. `$CASE` must be `LOWER`, `UPPER`, `SENTENCE`, or `TITLE`. |
| `CONCATENATE(value1, value2, ..., valueN)` | `CONCATENATE(%FirstName%, " ", %LastName%) == "Tony Jones"` | Concatenates the values into a single string. |
| `CONTAINS(input_string, value)` | `CONTAINS(%FirstName%, "Tony") == True` | True if the value is contained in the string. |
| `SPLIT(text, splitToken, limit)` | `SPLIT("Tony Jones", " ", 2) == "Tony", "Jones"` | Splits the text on the token. |
| `STRING(value)` | `STRING(%Friends%) == "6.5"` | Converts any value into a string. |
| `SUBSTRING(text, startIndex, endIndex)` | `SUBSTRING("Substring!", 3, 9) == "string"` | Returns the characters between the two indexes. |

## Date and Time Functions

Date functions expect values from a **Date** element.

| Function | Example | Details |
|----------|---------|---------|
| `AGE(dateOfBirth)` | `AGE(%Birthdate%) == 7` | Age in years on today's date. |
| `AGEON(dateOfBirth, futureDate)` | `AGEON(%Birthdate%,"07-09-2024") == 16` | Age in years on a future date. |
| `DATE(value)` | `DATE(%DOB%) == Wed Jul 19 1978 16:00:00 GMT-0700 (PDT)` | Returns the date in full JavaScript format. |
| `DATEDIFF(date1, date2)` | `DATEDIFF(%DOB%,%TODAY%) == 13559` | Difference between two dates in days (always a positive integer). |
| `DAYOFMONTH(date)` | `DAYOFMONTH(%TODAY%) == 2` | Day of the month. |
| `DAYOFWEEK(date)` | `DAYOFWEEK(%TODAY%) == 4` | Day of the week as an integer (Monday = 1, Sunday = 7). |
| `HOUR(date)` | | Current hour in local time. |
| `MINUTE(date)` | | Current minute in local time. |
| `MOMENT()` | `MOMENT(%policyStartDate%).add(1, 'year').subtract(1, 'day')` | Returns a Moment.js moment object for complex date formatting, calculation, manipulation and comparison. Must have a parameter (e.g. `MOMENT(NOW())`). Appending `.calendar()` is a recommended best practice. |
| `MONTH(date)` | `MONTH(%TODAY%) == 9` | Month of the year as an integer. |
| `NOW()` | `NOW() == Thu Aug 27 2019 16:32:00 GMT -0700 (PDT)` | Current date and time in full JavaScript format (milliseconds always 0). `NOW()` uses **UTC**; the `$Vlocity.NOW` environment variable applies the user/org time zone. |
| `TODAY()` | `TODAY() == Thu Aug 27 2019 00:00:00 GMT -0700 (PDT)` | Today's date, time set to midnight. **Known issue:** in Set Values, `TODAY()` returns the previous date — use `TODAY() + ""`, or `MOMENT()` / `TIMESTAMP()` instead. |
| `YEAR(date)` | `YEAR(%TODAY%) == 2019` | Year as an integer. |

## List and Aggregate Functions

Aggregate forms take a **repeating element** (e.g. a field in a repeat Block).

| Function | Example | Details |
|----------|---------|---------|
| `ARRAY(value1, ..., valueN)` | `ARRAY(%Child1%,%Child2%,%Child3%,%Child4%) == [4,3,1,2]` | Returns an array of the element values. |
| `AVERAGE(array)` | `AVERAGE(%Age%) == 2.5` | Aggregate: mean of the repeating element's values. |
| `AVERAGE(value1, ..., valueN)` | `AVERAGE(%Child1%,%Child2%,%Child3%,%Child4%) == 2.5` | Mean of the values provided. |
| `COUNT(array)` | `COUNT(%Age%) == 4` | Aggregate: number of repeated elements. |
| `EXISTS(array_or_value, expression_or_value)` | `EXISTS([%FirstName%,%LastName%], "Tony") == true` | True if the value exists in one or more elements. For Aggregate, pass a repeating element: `EXISTS(%FirstName%,"Tony")`. |
| `MAX(array)` | `MAX(%AGE%) == 4` | Aggregate: largest value of the repeating element. |
| `MAX(value1, ..., valueN)` | `MAX(%Child1%,%Child2%,%Child3%,%Child4%) == 4` | Largest of the values provided. |
| `MIN(array)` | `MIN(%AGE%) == 1` | Aggregate: smallest value of the repeating element. |
| `MIN(value1, ..., valueN)` | `MIN(%Child1%,%Child2%,%Child3%,%Child4%) == 1` | Smallest of the values provided. |
| `SUM(array)` | `SUM(%AGE%) == 10` | Aggregate: sum of the repeating element's values. |
| `SUM(value1, ..., valueN)` | `SUM(%Child1%,%Child2%,%Child3%,%Child4%) == 10` | Sum of the values provided. |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `SUM()` in a Formula element is shown with 2 decimal places even inside `ROUND(...)` — `ROUND(SUM(4.216546546,5.55463551),7)` gives `9.77` | Use `+` instead of `SUM()` for precision: `ROUND(4.216546546+5.55463551,7)` → `9.7711821` |
| `TODAY()` in Set Values returns the previous date | Use `TODAY() + ""`, `MOMENT()` or `TIMESTAMP()` |
| `NOW()` is UTC | Use `$Vlocity.NOW` for the user/org time zone |
