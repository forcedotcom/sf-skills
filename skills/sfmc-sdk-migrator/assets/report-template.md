# SFMC SDK Migration Report

> Fill every section. The "Needs manual review" section is the one a senior
> developer will actually read — be specific and honest there. Replace each
> `<...>` placeholder; delete sections that genuinely don't apply rather than
> leaving them empty.

## Summary

- **Platform:** <android | ios>
- **From:** <detected version / API era, e.g. legacy MarketingCloudSdk 8.x>
- **To:** <target version the customer chose, e.g. unified SFMCSdk 11.0.1>
- **Why this target:** <latest | staged jump to first unified release | within-era bump — one line on why this version was chosen vs. alternatives>
- **Migration kind:** <full-code-migration (crossed the legacy→unified boundary) | version-config-bump (stayed within era)>
- **Files changed:** <n>
- **Call sites rewritten:** <n>
- **Items needing manual review:** <n>
- **Build verification:** <passed | failed | not run — see Verification section>

One-paragraph plain-language description of the gap and what the migration did.

## Refactor units (parallel Phase 4)

Include this section whenever the refactor was fanned out to subagents. Build it
**directly from the observer ledger** (`observe_workers.py` output) — one row per
planned work unit, so nothing dispatched can go silently unreported. The report
must not be produced until the observer gate is green (all units terminal).

| Unit (files) | Status | Restarts | Flagged | Note |
|---|---|---|---|---|
| `<file/module>` | done / blocked / **demoted-to-review** | <n> | <n> | <why blocked/demoted, if any> |

- **Gate:** <all units terminal ✓ | list any that were demoted to manual review and why>

## Changes by area

For each area that had changes, list the rewrites with `file:line`. Keep it scannable.

### Initialization
- `<file>:<line>` — `<old>` → `<new>` <(any caveat applied)>

### Push / token registration
- ...

### Identity / contact key
- ...

### Event tracking
- ...

### In-app messaging
- ...

### Dependencies (Gradle / version catalog / CocoaPods / Swift Package Manager)
- `<file>` — removed `<old coordinate>`, added `<new coordinate(s)>`
- **Module versions resolved:** <how they were determined — "resolved at runtime via resolve_versions.py against `<repo>`" | "Maven repo unreachable, fell back to matrix seed versions (may be stale)">. List the exact versions used per module (`sfmcsdk:<v>`, `marketingcloudsdk:<v>`, ...). If a dependency resolution error occurred and was fixed by re-resolving a version, note it.

### Manifest / Info.plist / entitlements / config
- `<file>` — <removed legacy component | added required entry | no change needed because auto-merged>

## Needs manual review

The migration intentionally did **not** rewrite these. Each is a place where an
automated mapping would risk silently changing behavior. Format:

- **`<file>:<line>`** — <what was found>. **Why flagged:** <no matrix entry / custom subclass / ambiguous field mapping / tag handling>. **Suggested next step:** <concrete action for the developer>.

## Verification

- **Build:** <exact command run, e.g. `./gradlew :app:assembleDebug`> → <result; paste the relevant error lines if it failed>.
- **Manual checks for the developer:**
  1. Launch the app and confirm the SDK initializes (look for the init-status callback / log).
  2. Send a test push from Marketing Cloud and confirm it's received and opens correctly.
  3. Trigger a tracked event and confirm it appears in reporting.
  4. If push on Android 13+: confirm the `POST_NOTIFICATIONS` runtime prompt appears.

## Notes / assumptions

<Anything else the developer should know — e.g. "assumed BuildConfig.MC_APP_ID still holds the application id; did not touch Firebase config.">
