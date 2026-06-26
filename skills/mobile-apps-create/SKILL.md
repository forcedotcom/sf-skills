---
name: mobile-apps-create
description: "The entry point for building any Salesforce native mobile app on iOS or Android. TRIGGER when the user says: \"build a Salesforce iOS app\", \"add Salesforce login to my Android app\", \"set up Mobile SDK\", \"add MobileSync / SmartStore offline storage\", \"embed an Agentforce agent in my mobile app\", \"add Agentforce chat to iOS/Android\", or otherwise asks to create, extend, or integrate a Salesforce mobile experience in Swift or Kotlin (MSDK, Agentforce SDK, or both). SKIP when the user is building a non-Salesforce mobile app, using React Native / Flutter / Ionic without Salesforce integration, asking about generic mobile UI design, or working on a Salesforce-adjacent web/desktop surface (LWC, Experience Cloud, Mobile Publisher branding-only)."
metadata:
  version: "1.0"
---

# Salesforce Mobile

Route the user to the right SDK-family skill for building Salesforce-connected mobile apps. Do not implement features here; child skills own scenario detection and step-by-step instructions.

## Before routing

Disambiguate on two dimensions: **SDK family** (Mobile SDK vs. Agentforce SDK) and **platform** (iOS vs. Android). They are not mutually exclusive — an app can use both SDKs.

If the user's intent could plausibly map to either SDK, ask before routing. Guessing wrong wastes the user's time because the child skills are platform- and SDK-specific.

## Routing — which SDK family?

| User's situation | SDK |
|---|---|
| Authenticating end users to Salesforce, syncing records (MobileSync), storing data offline (SmartStore), biometric login, push notifications, REST integration | **Mobile SDK** |
| Embedding an Agentforce agent — chat UI, agent conversations, conversational features as the primary surface | **Agentforce SDK** |
| Both (data-driven app with an embedded agent) | **Mobile SDK first**, then **Agentforce SDK** layered on top |

### Tiebreakers when both seem to apply

- Is the agent the *primary surface* (chat-first app), or a *feature inside* an otherwise data-driven app?
  - Primary → Agentforce SDK
  - Feature → Mobile SDK; embed the agent via Agentforce SDK alongside it
- Are end users authenticating into Salesforce data?
  - Yes → Mobile SDK is required (Agentforce SDK can be added on top).
  - No → Agentforce SDK alone is likely sufficient (it uses guest auth).
- Asking about offline storage, sync, REST, push, or biometrics? → Mobile SDK.
- Asking about agent conversations, chat UI, or streaming responses? → Agentforce SDK.

When still unclear, ask the user directly.

## Routing — which platform?

| Platform | Mobile SDK skill | Agentforce SDK skill |
|---|---|---|
| iOS (Swift) | `ios-mobile-sdk` | `integrate-agentforce-ios` |
| Android (Kotlin) | `android-mobile-sdk` | `integrate-agentforce-android` |

If the user wants both platforms, route to each child skill separately — they are independent.

## Combined workflows (Mobile SDK + Agentforce SDK)

When an app needs both:

1. Route to the Mobile SDK platform skill first to scaffold and authenticate.
2. Route to the Agentforce SDK platform skill to layer the agent surface.
3. Treat each child skill's instructions as authoritative for its SDK; do not merge their steps. Each SDK owns its own auth setup, dependency installation order, and initialization sequence — interleaving them produces conflicting config and broken init order.

This sequencing is the only multi-skill logic this skill owns. Everything else lives inside the child skills.

## Loading a child skill

Invoke the child skill by name through the harness. If it is not available locally, prompt the user to install it with `npx skills add <repo>`. If the user confirms (or has pre-authorized installs), run the command and load the child skill — do not make the user go figure out how to continue the workflow. If the user declines, stop and explain that the child skill owns the SDK's setup steps and the workflow cannot continue without it. Each child skill is published from a public repo:

| Skill | Repo | Install command |
|---|---|---|
| `ios-mobile-sdk` | [`forcedotcom/SalesforceMobileSDK-Templates`](https://github.com/forcedotcom/SalesforceMobileSDK-Templates) → `skills/ios-mobile-sdk/` | `npx --yes skills add forcedotcom/SalesforceMobileSDK-Templates --skill ios-mobile-sdk --yes` |
| `android-mobile-sdk` | [`forcedotcom/SalesforceMobileSDK-Templates`](https://github.com/forcedotcom/SalesforceMobileSDK-Templates) → `skills/android-mobile-sdk/` | `npx --yes skills add forcedotcom/SalesforceMobileSDK-Templates --skill android-mobile-sdk --yes` |
| `integrate-agentforce-ios` | [`salesforce/AgentforceMobileSDK-iOS`](https://github.com/salesforce/AgentforceMobileSDK-iOS) → `skills/integrate-agentforce-ios/` | `npx --yes skills add salesforce/AgentforceMobileSDK-iOS --skill integrate-agentforce-ios --yes` |
| `integrate-agentforce-android` | [`salesforce/AgentforceMobileSDK-Android`](https://github.com/salesforce/AgentforceMobileSDK-Android) → `skills/integrate-agentforce-android/` | `npx --yes skills add salesforce/AgentforceMobileSDK-Android --skill integrate-agentforce-android --yes` |

After install, load the child skill and let it take over. Do not inline the child skill's content — the child skill owns scenario detection, prerequisites, and step-by-step instructions.
