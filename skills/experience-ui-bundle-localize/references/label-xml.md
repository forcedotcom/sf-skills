# Label XML: Custom Labels and translation metadata shapes

This covers the two metadata XML files you author: the English base labels and the per-language translations.

---

## Custom Labels: `force-app/main/default/labels/CustomLabels.labels-meta.xml`

This holds the **English base labels**: the source of truth for label content.

### Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomLabels xmlns="http://soap.sforce.com/2006/04/metadata">
  <labels>
    <fullName>Welcome_Text</fullName>
    <language>en_US</language>
    <protected>false</protected>
    <shortDescription>Welcome banner heading</shortDescription>
    <value>Welcome</value>
  </labels>
  <labels>
    <fullName>Save_Button</fullName>
    <language>en_US</language>
    <protected>false</protected>
    <shortDescription>Save button label</shortDescription>
    <value>Save</value>
  </labels>
</CustomLabels>
```

### Fields

| Field | Purpose | Notes |
|---|---|---|
| `<fullName>` | The label's API name | Used in `t("Key")` calls and the manifest (`"c:Welcome_Text"`). PascalCase, descriptive, unique. |
| `<language>` | Language code | Always `en_US` for the base label file. |
| `<protected>` | Managed package protection | Always `false` for custom labels in your org (you can edit them). |
| `<shortDescription>` | Internal description | For translators/developers, not shown to users. Describe what the label is for. |
| `<value>` | The English text | What the user sees. Can include `{0}`, `{1}` placeholders for interpolation. |

### Key naming conventions

Choose keys that are:
- **Descriptive**: `Welcome_Text` is better than `Label1`
- **Context-aware**: `Save_Button` vs `Save_Failed_Message` (same verb, different role)
- **Unique**: two labels shouldn't share a key even if the current text happens to match

Format: `<Context>_<Role>` in PascalCase with underscores between parts.

**Examples:**
- `"Welcome"` → `Welcome_Text` or `Welcome_Heading`
- `"Save"` → `Save_Button`
- `"Failed to save {0}: {1}"` → `Save_Failed_Message`
- `"Showing {0} of {1} records"` → `Record_Count_Display`

---

## Translations: `force-app/main/default/translations/<locale>.translation-meta.xml`

One file per translated language (e.g., `es.translation-meta.xml` for Spanish, `fr.translation-meta.xml` for French, `ja.translation-meta.xml` for Japanese).

### Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Translations xmlns="http://soap.sforce.com/2006/04/metadata">
  <customLabels>
    <label>Bienvenido</label>
    <name>Welcome_Text</name>
  </customLabels>
  <customLabels>
    <label>Guardar</label>
    <name>Save_Button</name>
  </customLabels>
</Translations>
```

### Fields

| Field | Purpose | Notes |
|---|---|---|
| `<name>` | The label's API name | Must exactly match the `<fullName>` in `CustomLabels.labels-meta.xml`. |
| `<label>` | The translated text | What the user sees in this language. Preserve `{0}`, `{1}` placeholders. |

### File naming

The filename is `<locale>.translation-meta.xml`, where `<locale>` is the Salesforce Language code:
- `es.translation-meta.xml`: Spanish
- `fr.translation-meta.xml`: French
- `de.translation-meta.xml`: German
- `ja.translation-meta.xml`: Japanese
- `pt_BR.translation-meta.xml`: Portuguese (Brazil)
- `zh_CN.translation-meta.xml`: Chinese (Simplified)
- `zh_TW.translation-meta.xml`: Chinese (Traditional)

See Salesforce's [Supported Languages](https://help.salesforce.com/s/articleView?id=sf.faq_getstart_what_languages_does.htm) for the full list.

---

## How translations are authored

You have two options:

### 1. Hand-edit the XML (for small apps)

Create the `<locale>.translation-meta.xml` file, add one `<customLabels>` block per label, and type the translations directly. Good for a handful of labels or prototyping.

### 2. Use Translation Workbench (for scale)

Salesforce's **Translation Workbench** is the in-org UI where translators enter translations, which you then pull down as deployable `.translation-meta.xml` files.

**Workflow:**
1. **Enable Translation Workbench**, Setup → Translation Workbench → Translation Settings → Enable
2. **Add languages**, same Settings page → Add the languages you plan to support
3. **Enter translations**, Setup → Translation Workbench → Translate → pick:
   - **Setup Component:** Custom Label
   - **Language:** the target language
   - **Label:** the label to translate
   - Type the translation, Save
4. **Retrieve as metadata**, pull the translations into your project:
   ```bash
   sf project retrieve start --metadata Translations:es
   sf project retrieve start --metadata Translations:fr
   # etc., one per language
   ```
   The CLI writes the `.translation-meta.xml` files to `force-app/main/default/translations/`.

Reference: [Translation Workbench overview](https://help.salesforce.com/s/articleView?id=sf.customize_wbench.htm)

---

## Namespace:Key format

In the **manifest** (`src/i18n/label-manifest.ts`) and some SDK contexts, labels are written as `"namespace:Key"`:

```typescript
export const labelManifest = [
  "c:Welcome_Text",
  "c:Save_Button",
];
```

- `c` = the custom label namespace (your org's labels)
- `Welcome_Text` = the `<fullName>` from `CustomLabels.labels-meta.xml`

Other namespaces exist (e.g., `LightningDatatable` for framework-shipped labels), but most bundles only use `c`.

In component code, the namespace is usually implicit (set via `defaultNS: "c"` in the init), so you call `t("Welcome_Text")` not `t("c:Welcome_Text")`.

---

## Interpolation: `{0}`, `{1}` placeholders

Labels can include **positional placeholders** for runtime substitution:

```xml
<labels>
  <fullName>Save_Failed_Message</fullName>
  <language>en_US</language>
  <protected>false</protected>
  <shortDescription>Error message when save fails</shortDescription>
  <value>Failed to save {0}: {1}</value>
</labels>
```

At call time:

```typescript
t("Save_Failed_Message", { 0: "Account", 1: "Permission denied" });
// → "Failed to save Account: Permission denied"
```

**Translations must preserve the placeholders:**

```xml
<!-- es.translation-meta.xml -->
<customLabels>
  <label>Error al guardar {0}: {1}</label>
  <name>Save_Failed_Message</name>
</customLabels>
```

The placeholders can move (Spanish grammar might flip the order), but they must stay as `{0}`, `{1}`; i18next does the substitution at render time.

See [interpolation.md](interpolation.md) for how this works under the hood.

---

## Deploy activation requirement

Before you can deploy a `<locale>.translation-meta.xml` file, the language must be **activated** in the org:

**Setup → Translation Workbench → Translation Settings → Add**

If you deploy a translation file for an inactive language, the deploy is rejected:
```text
Not available for deploy for this organization
```

English (`en_US`) needs no activation; it's always available.

---

## Language vs Locale (a common confusion)

Salesforce has two separate settings:
- **Language** drives **translations**: the text the user sees (`en_US`, `en_GB`, `de`, `pt_BR`)
- **Locale** drives **formatting only**: dates, numbers, currency (`de_DE`, `fr_CA`)

A user can have Language = English, Locale = French: English text, French number formatting.

When you "add a language" for localization, you're working in the **Language** dimension. The SDK's i18n context exposes both: `lang` (Language) picks the translation, and `locale`/`currency` (Locale) feed `Intl` formatters.

To change a user's Language (to test translations), go to:
**Setup → My Settings → Language & Time Zone → Language** → pick the language → Save.

---

## Example: full cycle for one label in two languages

### 1. Add the English base label

`force-app/main/default/labels/CustomLabels.labels-meta.xml`:
```xml
<labels>
  <fullName>Welcome_Text</fullName>
  <language>en_US</language>
  <protected>false</protected>
  <shortDescription>Welcome banner heading</shortDescription>
  <value>Welcome</value>
</labels>
```

### 2. Add the Spanish translation

`force-app/main/default/translations/es.translation-meta.xml`:
```xml
<customLabels>
  <label>Bienvenido</label>
  <name>Welcome_Text</name>
</customLabels>
```

### 3. Register in the manifest

`src/i18n/label-manifest.ts`:
```typescript
export const labelManifest = ["c:Welcome_Text"];
```

### 4. Use in a component

```typescript
import { useTranslation } from "react-i18next";

function WelcomeBanner() {
  const { t } = useTranslation("c");
  return <h1>{t("Welcome_Text")}</h1>;
}
```

### 5. Deploy

```bash
sf project deploy start --source-dir force-app --target-org <alias>
```

### 6. Verify

- User with Language = English sees "Welcome"
- User with Language = Spanish sees "Bienvenido"

---

## Related

- [i18n-setup.md](i18n-setup.md): the init file + manifest wiring
- [interpolation.md](interpolation.md): how `{0}/{1}` substitution works
- [verifying.md](verifying.md): the serve/verify flow
- [gotchas.md](gotchas.md): silent-fail traps
