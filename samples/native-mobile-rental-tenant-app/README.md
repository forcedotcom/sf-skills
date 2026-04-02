# Native Mobile Rental Tenant App

A sample Agentic Mobile App metadata project for Salesforce. Demonstrates a rental tenant mobile experience scaffold that you can deploy and extend for native iOS or Android.

## Table of Contents

1. [What's Included](#whats-included)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Step-by-Step Setup](#step-by-step-setup)
   - [1. Authenticate Your Org](#1-authenticate-your-org)
   - [2. Deploy Metadata](#2-deploy-metadata)
5. [Testing in the Playground App](#testing-in-the-playground-app)
6. [Resources](#resources)

---

## What's Included

| Path | Description |
| ---- | ----------- |
| `force-app/main/default/digitalExperiences/experiencecontainer/rentalApp/` | Agentic Mobile App Digital Experience metadata for the Rental Tenant app (screen definitions, app metadata, build metadata, and language settings) |
| `config/project-scratch-def.json` | Scratch org definition file for creating a development org |
| `sfdx-project.json` | Salesforce project configuration (default package directory, login URL, API version) |
| `package.json` | Lightweight project scripts for basic build/lint/test placeholders |

---

## Prerequisites

Before you begin, ensure the following are in place.

| Tool | Minimum Version | Install |
| ---- | --------------- | ------- |
| [Salesforce CLI (`sf`)](https://developer.salesforce.com/tools/salesforcecli) | v2+ | `npm install -g @salesforce/cli` |
| [Node.js](https://nodejs.org/) | v22+ | [nodejs.org](https://nodejs.org/) |
| [Git](https://git-scm.com/) | Any recent version | [git-scm.com](https://git-scm.com/) |

Verify your Salesforce CLI version with:

```bash
sf --version
```

---

## Quick Start

Run these commands from this sample directory:

```bash
sf org login web --alias <alias>
sf project deploy start --source-dir force-app --target-org <alias>
```

Replace `<alias>` with your target org alias or username.

---

## Step-by-Step Setup

Use this section if you prefer to run each step manually.

This project is metadata-first and does not require a local UI build step for deployment.

### 1. Authenticate Your Org

Log in to your target org using the Salesforce CLI:

```bash
sf org login web --alias <alias>
```

To verify authentication:

```bash
sf org display --target-org <alias>
```

If you are working with a sandbox, use:

```bash
sf org login web --alias <alias> --instance-url https://test.salesforce.com
```

### 2. Deploy Metadata

Deploy the rental app Digital Experience metadata:

```bash
sf project deploy start \
  --source-dir force-app/main/default/digitalExperiences \
  --target-org <alias>
```

---

## Testing in the Playground App

After deploying your metadata, you can preview the app on a mobile device using the Salesforce Mobile Playground.

1. In VS Code, open the Command Palette with **Cmd+Shift+P** and run:

   ```
   SFDX: Open in Live Preview
   ```

2. A QR code will appear — scan it with your device and follow the on-screen instructions to launch the app in the Playground.

---

## Resources

- [Salesforce Mobile Publisher](https://help.salesforce.com/s/articleView?id=xcloud.branded_apps_exp_cloud.htm&type=5)
- [Salesforce CLI Setup Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_intro.htm)
- [Salesforce DX Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_intro.htm)
- [Salesforce CLI Command Reference](https://developer.salesforce.com/docs/atlas.en-us.sfdx_cli_reference.meta/sfdx_cli_reference/cli_reference_top.htm)
