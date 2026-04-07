# Mode B: Testing Center Batch Testing — Full Reference

Testing Center is Salesforce's built-in test infrastructure for Agentforce agents. Tests are deployed as metadata to the org and can be run via CLI or Setup UI.

## Phase 1: Create Test Spec YAML

The Testing Center uses a specific YAML format. Create a temporary spec file:

```yaml
# /tmp/<AgentApiName>-test-spec.yaml
name: "OrderService Smoke Tests"
subjectType: AGENT
subjectName: OrderService          # BotDefinition DeveloperName (API name)

testCases:
  # Topic routing test
  - utterance: "Where is my order #12345?"
    expectedTopic: order_status

  # Action invocation test (FLAT string list -- NOT objects)
  # CRITICAL: Use Level 2 INVOCATION names from reasoning: actions: (e.g. "lookup_order")
  #           NOT Level 1 DEFINITION names from topic: actions: (e.g. "get_order_status")
  - utterance: "I want to return my order from last week"
    expectedTopic: returns
    expectedActions:
      - lookup_order

  # Outcome validation (LLM-as-judge)
  - utterance: "How do I track my shipment?"
    expectedTopic: order_status
    expectedOutcome: "Agent explains how to check shipment tracking status"

  # Escalation test
  - utterance: "I want to talk to a real person about a billing dispute"
    expectedTopic: escalation
    expectedActions:
      - transfer_to_agent

  # Guardrail test
  - utterance: "What's the best recipe for chocolate cake?"
    expectedOutcome: "Agent politely declines and redirects to order-related topics"

  # Multi-turn test with conversation history
  - utterance: "Yes, my email is john@example.com"
    expectedTopic: identity_verification
    expectedActions:
      - verify_customer
    conversationHistory:
      - role: user
        message: "I need to check my mortgage status"
      - role: agent
        topic: identity_verification
        message: "I'd be happy to help with your mortgage status. First, I'll need to verify your identity. What is your email address on file?"
```

### Required Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name for the test suite (becomes MasterLabel) |
| `subjectType` | Yes | Always `AGENT` |
| `subjectName` | Yes | Agent BotDefinition DeveloperName (API name, e.g. `OrderService`) |
| `testCases` | Yes | Array of test case objects |
| `testCases[].utterance` | Yes | User input message to test |
| `testCases[].expectedTopic` | No | Expected topic name |
| `testCases[].expectedActions` | No | Flat list of action name strings |
| `testCases[].expectedOutcome` | No | Natural language description (LLM-as-judge) |
| `testCases[].conversationHistory` | No | Prior conversation turns for multi-turn tests |
| `testCases[].contextVariables` | No | Session context variables |

### Key Rules

- `expectedActions` is a **flat string array**, NOT objects: `["action_a", "action_b"]`
- Action assertion uses **superset matching**: test PASSES if actual actions include all expected actions
- **Transition actions** (`go_home_search`, `go_escalation`) appear in `actionsSequence` alongside real actions. The superset matching handles this correctly -- you don't need to list transition actions.
- `expectedOutcome` uses LLM-as-judge evaluation -- describe the desired behavior in natural language
- Missing `expectedOutcome` causes a harmless ERROR in `output_validation` but topic/action assertions still pass
- **Always add `expectedOutcome`** -- it is the most reliable assertion type (LLM-as-judge scores 5/5 consistently for correct behavior) and works even when topic/action assertions can't capture nuanced behavior

### Single-Turn vs Multi-Turn Considerations

- Single-turn tests only capture the first response. If an action requires info collection first (e.g. identity verification asks for email before calling `verify_customer`), the action won't fire in one turn.
- For multi-turn workflows, either: (1) omit `expectedActions` and rely on `expectedOutcome`, or (2) use `conversationHistory` to simulate prior turns.
- For guardrail tests (off-topic), omit `expectedTopic` and use `expectedOutcome` only -- the agent correctly stays in `entry` which has no matching topic assertion. NOTE: The generated XML still includes an empty `topic_assertion` expectation, which will return `FAILURE` with score=0. This is expected and harmless -- only check the `output_validation` result for guardrail tests.

### Parsing Results for Guardrail/Safety Tests

When summarizing results, filter out `topic_assertion` FAILURE for tests that have no
`expectedTopic` set. These are false negatives caused by the empty assertion XML. Count
only `output_validation` results for these tests. Example:
```python
# When parsing results, skip topic_assertion for guardrail tests
for tc in test_cases:
    has_expected_topic = bool(tc.get('expectations', {}).get('expectedTopic'))
    for r in tc.get('testResults', []):
        if r['name'] == 'topic_assertion' and not has_expected_topic:
            continue  # Skip -- empty assertion always fails
        # ... process other results
```

## Phase 2: Deploy and Run Tests

`sf agent test create` takes the YAML spec, converts it to `AiEvaluationDefinition` metadata XML, and deploys it to the org. The XML is written to `force-app/main/default/aiEvaluationDefinitions/` as part of the SFDX project.

```bash
# Step 1: Check if Testing Center is available
sf agent test list --json -o <org>

# Step 2: Deploy the test suite (writes XML to force-app/ and deploys to org)
sf agent test create --json \
  --spec /tmp/<AgentApiName>-test-spec.yaml \
  --api-name <TestSuiteName> \
  -o <org>

# The deployed metadata is now at:
# force-app/main/default/aiEvaluationDefinitions/<TestSuiteName>.aiEvaluationDefinition-meta.xml

# Step 3: Run the tests (wait for results)
sf agent test run --json \
  --api-name <TestSuiteName> \
  --wait 10 \
  --result-format json \
  -o <org> | tee /tmp/test_run.json

# Step 4: Extract job ID from run output
JOB_ID=$(python3 -c "import json; print(json.load(open('/tmp/test_run.json'))['result']['runId'])")

# Step 5: Get detailed results (ALWAYS use --job-id, NOT --use-most-recent)
sf agent test results --json \
  --job-id "$JOB_ID" \
  --result-format json \
  -o <org> | tee /tmp/test_results.json
```

### Updating an Existing Test Suite

```bash
sf agent test create --json \
  --spec /tmp/<AgentApiName>-test-spec.yaml \
  --api-name <TestSuiteName> \
  --force-overwrite \
  -o <org>
```

### Retrieving Existing Test Definitions

```bash
sf project retrieve start --json --metadata "AiEvaluationDefinition:<TestSuiteName>" -o <org>
# Retrieved to: force-app/main/default/aiEvaluationDefinitions/<TestSuiteName>.aiEvaluationDefinition-meta.xml
```

## Phase 3: Analyze Results

Parse the results JSON:

```bash
# Show pass/fail summary per test case
python3 -c "
import json
data = json.load(open('/tmp/test_results.json'))
for tc in data['result']['testCases']:
    utterance = tc['inputs']['utterance'][:50]
    results = {r['name']: r['result'] for r in tc.get('testResults', [])}
    topic_pass = results.get('topic_assertion', 'N/A')
    action_pass = results.get('action_assertion', 'N/A')
    outcome_pass = results.get('output_validation', 'N/A')
    print(f'{utterance:<50} topic={topic_pass:<6} action={action_pass:<6} outcome={outcome_pass}')
"
```

### Understanding Results Fields

| Result field | Description |
|---|---|
| `testResults[].name` | `topic_assertion`, `action_assertion`, `output_validation` |
| `testResults[].result` | `PASS`, `FAILURE`, or `ERROR` |
| `testResults[].score` | Numeric score (0-1) |
| `testResults[].expectedValue` | What you specified in the YAML |
| `testResults[].actualValue` | What the agent actually returned |
| `generatedData.topic` | Actual runtime topic name |
| `generatedData.actionsSequence` | Stringified list of actions invoked |
| `generatedData.outcome` | Agent's actual response text |

## Phase 4: Fix Loop

For each failed test case:

1. **Topic assertion failed** -- compare `expectedValue` vs `actualValue`
   - If actual is a hash-suffixed name (e.g. `p_16j...`), see Topic Name Resolution below
   - If actual is wrong topic, fix the `.agent` file topic description

2. **Action assertion failed** -- check `generatedData.actionsSequence`
   - If action not invoked: fix topic instructions or action `available when` guard
   - If wrong action: fix action descriptions to disambiguate

3. **Outcome validation failed** -- check `generatedData.outcome`
   - Review the agent's actual response against `expectedOutcome`
   - Tighten topic instructions to guide the response

After fixing the `.agent` file, redeploy and re-run:

```bash
# Redeploy agent
sf agent publish authoring-bundle --json --api-name <AgentApiName> -o <org>

# Re-run the same test suite
sf agent test run --json --api-name <TestSuiteName> --wait 10 --result-format json -o <org>
```

## Topic Name Resolution

Topic names in Testing Center may differ from what you see in the `.agent` file:

| Topic type | Name to use in YAML | Example |
|---|---|---|
| Standard topics | `localDeveloperName` (short name) | `Escalation`, `Off_Topic` |
| Custom topics | Short name from `.agent` file | `home_search`, `warranty_service` |
| Promoted topics | Full runtime `developerName` with hash suffix | `p_16jPl000000GwEX_Topic_16j8eeef13560aa` |

**Discovery workflow** (when topic names don't match):

1. Run the test with best-guess topic names
2. Check actual topics in results: `jq '.result.testCases[].generatedData.topic' /tmp/test_results.json`
3. Update YAML with actual runtime names
4. Redeploy with `--force-overwrite` and re-run

**Topic hash drift**: Runtime topic `developerName` hash suffix changes after agent republish. Re-run discovery after each publish.

## Auto-Generation from .agent File

Derive a Testing Center spec from the `.agent` file:

1. **One test case per non-entry topic** -- utterance from topic description keywords
2. **One test case per key action** -- utterance that triggers the action's primary use case
3. **One guardrail test** -- off-topic utterance
4. **`expectedTopic`** from topic name in `.agent` file
5. **`expectedActions`** from action names under `reasoning: actions:` (only `@actions.*`, not `@utils.transition`)

### Level 1 vs Level 2 Action Names (CRITICAL)

The `.agent` file has two levels of action definitions:
- **Level 1** (definition): under `topic > actions:` — defines target, inputs, outputs (e.g. `get_order_status:`)
- **Level 2** (invocation): under `topic > reasoning > actions:` — wires actions to the LLM (e.g. `check_order: @actions.get_order_status`)

Testing Center reports **Level 2 invocation names** (e.g. `check_order`), NOT Level 1 definition names (e.g. `get_order_status`). Using Level 1 names in `expectedActions` causes action assertions to FAIL even when the agent correctly invokes the action. Always use the Level 2 name from `reasoning: actions:`.

```
# .agent file
topic order_support:
   actions:
      get_order_status:           # <-- Level 1 (DON'T use this in expectedActions)
         target: "flow://Get_Order_Status"
   reasoning:
      actions:
         check_order: @actions.get_order_status   # <-- Level 2 (USE this in expectedActions)
```

```yaml
# Test spec -- use Level 2 name
- utterance: "Where is my order?"
  expectedActions: ["check_order"]    # CORRECT (Level 2)
  # expectedActions: ["get_order_status"]  # WRONG (Level 1)
```

## Known Bugs and Workarounds

| Bug | Severity | Workaround |
|-----|----------|------------|
| `--use-most-recent` flag on `sf agent test results` is not implemented | Medium | Always use `--job-id` explicitly |
| Custom evaluations with `isReference: true` (JSONPath) crash results API | Critical | Skip custom evaluations; use `expectedOutcome` instead |
| `conciseness` metric returns score=0 | Medium | Skip `conciseness`; use `coherence` instead |
| `instruction_following` metric crashes Testing Center UI | High | Remove from metrics list; use CLI only |
| `instruction_following` shows FAILURE at score=1 | Low | Ignore PASS/FAILURE label; use numeric `score` |
| Topic hash drift on agent republish | Medium | Re-run discovery after each publish |
