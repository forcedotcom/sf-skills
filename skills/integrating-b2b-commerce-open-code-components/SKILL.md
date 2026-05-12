---
name: integrating-b2b-commerce-open-code-components
description: Integrate Salesforce B2B Commerce open source components from GitHub into B2B Commerce stores. Use when users mention "integrate open code components", "open source B2B commerce", "add open code components", "forcedotcom/b2b-commerce-open-source-components", or want to add open source commerce components to their store. Copies all components and labels so they become available in Experience Builder.
license: Apache-2.0
compatibility: Requires Salesforce CLI (sf), Git, B2B Commerce license, Experience Builder access, and internet connectivity
allowed-tools: Bash Read Write
metadata:
  author: afv-library
  version: "1.0"
---

## When to Use This Skill

Use this skill when you need to:
- Integrate all open source B2B Commerce components into a store
- Add open source components to a new or existing B2B Commerce store
- Make open code components available in Experience Builder

## Rules

1. **Always explain before executing.** Before running any command, you MUST tell the user what the command does and why you are running it. Never just show a raw command and ask for permission. The user should be able to read your explanation and understand the purpose before approving.

## Overview

This skill copies all open source B2B Commerce components from the official Salesforce repository (https://github.com/forcedotcom/b2b-commerce-open-source-components) into a B2B Commerce store's site metadata. After integration, the components appear in the Experience Builder component palette.

---

## Startup Flow

When this skill is triggered, perform these checks automatically before copying.

### Check 1: Open Source Repository

Verify the repo is cloned at `.tmp/b2b-commerce-open-source-components`:

1. **If directory does not exist:** Tell user: "I'm cloning the official B2B Commerce open source components repository from GitHub into a local `.tmp/` folder. This gives us access to all the open code components."
   Then run: `git clone https://github.com/forcedotcom/b2b-commerce-open-source-components .tmp/b2b-commerce-open-source-components`
2. **If directory exists** and contains `force-app/main/default/sfdc_cms__lwc` and `sfdc_cms__label`, present options:
   > "Open source repository is already cloned. How would you like to proceed?"
   > 1. **Reuse existing** — Use the already cloned repository
   > 2. **Re-clone** — Remove and clone fresh from GitHub
3. **If directory exists but structure is invalid:** Tell user: "The cloned repository has an unexpected structure. I'll remove it and clone a fresh copy."
   Then remove and re-clone.
4. **If clone fails:** inform user and abort

### Check 2: Store and Site Metadata

Verify a store is selected and site metadata is available locally:

1. Tell user: "I'm checking if your project already has B2B store metadata locally."
   Check if `force-app/main/default/digitalExperiences/site/` contains any store directories.
2. **If store metadata exists:** use it. If multiple stores found, ask user to select one.
3. **If no store metadata found:** Tell user: "No store metadata found locally. I'll help you create or select a B2B store and retrieve its metadata."
   Then delegate to the **creating-b2b-commerce-store** skill (`skills/creating-b2b-commerce-store/SKILL.md`).

**Required state** after both checks:
- **Store name** — the selected `fullName` value (e.g., `My_B2B_Store1`)
- **Site metadata path** — `force-app/main/default/digitalExperiences/site/<store-name>/`
- **Repo path** — `.tmp/b2b-commerce-open-source-components/`

---

## Integration Task

Copy all components and labels from cloned repo to site directory:

- **Source:** `.tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/*` and `sfdc_cms__label/*`
- **Destination:** `force-app/main/default/digitalExperiences/site/<store-name>/sfdc_cms__lwc/` and `sfdc_cms__label/`

**Steps:**

1. Tell user: "I'm checking if open code components already exist in your store's site metadata."
   Check if destination directories already contain files.
2. If files exist, present options:
   > "Components already exist in **{store-name}**. How would you like to proceed?"
   > 1. **Overwrite all** — Replace all existing components with latest from repo
   > 2. **Copy only new** — Skip existing components, copy only ones not yet present
3. Tell user: "I'm now copying all open code LWC components from the cloned repository into your store's site metadata directory."
   Copy all component directories from source to destination.
4. Tell user: "I'm copying the associated label files that these components need."
   Copy all label directories from source to destination.
5. Report: "Copied X components and Y label sets"

**Output:**
```
✅ Integration Complete!

Copied: X components and Y label sets to <store-name>

Next Steps:
1. Deploy: sf project deploy start -d force-app/main/default/digitalExperiences/site/<store-name>
2. Open Experience Builder and use new components from the palette
3. Publish your site when ready
```

---

## Example Interaction

**User:** "Integrate open code components to my store"

**Agent:** "I'm checking if the open source components repository is already cloned locally..."

**Agent:** _(repo exists)_
> "Open source repository is already cloned. How would you like to proceed?"
> 1. **Reuse existing** — Use the already cloned repository
> 2. **Re-clone** — Remove and clone fresh from GitHub

**User:** "1"

**Agent:** "I'm checking if your project already has B2B store metadata locally..."
- ✓ Found store metadata for My_B2B_Store1

**Agent:** "I'm checking if open code components already exist in your store's site metadata..."

**Agent:** _(files exist)_
> "Components already exist in **My_B2B_Store1**. How would you like to proceed?"
> 1. **Overwrite all** — Replace all existing components with latest from repo
> 2. **Copy only new** — Skip existing components, copy only ones not yet present

**User:** "1"

**Agent:** "I'm now copying all open code LWC components from the cloned repository into your store's site metadata directory..."
**Agent:** "I'm copying the associated label files that these components need..."
- ✓ Copied 45 components and 38 label sets

```
✅ Integration Complete!

Copied: 45 components and 38 label sets to My_B2B_Store1

Next Steps:
1. Deploy: sf project deploy start -d force-app/main/default/digitalExperiences/site/My_B2B_Store1
2. Open Experience Builder and use new components from the palette
3. Publish your site when ready
```

---

## Error Handling

| Error | Message | Action |
|-------|---------|--------|
| Store not found | "Store '{name}' not found in org." | List stores again |
| Git clone failed | "Failed to clone repository. Check internet connection." | Retry or abort |
| Invalid repo structure | "Repository structure has changed. Expected sfdc_cms__lwc and sfdc_cms__label." | Warn user, abort |
| File copy failed | "Failed to copy files. Check file permissions." | Show error details |

---

## Verification Checklist

- [ ] Startup Flow completed: repo cloned, store metadata available
- [ ] Components copied to correct destination path (`sfdc_cms__lwc/`)
- [ ] Labels copied to correct destination path (`sfdc_cms__label/`)
- [ ] No file permission errors during copy
- [ ] Deployment command provided and user informed about testing

---

## Anti-Patterns

**DO NOT:** copy without checking for existing files first, modify component code or labels from the open source repo, add components to wrong site directory, deploy without user confirmation.

**DO:** warn before overwriting existing files, verify paths before operations, report count of copied components and labels, inform user of next steps.
