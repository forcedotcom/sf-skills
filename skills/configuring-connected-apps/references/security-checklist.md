<!-- Parent: configuring-connected-apps/SKILL.md -->
# Security Checklist for Connected Apps & ECAs

Use this checklist before deploying any OAuth application to production.

## Pre-Deployment Checklist

### OAuth Configuration

- [ ] **Callback URLs are specific** (no wildcards)
- [ ] **All URLs use HTTPS** (required for production)
- [ ] **PKCE is enabled** for public clients (mobile, SPA)
- [ ] **Consumer secret is protected** (not in source control)
- [ ] **Minimal scopes selected** (principle of least privilege)
- [ ] **No deprecated scopes** in use

### Token Policies

- [ ] **Access token expiration** is configured appropriately
- [ ] **Refresh token policy** matches use case
  - `infinite` only for trusted server applications
  - `specific_lifetime` for user-facing apps
  - `zero` for JWT Bearer flows
- [ ] **Token rotation enabled** for ECAs in production
- [ ] **IP restrictions configured** for server-to-server apps

### Access Control

- [ ] **Admin pre-authorization** required for sensitive apps
- [ ] **User assignment via Permission Set** or Profile
- [ ] **Connected App policies** reviewed in Setup
- [ ] **High Assurance session** required if needed

### External Client Apps (Additional)

- [ ] **Distribution state** correctly set (Local vs Packageable)
- [ ] **Consumer key rotation** enabled for production
- [ ] **Consumer secret rotation** enabled for production
- [ ] **Policies file** reviewed after first deployment

---

## Security Scoring Criteria

### Critical (Block Deployment)

| Issue | Impact | Fix |
|-------|--------|-----|
| Wildcard callback URL | Token hijacking | Use specific URLs |
| HTTP callback URL | Credential interception | Use HTTPS only |
| Full scope without justification | Over-privileged access | Use minimal scopes |
| Consumer secret in code | Credential leak | Use environment variables |

### High Priority

| Issue | Impact | Fix |
|-------|--------|-----|
| PKCE disabled for mobile/SPA | Auth code interception | Enable PKCE |
| No IP restrictions (server) | Unauthorized access | Configure IP ranges |
| Infinite refresh tokens (user app) | Long-term compromise | Set expiration |
| No token rotation (ECA) | Compromised credentials | Enable rotation |

### Medium Priority

| Issue | Impact | Fix |
|-------|--------|-----|
| Missing description | Audit difficulty | Add clear description |
| Generic contact email | Incident response delay | Use team email |
| Introspection disabled | Token validation gaps | Enable if needed |
| No logout URL | Session persistence | Configure logout |

---

## Scope Security Guide

### Recommended Scopes by Use Case

| Use Case | Recommended Scopes |
|----------|-------------------|
| API Integration | `Api`, `RefreshToken` |
| User Authentication | `OpenID`, `Profile`, `Email` |
| Full API + Identity | `Api`, `RefreshToken`, `OpenID`, `Profile` |
| Chatter Integration | `Api`, `ChatterApi` |
| Server-to-Server | `Api` only |

### Scopes to Avoid

| Scope | Risk | Alternative |
|-------|------|-------------|
| `Full` | Complete access to everything | Use specific scopes |
| `Web` + `Api` together | Redundant, increases attack surface | Choose one |
| `RefreshToken` for JWT | Unnecessary, JWT generates new tokens | Remove scope |

---

## IP Restriction Policies

### Policy Options

| Policy | Description | Use Case |
|--------|-------------|----------|
| `ENFORCE` | Strict IP enforcement | Production server-to-server |
| `BYPASS` | No IP restrictions | Development only |
| `ENFORCE_ACTIVATED_USERS` | Enforce for active users | Mixed environments |

### Recommended Configuration

```xml
<!-- Production: Server-to-Server -->
<oauthPolicy>
    <ipRelaxation>ENFORCE</ipRelaxation>
</oauthPolicy>

<!-- Production: User-Facing -->
<oauthPolicy>
    <ipRelaxation>ENFORCE_ACTIVATED_USERS</ipRelaxation>
</oauthPolicy>

<!-- Development Only -->
<oauthPolicy>
    <ipRelaxation>BYPASS</ipRelaxation>
</oauthPolicy>
```

---

## Certificate Management (JWT Bearer)

### Certificate Requirements

- [ ] RSA 2048-bit or higher key size
- [ ] Valid not-before and not-after dates
- [ ] Uploaded to Salesforce Certificate and Key Management
- [ ] Private key stored securely (HSM, Vault, secure storage)

### Certificate Rotation

1. Generate new certificate before expiration
2. Upload new certificate to Salesforce
3. Update Connected App to use new certificate
4. Update external system with new private key
5. Test authentication
6. Remove old certificate after transition period

---

## Monitoring & Audit

### What to Monitor

- [ ] **Login History** for Connected App users
- [ ] **OAuth Usage** in Setup
- [ ] **Event Monitoring** for token events (Shield required)
- [ ] **API Usage** limits and patterns

### Audit Checklist

- [ ] Review Connected Apps quarterly
- [ ] Remove unused applications
- [ ] Rotate credentials annually
- [ ] Verify scope appropriateness
- [ ] Check for policy violations

---

## Incident Response

### If Credentials Are Compromised

1. **Immediately** rotate Consumer Secret
2. Revoke all active tokens
3. Review login and access logs
4. Update external systems with new credentials
5. Investigate scope of compromise
6. Document and report incident

### Commands for Response

```bash
# List all Connected Apps
sf org list metadata --metadata-type ConnectedApp --target-org <org>

# Retrieve for review
sf project retrieve start --metadata ConnectedApp:<AppName> --target-org <org>
```

---

## Compliance Considerations

### GDPR/Privacy

- Ensure data access matches user consent
- Document data flows through Connected Apps
- Implement data retention policies

### SOC 2

- Enable audit logging
- Implement access reviews
- Document security controls
- Use certificate-based authentication

### HIPAA

- Enable High Assurance sessions
- Restrict data access scopes
- Implement IP restrictions
- Use encrypted connections only
