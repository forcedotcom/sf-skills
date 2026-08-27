# Your task

Review {{SUBJECT}} and identify {{DOMAIN}} issues.
Return your analysis as report in SARIF JSON format with no additional text or explanation.

## Instructions for identifying {{DOMAIN}} issues.

The instructions below provide list of possible issues with the explanation how to find and report those.
Each section corresponds to a specific issue and describes what patterns to look for.

{{INSTRUCTIONS}}

## Requirements to output

- Return ONLY valid JSON without any additional information
- Do not write JSON to a file, just respond with it
- List of results should be empty if no issues were found
