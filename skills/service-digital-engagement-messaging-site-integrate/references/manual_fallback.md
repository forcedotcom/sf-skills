# Manual Fallback — Experience Builder Deep Link

Use this fallback when any automated step fails: bundle undetectable, patch write blocked, deploy fails and cannot be repaired, publish fails, or the guest URL smoke test never returns `200`.

Print the deep link and verbatim instructions below to the user. Do **not** claim the messaging widget is live on the site until the user has confirmed they completed the Publish step in Experience Builder.

## Resolve org-specific values

Never hardcode either value. Query them per run:

- **`MyDomain`** — take the `Instance URL` (or `Login URL`) from:

  ```bash
  sf org display --target-org <org-alias>
  ```

  Strip protocol and trailing slash. Typical form: `<mydomain>.lightning.force.com`.

- **`Network.Id`** — query by URL path prefix:

  ```bash
  sf data query --query \
    "SELECT Id FROM Network WHERE UrlPathPrefix='<urlPath>' LIMIT 1" \
    --target-org <org-alias>
  ```

## Deep link template

Substitute the resolved values into:

```text
https://<MyDomain>.lightning.force.com/sfsites/picasso/core/config/commeditor.apexp?...networkId=<Network.Id>
```

The `...` in the path represents any additional query-string parameters the org may require (some orgs redirect through an intermediate SSO step); take them from the org's own Experience Builder URL rather than fabricating them.

## Verbatim user instructions

Provide the user the following steps (adapt the deployment name to the one they supplied):

1. Open the deep link above. Salesforce may prompt for login; use an admin credential for the target org.
2. Once Experience Builder opens on the target site's home page, use the left-hand **Components** panel and drag the **Embedded Messaging** component onto the page. Drop it into the main content region — most templates render it at the bottom right regardless of exact drop position.
3. In the right-hand **Property panel** that appears after the drop:
   - **Deployment** — pick the deployment named `<deploymentName>` from the picklist. If it is not listed, confirm the Embedded Service Deployment has been published via Connect API.
   - Leave `Hide Chat Button on Load` set to **Default** unless the user needs the button hidden.
   - Leave `Auth Mode` unchecked for public sites (equivalent to `isExpSiteAuthMode: false`).
4. Click **Publish** in the top-right of Experience Builder. Confirm the publish dialog.
5. Wait 30–60 seconds for propagation, then reload the site's public URL. The chat button should appear.

## Reporting back

Once the user confirms publish in Experience Builder, re-run the guest URL smoke test:

```bash
curl -sL -o /dev/null -w "%{http_code}" \
  https://<domainHostname>/<urlPath>
```

Report success only when the response is `200`. If the user reports the button still does not appear, gather:

- The specific step where the automated flow failed.
- The `sf project deploy report` output (if a deploy was attempted).
- The `Network.Name` and `Network.Id` values used.

These are the minimum context needed to escalate to platform support.
