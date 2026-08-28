---
name: service-de-channel-activate-worked-examples
description: "Load when you want a reference run of service-de-channel-activate's activation flow — a full end-to-end trace for a given path or failure mode. Covers WhatsApp activation via REST PATCH (the reference happy-path), Apple Business Chat activation, a readiness-validator failure (missing consent), and an already-active no-op. DO NOT load this during normal execution of the skill's stages — only when a concrete trace is wanted for reference or debugging."
metadata:
  version: "1.0"
  related-skills: service-de-channel-activate
---

# Worked examples: `service-de-channel-activate`

- WhatsApp activation on wadtesting via REST PATCH (verified 2026-04-30 — the reference happy-path, ~21s wall-clock)
- Apple Business Chat activation (sub-second, no external call)
- Readiness-validator failure (missing consent)
- Already-active no-op
