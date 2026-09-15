# Evaluation Types Reference

Complete guide to all 13 evaluation types in Agentforce Grid.

## Overview

Evaluation columns assess the quality or correctness of agent/prompt outputs. Some evaluations compare against expected values (requiring a reference column), while others assess quality independently.

## Evaluation Types Summary

| Type | Requires Reference | Supported Inputs | Use Case |
|------|-------------------|------------------|----------|
| `COHERENCE` | No | Agent, AgentTest, PromptTemplate | Assess logical flow |
| `CONCISENESS` | No | Agent, AgentTest, PromptTemplate | Assess brevity |
| `FACTUALITY` | No | Agent, AgentTest, PromptTemplate | Assess factual accuracy |
| `INSTRUCTION_FOLLOWING` | No | Agent, AgentTest, PromptTemplate | Assess instruction adherence |
| `COMPLETENESS` | No | Agent, AgentTest, PromptTemplate | Assess coverage |
| `RESPONSE_MATCH` | **Yes** | Agent, AgentTest | Compare to expected |
| `TOPIC_ASSERTION` (UI: "Subagent") | **Yes** | Agent, AgentTest | Verify topic routing |
| `ACTION_ASSERTION` | **Yes** | Agent, AgentTest | Verify actions |
| `LATENCY_ASSERTION` | No | Agent, AgentTest | Check response time |
| `BOT_RESPONSE_RATING` | **Yes** | Agent, AgentTest | Overall quality rating |
| `EXPRESSION_EVAL` | No | Agent, AgentTest | Custom formula |
| `CUSTOM_LLM_EVALUATION` | **Yes** | Agent, AgentTest | Custom LLM judge |
| `TASK_RESOLUTION` | No | Agent, AgentTest (conversation-level only) | Assess task completion |

---

## Quality Assessment Evaluations (No Reference Required)

These evaluations assess intrinsic quality without comparing to expected output.

### COHERENCE

Measures logical flow and consistency of the response.

**Assesses:**
- Logical flow of ideas
- Consistency in reasoning
- Clear connection between statements

**Example:**
```json
{
  "name": "Coherence Score",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "COHERENCE",
      "inputColumnReference": {
        "columnId": "agent-output-col-id",
        "columnName": "Agent Output",
        "columnType": "AgentTest"
      },
      "autoEvaluate": true
    }
  }
}
```

### CONCISENESS

Measures brevity without losing important information.

**Assesses:**
- Brevity without losing important information
- Elimination of redundancy
- Efficient communication

**Example:**
```json
{
  "name": "Conciseness Score",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "CONCISENESS",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "autoEvaluate": true
    }
  }
}
```

### FACTUALITY

Measures factual accuracy of the response.

**Assesses:**
- Correctness of stated facts
- Absence of misinformation
- Verifiable claims

**Example:**
```json
{
  "name": "Factuality Score",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "FACTUALITY",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "autoEvaluate": true
    }
  }
}
```

### INSTRUCTION_FOLLOWING

Measures how well the response follows given instructions.

**Assesses:**
- Adherence to specific requirements
- Compliance with format guidelines
- Following of step-by-step instructions

**Example:**
```json
{
  "name": "Instruction Following",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "INSTRUCTION_FOLLOWING",
      "inputColumnReference": {
      "columnId": "prompt-output-col-id",
      "columnName": "Prompt Output",
      "columnType": "PromptTemplate"
      },
      "autoEvaluate": true
    }
  }
}
```

### COMPLETENESS

Measures if the response fully addresses the query.

**Assesses:**
- Coverage of all required information
- Depth of explanation
- Inclusion of necessary context

**Example:**
```json
{
  "name": "Completeness Score",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "COMPLETENESS",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "Agent"
      },
      "autoEvaluate": true
    }
  }
}
```

---

## Comparison Evaluations (Reference Required)

These evaluations compare output against expected values.

### RESPONSE_MATCH

Compares agent's response to an expected response.

**Assesses:**
- Content similarity and accuracy
- Tone and style consistency
- Completeness of information

**Required:** `referenceColumnReference` pointing to expected response column

**Example:**
```json
{
  "name": "Response Match",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "RESPONSE_MATCH",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "referenceColumnReference": {
      "columnId": "expected-response-col-id",
      "columnName": "Expected Response",
      "columnType": "Text"
      },
      "autoEvaluate": true
    }
  }
}
```

### TOPIC_ASSERTION

**Note:** This evaluation type appears as "Subagent" in the Grid UI. The API name remains `topic_sequence_match`.

Validates that the agent correctly identified and used the expected topic.

**Assesses:**
- Topic selection accuracy
- Matches expected topic from reference column

**Required:** `referenceColumnReference` pointing to expected topic column

**Example:**
```json
{
  "name": "Topic Assertion",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "TOPIC_ASSERTION",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "referenceColumnReference": {
      "columnId": "expected-topic-col-id",
      "columnName": "Expected Topic",
      "columnType": "Text"
      },
      "autoEvaluate": true
    }
  }
}
```

### ACTION_ASSERTION

Validates that the agent executed the expected actions.

**Assesses:**
- Action execution accuracy
- All expected actions were performed

**Required:** `referenceColumnReference` pointing to expected actions column

**Example:**
```json
{
  "name": "Action Assertion",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "ACTION_ASSERTION",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "referenceColumnReference": {
      "columnId": "expected-actions-col-id",
      "columnName": "Expected Actions",
      "columnType": "Text"
      },
      "autoEvaluate": true
    }
  }
}
```

### BOT_RESPONSE_RATING

Provides overall quality rating comparing to expected response.

**Assesses:**
- Overall response quality
- Comparison against expected baseline

**Required:** `referenceColumnReference` pointing to expected response column

**Example:**
```json
{
  "name": "Response Rating",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "BOT_RESPONSE_RATING",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "referenceColumnReference": {
      "columnId": "expected-response-col-id",
      "columnName": "Expected Response",
      "columnType": "Text"
      },
      "autoEvaluate": true
    }
  }
}
```

---

## Performance Evaluation

### LATENCY_ASSERTION

Validates that response time meets performance requirements.

**Assesses:**
- Response time is within acceptable limits

**Example:**
```json
{
  "name": "Latency Check",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "LATENCY_ASSERTION",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "autoEvaluate": true
    }
  }
}
```

---

## Custom Evaluations

### EXPRESSION_EVAL

Evaluate using a custom formula expression over the agent response JSON.

**Fields:**
- `expressionFormula` (String, required) - Formula with JSON path references
- `expressionReturnType` (String, optional) - Expected return type

**Example - Check Topic Name:**
```json
{
  "name": "Topic Check",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "EXPRESSION_EVAL",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "expressionFormula": "{response.topicName} == 'Service'",
      "expressionReturnType": "boolean",
      "autoEvaluate": true
    }
  }
}
```

**Example - Check Message Count:**
```json
{
  "name": "Message Count Check",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "EXPRESSION_EVAL",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "expressionFormula": "LEN({response.botMessages}) > 0",
      "expressionReturnType": "boolean",
      "autoEvaluate": true
    }
  }
}
```

### CUSTOM_LLM_EVALUATION

Use a custom prompt template for LLM-as-a-Judge evaluation.

**Fields:**
- `customEvaluation` (object, required)
  - `type`: "llm"
  - `apiName`: Prompt template API name
  - `customInput`: Optional custom input

**Required:** `referenceColumnReference` for comparison baseline

**Example:**
```json
{
  "name": "Custom Quality Check",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "CUSTOM_LLM_EVALUATION",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "referenceColumnReference": {
      "columnId": "criteria-col-id",
      "columnName": "Evaluation Criteria",
      "columnType": "Text"
      },
      "customEvaluation": {
      "type": "llm",
      "apiName": "Custom_Evaluation_Template"
      },
      "autoEvaluate": true
    }
  }
}
```

---

### TASK_RESOLUTION

Assesses whether the agent successfully resolved the user's task across the full conversation.

**IMPORTANT:** Only works with conversation-level agent tests (`testType: "CONVERSATION_LEVEL"`). Does not apply to turn-level tests.

**Assesses:**
- Whether the agent achieved the user's stated goal
- End-to-end task completion across multiple turns

**Example:**
```json
{
  "name": "Task Resolution",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "TASK_RESOLUTION",
      "inputColumnReference": {
      "columnId": "agent-output-col-id",
      "columnName": "Agent Output",
      "columnType": "AgentTest"
      },
      "autoEvaluate": true
    }
  }
}
```

---

## Selection Guide

### For Quality Assessment (No Expected Output)

When you want to assess intrinsic quality without a reference:

- **COHERENCE** - Is the response logically structured?
- **CONCISENESS** - Is the response appropriately brief?
- **FACTUALITY** - Are the facts accurate?
- **INSTRUCTION_FOLLOWING** - Did it follow instructions?
- **COMPLETENESS** - Did it cover everything needed?

### For Comparing Against Expected Output

When you have expected/golden responses:

- **RESPONSE_MATCH** - Does the response match expected?
- **BOT_RESPONSE_RATING** - Overall quality vs expected

### For Agent Routing Validation

When testing agent topic/action routing:

- **TOPIC_ASSERTION** - Did it route to correct topic?
- **ACTION_ASSERTION** - Did it execute correct actions?

### For Performance Testing

- **LATENCY_ASSERTION** - Is response time acceptable?

### For Conversation-Level Testing

- **TASK_RESOLUTION** - Did the agent resolve the task? (conversation-level only)

### For Custom Logic

- **EXPRESSION_EVAL** - Custom formula over response JSON
- **CUSTOM_LLM_EVALUATION** - Custom LLM judge with your criteria

---

## Common Patterns

### Agent Testing Suite

```
Text: "Utterances"
Text: "Expected Responses"
Text: "Expected Topics"
AgentTest: "Agent Output"
Evaluation: "Response Match" (RESPONSE_MATCH)
Evaluation: "Topic Check" (TOPIC_ASSERTION)
Evaluation: "Coherence" (COHERENCE)
Evaluation: "Latency" (LATENCY_ASSERTION)
```

### Prompt Quality Evaluation

```
Text: "Inputs"
PromptTemplate: "Output"
Evaluation: "Coherence" (COHERENCE)
Evaluation: "Completeness" (COMPLETENESS)
Evaluation: "Instruction Following" (INSTRUCTION_FOLLOWING)
```
