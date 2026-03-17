---
name: salesforce-fragment
description: Use this skill when users need to create or edit Salesforce Fragments (reusable UI pieces). Trigger when users mention fragments, UEM blocks, reusable UI templates, structured rendering across Slack/Mobile/LEX, or block-based layouts. Also use when users want to create unified experience components. Always use this skill for any fragment work.
---

## When to Use This Skill

Use this skill when you need to:
- Create reusable UI fragments for Salesforce experiences
- Generate Fragment metadata following UEM structure
- Build fragments for Slack, Mobile, LEX, and other Salesforce experiences
- Troubleshoot deployment errors related to Fragments

## Specification

# Fragment Generation Guide

## 📋 Overview
Fragments are reusable pieces of UI similar to templates, with placeholders for actual data values. The purpose of this file is to assist developers in creating and editing fragments.

## 🎯 Purpose
Fragments render data in a structured and unified way across various Salesforce experiences like Slack, Mobile, LEX etc

## ⚙️ Composition
A fragment is a UEM (Unified Experience Model) tree of blocks and regions. The fragment you return must follow the Typescript interfaces below:

```ts
interface BlockType {
    type: 'block'
    definition: string  // {namespace}/{blockName}
    attributes?: Record<string, any>
    children?: (BlockType | RegionType)[]
}

interface RegionType {
    type: 'region'
    name: string
    children: BlockType[]
}
```

---

## 🔧 Available Metadata Actions

### When to Use Each Action

#### discoverUiComponents

**When:** You want to see what block components are available for fragments.

**Purpose:** Discover the palette of available blocks that can be used in fragment composition.

**Input Parameters:**
- `pageType` (required): "FRAGMENT"
- `pageContext` (optional): JSON object - not required for FRAGMENT type
- `searchQuery` (optional): String to filter components by name or description

**Returns:** List of components with:
- `definition`: Fully qualified name (e.g., "namespace/definiton")
- `description`: Component description
- `label`: Human-readable label
- `attributes`: Optional attribute metadata

**Use for:** Finding available blocks before building your fragment structure.

#### getUiComponentSchemas

**When:** You know which components you want but need to understand their properties and attributes.

**Purpose:** Get detailed JSON schemas for component configuration, including property types, required vs optional fields, and validation rules.

**Input Parameters:**
- `pageType` (required): "FRAGMENT"
- `pageContext` (optional): JSON object - not required for FRAGMENT type
- `componentDefinitions` (required): List of fully qualified names (e.g., ["namespace/definition"])
- `includeKnowledge` (optional): Boolean, defaults to true - includes additional component-specific guidance

**Returns:**
- `componentSchemas`: List of results (supports partial failures)
- **Success entries**: Contains JSON schema with property definitions, types, constraints
- **Failure entries**: Contains error message explaining why schema couldn't be retrieved
- `$defs`: Schema definitions and references (if schema transformation applied)

**Use for:** Understanding how to configure component attributes before adding blocks to your fragment.

**Key Feature:** Supports partial failures - if some components can't be found, you still get schemas for the successful ones.

---

## 💡 Typical Workflow

1. **Discover Available Blocks**
- Use `discoverUiComponents` to explore what blocks are available
- Optional: Use `searchQuery` to filter by keywords (e.g., "text", "button", "image")

2. **Select Components**
- Choose blocks that fit your fragment requirements
- Note their fully qualified definitions (e.g., "namespace/definition")

3. **Get Component Schemas**
- Use `getUiComponentSchemas` with the selected component definitions
- Review the JSON schemas to understand required and optional attributes

4. **Build Fragment**
- Construct your fragment using the UEM tree structure
- Configure block attributes according to the schemas
- Use the TypeScript interfaces defined above

---

## ⚠️ Important Notes

- Block definitions always follow the `{namespace}/{blockName}` convention
- Use the same definition format returned by `discoverUiComponents` when calling `getUiComponentSchemas`
- The FRAGMENT page type doesn't require additional `pageContext` parameters
- Schemas include both required and optional attributes - review carefully to ensure valid configuration
