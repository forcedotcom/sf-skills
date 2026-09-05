---
name: experience-ui-bundle-site-generate
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the task involves creating or configuring site infrastructure. Use this skill when creating or configuring a Salesforce Digital Experience Site for hosting a UI bundle. Activate when files matching digitalExperiences/, networks/, customSite/, or DigitalExperienceBundle exist and need modification, or when the user wants to publish, host, or configure guest access for their app. Also use this skill to add multi-language, multi-locale, internationalization, or translation support to such a site by declaring a default locale and additional supported languages via the sfdc_cms__languageSettings content type. DO NOT TRIGGER for LWR (non-React) sites; use experience-lwr-site-generate instead."
metadata:
  version: "1.3"
  domains: ["Experience"]
  minApiVersion: "65.0"
  relatedSkills:
    - experience-lwr-site-generate
  cliTools:
    - tool: ["awk"]
      semver: ">=1.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Digital Experience Site for React UI Bundles
Create and configure Digital Experience Sites that host React UI bundles on Salesforce. This skill generates the minimum necessary site infrastructure — Network, CustomSite, DigitalExperienceConfig, DigitalExperienceBundle, and the `sfdc_cms__site` content type — so a React app can be served from Salesforce.

React sites differ from standard LWR sites: they don't need routes, views, theme layouts, or branding sets. The site acts as a thin container (`appContainer: true`) that delegates rendering to the React UI bundle referenced by `appSpace`.

## Required Properties
Resolve all five properties before generating any metadata. Each has a fallback chain — work through each option in order until a value is found.

| Property | Format | How to Resolve |
|----------|--------|----------------|
| **siteName** | `UpperCamelCase` (e.g., `MyCommunity`) | Ask user or derive from context |
| **siteUrlPathPrefix** | `All lowercase` (e.g., `mycommunity`) | User-provided, or convert siteName to all lowercase with alphanumeric characters only |
| **appNamespace** | String | `namespace` in `sfdx-project.json` → `sf data query -q "SELECT NamespacePrefix FROM Organization" --target-org ${usernameOrAlias}` → default `c` |
| **appDevName** | String | `UIBundle` metadata in the project → `sf data query -q "SELECT DeveloperName FROM UIBundle" --target-org ${usernameOrAlias}` → default to siteName |
| **enableGuestAccess** | Boolean | Ask user whether unauthenticated guest users can access site APIs → default `false` |

The `appNamespace` and `appDevName` properties record the intended UIBundle binding for a **future follow-up update**; they are **not** substituted into `appSpace` at initial site creation. `appSpace` in the `sfdc_cms__site` `content.json` is always `""` at initial creation — see [configure-metadata-digital-experience.md](references/configure-metadata-digital-experience.md) for the reason and the follow-up flow.

### Language Properties
The skill always emits `sfdc_cms__languageSettings` alongside `sfdc_cms__site`. Resolve `defaultLocale` for every site (defaults to `en_US`); resolve `languages` only when the user requests additional languages beyond the default.

| Property | Format | How to Resolve |
|----------|--------|----------------|
| **defaultLocale** | `xx` or `xx_YY` (e.g., `en`, `en_US`) | Ask user → default `en_US` |
| **languages** | List of `{label, locale}` | Only when the user asks for multiple languages, locales, internationalization, or translation support: ask for the additional languages the site supports. When not requested, the languageSettings content declares only the resolved `defaultLocale` as a single-language entry. |

The content-item folder name (`languages`), `title` (`LanguageContent`), and `urlName` (`languagecontent`) are fixed Experience Builder auto-defaults — they are **not** user-authored. See [configure-metadata-language-settings.md](references/configure-metadata-language-settings.md).

## Pre-flight: Target Org Release (Multi-Language Only)
The `sfdc_cms__languageSettings` content type accepts multi-language declarations only on Salesforce Release 264 (API **v68.0** or higher). Sites reduced to a single-locale `en_US` declaration work on any org and do not need this check.

When the user requests multiple languages, verify the target org's maximum supported API version **before writing any metadata**. `sf api request rest` hits `/services/data/` on the instance directly and handles authentication at the transport layer, so the org's true ceiling is returned without any access token entering this script's context.

```bash
MAX_API=$(sf api request rest "/services/data/" --target-org "${usernameOrAlias}" \
          | jq -r '[.[].version | tonumber] | max')

awk -v v="$MAX_API" 'BEGIN{ exit !(v+0 >= 68.0) }' \
  || { echo "ERROR: multi-language site containers require Salesforce Release 264 (API v68.0+). Target org's maximum supported API version is v${MAX_API}. Retarget to a Release 264+ org, or reduce the site to a single-locale (en_US) declaration." >&2; exit 1; }
```

If the check fails, do not write metadata. Report the version mismatch to the user and stop.

## Generation Workflow
### Step 1: Resolve All Required Properties
Determine values for all five required properties and the `defaultLocale` language property before constructing anything. Use the resolution strategies in the tables above, falling through each option until a value is found. Resolve the `languages` property only when the user has requested multiple languages — and when they do, run the [Pre-flight](#pre-flight-target-org-release-multi-language-only) check above before continuing to Step 2.

### Step 2: Create the Project Structure
Use available Salesforce metadata schema and field context for `Network`, `CustomSite`, `DigitalExperienceConfig`, and `DigitalExperienceBundle` to ensure each file uses valid structure.

Create any files and directories that don't already exist, using these paths:

| Metadata Type | Path |
|--------------|------|
| Network | `networks/{siteName}.network-meta.xml` |
| CustomSite | `sites/{siteName}.site-meta.xml` |
| DigitalExperienceConfig | `digitalExperienceConfigs/{siteName}1.digitalExperienceConfig-meta.xml` |
| DigitalExperienceBundle | `digitalExperiences/site/{siteName}1/{siteName}1.digitalExperience-meta.xml` |
| DigitalExperience (sfdc_cms__site) | `digitalExperiences/site/{siteName}1/sfdc_cms__site/{siteName}1/*` |
| DigitalExperience (sfdc_cms__languageSettings) | `digitalExperiences/site/{siteName}1/sfdc_cms__languageSettings/languages/*` |

Each DigitalExperience content-type directory contains only `_meta.json` and `content.json`. Both `sfdc_cms__site` and `sfdc_cms__languageSettings` are always required inside the bundle. The `sfdc_cms__languageSettings` default declares only the resolved `defaultLocale` (e.g. `en_US`); it is extended with additional languages when the user requests multi-language support. No other content types are permitted.

### Step 3: Populate All Metadata Fields
Use the default templates in the docs below. Values in `{braces}` are resolved property references — substitute them with the actual values from Step 1.

| Metadata Type | Template Reference |
|--------------|-------------------|
| Network | [configure-metadata-network.md](references/configure-metadata-network.md) |
| CustomSite | [configure-metadata-custom-site.md](references/configure-metadata-custom-site.md) |
| DigitalExperienceConfig | [configure-metadata-digital-experience-config.md](references/configure-metadata-digital-experience-config.md) |
| DigitalExperienceBundle | [configure-metadata-digital-experience-bundle.md](references/configure-metadata-digital-experience-bundle.md) |
| DigitalExperience (sfdc_cms__site) | [configure-metadata-digital-experience.md](references/configure-metadata-digital-experience.md) |
| DigitalExperience (sfdc_cms__languageSettings) | [configure-metadata-language-settings.md](references/configure-metadata-language-settings.md) |

For URL updates, see [update-site-urls.md](references/update-site-urls.md).

### Execution Note for Step 3: Load and use the docs
- Agents MUST read the full contents of each references/*.md file referenced in Step 3 before attempting to populate metadata fields.
- Use your platform's file-read tool (for example, `read_file`) to load these files in full, then perform placeholder substitution for values in `{braces}` using the resolved properties from Step 1.
- Files to load:
  - `references/configure-metadata-network.md`
  - `references/configure-metadata-custom-site.md`
  - `references/configure-metadata-digital-experience-config.md`
  - `references/configure-metadata-digital-experience-bundle.md`
  - `references/configure-metadata-digital-experience.md`
  - `references/configure-metadata-language-settings.md`
- Read entire file contents, replace placeholders (e.g. `{siteName}`) with the resolved values, then use the expanded templates to populate the metadata XML/JSON content.
  
### Step 4: Do Not Modify Non-Templated Properties
Do not modify any default property values for `Network`, `CustomSite`, `DigitalExperience`, `DigitalExperienceConfig`, or `DigitalExperienceBundle` metadata that are not expressed as variables wrapped in `{braces}`.

## Verification Checklist
Before deploying, confirm:

- [ ] All five required properties are resolved, and `defaultLocale` is resolved (defaulting to `en_US` when the user does not specify one)
- [ ] All metadata directories and files exist per the project structure
- [ ] All metadata fields match the Step 3 templates with `{braces}` substituted only; no other default property values were added or changed
- [ ] `appSpace` in `sfdc_cms__site` `content.json` is the empty string `""` (initial site creation never binds `appSpace`; that is a separate follow-up update after the UIBundle is deployed to the target org)
- [ ] The `sfdc_cms__languageSettings/languages/` files exist. The language declaration satisfies every platform rule below:
  - [ ] `defaultLocale` matches the `locale` of one declared language, which is active
  - [ ] every `locale` is Salesforce-supported, every language is `isActive: true`, each `locale` + `label` combination is unique, and the number of declared languages does not exceed the platform maximum
  - See [configure-metadata-language-settings.md](references/configure-metadata-language-settings.md) for the full rule catalog. Single-language default declarations satisfy every rule trivially.
- [ ] Deployment validates successfully (the `DigitalExperience` type already covers `sfdc_cms__languageSettings` — no change to the `--metadata` list is needed):
```bash
sf project deploy validate --metadata Network CustomSite DigitalExperienceConfig DigitalExperienceBundle DigitalExperience --target-org ${usernameOrAlias}
```

## Common Workflows

### Updating Experience Site URLs

**Use when** user wants to update or change site URLs (urlPathPrefix).

**Steps**:
- [ ] Read [update-site-urls.md](references/update-site-urls.md) to understand the three-component architecture and URL update workflow
- [ ] Follow the step-by-step workflow in the doc to update URLs consistently across all three components (DigitalExperienceConfig, Network, CustomSite)

### Configuring Multi-Language Support

**Use when** user wants the site to support multiple languages, locales, internationalization, or translation — beyond the default-locale-only declaration that every site already receives.

**Steps**:
- [ ] Collect the additional languages the site should support and which locale is the default (resolve the `defaultLocale` and `languages` properties above)
- [ ] Run the [Pre-flight: Target Org Release](#pre-flight-target-org-release-multi-language-only) check — abort if the org is below Release 264 (API v68+)
- [ ] Read [configure-metadata-language-settings.md](references/configure-metadata-language-settings.md) for the templates, field reference, and platform validation rules
- [ ] Extend the `sfdc_cms__languageSettings/languages/content.json` (which already exists with the default locale) to include the additional language entries, then re-run deploy validation

**Note:** This is authoring-only — declared locales deploy cleanly, but locale-in-path routing does not resolve at request time yet. Do not translate the UI bundle content itself; this only declares the site's supported languages.
