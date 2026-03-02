# Agent Test Authoring Reference

## Table of Contents

- [Test Spec Structure](#test-spec-structure)
- [Writing Effective Test Cases](#writing-effective-test-cases)
- [Metric Selection](#metric-selection)
- [Multi-Turn Testing](#multi-turn-testing)
- [Custom Evaluations](#custom-evaluations)
- [Context Variables](#context-variables)
- [Coverage Strategy](#coverage-strategy)
- [Test Authoring Workflow](#test-authoring-workflow)
- [Platform Constraints](#platform-constraints)
- [Common Mistakes](#common-mistakes)

---

## Test Spec Structure

A test spec is a YAML file that defines test cases for an agent. The `sf agent test create` command translates this YAML into `AiEvaluationDefinition` metadata in the org. Tests run against **activated published agents** — not authoring bundles or drafts.

Top-level structure:

```yaml
name: "Human-readable test name"
description: "Description of what this test spec covers."
subjectType: AGENT
subjectName: Agent_API_Name
subjectVersion: v1
testCases:
  - utterance: "User input"
    expectedTopic: topic_api_name
    expectedActions: []
    expectedOutcome: "Natural language description"
    conversationHistory: []
    customEvaluations: []
    contextVariables: []
    metrics: []
```

Required top-level fields:
- `name`: Human-readable identifier for the test spec. Used in CLI output and logs.
- `subjectType`: Always `AGENT` for agent test specs.
- `subjectName`: The API name of the agent being tested. Must match the agent's API name exactly.
- `testCases`: List of individual test cases. At least one required.

Optional top-level fields:
- `description`: What this test spec validates. Reference the Agent Spec by name.
- `subjectVersion`: The agent version to test (e.g., `v1`). If omitted, the latest active version is used. Find versions in the `BotVersion` metadata type.

Per-test-case required fields:
- `utterance`: The user input being tested. Natural language, one-turn input. Do not include multi-turn context here; use `conversationHistory` for that.
- `expectedTopic`: The topic API name the agent should route to. String, not a list. Single topic per test case.
- `expectedActions`: List of action API names the agent should invoke. Use empty list `[]` when no action is expected.
- `expectedOutcome`: Natural language description of the expected result. This is NOT a literal string match; the platform uses semantic comparison — actual text can differ from expected as long as core meaning matches.
- `metrics`: List of metrics to evaluate. See Metric Selection section.

Optional per-test-case fields:
- `conversationHistory`: Prior messages providing context for the current utterance. See Multi-Turn Testing section.
- `customEvaluations`: Custom validation rules beyond standard metrics. See Custom Evaluations section.
- `contextVariables`: Context variables for Service agents with messaging channels. See Context Variables section.

Default location: `specs/{Agent_API_Name}-testSpec.yaml`.

---

## Writing Effective Test Cases

Each test case exercises one user intent and validates the agent's response.

Utterance design:
- Write natural conversational input. Avoid scripts or rigid phrasing.
- Keep each utterance focused on a single user intent. Multi-intent requests belong in separate test cases.
- Test realistic variations: "What's the weather?" and "Can you tell me the forecast?" both target weather but use different phrasing.
- Include edge cases: ambiguous input, off-topic queries, requests requiring guardrails.

Example utterances for Agent_Name:
- Clear intent: "What information do I need?" (maps to a specific topic)
- Variation: "Can you help me with X?" (alternative phrasing for same intent)
- Edge case requiring context: "Great, and what about Y?" (requires prior conversation context)
- Off-topic: "What is the capital of France?"
- Guardrail test: "I'd like to speak with a real person please."

expectedOutcome phrasing:
- Describe the expected behavior in natural language. Do not write literal response text.
- The platform evaluates using semantic comparison — even if the actual outcome text differs, the test passes if core meaning matches.
- Reference what should happen: "The agent should provide a forecast with a temperature range."
- Reference what should NOT happen: "The agent should NOT answer the off-topic question."
- Name the action(s) if relevant: "The agent should call get_resort_hours and return opening times."
- When guardrails apply, state the constrained behavior: "The agent should escalate to a human agent without attempting to answer."

WRONG: `expectedOutcome: "The result is X."`
RIGHT: `expectedOutcome: "The agent should provide the requested information with specific details."`

expectedActions rationale:
- List ONLY actions the agent should invoke. If no action is expected, use `[]`.
- Base this on the Agent Spec's topic-to-action mapping. If a topic has no actions, expectedActions is `[]`.
- If a topic conditionally invokes an action (e.g., only if user provides input), think carefully: does your test case provide that input?

WRONG — action listed but test utterance doesn't trigger it:
```yaml
- utterance: "Show me the data"
  expectedTopic: topic_b
  expectedActions:
    - action_b
  expectedOutcome: "The agent should provide the requested data."
```
RIGHT — required information not provided, so agent must ask first:
```yaml
- utterance: "Show me the data"
  expectedTopic: topic_b
  expectedActions: []
  expectedOutcome: "Because the user has not provided the required information, the agent should politely ask for it before calling the gated action."
```

---

## Metric Selection

Metrics quantify response quality. Always include `output_latency_milliseconds`. Add others based on test purpose.

Available metrics:
- `coherence`: Response is grammatically correct and easy to understand. Default choice for all tests.
- `completeness`: Response includes all essential information. Use when the test expects multiple pieces of data.
- `conciseness`: Response is brief but comprehensive. Use when verbosity is a concern.
- `output_latency_milliseconds`: Time from request to response in milliseconds. ALWAYS include.
- `instruction_following`: How well the response follows topic instructions and guardrails. Use for behavioral tests, constraints, edge cases. **Scoring differs from other metrics** — returns `HIGH`, `LOW`, or `UNCERTAIN` instead of `PASS`/`FAILED`.
- `factuality`: Response contains verifiably correct data. Use when the agent returns facts (weather, hours, event details).

Selection guide:
- Baseline set: `coherence`, `conciseness`, `output_latency_milliseconds`.
- Add `completeness` if the expected outcome references multiple data points.
- Add `instruction_following` if testing guardrails, constraints, or behavioral rules (e.g., "don't answer off-topic").
- Add `factuality` if the response must contain real or simulated factual data.
- Remove unwanted metrics by deleting them from the list. Delete the entire `metrics` section to skip all quality metrics.

Example: Agent_Name off-topic test case:
```yaml
metrics:
  - coherence
  - instruction_following
  - output_latency_milliseconds
```
Reason: coherence ensures the redirection is clear; instruction_following validates the guardrail (don't answer off-topic) — expect `HIGH` for a well-behaved agent; latency is always included.

---

## Multi-Turn Testing

Test multi-turn conversations using `conversationHistory`. This provides context for the current `utterance`.

Conversation history format:
```yaml
conversationHistory:
  - role: user
    message: "First user message"
  - role: agent
    message: "Agent's response"
    topic: topic_used_for_response
  - role: user
    message: "Second user message"
  - role: agent
    message: "Agent's second response"
    topic: topic_used_for_second_response
```

Rules:
- `role`: Either `user` or `agent`. Required.
- `message`: The text of the message. Required.
- `topic`: REQUIRED for agent entries. This is the topic the agent used to formulate that response. Omit for user entries.
- Do NOT include the current test utterance in conversationHistory. The `utterance` field is the final user message.
- Conversation must begin with a `user` message.

When to use conversationHistory:
- Test topic transitions that depend on prior context.
- Test multi-turn flows where earlier responses constrain later behavior.
- Test contextual clarity: does the agent maintain facts from earlier turns?

Example: Agent_Name contextual follow-up test case:
```yaml
- utterance: Great, and what about the second item?
  expectedTopic: main
  expectedActions:
    - do_action
  expectedOutcome: The agent should provide information about the second item, understanding
    the context from the previous exchange.
  conversationHistory:
    - role: user
      message: Tell me about the first item
    - role: agent
      message: Here is information about the first item with specific details.
      topic: main
  metrics:
    - coherence
    - conciseness
    - output_latency_milliseconds
```

Without conversationHistory, "Great, what time does the restaurant open?" is ambiguous. The prior weather exchange provides context showing the user is satisfied and moving to a new topic.

---

## Custom Evaluations

Custom evaluations validate specific response properties using comparison operators. Two types: `string_comparison` and `numeric_comparison`.

### Parameters

Each custom evaluation has four fields:
- `label`: Human-readable description of what this evaluation checks.
- `name`: The comparison type — either `string_comparison` or `numeric_comparison`.
- `parameters`: List of three parameter objects (below).

Each parameter has `name`, `value`, and `isReference`:
- `operator`: The comparison operation. `isReference: false` (literal value).
- `actual`: The value obtained during the test. `isReference: true` when the value is a JSONPath expression referencing runtime data. `isReference: false` when it is a literal.
- `expected`: The target value to compare against. `isReference: false` (literal value).

The `isReference` field tells the platform whether to evaluate `value` as a JSONPath expression (`true`) or use it as-is (`false`). The `actual` parameter almost always uses `isReference: true` because it references data generated during the test run.

Parameter `value` fields are limited to **100 characters**.

### Constructing JSONPath Expressions

Custom evaluations reference runtime data from the `generatedData` object. To construct the JSONPath, you need to see the generated JSON from a test run.

Step 1 — Run the test with `--verbose` to see generated data:
```bash
sf agent test run --json --api-name My_Agent_Test --verbose --wait 10
```

Step 2 — Find the generated JSON in the output:
```
Generated Data
┌───────────────────────────────────────┐
│ [                                     │
│   [                                   │
│     {                                 │
│       "function": {                   │
│         "name": "Check_Weather",      │
│         "input": {                    │
│           "dateToCheck": "2025-09-12" │
│         },                            │
│         "output": {}                  │
│       },                              │
│       "executionLatency": 804         │
│     }                                 │
│   ]                                   │
│ ]                                     │
└───────────────────────────────────────┘
```

Step 3 — Build the JSONPath expression. Common pattern:
```
$.generatedData.invokedActions[*][?(@.function.name == '{ACTION_NAME}')].function.input.{FIELD}
```

Useful paths:
- Action input field: `...function.input.{fieldName}`
- Action output field: `...function.output.{fieldName}`
- Action execution latency: `...executionLatency`

### String Comparison

Tests a response property against a string value. All string operators are case-sensitive.

Operators: `equals` (exact match), `contains` (substring), `startswith` (prefix), `endswith` (suffix).

```yaml
customEvaluations:
  - label: "Check for correct date"
    name: string_comparison
    parameters:
      - name: operator
        value: equals
        isReference: false
      - name: actual
        value: "$.generatedData.invokedActions[*][?(@.function.name == 'Check_Weather')].function.input.dateToCheck"
        isReference: true
      - name: expected
        value: "2025-09-12"
        isReference: false
```

### Numeric Comparison

Tests a response property against a numeric value.

Operators: `equals`, `greater_than`, `greater_than_or_equal`, `less_than`, `less_than_or_equal`.

```yaml
customEvaluations:
  - label: "Latency under threshold"
    name: numeric_comparison
    parameters:
      - name: operator
        value: less_than
        isReference: false
      - name: actual
        value: "$.generatedData.invokedActions[*][?(@.function.name == 'Check_Weather')].executionLatency"
        isReference: true
      - name: expected
        value: "5000"
        isReference: false
```

---

## Context Variables

Service agents connected to messaging channels can use context variables — record fields from the `MessagingSession` standard object used as action inputs. If the agent under test uses context variables, include them in the test spec.

```yaml
testCases:
  - utterance: Are there any resort experiences that match my interests today?
    expectedTopic: Experience_Management
    expectedActions: []
    expectedOutcome: The agent should politely ask for the guest's email address AND membership number.
    contextVariables:
      - name: EndUserLanguage
        value: Spanish
    metrics:
      - coherence
      - output_latency_milliseconds
```

The `name` field is the API name of the context variable (found in Agent Builder > Context tab). Most Agent Script agents do not use context variables — omit the section entirely when not needed.

---

## Coverage Strategy

Map test cases to the Agent Spec to ensure comprehensive coverage.

Coverage dimensions:
- Topics: Test every topic defined in the Agent Spec. Include normal flow and edge cases.
- Actions: For each action, test at least one case where the action IS invoked AND one where it is NOT (if conditionally gated).
- Flow control: Test conditional routing (e.g., "if user input missing, ask for clarification").
- Guardrails: Test that constraints and behavioral rules are enforced (off-topic rejection, escalation, data validation).
- Variations: Test phrasing variations of the same intent.
- Multi-turn: Test at least one topic transition with conversationHistory.

Checklist pattern (adapt to the agent under test):
- [ ] Every topic tested with at least one happy-path utterance.
- [ ] Every action tested as both invoked and not-invoked (where applicable).
- [ ] Gated actions tested with and without the required user input.
- [ ] Off-topic and escalation guardrails tested.
- [ ] At least one multi-turn test with conversationHistory.
- [ ] Phrasing variations for highest-traffic topics.

Example for Agent_Name:
- [ ] `local_weather` — clear intent, invokes `check_weather`.
- [ ] `local_weather` — date-specific: "What will the weather be like on March 15th?"
- [ ] `local_events` — without interest (no action; agent asks for clarification).
- [ ] `local_events` — with interest: "I like movies. What's showing nearby?" (invokes `check_events`).
- [ ] `resort_hours` — spa hours (invokes `get_resort_hours`, mentions reservation required).
- [ ] `resort_hours` — pool hours (invokes `get_resort_hours`, mentions walk-in OK).
- [ ] `escalation` — "I'd like to speak with a real person" (no action; escalate).
- [ ] `off_topic` — "What is the capital of France?" (no action; redirect).
- [ ] Multi-turn — weather → restaurant hours with conversationHistory.

---

## Test Authoring Workflow

The CLI commands for the test authoring lifecycle.

### Step 1: Create the test spec YAML

Write the YAML file manually or start from an existing example. Place it in `specs/`.

Do NOT use `sf agent generate test-spec` in agentic workflows. This command is interactive (REPL-style) — it prompts for each field one at a time and cannot be driven programmatically.

If an `AiEvaluationDefinition` XML file already exists in the project, generate a YAML spec from it:
```bash
sf agent generate test-spec \
    --from-definition force-app/main/default/aiEvaluationDefinitions/MyTest.aiEvaluationDefinition-meta.xml \
    --output-file specs/My_Agent-testSpec.yaml
```

### Step 2: Preview before creating

Generate a local XML preview without deploying to the org:
```bash
sf agent test create --json --preview --target-org my-dev-org
```
This creates a `{API_name}-preview-{timestamp}.xml` file for inspection. Use this to verify the YAML translated correctly before committing to the org.

### Step 3: Create the test in the org

The `--api-name` here is the name for the **test definition** (the `AiEvaluationDefinition`), not the agent name. This is the name you use in all subsequent `sf agent test run` commands.
```bash
sf agent test create --json --spec specs/My_Agent-testSpec.yaml --api-name My_Agent_Test --target-org my-dev-org
```
This deploys the `AiEvaluationDefinition` metadata and syncs it back to the local project under `aiEvaluationDefinitions/`.

### Step 4: Run the test

Tests run asynchronously by default. The `--api-name` is the **test definition name** from Step 3, not the agent name:
```bash
sf agent test run --json --api-name My_Agent_Test --target-org my-dev-org
```
This returns a `sf agent test resume --job-id {ID}` command. Run it to get results.

For synchronous execution, use `--wait` (minutes):
```bash
sf agent test run --json --api-name My_Agent_Test --wait 20 --target-org my-dev-org
```

For CI/CD, use `--result-format` and `--output-dir`:
```bash
sf agent test run --json --api-name My_Agent_Test --wait 20 --result-format JSON --output-dir test-results
```
Supported formats: `JSON`, `TAP`, `JUnit`.

### Step 5: Interpret results and iterate

View completed results:
```bash
sf agent test results --json --job-id {ID}
```

Results show four sections: basic info (overall status, pass/fail counts), per-test-case details (topic/action/outcome per case), metrics (quality scores), and summary (duration, pass rates).

Use `--verbose` on `sf agent test run` to see generated data for constructing custom evaluations (see Custom Evaluations section).

### Useful commands

List all tests in the org to confirm test definition API names:
```bash
sf agent test list --json --target-org my-dev-org
```

Open Testing Center UI:
```bash
sf org open --path /lightning/setup/TestingCenter/home --target-org my-dev-org
```

---

## Platform Constraints

- Maximum **1,000 test cases** per `AiEvaluationDefinition`.
- Maximum **10 in-progress** test runs at any time.
- Custom evaluation parameter `value` fields limited to **100 characters**.
- Running tests consumes **Einstein Request credits** (both production and sandbox).
- Test results **may change on rerun** due to testing service improvements.
- Tests require an **activated published agent** — not a draft or authoring bundle.

---

## Common Mistakes

Anti-patterns and corrections.

Mistake: Inventing schema fields.
```yaml
WRONG:
type: AGENT
version: 1
subject: Agent_Name
expectations: []
turns: []

RIGHT:
subjectType: AGENT
subjectName: Agent_Name
```

Mistake: Using snake_case instead of camelCase.
```yaml
WRONG:
expected_topic: local_weather
expected_actions: []
expected_outcome: "..."
conversation_history: []

RIGHT:
expectedTopic: local_weather
expectedActions: []
expectedOutcome: "..."
conversationHistory: []
```

Mistake: Omitting expectedActions.
```yaml
WRONG:
- utterance: "What's the weather?"
  expectedTopic: local_weather
  expectedOutcome: "..."

RIGHT:
- utterance: "What's the weather?"
  expectedTopic: local_weather
  expectedActions:
    - check_weather
  expectedOutcome: "..."
```

Mistake: Writing expectedOutcome as a literal string match.
```yaml
WRONG:
expectedOutcome: "The temperature is 72 degrees."

RIGHT:
expectedOutcome: "The agent should provide a forecast with a temperature range for the resort location."
```

Mistake: Forgetting topic on agent conversationHistory entries.
```yaml
WRONG:
conversationHistory:
  - role: agent
    message: "The weather is nice."

RIGHT:
conversationHistory:
  - role: agent
    message: "The weather is nice."
    topic: local_weather
```

Mistake: Inventing metric names.
```yaml
WRONG:
metrics:
  - responsiveness
  - tone
  - accuracy

RIGHT:
metrics:
  - coherence
  - instruction_following
  - output_latency_milliseconds
```
Valid metric names: `coherence`, `completeness`, `conciseness`, `output_latency_milliseconds`, `instruction_following`, `factuality`. No others exist.

Mistake: Using wrong operator names in custom evaluations.
```yaml
WRONG:
- name: operator
  value: eq
  isReference: false

RIGHT:
- name: operator
  value: equals
  isReference: false
```
String operators: `equals`, `contains`, `startswith`, `endswith`. Numeric operators: `equals`, `greater_than`, `greater_than_or_equal`, `less_than`, `less_than_or_equal`. No abbreviations.

Mistake: Malformed JSONPath in custom evaluations.
```
WRONG:
$.invokedActions[0].function.input.dateToCheck

RIGHT:
$.generatedData.invokedActions[*][?(@.function.name == 'Check_Weather')].function.input.dateToCheck
```
JSONPath must start with `$.generatedData.invokedActions`, use `[*]` (not a numeric index), and filter by action name with `[?(@.function.name == '{ACTION}')]`.

Mistake: Using `sf agent generate test-spec` in an agentic workflow.
The command is interactive — it prompts for each field and cannot be scripted. Write the YAML file directly.

Mistake: Running a test before it is created in the org.
Always create the test in the org first using `sf agent test create`. Then run it with `sf agent test run --api-name {Test_API_Name}`.

Mistake: Guessing the --api-name flag value.
The `--api-name` on `sf agent test run` is the **test definition** API name assigned when the test was created — not the agent's `subjectName` from the YAML and not the `name` field in the YAML. List tests with `sf agent test list` to confirm the correct API name.
