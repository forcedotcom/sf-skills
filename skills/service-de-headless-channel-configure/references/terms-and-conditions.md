---
name: service-de-headless-channel-configure-terms-and-conditions
description: "Load when rendering the Stage 0.5 Enhanced Messaging Terms and Conditions disclaimer and certification prompt for any channel type (WhatsApp, LINE, Facebook Messenger, Apple Messages for Business, SMS/Text). Covers the verbatim disclaimer text, the per-type CHANNEL_LABEL/THIRD_PARTY substitution table, and the certification prompt wording. DO NOT load for the gate's accept/decline behavior or the terms-not-accepted envelope — those stay inline in the parent skill's Stage 0.5 section."
metadata:
  version: "1.0"
  related-skills: service-de-headless-channel-configure
---

# Enhanced Messaging Terms and Conditions — disclaimer text and mappings

Render the disclaimer verbatim, substituting the human-readable channel name for `{MESSAGE_TYPE}` (`Facebook Messenger`, `WhatsApp`, `LINE`, `Apple Messages for Business`, `SMS (Text)`):

```text
────────────────────────────────────────────────────────────────────
  Terms and Conditions
────────────────────────────────────────────────────────────────────

The {CHANNEL_LABEL} channel you have selected is part of the service
branded as Enhanced Messaging. Enhanced Messaging features are provided
using infrastructure technology different from Messaging. Any service
level commitments and any security, privacy, data storage or processing
locations or data recovery measures that are specific to Messaging do
not apply to Enhanced Messaging features, and such information for
Enhanced Messaging features is as described in the applicable Trust and
Compliance Documentation available at
https://www.salesforce.com/company/legal/trust-and-compliance-documentation/.

The {CHANNEL_LABEL} channel integrates with third-party functionality
powered by {THIRD_PARTY}. By enabling an integration with such
functionality, you acknowledge and agree that the {CHANNEL_LABEL}
channel is a Non-SFDC Application (as defined in your main services
agreement), and your use of the {CHANNEL_LABEL} channel is subject to
the applicable third-party terms in the Enhanced Messaging Notices and
License Information Documentation.

Enhanced Messaging is also subject to the relevant Documentation and
terms on your order form for Digital Engagement.
────────────────────────────────────────────────────────────────────

Do you certify that you have the authority to accept and bind your
organization to these terms? [yes/no]
```

`{CHANNEL_LABEL}` and `{THIRD_PARTY}` by type:

| `{MESSAGE_TYPE}` | `{CHANNEL_LABEL}` | `{THIRD_PARTY}` |
| --- | --- | --- |
| `Facebook` | `Facebook Messenger` | `Meta Platforms, Inc. or its affiliates` |
| `WhatsApp` | `WhatsApp` | `Meta Platforms, Inc. or its affiliates` |
| `Line` | `LINE` | `LINE Corporation or its affiliates` |
| `AppleBusinessChat` | `Apple Messages for Business` | `Apple Inc. or its affiliates` |
| `Text` | `SMS (Text)` | the supplied `{SMS_PROVIDER}` (e.g. `Sinch`), else `your SMS provider` |

The certification prompt mirrors the wizard's checkbox — *"I hereby certify that I have the authority to accept and bind my organization to these terms."*
