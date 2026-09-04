# Failure-threshold policy (native, directive-based)

## Why this is not a metadata counter

Agentforce does not expose a metadata field or setting that counts "consecutive failed
turns" and escalates automatically. The "escalate after two failures" behaviour is a
**planner policy expressed as instruction text** in the agent's Agent Script (NGA
authoring model). This is the platform-native representation the user selected.

Consequences:

- The threshold is **authored, not enforced by a counter**. The bundled template
  [`assets/escalation-thresholds.instructions.md`](../assets/escalation-thresholds.instructions.md)
  is the source directive text.
- It is **verified by an ADK eval rubric** (does the agent escalate on the 2nd failure? on
  the 1st failure for password reset?) and a **documented manual conversation test** — never
  by a deterministic metadata round-trip.
- The `verify-and-configure.sh` verdict therefore reports the threshold as `directive`
  (authored / not-authored), distinct from the `deterministic` config surfaces
  (`canEscalate`, `outboundRouteConfigs` name+type coupling on the Messaging surface, outbound
  flow Active, queue + QueueSobject + bound QueueRoutingConfig, ≥1 active human member, agent Active).

## Recommended thresholds

The threshold is a **caller input**, not a fixed constant. The values below are defaults;
a scenario that mandates a different number (e.g. a narrative requiring escalation after
**three** consecutive failures) supplies its own value via the skill input — no code change
is needed.

| Scenario | Threshold | Rationale |
|---|---|---|
| Default (any unresolved request) | 2 consecutive failures | Give the agent one retry before handing off |
| Password reset / credential issues | 1 failure | Time-sensitive; do not retry repeatedly |
| Caller-specified | any N | Whatever the scenario's authoritative requirement is (pass N as the input) |

## Authoring steps

1. Substitute tokens in the template (`__DEFAULT_FAILURES__=2`, `__RESET_TOPIC_LABEL__`,
   `__ESCALATION_MESSAGE__`).
2. Add the default directive to the agent's global/system instructions.
3. Add the per-topic override to the password-reset topic instructions.
4. Republish + reactivate the agent (`sf agent validate|publish|activate ... --target-org $ORG`).
5. Confirm via the eval rubric and the manual test in
   [runtime-verification.md](./runtime-verification.md).
