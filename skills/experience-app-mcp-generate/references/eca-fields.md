# External Client Application Field Map

Read this reference when reviewing or changing ECA metadata produced by `render_eca.mjs`. Paths below are under `<default-package>/main/default` and use the ECA DeveloperName as `<name>`.

## Generated files

### `externalClientApps/<name>.eca-meta.xml`

Full path: `<default-package>/main/default/externalClientApps/<name>.eca-meta.xml`

| Field | Controls |
|---|---|
| `<label>` | Display label |
| `<description>` | Description |
| `<contactEmail>` | Contact email |

### `extlClntAppGlobalOauthSets/<name>.ecaGlblOauth-meta.xml`

Full path: `<default-package>/main/default/extlClntAppGlobalOauthSets/<name>.ecaGlblOauth-meta.xml`

| Field | Controls |
|---|---|
| `<callbackUrl>` | OAuth callback URLs |
| `<isPkceRequired>` | PKCE requirement |
| `<isRefreshTokenRotationEnabled>` | Refresh-token rotation |
| `<isNamedUserJwtEnabled>` | Named-user JWT |
| `<label>` | Global OAuth settings label |

### `extlClntAppOauthSettings/<name>.ecaOauth-meta.xml`

Full path: `<default-package>/main/default/extlClntAppOauthSettings/<name>.ecaOauth-meta.xml`

| Field | Controls |
|---|---|
| `<commaSeparatedOauthScopes>` | OAuth scopes |
| `<label>` | OAuth settings label |

### `extlClntAppOauthPolicies/<name>.ecaOauthPlcy-meta.xml`

Full path: `<default-package>/main/default/extlClntAppOauthPolicies/<name>.ecaOauthPlcy-meta.xml`

| Field | Controls |
|---|---|
| `<permittedUsersPolicyType>` | Permitted users |
| `<refreshTokenPolicyType>` | Refresh-token policy |
| `<refreshTokenValidityPeriod>` | Refresh-token lifetime value |
| `<refreshTokenValidityUnit>` | Refresh-token lifetime unit |
| `<ipRelaxationPolicyType>` | IP relaxation |
| `<requiredSessionLevel>` | Required session level |
| `<label>` | OAuth policy label |

### `extlClntAppPolicies/<name>_defaultPolicy.ecaPlcy-meta.xml`

Full path: `<default-package>/main/default/extlClntAppPolicies/<name>_defaultPolicy.ecaPlcy-meta.xml`

| Field | Controls |
|---|---|
| `<isEnabled>` | Application availability |
| `<isOauthPluginEnabled>` | OAuth plugin availability |
| `<label>` | Default policy label |

## Permitted users

Default new ECAs to `AdminApprovedPreAuthorized`: the admin grants ECA access through associated profiles or permission sets; those users do not individually consent. This is not limited to administrator users. Remind the admin to arrange preauthorization; this skill does not manage end-user permissions.

If the MCP server is intended for all authenticated site users, suggest `AllSelfAuthorized`: eligible authenticated users authorize the ECA themselves without individual admin preauthorization. Apply it only after an explicit choice. ECA authorization does not replace site, tool, or data access controls.

Pass `--permitted-users-policy <AdminApprovedPreAuthorized|AllSelfAuthorized>` to `render_eca.mjs` for generation and `--check` with the confirmed choice; omission uses the admin-preauthorized baseline. Preserve intentional existing policies. A baseline difference is a review finding, not authorization to change a live ECA.

## Editing invariants

- Store all client-specific OAuth redirect URIs as newline-separated values inside the single `<callbackUrl>` element. Each value must be an absolute redirect URI with an allowed scheme and host. Do not invent a default callback URL, and do not write an empty `<callbackUrl>`.
- Keep the `MCP` and `RefreshToken` OAuth scopes unless the user explicitly changes the supported authorization flow.
- Refresh-token lifetime is controlled by the policy type, period, and unit in the OAuth policy component.
- Keep every `<externalClientApplication>` value aligned with the ECA DeveloperName. A rename requires coordinated file-name and cross-component reference changes, not an isolated field edit.
- The renderer derives labels across the related components. When changing the display label, review the labels in the global OAuth, OAuth settings, and OAuth policy components for consistency.
