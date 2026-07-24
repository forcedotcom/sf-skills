# Changes to Force Sales Agent BotDefinition Creation

## Product Context

**Previous behavior**: Pipeline Management had two architectures — "Platform Copilot" (agent user only, backend suggestions work) and "Standalone Bot" (agent user + BotDefinition, interactive chat + backend suggestions). The scripts treated both as valid and would exit successfully with just the agent user.

**Product requirement change**: Users now **require** an interactive Sales Agent they can chat with, which requires the BotDefinition. While backend suggestion generation can technically work with just the agent user + PSG, the complete user experience demands the BotDefinition for conversation interface.

## Problem
The `create-agent.sh` script previously accepted a "Platform Copilot" architecture where no BotDefinition existed and only backend suggestion generation worked. However, **BotDefinition:SalesAgent is REQUIRED** for a complete Pipeline Management experience — users need an interactive Sales Agent they can chat with. The original script would exit successfully when it found the agent user, even if no BotDefinition existed, leaving users without the required interactive agent.

## Solution
Modified `create-agent.sh` to **always attempt to create the Sales Agent BotDefinition** when:
- Agent user exists ✓
- PSG is assigned ✓
- **BotDefinition does NOT exist** ❌

## Changes Made to `create-agent.sh`

### Before (Lines 80-93)
```bash
if [[ -n "$EXISTING_BOT" ]]; then
  echo "  Architecture: Standalone Bot (BotDefinition:SalesAgent found)"
else
  echo "  Architecture: Platform Copilot (no standalone BotDefinition — this is normal)"
  echo "  PM actions are wired into the platform-level Copilot agent."
fi
echo ""
echo "Agent setup is FUNCTIONAL."
# ... exits immediately
exit 0
```

**Issue**: Script exits without creating BotDefinition, leaving users with no interactive agent.

### After (Lines 80-165)
```bash
if [[ -n "$EXISTING_BOT" ]]; then
  # BotDefinition exists - done
  echo "  Architecture: Standalone Bot (BotDefinition:SalesAgent found)"
  exit 0
else
  # BotDefinition missing - create it (REQUIRED)
  echo "  BotDefinition:SalesAgent not found"
  echo "  Attempting to create Sales Agent BotDefinition for user interaction..."
  
  # Deploy via authoring bundle
  if ! sf agent publish authoring-bundle --api-name SalesAgent; then
    echo "ERROR: Failed to publish Sales Agent"
    exit 1
  fi
  
  # Activate latest version
  if ! sf agent activate --api-name SalesAgent --version <latest>; then
    echo "ERROR: Failed to activate Sales Agent"
    exit 1
  fi
  
  # Success - BotDefinition created and activated
  exit 0
fi
```

**Fix**: Script now:
1. Detects missing BotDefinition
2. Deploys Sales Agent via authoring bundle
3. Activates the agent automatically
4. **Exits 1 if creation fails** (BotDefinition is required, not optional)
5. Provides clear success/failure messaging

## New Behavior

### When agent user exists AND BotDefinition exists

```text
✓ Agent user found
✓ BotDefinition found
✓ Agent setup is FUNCTIONAL
✓ No further action needed
```

### When agent user exists BUT BotDefinition missing

```text
✓ Agent user found
⚠ BotDefinition NOT found
→ Creating Sales Agent via authoring bundle...
→ Publishing Sales Agent...
→ Activating Sales Agent version <latest>...
✓ Agent setup is COMPLETE
```

### When agent user is missing

```text
✗ Agent user NOT found
→ Attempting SOAP toggle...
→ (existing fallback logic)
```

## Testing

To test the modified script:

```bash
cd skills/sales-agentforce-pipeline-management-configure/scripts

# Test on org with agent user but no BotDefinition
/opt/homebrew/bin/bash create-agent.sh <org-alias>

# Expected output:
# - Detects agent user
# - Detects missing BotDefinition
# - Creates and activates Sales Agent
# - Exits with status 0
```

## Files Modified

1. **`scripts/create-agent.sh`** - Main logic change (lines 80-165)
   - Added authoring bundle deployment when BotDefinition is missing
   - Added agent activation step
   - Added improved status messaging

## Backward Compatibility

✅ **Fully backward compatible**
- If BotDefinition already exists → same behavior as before (early exit)
- If agent user is missing → existing fallback logic unchanged
- Only new behavior is when agent user exists but BotDefinition is missing

## Related Files

- **Assets used**:
  - `assets/sales_management_agent.agent` - Agent Script definition
  - `assets/sales_management_agent.bundle-meta.xml` - Bundle metadata
  
- **Called from**:
  - `setup-all.sh` - Main orchestration script (Phase 4)

## Verification

After running the modified script, verify with:

```bash
/opt/homebrew/bin/bash verify-all.sh <org-alias>
```

Expected output:

```text
--- Agent ---
  [PASS] Agent user: salesmanagementagentuser@...
  [PASS] BotDefinition: SalesAgent  ← Should now PASS instead of FAIL
```

## Impact

**Before**: Users had to manually create the Sales Agent BotDefinition  
**After**: Sales Agent BotDefinition is created automatically

This ensures users get both:
1. ✅ Backend suggestion generation (agent user + flow)
2. ✅ Interactive Sales Agent for user chat (BotDefinition)

## Commit Message

```text
fix: always create Sales Agent BotDefinition in create-agent.sh

When agent user exists but BotDefinition is missing, the script now:
- Deploys Sales Agent via authoring bundle
- Activates version 1 automatically
- Provides clear success/failure messaging

This ensures users get an interactive Sales Agent they can chat with,
not just backend suggestion generation.

Fixes: Pipeline Management setup completing without user-facing agent
```
