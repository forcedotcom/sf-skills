# Content display formats

Consistent tables used after every successful `create_cms_content`, `update_cms_content_variant`, `get_content` / `get_content_variant` fetch, and `publish_content` response. Never switch between formats mid-session.

**RENDER AS A REAL MARKDOWN TABLE — do NOT wrap it in a code fence.** The templates below are shown inside ```` ```text ```` fences ONLY so you can see the literal layout. When you emit the table to the user, write the raw markdown (`| Field | Value |` with the `|---|---|` separator row) directly in your chat response with **no surrounding ```` ``` ```` fence and no `text`/`markdown` language tag** — a fenced block renders as preformatted plain text and the pipes do NOT become a table. The pipe rows must be at the start of a line, one row per line, so the chat client renders an actual table. This applies to the fetched content body too (Step 0-U / Step 6): show it as a rendered table, never as pasted plain text.

## Single content — summary table

```text
| Field | Value |
|---|---|
| **Title** | <title> |
| **Content Key** | <contentKey> |
| **Managed Content ID** | <managedContentId> |
| **Content Type** | <contentFqn> |
| **Workspace / Folder** | <contentSpace.label>[/<folder.label>] |
| **URL slug** | <urlName> |
```

Omit fields the response did not include.

## Single content — content body table

```text
| Field | Value |
|---|---|
| **<fieldName>** | <fieldValue> |
| ... | ... |
```

Iterate over all keys in `contentBody` from the response. For nested objects (e.g. `bannerImage` with `source` and `altText`), flatten into readable sub-fields:

```text
| **Banner Image** | <bannerImage.source.ref> |
| **Banner Alt Text** | <bannerImage.altText> |
```

## Bulk content — summary table

```text
Created <N> content items:

| # | Title | Managed Content ID | Variant ID |
|---|---|---|---|
| 1 | <title1> | <id1> | <variantId1> |
| 2 | <title2> | <id2> | <variantId2> |
| ... | ... | ... | ... |
```

Then display each item's content body using the single-item format above, prefixed with its number:

```text
### Item 1: <title1>
| Field | Value |
|---|---|
| ... | ... |

### Item 2: <title2>
| Field | Value |
|---|---|
| ... | ... |
```

## Single publish confirmation

```text
Content published successfully.

  Title:              <title>
  Managed Content ID: <managedContentId>
  Variant ID:         <managedContentVariantId>
```

## Bulk publish confirmation

```text
Published <N> content items successfully.

| # | Title | Managed Content ID | Variant ID |
|---|---|---|---|
| 1 | <title1> | <id1> | <variantId1> |
| 2 | <title2> | <id2> | <variantId2> |
| ... | ... | ... | ... |
```
