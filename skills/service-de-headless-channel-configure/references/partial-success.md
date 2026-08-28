---
name: service-de-headless-channel-configure-partial-success
description: "Load when the orchestrator fails mid-way through Stage 2-4 and you need to render the partial-success/resume message to the user. Covers the stateSoFar rendering template showing which of insert/route/consent/activate landed before the failure and the retry instructions. DO NOT load for the success-path Stage 5 final summary or the terms-not-accepted envelope."
metadata:
  version: "1.0"
  related-skills: service-de-headless-channel-configure
---

# Partial-success and resume reporting

If the orchestrator fails mid-way, the envelope always includes `stateSoFar` describing what landed. Render as:

```text
Error: Step {N} of 4 ({stepName}) failed: {leafEnvelope.kind} — {leafEnvelope.message or hint}

   What's already in place:
   - Channel inserted: {channelId ? "yes — " + channelId : "no"}
   - Routing configured: {sessionHandlerId ? "yes — " + queueName : "no"}
   - Consent configured: {(stepsRun.includes("consent") || (stepsSkipped || []).includes("consent")) ? "yes" : "no"}
   - Activation: {isActive ? "yes" : "no"}

   To retry: fix the issue above, then re-run this skill with the same
   inputs. The orchestrator will skip completed steps.
```
