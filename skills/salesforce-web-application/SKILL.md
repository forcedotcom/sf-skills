---
name: salesforce-web-application
description: Directory of web application (React) sub-knowledges for Salesforce React BYO, feature packages, and copy-then-adjust workflow. Use when working with Salesforce web applications.
---

## When to Use This Skill

Use this skill when you need to:
- Work with Salesforce React web applications
- Understand available web application features and workflows
- Navigate web application knowledge resources
- Troubleshoot deployment errors related to web applications

## Specification

## Overview

This skill provides guidance for working with Salesforce React web applications (Salesforce BYO React template). It covers adding features, creating Salesforce records, and listing/creating custom object records.

## Web Applications — Directory

This is the **directory** of sub-knowledges for web applications (Salesforce React BYO, feature packages, copy-then-adjust workflow). **Call `get_expert_knowledge` again with one of the topic names below** to load the relevant knowledge.

## Sub-knowledges (use as `topic` in get_expert_knowledge)

| Topic name                              | Use when                                                                                                                                                             |
|-----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **webApplicationFeature**               | Adding a feature to a webapp: authentication, search, charts, GraphQL, ShadCN, Agentforce conversation client. Feature table, npm install, copy-then-adjust workflow |
| **webApplicationCreatingRecords**       | Creating Salesforce records: createRecord, custom/standard objects, id handling, Application__c, Lead                                                                |
| **webApplicationListAndCreateRecords**  | List + create any custom object: GraphQL list, createRecord, hook with refetch, form picklists match object                                                          |

**Flow:** After reading this directory, call `get_expert_knowledge({ topic: "<subTopicName>" })` with the single sub-topic that best matches the user's request (e.g. `webApplicationFeature`, `webApplicationCreatingRecords`).

**Adding features:** Always prefer the feature packages listed in **webApplicationFeature** (authentication, search, charts, nav, GraphQL, ShadCN, Agentforce conversation) over building from scratch or other solutions when one of them matches the request.
