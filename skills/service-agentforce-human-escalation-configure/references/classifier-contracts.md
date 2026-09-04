# Escalation classifier contracts

Reference material for the deterministic Node classifiers under `scripts/`. Keeping the
pass/fail logic in these scripts (not in bash or model prose) satisfies authoring standard
A9 and makes each verdict unit-testable org-free.

## `classify-agent-active.mjs`

Gates the write: escalation can only be wired onto an agent that exists AND whose latest
`BotVersion` is `Active`.

Input is the file path to the JSON stdout of:

```bash
sf data query -q "SELECT Id,DeveloperName,MasterLabel,
  (SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1)
  FROM BotDefinition WHERE DeveloperName='<developerName>'" --target-org <org> --json
```

Emits: `{ exists, active, agentId, developerName, latestVersionId, latestVersionStatus, ready, reason }`
— `ready` is true only when `exists && active`. Exit 0 on a parseable body (verdict is in
the payload); exit 3 on an unparseable/failed query so the workflow surfaces the raw error
rather than assuming NOT-READY.

## `extract-outbound-route.mjs`

Couples `outboundRouteName` + `outboundRouteType` from WITHIN the same
`outboundRouteConfigs` block so a bundle cannot pass by carrying an unrelated name and type
in different blocks. The compiled `GenAiPlannerBundle` nests the route in a planner surface:

```xml
<plannerSurfaces>
    <surfaceType>Messaging</surfaceType>        <!-- or CustomerWebClient for MIAW -->
    <outboundRouteConfigs>
        <escalationMessage>…</escalationMessage>
        <outboundRouteName>Human_Escalation_Outbound_Flow</outboundRouteName>
        <outboundRouteType>OmniChannelFlow</outboundRouteType>
    </outboundRouteConfigs>
</plannerSurfaces>
```

Emits `{ name, type, surface, sameBlock, messagingSurface }` for the block matched by the
expected flow name (or the first block if none matches). `sameBlock=true` means name+type
came from the same block; `messagingSurface=true` means it sits on a Messaging-class
surface. Exit 0 on any parseable input (missing file => empty result); exit 2 on bad usage.

## `patch-escalation-surfaces.mjs`

Schema-aware, loss-less, idempotent in-place patcher for the two doc-driven surfaces. It
only ever touches the two target elements, never reorders surrounding metadata, and
refuses (exit 4) rather than guess when no safe insertion point exists.

**XSD order (authoritative — `GenAiPlannerBundle.json` wsdl_segment):**

- `AiPlannerSurfaceDef` (`<plannerSurfaces>`): `adaptiveResponseAllowed?`,
  `callRecordingAllowed?`, `outboundRouteConfigs*`, `surface`, `surfaceType` — a NEW
  `<outboundRouteConfigs>` MUST be inserted BEFORE `<surface>` (never appended after it).
- `AiPlannerSurfOtbdRouteDef` (`<outboundRouteConfigs>`): `escalationMessage?`,
  `outboundRouteName`, `outboundRouteType`.
- `GenAiPlugin` / `GenAiLocalPlugin`: `aiPluginUtterances*`, `canEscalate?`,
  `description?`, `developerName`, … — `<canEscalate>` MUST be inserted AFTER the last
  `<aiPluginUtterances>` and BEFORE `<description>` (or, if absent, before the first
  following required sibling — `developerName`/`masterLabel`/…).

Modes:

```bash
node patch-escalation-surfaces.mjs canEscalate   <genAiPlugin-xml-file>
node patch-escalation-surfaces.mjs outboundRoute <genAiPlannerBundle-xml-file> <flowApiName> [escalationMessage]
```

Patched IN PLACE. Exit 0 on success (prints a short JSON summary), 2 on bad usage, 4 when
no safe patch point is found (nothing written).

## `verify-escalation-config.mjs`

Renders the single deterministic verdict from an evidence object assembled by
`verify-and-configure.sh` (retrieved XML greps + SOQL reads).

`evidence.json` shape (all keys optional; missing => treated as not-satisfied):

| key | meaning |
| --- | --- |
| `canEscalate` | escalation topic flag set |
| `outboundRouteName` | route name on the bundle |
| `outboundRouteType` | must equal `OmniChannelFlow` |
| `outboundRouteSameBlock` | name+type from the SAME config block |
| `outboundRouteMessagingSurface` | block sits on a Messaging planner surface |
| `expectedFlowName` | expected outbound flow name |
| `flowActiveVersionId` | non-empty => flow active |
| `queueId` | non-empty => queue exists |
| `queueSobjectPresent` | context object bound to the queue |
| `queueHasActiveDirectUserMember` | ≥1 active DIRECT User member (necessary, not sufficient — Omni perm + presence access are proven only at runtime) |
| `queueRoutingConfigPresent` | QRC exists |
| `queueRoutingConfigBound` | `Group.QueueRoutingConfigId` points at the QRC |
| `agentActive` | latest BotVersion active |
| `thresholdAuthored` | directive policy authored (not a counter) |
| `defaultFailureThreshold` | numeric consecutive-failure threshold rendered into the directive (evidence only, never a gate) |

Emits `{ verdict, deterministicPass, directivePass, checks[], missing[] }` where `verdict`
is `CONFIGURED` | `INCOMPLETE`. The deterministic surfaces gate `CONFIGURED`; the threshold
directive is reported separately (never blocks the headless verdict — it is eval-verified,
not metadata-verified). Exit 0 on a parseable body; exit 3 on unparseable input.
