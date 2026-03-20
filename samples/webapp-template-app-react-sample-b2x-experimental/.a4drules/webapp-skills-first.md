---
description: Always search for and read relevant skills before starting any task
paths:
  - "**/webapplications/**/*"
---

# Skills-First Protocol (MUST FOLLOW)

**Before planning, executing any task, generating code, or running terminal commands**, you MUST explicitly check if an existing Skill is available to handle the request. Do not default to manual implementation if a specialized domain Skill exists.

## Pre-Task Sequence
1. **Skill Discovery:** Review the names and descriptions of all available/loaded Skills in your current context.
2. **Match Analysis:** Evaluate if the user's current task aligns with any Skill's described use case (e.g., code reviews, PR generation, database migrations, specific framework debugging).
3. **Explicit Declaration:** If a matching Skill is found, your first output MUST be:
   > "Skill identified: [Skill Name]. Executing via Skill instructions..."
   You must then strictly adhere to the instructions defined in that specific Skill.

## Prohibited Actions
* Do not write custom utility scripts or complex bash commands for a workflow that is already covered by a loaded Skill.
* Do not bypass or ignore the loaded `SKILL.md` instructions if a relevant Skill is triggered.

## Manual Fallback
Only proceed with standard/manual execution if you have actively evaluated your available Skills and confirmed that no relevant Skill exists for the current prompt.