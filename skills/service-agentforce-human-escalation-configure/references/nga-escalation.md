# Next-gen (NGA) escalation — detection, surface split, and verdict

The classic escalation surface (`GenAiPlannerBundle.outboundRouteConfigs` + `GenAiPlugin.canEscalate`) does not exist on next-gen authoring (NGA) orgs. NGA agents are defined by `AiAuthoringBundle` (Agent Script), and the escalation surface moves into the bundle. This skill supports both models from one code path; only the agent-side surface differs.

## Detection (Phase 1b)

`sf org list metadata-types` identifies the model surfaces available in the org. When both surfaces exist, the skill retrieves the requested agent from each surface and classifies that specific target rather than applying an org-wide default:

| Metadata types exposed | `authoring_model` | Agent surface authored/verified |
|---|---|---|
| Requested agent is found only in `GenAiPlannerBundle` | `classic` | `canEscalate` + `outboundRouteConfigs` |
| Requested agent is found only in `AiAuthoringBundle` | `nga` | `@utils.escalate` (Service) / create-record (Employee) |
| Requested agent is found in both surfaces | `ambiguous` | — (skill blocks before any write) |
| Requested agent is found in neither surface while both models exist | `none` | — (skill blocks before any write) |

`AUTHORING_MODEL_OVERRIDE=classic|nga` explicitly pins the branch when the target is genuinely ambiguous or metadata retrieval is inconclusive. There is no classic-first default: an NGA target in a mixed-model org stays NGA.

## Why classic ≠ NGA (not a straight port)

The classic skill's value was deterministically authoring + verifying a failure-threshold outbound route on one metadata surface. NGA splits that into pieces of different natures:

| Classic single surface | NGA equivalent | Deterministic? |
|---|---|---|
| `outboundRouteConfigs` → named queue | channel → queue Omni routing (the routing half this skill builds) | yes |
| failure-threshold trigger | Agent Script instruction / `@utils.escalate` action | no — prompt-led (a directive) |
| (n/a for employee agents) | Employee agent → create Incident/Case action → Omni-route that record | yes |

There is no numeric "escalate after N failures" field in Agent Script; the threshold stays a directive (the same boundary the classic path already uses).

## Service vs Employee split

- **Service agent** — declares `connection messaging:` and can call `@utils.escalate` for a live hand-off routed through the messaging connection to the queue.
- **Employee agent** — cannot declare `connection messaging:` or use `@utils.escalate`. Its escalation surrogate is an action that creates a routable record (Case/Incident/ticket) which then Omni-routes to the human queue.

`scripts/classify-nga-escalation.mjs` walks the retrieved `AiAuthoringBundle` (in-process, so it never invokes `find` — the sandbox blocks `find -exec`'s `ARG_MAX` probe) and returns:

To avoid a false `CONFIGURED`, it scans **only Agent Script** (`*.agent` files, or any file whose content declares `start_agent`), **strips comments** (`/* */`, whole-line `//`/`#`), and proves reachability **per agent block**: the escalation surface must live in the same `start_agent` block as its trigger, under a `reasoning: actions:` section (a line more indented than the `actions:` header). A commented-out block, prose mention, cross-block match, or unrelated file no longer satisfies the surface — when reachability cannot be proven it reports `escalationSurfacePresent:false` (→ caller stays `INCOMPLETE`). An unreadable/missing retrieve dir exits `3` (inconclusive), never an empty exit `0`.

```text
{ agentType, bundleFound, connectionMessaging, escalateActionPresent, createRecordActionPresent, escalationSurfacePresent }
```

- `agentType`: `service` if `connection messaging:` present, else `employee` (or `unknown` when no bundle was retrieved).
- `escalationSurfacePresent`: `escalateActionPresent` for Service, `createRecordActionPresent` for Employee. `createRecordActionPresent` is a heuristic (action refs matching create + case/incident/ticket/record) — treat a false negative as "author via agentforce-generate", never as a hard failure of the agent.

## NGA verdict set

`verify-escalation-config.mjs` keeps the model-agnostic routing checks (`outboundFlowActive`, `humanQueue`, `queueSobject`, `queueHasActiveDirectUserMember`, `queueRoutingConfig`, `queueRoutingConfigBound`, `agentActive`) and swaps the surface checks:

- classic → `canEscalate` + `outboundRouteConfigs`
- nga → `ngaEscalationSurface` (from `escalationSurfacePresent`)

`thresholdDirective` remains a directive check in both. `CONFIGURED` requires all deterministic checks; the threshold is reported separately.

## Authoring delegation

This skill **verifies** the NGA surface; it does not mutate Agent Script. When `ngaEscalationSurface` is missing the verdict is `INCOMPLETE` and `next_steps` points to `agentforce-generate` to author the surface: for a Service agent add a reachable `{!@utils.escalate}` action (needs `connection messaging:`); for an Employee agent add a create-record (Case/Incident) action that Omni-routes to the queue. Re-run afterward to reach `CONFIGURED`.
