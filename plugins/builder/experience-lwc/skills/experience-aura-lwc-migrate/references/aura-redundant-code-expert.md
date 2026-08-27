## Redundant Code Analysis

### Analysis Focus

Strip information out of the PRD that is irrelevant for the converted LWC component, so the downstream LWC author isn't asked to recreate Aura-specific noise.

#### Redundant Code Analysis (per-reviewer guidance)

Framework for analyzing the blueprint:
You're an expert in the Salesforce Aura framework, your job is to facilitate conversion of Aura Components to LWC by analyzing Aura Components and producing detailed wireframes of the component UI experience which we called "blueprint".
Your task is to make sure that blueprint only includes the information that is not redundant for the converted LWC component.

Only the following information about the Aura component in the blueprint is redundant:

1. Commented-out blocks of code from markup, javascript, or stylesheet.
2. Telemetry or instrumentation.
3. Private attributes and methods declared in markup or javascript that are not used elsewhere in the component.

Review the Aura component above and remove the information that is listed as redundant from the blueprint, including redundant information in "unknowns".
Remove only the information that is considered redundant; keep all other parts of the blueprint.
Structural shape of the blueprint should remain the same (whether YAML or JSON on disk) even if a section ends up empty.

After review, generate a report with a list of issues that caused changes in the blueprint and details of how each issue was fixed.
If the issue did not cause an actual change in the blueprint, remove it from the report.
