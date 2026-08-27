# Phase Execution Pattern

Each phase follows this standard pattern:

| Step | What to do | Why |
|------|-----------|-----|
| **0. Precondition Check** | Run `scripts/check-phase-N-*.sh` script | Verifies prerequisites are met before proceeding |
| **1. Load skill** | Invoke the skill for this phase | Gives you current rules, patterns, constraints |
| **2. Execute** | Follow the loaded skill's workflow | The skill defines HOW to do the work correctly |
| **3. Verify** | Run lint and build | Catch errors before moving to next phase |
| **4. Post-verification** | Run `scripts/check-phase-N-complete.sh` (if available) | Machine-checkable validation of phase completion |
| **5. Checkpoint** | Confirm phase completion | Ensures dependencies satisfied for next phase |

**CRITICAL: Do NOT skip step 1 (loading the skill).** Skills evolve — always load the current version.

## Available Verification Scripts

- `scripts/check-sfdx-project.sh` - Validates SFDX project exists (Phase 0/1 prerequisite)
- `scripts/check-phase-1-complete.sh` - Verifies scaffold complete (Phase 4/6 prerequisite)
- `scripts/check-phase-4-complete.sh` - Verifies UI build complete (Phase 6 prerequisite)
- `scripts/check-phase-6-ready.sh` - Verifies deployment prerequisites met
- `scripts/check-hosting-target.sh` - Determines which hosting target is configured

All scripts exit 0 on success, exit 1 on failure with an error message.
