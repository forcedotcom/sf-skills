# configuring-connected-apps

Salesforce Connected Apps & External Client Apps skill for Claude Code.

## Overview

This skill helps you create and manage:

- **Connected Apps**: Traditional OAuth-enabled applications for Salesforce integration
- **External Client Apps (ECAs)**: Modern, security-first applications with enhanced controls (API 61.0+)

## Features

| Feature | Description |
|---------|-------------|
| App Generation | Create Connected Apps or ECAs from requirements |
| Security Scoring | 120-point validation across 6 categories |
| Template Library | Pre-built templates for common OAuth flows |
| Migration Support | Guidance for Connected App → ECA migration |
| Best Practices | Built-in security recommendations |

## Quick Start

### Create a Connected App

```
Use the configuring-connected-apps skill to create a Connected App named "MyIntegration"
with API and RefreshToken scopes for server-to-server integration.
```

### Create an External Client App

```
Use the configuring-connected-apps skill to create an External Client App named
"MobileApp" for a mobile application with PKCE enabled.
```

### Review Existing Apps

```
Use the configuring-connected-apps skill to review and score my existing Connected Apps
for security best practices.
```

## Scoring Categories

| Category | Points | Focus |
|----------|--------|-------|
| Security | 30 | PKCE, rotation, certificates |
| OAuth Configuration | 25 | Callbacks, flows, tokens |
| Metadata Compliance | 20 | Required fields, API version |
| Best Practices | 20 | Minimal scopes, admin approval |
| Scopes | 15 | Least privilege principle |
| Documentation | 10 | Description, contact info |

## When to Use Each App Type

### Choose Connected App When:
- Simple, single-org integration
- Legacy system compatibility needed
- Quick setup is priority
- No cross-org deployment needs

### Choose External Client App When:
- Multi-org or ISV distribution
- Automated secret rotation required
- Enhanced audit logging needed
- Full metadata compliance required
- Packaging in 2GP

## Directory Structure

```
configuring-connected-apps/
├── skills/
│   └── configuring-connected-apps/
│       └── SKILL.md          # Main skill definition
├── assets/
│   ├── connected-app-basic.xml
│   ├── connected-app-oauth.xml
│   ├── connected-app-jwt.xml
│   ├── connected-app-canvas.xml
│   ├── external-client-app.xml
│   ├── eca-global-oauth.xml
│   ├── eca-oauth-settings.xml
│   └── eca-policies.xml
├── references/
│   └── example-usage.md
├── references/
│   ├── oauth-flows-reference.md
│   ├── security-checklist.md
│   └── migration-guide.md
└── README.md
```

## Dependencies

- **deploying-metadata**: For deploying apps to orgs
- **sf-metadata**: For creating related metadata (Named Credentials)
