# building-sf-integrations Helper Scripts

Automation scripts for configuring Salesforce integrations without manual UI steps.

> **Mirror note:** These files mirror the canonical generic helpers in the repository root `scripts/` directory. Keep both locations aligned until the packaging layout is consolidated.

## Scripts

| Script | Purpose | Auth Type |
|--------|---------|-----------|
| `configure-named-credential.sh` | Set API keys via ConnectApi | Enhanced Named Credentials |
| `set-api-credential.sh` | Store keys in Custom Settings | Legacy (dev/test) |

## Quick Start

```bash
# Enhanced Named Credentials (recommended for production)
./configure-named-credential.sh <external-credential-name> <principal-name> <org-alias>

# Custom Settings (legacy, for dev/test)
./set-api-credential.sh <setting-name> - <org-alias>
```

## Prerequisites

- **Salesforce CLI v2+** (`sf` command)
- **Authenticated org** (`sf org login web -a <alias>`)
- **Deployed metadata** (External Credential, Named Credential, CSP)

## Usage Examples

### Configure Named Credential

```bash
# Interactive mode - prompts for API key securely
./configure-named-credential.sh VisualCrossingWeather weatherAPIKey MyDevOrg

# The script will:
# 1. Validate org connection
# 2. Check External Credential exists
# 3. Prompt for API key (hidden input)
# 4. Execute ConnectApi Apex to store encrypted
```

### Custom Settings (Legacy)

```bash
# Secure input (dash prompts for hidden input)
./set-api-credential.sh WeatherAPI - MyDevOrg

# Direct input (less secure, for CI/CD)
./set-api-credential.sh WeatherAPI sk_live_abc123 MyDevOrg
```

## Templates

The `templates/` directory contains customizable scripts for new integrations:

| Template | Purpose |
|----------|---------|
| `setup-credentials-with-csp.sh` | Full setup with CSP Trusted Sites |

### Using Templates

```bash
# Copy template for your integration
cp templates/setup-credentials-with-csp.sh my-integration-setup.sh

# Edit configuration variables
# - SKILL_NAME
# - CSP_NAME
# - API_KEY_URL
```

## Auto-Run Behavior

When you create credential metadata files, Claude will automatically suggest running these scripts:

| File Pattern | Suggested Script |
|--------------|------------------|
| `*.namedCredential-meta.xml` | `configure-named-credential.sh` |
| `*.externalCredential-meta.xml` | `configure-named-credential.sh` |

## Troubleshooting

**"sf: command not found"**
- Install Salesforce CLI: `npm install -g @salesforce/cli`

**"Not authenticated"**
- Run: `sf org login web -a <alias>`

**"External Credential not found"**
- Deploy External Credential first
- Check developer name matches

## Related Documentation

- [Named Credentials Automation Guide](../references/named-credentials-automation.md)
- [Named Credentials Template Reference](../references/named-credentials-guide.md)
- [Security Best Practices](../references/security-best-practices.md)
