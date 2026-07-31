---
name: service-digital-engagement-messaging-site-integrate
description: "Integrates a Messaging for In-App and Web (MIAW) Embedded Messaging chat widget into an Experience Cloud site by patching the site's LWR or Aura page bundle, deploying, publishing, and verifying guest access. Use when the user wants to embed messaging on an Experience site, add a chat widget to a community, place the Embedded Messaging component on an LWR or Aura page, wire an embedded service deployment to a site, references the retrieved bundle artifacts (`content.json`, `homeGuestLayout.json`, or a `*.site-meta.xml` file), or automates the retrieve/patch-JSON/deploy/publish flow instead of clicking through Experience Builder. DO NOT TRIGGER when creating the messaging channel (use service-digital-engagement-channel-configure), when creating or updating the EmbeddedServiceConfig deployment (use service-digital-engagement-deployment-configure), or when generating a standalone JavaScript snippet for a non-Experience website."
metadata:
  version: "1.0"
  minApiVersion: "62.0"
  relatedSkills:
    - "experience-lwr-site-generate"
    - "service-digital-engagement-channel-configure"
    - "service-digital-engagement-deployment-configure"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Embed Messaging Widget on an Experience Cloud Site

Wires an existing Embedded Messaging (MIAW) deployment onto an Experience Cloud site by retrieving the site's bundle (LWR `DigitalExperienceBundle` or Aura `ExperienceBundle`), patching the home page JSON to place the `experience_messaging:embeddedMessaging` component, staging the bundle into the local project, deploying it, publishing the site, and verifying guest access.

The operation is idempotent: if the component is already present it is updated in place (its `id` is preserved), so re-running with different ESD coordinates cleanly updates.

## Scope

- **In scope**: Detecting LWR vs Aura bundle type; scaffolding missing LWR template routes required by the site template (e.g. `too-many-requests`); patching the home-page JSON to insert or update the Embedded Messaging component; staging the bundle into `force-app`; async deploy with polling; resolving the `Network.Name` and publishing the site; guest-URL smoke test; manual Experience Builder fallback with a deep link.
- **Out of scope**: Creating the `EmbeddedServiceConfig` (Embedded Service Deployment) itself — use `service-digital-engagement-deployment-configure`; creating the `MessagingChannel` — use `service-digital-engagement-channel-configure`; creating the Experience Cloud site itself — use `experience-lwr-site-generate`; generating a standalone JS snippet for a non-Experience website.

---

## Clarifying Questions

Before executing, ask the user if not already clear:

- **Site name?** The `DeveloperName` of the Experience Cloud site (the metadata folder name under `digitalExperiences/site/<siteName>/` or `experiences/<siteName>/`).
- **Deployment coordinates?** The `deploymentName` (Embedded Service Deployment `DeveloperName`), the `scrtUrl`, and the `siteEndpoint` (Experience site base URL). All three come from the published `EmbeddedServiceConfig` — obtain from `service-digital-engagement-deployment-configure` output if not provided.
- **Target org alias?** For the `sf` commands.
- **URL path prefix?** The site's `UrlPathPrefix` (needed to resolve `Network.Name` for publish and to hit the guest URL for verification).

---

## Required Inputs

Gather or infer before proceeding:

- **Site name** — `DeveloperName` of the site
- **Deployment name** — `DeveloperName` of the `EmbeddedServiceConfig`
- **scrtUrl** — SCRT2 endpoint URL from the deployment
- **siteEndpoint** — Base URL of the Experience site
- **Target org alias**
- **URL path prefix** — Site's public URL path segment (e.g. `esw-site`)

Defaults applied to the component's attributes when writing:

- `isExpSiteAuthMode`: `false`
- `hideChatButtonOnLoad`: `"Default"`
- `clientVersion`: `"WebV1"`

---

## Workflow

Steps are sequential. If any automated step fails, proceed to the manual fallback (Phase 6) and do not claim the widget is "live" until either the guest-URL smoke test returns `200` or the user confirms manual publish.

### Phase 1 — Detect Bundle Type

1. **Retrieve both candidate bundles** into `<retrieve-dir>`. The script only performs a deterministic path check, so the retrieve calls must run first:

   ```bash
   sf project retrieve start --metadata "DigitalExperienceBundle:site/<siteName>" \
     --target-org <org-alias> --target-metadata-dir <retrieve-dir>
   sf project retrieve start --metadata "ExperienceBundle:<siteName>" \
     --target-org <org-alias> --target-metadata-dir <retrieve-dir>
   ```

   Either call may return "no metadata found" — that is expected; the missing bundle simply means the site is the other type.

2. **Run `scripts/detect_bundle_type.sh <retrieve-dir> <siteName>`.** It emits exactly one token to stdout:

   - `LWR` → the LWR marker file exists (`digitalExperiences/site/<siteName>/sfdc_cms__view/home/content.json`). Go to Phase 2.
   - `AURA` → the Aura marker file exists (`experiences/<siteName>/views/homeGuestLayout.json`). Go to Phase 3.
   - `UNKNOWN` (exit code 1) → neither marker exists. Skip to the manual fallback in Phase 6.

Read `references/bundle_detection.md` for retrieval command shapes and troubleshooting.

### Phase 2 — Patch the LWR Bundle

3. **Scaffold any missing LWR template routes** (commonly `too-many-requests`) before patching — missing routes fail the deploy. Route+view scaffolding is owned by `experience-lwr-site-generate` (see its `configure-content-route.md`, `configure-content-view.md`, and `handle-component-and-region-ids.md`). Delegate to that skill for the actual scaffold; this skill only supplies the messaging-specific context (which route the deploy is complaining about, and confirmation that the scaffolded pair resolves that specific deploy error). See `references/lwr_route_scaffolding.md` for the delegation pointer.

4. **Patch the home page** by running:

   ```bash
   scripts/patch_lwr_bundle.sh \
     <retrieve-dir>/digitalExperiences/site/<siteName>/sfdc_cms__view/home/content.json \
     <deploymentName> <scrtUrl> <siteEndpoint>
   ```

   The script deterministically walks `.contentBody.component.children[]`, targets the region with `.type == "region"` and `.name == "content"`, and either updates the existing `.definition == "experience_messaging:embeddedMessaging"` component in place (preserving its `id`) or appends a fresh `community_layout:section` wrapper with a JSON-string `sectionConfig`. See `references/lwr_patch.md` for the JSON shapes it emits and how to verify.

5. Proceed to Phase 4.

### Phase 3 — Patch the Aura Bundle

6. **Patch the home guest layout** by running:

   ```bash
   scripts/patch_aura_bundle.sh \
     <retrieve-dir>/experiences/<siteName>/views/homeGuestLayout.json \
     <deploymentName> <scrtUrl> <siteEndpoint>
   ```

   The script iterates `.regions[]`, picks the first region whose `.components[]` is non-empty, recurses through any `forceCommunity:section` wrappers, and either updates the existing `.componentName == "experience_messaging:embeddedMessaging"` component in place (preserving `id`) or appends a fresh `forceCommunity:section` wrapper. Aura uses `componentName` / `componentAttributes` (not `definition` / `attributes`) and has no `dxpStyle`. See `references/aura_patch.md` for JSON shapes and verification steps.

7. Proceed to Phase 4.

### Phase 4 — Stage and Deploy

8. **Copy the modified bundle into the project's default package.** Use `cp -R` so unchanged files travel with the modified one:

   - LWR: `cp -R <retrieve-dir>/digitalExperiences force-app/main/default/`
   - Aura: `cp -R <retrieve-dir>/experiences force-app/main/default/` **and also copy** the sibling `<siteName>.site-meta.xml` file — Aura deploys are rejected without it.

9. **Async deploy and poll**:

    ```bash
    sf project deploy start --source-dir force-app/main/default \
      --target-org <org-alias> --async
    ```

    Poll every 15 seconds up to 10 minutes:

    ```bash
    sf project deploy report --job-id <job-id> --target-org <org-alias>
    ```

    Stop when status is `Succeeded`, `Failed`, `SucceededPartial`, or `Canceled`. On failure, surface the deploy report and do not proceed to publish. See `references/deploy_and_publish.md` for the full polling loop and common failure modes.

### Phase 5 — Publish and Verify

10. **Resolve the `Network.Name`.** `Network.Name` frequently differs from the site `DeveloperName`, so query it by the URL path prefix rather than guessing:

    ```bash
    sf data query --query \
      "SELECT Name FROM Network WHERE UrlPathPrefix='<urlPath>' LIMIT 1" \
      --target-org <org-alias>
    ```

11. **Publish the community** with the resolved name:

    ```bash
    sf community publish --name "<resolved-Name>" --target-org <org-alias>
    ```

12. **Smoke-test guest access** by hitting the public URL:

    ```bash
    curl -sL -o /dev/null -w "%{http_code}" \
      https://<domainHostname>/<urlPath>
    ```

    Report success only when the response is `200`.

### Phase 6 — Manual Fallback

13. If any automated step fails (bundle undetectable, patch write blocked, deploy fails, publish fails, or guest URL not `200`), print the Experience Builder deep link and verbatim instructions from `references/manual_fallback.md`. Do **not** claim the widget is live until the user confirms.

    The deep link is:

    ```text
    https://<MyDomain>.lightning.force.com/sfsites/picasso/core/config/commeditor.apexp?...networkId=<Network.Id>
    ```

    Resolve `<MyDomain>` via `sf org display --target-org <org-alias>` and `<Network.Id>` via:

    ```bash
    sf data query --query \
      "SELECT Id FROM Network WHERE UrlPathPrefix='<urlPath>' LIMIT 1" \
      --target-org <org-alias>
    ```

    **Do not hardcode either value.** Instruct the user to open Experience Builder, drag the Embedded Messaging component onto the target page, pick the deployment from the property panel, and click Publish.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Detect bundle type from retrieval output, do not assume | LWR and Aura sites need different files patched with different key names |
| Preserve the existing component `id` when updating in place | Ensures idempotency; the Experience runtime keys off `id` |
| Every new `id` must be a fresh UUID | Duplicate IDs corrupt the layout and can fail render |
| LWR uses `definition` / `attributes`; Aura uses `componentName` / `componentAttributes` | Wrong key names silently drop the component from render |
| LWR `community_layout:section` `sectionConfig` is a JSON string, not a nested object | The Experience CMS serializer expects a string |
| Aura sibling `<siteName>.site-meta.xml` must be copied alongside the bundle | Deploy is rejected without it |
| Poll the async deploy; do not fire-and-forget | Publish must run only after deploy succeeds |
| Resolve `Network.Name` from `UrlPathPrefix`, do not reuse site `DeveloperName` | The two are frequently different |
| Do not claim "live on the site" until the guest URL returns `200` or the user confirms | Publish is asynchronous; premature success reports mislead |
| Never hardcode `MyDomain` or `Network.Id` in the manual fallback link | Values are org-specific and must be queried |
| Idempotency: re-running with new ESD coordinates must update in place | Users iterate on `deploymentName`, `scrtUrl`, `siteEndpoint` during setup |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `too-many-requests` route missing during LWR deploy | Scaffold the missing route+view pair per `references/lwr_route_scaffolding.md` |
| Aura deploy rejected with missing site metadata | Copy the sibling `<siteName>.site-meta.xml` from the retrieve dir |
| Component appended but not rendering | Confirm the region wrapper uses the correct `type: "region"` key and that Aura components use `componentName` (not `definition`) |
| `sf community publish` fails with "community not found" | The `Network.Name` differs from site `DeveloperName`; resolve via `UrlPathPrefix` query |
| Guest URL returns `403` or `503` after publish | Publish is async — retry the smoke test after 60s before falling back to manual |
| Re-run adds a second messaging component | The recursive search matched on the wrong key name; component detection must use `definition` (LWR) or `componentName` (Aura) |
| Deploy succeeds but widget does not appear | The messaging component is present in a region that is not on the site's home page — patch `home/content.json` (LWR) or `homeGuestLayout.json` (Aura), not another view |
| `sectionConfig` written as an object | Serialize it as a JSON string; the CMS parser will not accept an object |

---

## Verification Checklist

### Bundle Detection
- [ ] Was exactly one of `sfdc_cms__view/home/content.json` (LWR) or `views/homeGuestLayout.json` (Aura) found?
- [ ] If neither was found, did the workflow route to the manual fallback?

### Patch Correctness
- [ ] For LWR, are the messaging component's keys `definition` and `attributes`?
- [ ] For Aura, are the keys `componentName` and `componentAttributes`?
- [ ] When updating in place, was the existing `id` preserved?
- [ ] When appending, are all new `id` values fresh UUIDs?
- [ ] For LWR, is `sectionConfig` a JSON *string* (not a nested object)?
- [ ] For LWR, do the UUIDs referenced inside `sectionConfig` match the section `id` and child region `id`?

### Deploy
- [ ] For Aura, was `<siteName>.site-meta.xml` copied alongside the bundle?
- [ ] Was the async deploy polled until a terminal status?
- [ ] Is the terminal status `Succeeded` or `SucceededPartial` before proceeding to publish?

### Publish
- [ ] Was `Network.Name` resolved via `UrlPathPrefix`, not reused from site `DeveloperName`?
- [ ] Did `sf community publish` complete without error?

### Verify
- [ ] Did the guest URL curl return `200`?
- [ ] Did the workflow refrain from claiming success until `200` was observed or the user confirmed manual publish?

---

## Output Expectations

Deliverables:

- Modified home-page JSON in the retrieval directory and in `force-app/main/default/...`
- (LWR only, if needed) new `sfdc_cms__route/<RouteApiName>/` + `sfdc_cms__view/<viewId>/` pair for any scaffolded missing route
- Deploy `job-id` and the final deploy report
- Publish confirmation
- Guest URL smoke-test HTTP status
- On failure: the Experience Builder deep link and manual instructions

Do not produce the `EmbeddedServiceConfig` or the `MessagingChannel` metadata — those are the responsibilities of the deployment and channel skills below.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Create or update the Embedded Service Deployment | `service-digital-engagement-deployment-configure` |
| Create the underlying MIAW messaging channel | `service-digital-engagement-channel-configure` |
| Create the Experience Cloud LWR site itself | `experience-lwr-site-generate` |
| Scaffold a missing LWR route + view pair (e.g. `too-many-requests`) | `experience-lwr-site-generate` (route/view creation, ID handling) |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/bundle_detection.md` | Phase 1 — LWR vs Aura retrieval and disambiguation |
| `references/lwr_route_scaffolding.md` | Phase 2 — delegation pointer for scaffolding missing LWR template routes (owned by `experience-lwr-site-generate`) |
| `references/lwr_patch.md` | Phase 2 — what `patch_lwr_bundle.sh` does and how to verify its output |
| `references/aura_patch.md` | Phase 3 — what `patch_aura_bundle.sh` does and how to verify its output |
| `references/deploy_and_publish.md` | Phases 4–5 — staging into `force-app`, async deploy polling, publish, and guest-URL smoke test |
| `references/manual_fallback.md` | Phase 6 — Experience Builder deep link and manual drag-drop-publish instructions |
| `scripts/detect_bundle_type.sh` | Phase 1 — deterministic LWR/Aura/UNKNOWN detection over a retrieved bundle |
| `scripts/patch_lwr_bundle.sh` | Phase 2 — idempotent LWR `content.json` patch (insert or update in place) |
| `scripts/patch_aura_bundle.sh` | Phase 3 — idempotent Aura `homeGuestLayout.json` patch (insert or update in place) |
