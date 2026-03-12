---
name: salesforce-custom-tab
description: Use this skill when users need to create or configure Salesforce Custom Tabs. Trigger when users mention tabs, navigation tabs, object tabs, web tabs, Visualforce tabs, Lightning component tabs, app page tabs, or tab configuration. Also use when users want to add navigation to custom objects, create tabs for external content, or set up Lightning page tabs. Always use this skill for any custom tab work.
---

## When to Use This Skill

Use this skill when you need to:
- Create tabs for objects, web pages, or Visualforce pages
- Add navigation tabs to applications
- Configure tab visibility and access
- Troubleshoot deployment errors related to custom tabs

## Specification

# CustomTab Metadata Specification

## 📋 Overview
Custom tabs for navigating to objects, web content, or Visualforce pages within Salesforce applications.

## 🎯 Purpose
- Provide navigation to custom objects
- Link to external web content
- Access Visualforce pages
- Organize application navigation

## ⚙️ Required Properties

### Core Tab Properties
- **label**: Display name of the tab
- **fullName**: API name of the object (for object tabs)
- **url**: Web URL (for web tabs)
- **page**: Visualforce page name (for Visualforce tabs)

## 🔧 Tab Types

### Object Tabs
- **Purpose**: Navigate to custom or standard objects
- **Required**: `fullName` property (set to object API name)
- **Example**: `<fullName>CustomObject__c</fullName>`

### Web Tabs
- **Purpose**: Link to external websites or web applications
- **Required**: `url` property
- **Example**: `<url>https://example.com</url>`

### Visualforce Tabs
- **Purpose**: Access custom Visualforce pages
- **Required**: `page` property
- **Example**: `<page>CustomPage</page>`

## 🎨 Tab Configuration

### Tab Style
- **Default**: Use standard tab styling
- **Custom**: Can specify custom tab styles if needed

### Tab Visibility
- **Default**: Visible to all users with access
- **Custom**: Can be configured for specific user profiles

## 📱 Supported Applications
- **Standard Apps**: Available in standard Salesforce applications
- **Custom Apps**: Can be included in custom applications
- **Community Apps**: Available in community applications

## 🔗 Integration Points
- **Object Relationships**: Links to related object records
- **Web Content**: External website integration
- **Visualforce Pages**: Custom page functionality
- **Lightning Components**: Modern component integration
## ✅ Best Practices
- Use clear, descriptive tab labels
- Choose appropriate tab types for functionality
- Consider user experience and navigation flow
- Test tab functionality across different applications
- Ensure proper permissions and visibility settings
- Follow consistent naming conventions
