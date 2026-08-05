# Scratch Org Edition Types

Reference for choosing the right Salesforce edition for scratch org creation.

## Available Editions

| Edition | When to use | License limits | Features |
|---------|-------------|----------------|----------|
| `developer` | Default choice for most development | 2 user licenses | Most features available, best for general development |
| `enterprise` | Enterprise-specific features needed | 5 user licenses | All enterprise features, territory management, advanced approvals |
| `group` | Testing Professional edition behavior | 5 user licenses | Professional edition features |
| `professional` | Professional edition-specific testing | 5 user licenses | Professional edition feature set |

## Partner Editions

Only available if the Dev Hub is a Partner Business Org:

| Edition | When to use |
|---------|-------------|
| `partner developer` | Partner app development |
| `partner enterprise` | Partner enterprise app testing |
| `partner group` | Partner professional edition testing |
| `partner professional` | Partner professional edition apps |

## Edition Comparison

### Developer Edition (Recommended Default)
- **Best for**: General development, most common use case
- **Features**: Apex, Visualforce, Lightning, Process Builder, Flow, most platform features
- **Limitations**: 2 user licenses (sufficient for most dev work)
- **Use when**: User doesn't specify or needs general Salesforce development environment

### Enterprise Edition
- **Best for**: Enterprise-specific features, larger team testing
- **Additional features**: Territory Management 2.0, Advanced Approval Processes
- **Use when**: Testing enterprise-only features or need more than 2 users

### Group/Professional Edition
- **Best for**: Testing behavior specific to Professional edition
- **Use when**: Building apps for Professional edition customers or testing edition-specific constraints

## Choosing an Edition

Follow this decision tree:

```text
1. Does user specify edition? → Use specified edition
2. Does user need Partner edition? → Check if Dev Hub is Partner Business Org
3. Does user need Enterprise features? → Use enterprise
4. Default → Use developer
```

## CLI Usage

**With flag:**
```bash
sf org create scratch --edition developer --alias my-org
```

**With definition file:**
```json
{
  "edition": "Developer"
}
```

**Important notes:**
- Edition value is case-insensitive in CLI flags but case-sensitive in definition files (capital first letter)
- Partner editions use space format: `partner developer`, `partner enterprise`, etc. (no hyphen)
- CLI flag `--edition` overrides definition file `edition` if both are specified

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `edition value must be one of` | Invalid edition name | Use: developer, enterprise, group, professional, or partner editions (e.g., "partner developer") |
| Partner edition not available | Dev Hub is not a Partner Business Org | Use non-partner edition or switch to Partner Dev Hub |
| Features not available in edition | Requested features not available in chosen edition | Use Enterprise edition or remove unavailable features |
