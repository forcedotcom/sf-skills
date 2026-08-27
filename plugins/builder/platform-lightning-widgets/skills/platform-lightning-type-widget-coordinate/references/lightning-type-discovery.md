# Lightning Type Discovery Procedure

Use this procedure in Phase 2 of the orchestrator workflow. The goal is to resolve the user's named Lightning Type into an on-disk `schema.json`, verify it is **Apex-backed** (the only kind this orchestrator handles), and capture a SHA-256 fingerprint plus the Apex class FQN for the Phase 5 P0 gate and the Phase 4 widget-skill handoff.

> **Applies to the `existing-lightning-type-with-widget` path only.** Skipped on the `new-lightning-type-with-widget` path (the user is creating a new Lightning Type — there is nothing to discover). Do not run this procedure when Phase 1 picks `new-lightning-type-with-widget`.

---

The sequence is **find → verify → ensure-class**: locate the Lightning Type (local project first, then org), verify it is Apex-backed, then ensure its backing Apex class is in the local project (retrieving it from the org if needed). The downstream widget skill and the Phase 5 `field-trace` gate both read the `.cls` to enumerate `@AuraEnabled` fields — a Lightning Type without its class in the local project is unrenderable.

---

## Step 1 — Search the local project files

Look for any of:

- `force-app/**/lightningTypes/<TypeName>/schema.json`
- `<pkgDir>/lightningTypes/<TypeName>/schema.json` where `<pkgDir>` = `<packageDirectories[].path>/main/default` (per `platform-widget-generate/references/widget-bundle-layout.md`).

Match `<TypeName>` case-insensitively for the search but preserve the directory's actual case for outputs.

**Outcomes:**

- **Exactly one match.** Continue to Step 3 (verify Apex-backed) before capturing path + SHA-256.
- **Multiple matches** (case-insensitive name collision, multiple package directories, etc.). List candidates with their full paths to the user. Ask: *"Multiple Lightning Types match `<TypeName>`. Which one should the widget ground on?"* Wait for the user's pick, then continue to Step 3.
- **No match — do not skip.** Continue to Step 2 (org retrieve).

---

## Step 2 — Retrieve from the org

If the Lightning Type is not in the local project, run:

```bash
sf project retrieve start --metadata LightningTypeBundle:<TypeName>
```

The retrieve writes the Lightning Type bundle into the project under the configured package directory.

**Outcomes:**

- **Retrieve succeeds with one Lightning Type.** Continue to Step 3 (verify Apex-backed) before capturing path + SHA-256 + Apex class FQN.
- **Retrieve succeeds with multiple Lightning Types** (wildcard match; `LightningType:*<partial>*`). List them. Ask the user to pick. Re-retrieve with the exact name if needed, then continue to Step 3.
- **Retrieve reports "no metadata found".** The Lightning Type does not exist in the org. Continue to Step 5.
- **Retrieve fails with an error** (auth expired, org unreachable, permission denied, etc.). Surface the CLI error verbatim. Ask the user to fix and re-run.

---

## Step 3 — Verify the Lightning Type is Apex-backed

Read the located `schema.json`. Inspect the root `lightning:type` value.

| Root `lightning:type` value | Decision |
|---|---|
| Starts with `@apexClassType/` (for example `@apexClassType/c__AccountBriefing`) | **Apex-backed.** Continue. Capture the FQN — everything after `@apexClassType/`. The FQN points at the **outer Apex class**, whose `@AuraEnabled` fields define the payload shape. The `$<InnerClass>` suffix is not used at the Lightning Type root; inner classes live as `List<Inner>` fields on the outer class. |
| `lightning__objectType` (with primitive `properties`) | **Object/JSON-based.** Out of scope for this orchestrator. Tell the user: *"`<TypeName>` is an object/JSON-based Lightning Type. This orchestrator only handles Apex-backed Lightning Types. Use `platform-custom-lightning-type-generate` and `platform-widget-generate` separately for this case."* Stop. |
| Anything else | Surface the unrecognized value to the user and stop. Do not guess. |

When Apex-backed, capture path + SHA-256 + Apex class FQN, then continue to Step 4 (do not stop here — the class must be verified in the local project first).

---

## Step 4 — Ensure the backing Apex class is in the local project

**Both entry paths converge here** — a Lightning Type located in the local project (Step 1) and one retrieved from the org (Step 2) both reach this step. Locating the Lightning Type does NOT guarantee its backing class is local: `sf project retrieve --metadata LightningTypeBundle:<TypeName>` pulls only the bundle, not the referenced Apex class, and a hand-authored or partially-synced local bundle can reference a class that was never committed.

Parse `<ClassName>` from the Apex class FQN captured in Step 3 (`@apexClassType/<namespace>__<ClassName>` → `<ClassName>`; strip any `$<Inner>` suffix — retrieve the outer class). Check whether `<pkgDir>/classes/<ClassName>.cls` exists in the local project.

**Outcomes (covering all four LT × class scenarios):**

| Lightning Type source | `.cls` in local project? | Action |
|---|---|---|
| local project (Step 1) | yes | Nothing to do — continue. |
| local project (Step 1) | no | Retrieve the class (below). |
| org-retrieve (Step 2) | yes | Nothing to do — continue. |
| org-retrieve (Step 2) | no | Retrieve the class (below). |

When the class is absent, retrieve it by name:

```bash
sf project retrieve start --metadata ApexClass:<ClassName>
```

`ApexClass` is the metadata type; `<ClassName>` is the bare class name — no namespace prefix, no `.cls` extension. For multiple classes, comma-separate: `--metadata ApexClass:OrderSummary --metadata ApexClass:OrderLine`.

**Retrieve outcomes:**

- **Succeeds.** The `.cls` now lands under `<pkgDir>/classes/`. Continue.
- **Reports "no metadata found".** The backing class exists neither in the local project nor in the org — the Lightning Type is **unrenderable** (its payload shape is undefined). Surface this to the user verbatim and STOP. Do not hand the widget skill a Lightning Type whose `@AuraEnabled` fields cannot be enumerated.
- **Fails with an error** (auth expired, org unreachable, permission denied). Surface the CLI error verbatim. Ask the user to fix and re-run.

Done — path + SHA-256 + Apex class FQN captured, and the `.cls` confirmed in the local project.

---

## Step 5 — Lightning Type does not exist anywhere

Tell the user the Lightning Type is not in the local project and not in the org. Offer to **switch to the `new-lightning-type-with-widget` path** — generate a new Apex-backed Lightning Type (with its Apex class, auto-engaged) before authoring the widget.

Wait for the user's confirmation. Do not silently pick. If the user does not want a Lightning Type at all, route them to `platform-widget-generate` directly — that case is outside this orchestrator's scope.

---

## Staleness rule

Do **not** maintain a cross-session cache. Each invocation of this orchestrator re-reads the local project and re-retrieves from the org as needed. Any single retrieve result is treated as authoritative for the lifetime of that orchestrator run.

---

## Output of Phase 2

```text
lightningTypeSchema = {
  name: "<TypeName>",
  path: "<pkgDir>/lightningTypes/<TypeName>/schema.json",
  sha256: "<hex>",
  source: "fs" | "org-retrieve",
  apexClassFqn: "<namespace>__<ClassName>",   # outer class only — no $<Inner> form
  apexClassPath: "<pkgDir>/classes/<ClassName>.cls",   # guaranteed in the local project by Step 4
  apexClassSource: "fs" | "org-retrieve",
}
```

Phase 2 always ends with a non-null `lightningTypeSchema` on the `existing-lightning-type-with-widget` path, **and with the backing `.cls` confirmed in the local project** (per Step 4). If discovery fails and the user does not switch to `new-lightning-type-with-widget`, or if the backing Apex class exists nowhere, the orchestrator stops.
