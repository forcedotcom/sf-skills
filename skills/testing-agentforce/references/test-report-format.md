# Test Report Format, Coverage Analysis, and CI/CD — Reference

## Summary Report

```
Agentforce Agent Test Report
===========================================

Agent: OrderManagementAgent
Org: production
Test Cases: 6
Duration: 45.2s

Results:
  Subagent Routing: 5/6 passed (83.3%)
  Action Invocation: 4/6 passed (66.7%)
  Grounding: 6/6 passed (100%)
  Safety: 6/6 passed (100%)
  Response Quality: 5/6 passed (83.3%)

Overall Score: 86.7%
Status: PASSED WITH WARNINGS
```

## Detailed Test Cases

```
Test Case 1: "Where is my order?"
  Expected Topic: order_mgmt
  Actual Topic: order_mgmt (pass)
  Expected Action: get_order_status
  Actual Action: get_order_status (pass)
  Grounding: GROUNDED (pass)
  Safety Score: 0.95 (pass)
  Response Quality: Relevant (pass)

Test Case 2: "I want to return this"
  Expected Topic: returns
  Actual Topic: order_mgmt (fail - misrouted)
  Fix Applied: Expanded 'returns' subagent description
  Retry Result: Correctly routed (pass)
```

## Coverage Analysis

Track which subagents and actions are tested across both modes:

| Dimension | Target | How to measure |
|-----------|--------|----------------|
| Subagent coverage | 100% of non-entry subagents | Count subagents with at least 1 test case |
| Action coverage | 100% of actions | Count actions with at least 1 test case targeting them |
| Phrasing diversity | 3+ utterances per subagent (production) | Multiple wordings per intent |
| Guardrail coverage | At least 1 off-topic test | Verify agent deflects non-relevant queries |
| Multi-turn coverage | Test subagent transitions | Conversation history tests |
| Escalation coverage | Test escalation triggers | Verify human handoff works |

## CI/CD with Testing Center

For CI/CD pipelines, use Mode B (Testing Center) for persistent regression suites:

```yaml
# .github/workflows/agent-testing.yml
name: Agent Testing
on:
  pull_request:
    paths:
      - 'force-app/**/*.agent'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate org
        run: |
          echo "${{ secrets.SFDX_AUTH_URL }}" > auth.txt
          sf org login sfdx-url --sfdx-url-file auth.txt --alias testorg

      - name: Deploy test suite
        run: |
          sf agent test create --json \
            --spec tests/${{ vars.AGENT_NAME }}-testing-center.yaml \
            --api-name ${{ vars.AGENT_NAME }}_CI \
            --force-overwrite \
            -o testorg

      - name: Run tests
        run: |
          sf agent test run --json \
            --api-name ${{ vars.AGENT_NAME }}_CI \
            --wait 15 \
            --result-format junit \
            --output-dir test-results \
            -o testorg

      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: agent-test-results
          path: test-results/
```

## Cross-Skill Integration (/observing-agentforce)

The /observing-agentforce skill creates test cases during its Phase 3.7 after fixing issues found through STDM session analysis. These test cases use **Testing Center format** so they can be deployed directly to the org.

### Test Case Convention

Test cases from /observing-agentforce follow Testing Center YAML format:

```yaml
# tests/<AgentApiName>-regression.yaml
name: "<AgentName> Regression Tests"
subjectType: AGENT
subjectName: <AgentApiName>

testCases:
  - utterance: "find me a home in San Jose"
    expectedTopic: home_search
    expectedActions:
      - search_homes_and_communities

  - utterance: "I have a legal dispute"
    expectedTopic: escalation
    expectedActions:
      - transfer_to_agent
```

### Deploying Cross-Skill Tests

When /observing-agentforce generates test cases, deploy them using Mode B:

```bash
# Deploy the regression test suite
sf agent test create --json \
  --spec tests/<AgentApiName>-regression.yaml \
  --api-name <AgentApiName>_Regression \
  --force-overwrite \
  -o <org>

# Run
sf agent test run --json \
  --api-name <AgentApiName>_Regression \
  --wait 10 \
  --result-format json \
  -o <org>
```

### Test File Location Convention

```
<project-root>/
  tests/
    <AgentApiName>-testing-center.yaml  # Full smoke suite (Mode B -- Testing Center)
    <AgentApiName>-regression.yaml      # Regression tests from /observing-agentforce (Mode B)
    <AgentApiName>-smoke.yaml           # Ad-hoc smoke tests (Mode A -- preview only)
```

Both this skill and /observing-agentforce write to the `tests/` directory using the agent's API name as prefix. Testing Center files (`-testing-center.yaml`, `-regression.yaml`) use the `name/subjectType/subjectName/testCases` format.
