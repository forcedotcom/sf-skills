# flexipage:richText — Rich Text

## Purpose

Displays HTML-formatted rich text content on a page. Supports text formatting, headings, lists, links, and inline styles. Content is static (not data-bound).

## Supported Page Types

- RecordPage
- AppPage
- HomePage

## Property Table

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| richTextValue | String (HTML-encoded) | Yes | — | HTML content, entity-encoded for XML |
| decorate | Boolean | No | true | Show card-style border/decoration around the content |

## Property Inference Rules

| User Intent | Inferred Properties |
|-------------|-------------------|
| "add rich text with {content}" | `richTextValue` = HTML-encoded version of content |
| "add a heading {text}" | `richTextValue` = `&lt;p&gt;&lt;b style=&quot;font-size: 16px;&quot;&gt;{text}&lt;/b&gt;&lt;/p&gt;` |
| "add a link to {url}" | `richTextValue` = `&lt;p&gt;&lt;a href=&quot;{url}&quot; rel=&quot;noopener noreferrer&quot; target=&quot;_blank&quot;&gt;{text}&lt;/a&gt;&lt;/p&gt;` |
| "no border" or "borderless" | `decorate` = `false` |
| "with card border" or "in a card" | `decorate` = `true` |

## HTML Encoding Rules

**CRITICAL:** The `richTextValue` must be double-encoded for XML:
1. Write the desired HTML content
2. Entity-encode ALL HTML characters:
   - `&` -> `&amp;` (encode FIRST)
   - `<` -> `&lt;`
   - `>` -> `&gt;`
   - `"` -> `&quot;`

**Example:** To display `<b>Hello</b>`, the value must be `&lt;b&gt;Hello&lt;/b&gt;`

**Supported HTML tags:**
- `<p>` — paragraphs (required wrapper for all content)
- `<b>` — bold
- `<u>` — underline
- `<i>` — italic
- `<a href="..." rel="noopener noreferrer" target="_blank">` — links
- `<span style="...">` — inline styling
- `<br>` or `<br />` — line breaks

**Supported inline styles:**
- `font-size: Npx` (e.g., `12px`, `14px`, `16px`, `18px`)
- `color: #hex` or `color: colorname`
- `text-align: left|center|right`
- `background-color: #hex`

## XML Example

```xml
<itemInstances>
    <componentInstance>
        <componentInstanceProperties>
            <name>richTextValue</name>
            <value>&lt;p style=&quot;text-align: center;&quot;&gt;&lt;b style=&quot;font-size: 16px;&quot;&gt;Welcome to the Account Page&lt;/b&gt;&lt;/p&gt;&lt;p&gt;Use this page to manage account details and related records.&lt;/p&gt;</value>
        </componentInstanceProperties>
        <componentInstanceProperties>
            <name>decorate</name>
            <value>true</value>
        </componentInstanceProperties>
        <componentName>flexipage:richText</componentName>
        <identifier>flexipage_richText</identifier>
    </componentInstance>
</itemInstances>
```

## Edge Cases

- Never put raw HTML in `<value>` tags — always entity-encode
- Encode `&` FIRST before encoding `<` and `>` to avoid double-encoding `&amp;lt;`
- Multiple rich text components on same page: increment identifier (`flexipage_richText`, `flexipage_richText2`)
- Empty content is invalid — always include at least one `<p>` element
- Links must include `rel="noopener noreferrer" target="_blank"` for security
- Can be placed in any region
- Keep content concise — rich text is for static labels/instructions, not data display
