---
name: salesforce-webapp-feature-micro-frontend-generating-micro-frontend-lwc
description: Generate a Micro Frontend LWC component for a Web Application.
license: Proprietary. LICENSE.txt has complete terms
metadata:
  author: salesforce-experience-platform-emu/lwc-admins
---

# Micro Frontend generation (workflow)

When the user wants a Micro Frontend for a Web Application, follow this workflow.

## 1. Install the dependency

Micro Frontends are generated using the `generate-micro-frontend` CLI command from the `@salesforce/micro-frontends-experimental` package.

```bash
npm install @salesforce/micro-frontends-experimental
```

The dependency should be added to the project's `package.json` dependencies.

## 2. Identify the Web Application

- Verify the Web Application exists in `force-app/main/default/webapplications/<web-app-name>/`.
- Confirm the Web Application has a `lightningOut` target in its `webapplication-meta.xml` file.
- If no Web Application exists, the user must create one first using the Web Apps template system.

## 3. Generate the Micro Frontend component

Run the `generate-micro-frontend` command with the Web Application name from the root of an SFDX project:

```bash
npx generate-micro-frontend <web-app-name>
```

This creates:

- A custom wrapper LWC component in `force-app/main/default/lwc/<webAppName>/`. This is the "Micro Frontend component".
- The static `microFrontendShell` component that handles iframe communication.

Notes:

- The command may be added to the project's `package.json` scripts for convenience.
- The Micro Frontend component uses the Web Application name (e.g. `my-web-app/`) in camelCase for its folder and file names (e.g. `myWebApp/myWebApp.js`, `myWebApp/myWebApp.html`).

## 4. Customize the Micro Frontend component metadata

Edit the `<webAppName>.js-meta.xml` file to:

- Set appropriate `targets` (e.g. `lightning__HomePage`, `lightning__AppPage`, `lightning__RecordPage`, `lightningCommunity__Page`)
- Add `targetConfigs` for page-specific properties
- Optionally update the `masterLabel` and `description`

Example:

```xml
<targetConfigs>
    <targetConfig targets="lightning__HomePage">
        <property name="height" type="Integer" min="0" max="600" default="300" />
    </targetConfig>
</targetConfigs>
```

## 5. Pass properties to the Micro Frontend component

Edit the `<webAppName>.js` file to customize the `properties` getter:

```javascript
@api height;

@api get properties() {
    return {
        height: this.height,
        // Add any other data your Web Application needs
    };
}
```

All properties are passed to the embedded Web Application via `postMessage` and can be accessed in the app's code.

## 6. Deploy and test

Deploy the Micro Frontend component using standard SF CLI commands:

```bash
sf project deploy start --source-dir force-app/main/default
```

Add the component to a page using Lightning App Builder or Experience Builder and verify it loads correctly.

# Micro Frontend component customization examples

## Record page example

Command to generate a Micro Frontend component for the `my-site` Web Application:

```bash
npx generate-micro-frontend my-site
```

`mySite.js-meta.xml` file with a `lightning__RecordPage` target:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>Micro Frontend for "My Site"</masterLabel>
    <targets>
        <target>lightning__RecordPage</target>
    </targets>
        <targetConfigs>
        <targetConfig targets="lightning__RecordPage">
            <property name="mode" type="String" default="dark" />
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

`mySite.js` file with public properties and `properties` getter:

```js
// Micro Frontend component
export default class mySite extends LightningElement {
  @api recordId;
  @api mode;

  @api get properties() {
    // This data is passed to the Micro Frontend
    return {
      recordId: this.recordId, // automatically populated for lightning__RecordPage target
      mode: this.mode, // matches the mode targetConfig
    };
  }
}
```
