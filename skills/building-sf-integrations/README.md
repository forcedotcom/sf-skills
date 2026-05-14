# building-sf-integrations

Creates comprehensive Salesforce integrations with 120-point scoring. Build secure Named Credentials, External Services, REST/SOAP callouts, Platform Events, and Change Data Capture patterns.

## Features

- **Named Credentials**: OAuth 2.0, JWT Bearer, Certificate, API Key authentication patterns
- **External Credentials**: Modern API 61+ credential architecture with Named Principals
- **External Services**: Auto-generate Apex from OpenAPI/Swagger specs
- **Callout Patterns**: Synchronous and asynchronous REST/SOAP implementations
- **Event-Driven**: Platform Events and Change Data Capture subscribers
- **120-Point Scoring**: Automated validation across 6 categories
- **Automation Scripts**: Configure credentials without UI (ConnectApi)


## Quick Start

### 1. Invoke the skill

```
Skill: building-sf-integrations
Request: "Create a Named Credential for Stripe API with OAuth"
```

### 2. Answer requirements questions

The skill will ask about:
- Integration type (REST, SOAP, Event-driven)
- Authentication method (OAuth, JWT, Certificate, API Key)
- External system details (URL, rate limits)
- Sync vs Async requirements

### 3. Deploy and configure

```bash
# Deploy credential metadata
sf project deploy start --metadata NamedCredential:StripeAPI --target-org MyOrg

# Run automation script to set API key
./scripts/configure-named-credential.sh MyOrg
```

## Scoring System (120 Points)

| Category | Points | Focus |
|----------|--------|-------|
| Security | 30 | Named Credentials, no hardcoded secrets, OAuth scopes |
| Error Handling | 25 | Retry logic, timeouts, specific exceptions |
| Bulkification | 20 | Batch callouts, event batching |
| Architecture | 20 | Async patterns, service separation |
| Best Practices | 15 | Governor limits, idempotency |
| Documentation | 10 | Clear intent, API versioning |

**Thresholds**: ⭐⭐⭐⭐⭐ 90+ | ⭐⭐⭐⭐ 80-89 | ⭐⭐⭐ 70-79 | Block: <45%

## Helper Scripts

Automate credential configuration without manual UI steps:

| Script | Purpose |
|--------|---------|
| `configure-named-credential.sh` | Set API keys via ConnectApi (Enhanced NC) |
| `set-api-credential.sh` | Store keys in Custom Settings (dev/test) |

**Auto-run**: When you create credential files, Claude suggests running these scripts.

```bash
# After deploying Named Credential metadata
./scripts/configure-named-credential.sh MyOrg
# Enter API key when prompted (secure, hidden input)
```

## Prerequisites

- **Salesforce CLI v2+**: `sf` command
- **Authenticated org**: `sf org login web -a <alias>`
- **API Version**: 62.0+ recommended for External Credentials

## Cross-Skill Integration

| Skill | Integration |
|-------|-------------|
| configuring-connected-apps | Create OAuth Connected App for Named Credential |
| generating-apex | Custom callout services beyond templates |
| generating-flow | HTTP Callout Flow for Agentforce |
| deploying-sf-metadata | Deploy credentials and callout code |
| sf-ai-agentscript | Agent actions using External Services |

## Documentation

- [SKILL.md](SKILL.md) - Complete skill reference
- [references/named-credentials-automation.md](references/named-credentials-automation.md) - Script automation guide
- [references/named-credentials-guide.md](references/named-credentials-guide.md) - Template reference
- [references/callout-patterns.md](references/callout-patterns.md) - REST/SOAP patterns
- [references/event-patterns.md](references/event-patterns.md) - Platform Events & CDC

## License

See [LICENSE](LICENSE) for complete terms.
