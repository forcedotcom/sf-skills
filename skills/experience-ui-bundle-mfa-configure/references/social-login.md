# Social Login / SSO (IDP) on React Experience Sites

Social Login and SSO are **separate from MFA**. MFA (this skill's main flow)
challenges a user for a second factor *after* they authenticate with a
username and password. Social Login / SSO lets a user authenticate *with an
external identity provider* (Google, a SAML IDP, another Salesforce org, etc.)
instead of a local password. They can be used together or independently.

## What shipped

Before 264, the LWC `community_login/socialLogin` component did not render in
the React runtime (Site Container sites, `isSiteContainer = true`) — the React
login page does not load or execute LWC. As of **264**, React
sites ship a built-in **Social Login rendering component** that fills this gap:

- Fetches the configured Auth Provider list from an Apex REST endpoint on mount
- Renders a styled button per provider (name + icon)
- On click, redirects via `window.location.assign(ssoUrl)` to start the SSO flow
- Auto-redirects when a single IDP is configured and password login is disabled

**No custom code is required.** The component is part of the React auth
templates; you enable Social Login by configuring Auth Providers, not by
writing a component.

## How to enable

1. **Configure the Auth Provider(s)** in Setup → Identity → Auth. Providers
   (e.g. Google, Facebook, Salesforce, or a SAML/OpenID Connect provider).
2. **Add the provider(s) to the site's login configuration** so they are
   exposed to the community — Setup → Digital Experiences → *(site)* → 
   Administration → Login & Registration.
3. **Publish** the site. The React login page renders a button per configured
   provider automatically.

## How the redirect works (for troubleshooting)

- The SSO URL uses the `vforcesite` path:
  `/<sitename>vforcesite/services/auth/sso/<providerId>...`
  (same domain family as the platform-rendered MFA/login page — expected).
- `startURL` must point to the **site home path**, not `/` or `/login` —
  otherwise the post-login redirect can loop.
- Single-IDP + password-login-disabled sites auto-redirect to the provider,
  skipping the button screen.

## Interaction with MFA

- Social Login and the `ForceTwoFactor` MFA permission set are independent.
  A user who logs in through an external IDP may still be MFA-challenged if
  the IDP session doesn't satisfy the org's assurance requirements; a user who
  logs in with a password is challenged per the MFA permission set as usual.
- Deploying the MFA permission sets from this skill does **not** enable or
  disable Social Login, and configuring Auth Providers does **not** change MFA
  enforcement.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No provider buttons on React login page | No Auth Providers configured, or not added to the site's Login & Registration settings | Configure Auth Providers and add them to the site, then re-publish |
| Buttons appear but SSO fails to start | `startURL` points at `/` or `/login` | Set `startURL` to the site home path |
| Redirect loop after SSO | `startURL` misconfigured | Point `startURL` at the site home path, not the login page |
| Provider button missing an icon | Auth Provider icon not set | Set the icon on the Auth Provider definition |
| No Social Login buttons render on the React login page even with Auth Providers configured | Org predates 264 (React runtime shipped the built-in Social Login component in 264) | Ensure the org is on 264+ |
