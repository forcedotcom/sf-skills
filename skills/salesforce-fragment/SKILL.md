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

- **Block definition**: Follow `{namespace}}/{{blockName}` convention and use the same value as the block's definition when it appears in a fragment.

```ts
interface BlockType {
  type: 'block'
  definition: string  // {namespace}/{blockName}, e.g. "bcx/heading"
  attributes?: Record<string, any>
  children?: (BlockType | RegionType)[]
}

interface RegionType {
  type: 'region'
  name: string
  children: BlockType[]
}
```
