# Source Format Handling

The customer SOP can arrive in any of the formats below — sometimes
several at once. This file gives the exact extraction recipe per
format so action records and endpoint values can be located reliably,
and explains how to decide whether an embedded image carries data or
is illustrative.

> **Rule of thumb**: the action list (which OBM / Remote Site to
> update) and the endpoint table (the actual URL values) are
> frequently in **different files or different tabs / pages**. Always
> read every source the user supplies before deciding a value is
> missing. If a value still cannot be located after exhausting every
> source, skip the entry — never emit empty / placeholder fields.

---

## PDF (`.pdf`)

```python
import pypdf
reader = pypdf.PdfReader(path)
for i, page in enumerate(reader.pages):
    text = page.extract_text()
```

- Many enterprise SOPs are slide decks exported to PDF — the text
  layer is usually present, but tables may flatten oddly. Inspect the
  raw extracted text rather than trusting visual alignment.
- For section navigation, search case-insensitively for: "Post
  Refresh", "Post-Refresh", "Post Copy", "Post-Copy", "After
  Refresh", "Update <X>".
- If `extract_text()` returns empty or near-empty for a page, the
  page is likely an embedded image. OCR it:

```python
import pdfplumber, pytesseract
with pdfplumber.open(path) as pdf:
    for page in pdf.pages:
        if not (page.extract_text() or "").strip():
            img = page.to_image(resolution=200).original
            text = pytesseract.image_to_string(img)
```

- If `pytesseract` is unavailable, fall back to `pdftotext -layout`
  (Poppler) and `tesseract` CLI.

## xlsx (`.xlsx`)

```python
import openpyxl
wb = openpyxl.load_workbook(path, data_only=True)
for sname in wb.sheetnames:
    ws = wb[sname]
    for row in ws.iter_rows(values_only=False):
        for cell in row:
            ...
```

- **Always read every sheet.** Customer planners routinely split the
  task list and the URL table across tabs (real example: Michelin UAT
  Refresh Planner — task list in `Integration (Indus)`, URL table in
  `Evolution SFA` columns K/L/M).
- Iterate **every column** up to `ws.max_column`. Some sheets have
  data far past column M (e.g., column index 10000+) that the visible
  layout hides.
- Read with `data_only=True` so cached formula values are returned.
- Check `cell.comment` for free-text annotations that often contain
  the post-refresh value.
- Look for canonical column headers: `Outbound Message`, `Remote
  Site`, `Object`, `Endpoint`, `Endpoint URL`, `Prod Endpoint URL`,
  `UAT Endpoint URL`, `Post-refresh URL`. The post-refresh value is
  the one to emit.
- For embedded images on a sheet, use `ws._images` (or unzip the
  xlsx and inspect `xl/media/`) — see the image rules below.

## csv (`.csv`)

```python
import csv
with open(path, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        ...
```

- Treat the same way as a single xlsx sheet — look for the canonical
  column headers above.

## JSON (`.json`)

- If the customer already supplies a JSON document, scan every key
  for the canonical names (`outboundMessage`, `endpointUrl`, `object`,
  `remoteSiteUrl`, `label`, `name`). Be tolerant of casing
  (`endpointURL`, `EndpointUrl`, `endpoint_url`).
- Customer JSON might already be partially in the target shape; do
  not blindly copy it through — re-validate every entry against
  `assets/json_schema.json` and the catalog.

## docx (`.docx`)

```python
from docx import Document
doc = Document(path)
for p in doc.paragraphs:
    ...
for tbl in doc.tables:
    for row in tbl.rows:
        for cell in row.cells:
            ...
```

- Extract both paragraph text and table cells. Word tables
  frequently hold the endpoint table.
- Inline images (`doc.inline_shapes`) follow the image rules below.

## Markdown / plain text (`.md`, `.txt`)

- Read directly with the `Read` tool. Tables in pipe-delimited
  Markdown are easy to parse — split on `|`.

## Pasted excerpts in the conversation

- The user may paste content directly. Treat it as plain text.
- If they paste an image (drag-drop), use the `Read` tool on the
  image path and follow the image rules below.

---

## Images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`)

Two kinds of image arrive in customer SOPs:

| Kind | Examples | What to do |
|------|----------|------------|
| **Data-bearing** | screenshot of the Outbound Messages list page showing real Names + Endpoint URLs; captured Remote Site Settings table with real URLs; spreadsheet snippet pasted as a screenshot; configuration page where the endpoint values are visible | OCR and treat the values as authoritative for the entries they cover |
| **Illustrative** | "this is what the setup screen looks like" with placeholder values; architecture diagram showing system topology; UI flow chart; redacted/blurred values; screenshot whose surrounding text says "for example" / "as shown below your values will look like this" | Do NOT extract values — the image is documentation, not data |

### Heuristic — is this image data-bearing?

Yes (use the values), if any of:

- The surrounding paragraph references it as the source of truth:
  "the values listed below", "as captured in the spreadsheet
  above", "copy these into the post-refresh setup", "the URLs you
  copied before the refresh".
- The image shows a Salesforce setup table (Outbound Messages list,
  Remote Site Settings list, Custom Metadata Type list) with real
  values for known catalog types.
- Real endpoint URLs are visible (full domain, not redacted, not
  obviously a placeholder like `https://example.com/...`).
- The image directly precedes or follows a "Post Refresh Steps"
  heading and lists the entities named in that step.

No (skip the image), if any of:

- Surrounding text says "for example", "as a sample", "this is what
  it will look like", "your real values will differ".
- The values shown are placeholders (`PROD_URL`, `<your domain>`,
  `username/password`, all-`x` or all-`*` redaction).
- The image is a flowchart / arch diagram / sequence diagram.
- The image is a UI walkthrough screenshot whose purpose is to show
  *where* to click, not *what* to enter.
- The image is a stock screenshot of the Salesforce Help / Setup
  interface unrelated to the customer's actual values.

### OCR recipe

```python
from PIL import Image
import pytesseract
img = Image.open(image_path)
text = pytesseract.image_to_string(img)
```

For higher accuracy on tables:

```python
text = pytesseract.image_to_string(img, config="--psm 6")
```

`--psm 6` treats the image as a single uniform block of text (good
for tables). Try `--psm 4` for column-of-text layouts.

If `pytesseract` is unavailable, **read the image with the `Read`
tool and transcribe the visible values into a temporary text
buffer** — the multimodal `Read` reliably picks up table contents
in screenshots.

### After OCR

- Normalise whitespace, strip trailing zero-width chars.
- Fix common OCR confusions in URLs: `0`/`O`, `1`/`l`/`I`, `:`/`;`,
  `/`/`\`, `_`/`—`. Cross-check with surrounding text where possible.
- If two URL columns are present (Prod / UAT), use the
  **post-refresh** column.
- Treat OCR'd values like any other extracted value — if the text
  is unreadable or ambiguous, skip the entry and surface it. Do
  NOT guess to fill a field.

---

## Multi-source merge

When the user supplies multiple files:

1. Read every file end-to-end first; build an internal map of
   "named entity → values found".
2. Identify the action list source (which OBMs / Remote Sites need
   updating) — usually the file with "Post Refresh Steps".
3. For each named action, look up the value in the map. If found in
   any source, use it. If not found anywhere, skip and surface.
4. Emit one entry per (configuration, label) pair — do not duplicate
   when the same OBM appears in multiple sources.

---

## Failure modes to surface in the response

When you skip an entry, list it explicitly so the customer can
correct the source. Use one of these labels in the response:

- **Missing value** — the entity is named but no concrete value was
  found in any supplied source.
- **Out of catalog** — the action targets a configuration type not
  yet supported (Custom Labels, Connected Apps, etc.).
- **Unreadable image** — an image was data-bearing but OCR returned
  unintelligible output.
- **Ambiguous Object (OutboundMessages only)** — the OBM name does
  not reveal the target SObject and no supplemental table provides it.
