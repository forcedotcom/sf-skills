# Deployment State Tracking

Maintain a deployment state object throughout the workflow. This enables pause/resume and partial-deploy recovery.

```text
State = {
  targetOrg: string,
  steps: [
    { name: "StandardValueSets", status: "pending|in-progress|done|failed", detail?: string },
    { name: "Objects", status: "pending|in-progress|done|failed", detail?: string },
    { name: "ProductSpecificationTypes", status: "pending|in-progress|done|failed", detail?: string },
    { name: "ProductSpecificationRecTypes", status: "pending|in-progress|done|failed", detail?: string },
    { name: "QuickActions", status: "pending|in-progress|done|failed", detail?: string },
    { name: "SkeletonProfile", status: "pending|in-progress|done|failed", detail?: string },
    { name: "LifeSciConfigRecords", status: "pending|in-progress|done|failed", detail?: string },
    { name: "LifeSciMetadataRecords", status: "pending|in-progress|done|failed", detail?: string },
    { name: "TriggerHandlers", status: "pending|in-progress|done|failed", detail?: string },
    { name: "PageLayouts", status: "pending|in-progress|done|failed", selected?: [], deployed?: [], detail?: string },
    { name: "ProfileLayoutAssignments", status: "pending|in-progress|done|failed", detail?: string },
    { name: "FlexiPages", status: "pending|in-progress|done|failed", selected?: [], deployed?: [], detail?: string },
    { name: "ApplicationUpdate", status: "pending|in-progress|done|failed", detail?: string }
  ]
}
```

On failure at any step, show:

```text
Deployment paused at step: <StepName>
    Completed: <N>/<Total> steps
    Failed component: <component-name>
    Error: <error-message>

Options:
  1. Retry failed step
  2. Skip and continue
  3. Roll back (where applicable)
```

Wait for user choice before continuing.

## Progress Display

After each step completes, display progress:

```text
[done]    Step 1/13: StandardValueSets — deployed
[done]    Step 2/13: Objects — deployed
[done]    Step 3/13: ProductSpecificationTypes — deployed
[current] Step 4/13: ProductSpecificationRecTypes — in progress...
[pending] Step 5/13: QuickActions — pending
```

At the end, show final summary:

```text
LSC Starter Config Deployment Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
13/13 steps completed successfully
   - 14 layouts deployed (user selected: all)
   - 8 flexipages deployed (user selected: all)
   - 28 trigger handlers activated
   - Application file updated for selected flexipages
```
</content>
