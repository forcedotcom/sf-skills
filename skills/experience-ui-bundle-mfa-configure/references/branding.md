# Customizing MFA / Login Page Branding

The MFA challenge page and login page are platform-rendered. Their branding is controlled by `NetworkBranding` metadata, not by React components or custom LWC.

## When to use

- User wants custom logo on the MFA/login page
- User wants branded footer text or accent color
- MFA page shows default Salesforce branding and user wants it customized

## Important notes

- **Site Containers (React sites):** The branding admin UI is available in Setup → Digital Experiences → Login Settings (since 264) — the "Login & Registration" branding section is shown even before any branding is configured. Use it to set logo, colors, and footer. Metadata API deployment still works and is the option for scripted/repeatable setup.
- Branding applies to the vforcesite-domain pages (login, MFA challenge, password reset)

## Retrieve existing branding

```bash
# Create a package.xml manifest
cat > /tmp/branding-pkg.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>*</members>
    <name>NetworkBranding</name>
  </types>
  <version>62.0</version>
</Package>
EOF

# Retrieve from org
sf project retrieve start --target-org <org-alias> \
  --manifest /tmp/branding-pkg.xml \
  --target-metadata-dir ./branding-retrieve --unzip
```

## NetworkBranding metadata fields

| Field | Purpose | Notes |
|-------|---------|-------|
| `loginLogo` | Logo image on login/MFA page | Reference to a static resource or content asset |
| `loginFooterText` | Footer text below the form | Plain text, no HTML |
| `loginPrimaryColor` | Accent color for buttons/links | Hex color code (e.g., `#0070D2`) |
| `loginBackgroundColor` | Page background color | Hex color code |
| `pageFooter` | Footer content for community pages | Separate from login footer |

## Deploy custom branding

After modifying the `networkBranding-meta.xml` file:

```bash
sf project deploy start --target-org <org-alias> \
  --source-dir force-app/main/default/networkBranding --test-level NoTestRun
```

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Branding not appearing | Ensure at least one non-default value is set (logo or footer text) |
| Login Settings branding section missing in Setup | Site Containers (React) show the Login & Registration branding section (since 264); if it's missing, confirm the org is on 264+. Metadata API deployment works regardless. |
| Logo not displaying | Verify the static resource or content asset is deployed and accessible to guest users |
| Changes not visible | Clear browser cache or test in incognito — branding is cached aggressively |
