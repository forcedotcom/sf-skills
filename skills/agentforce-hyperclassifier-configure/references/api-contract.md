# Full-description classification contract

Classification sends a customer-org JWT to `https://api.salesforce.com/ai/gpt/v1/chat/generations`:

```json
{
  "model": "llmgateway__EinsteinHyperClassifier",
  "messages": [{"role": "user", "content": "Where is my order?"}],
  "topics_config": {
    "return_single_topic": false,
    "topics": [
      {"go_to_orders": "Order status, tracking, delivery and returns."},
      {"go_to_billing": "Charges, invoices and payment problems."}
    ]
  },
  "generation_settings": {"parameters": {"return_probability": true}}
}
```

Headers include `Authorization: Bearer <JWT>`, `Content-Type: application/json`, `x-sfdc-app-context: EinsteinGPT` and `x-client-feature-id: ai-platform-models-connected-app`.

The parser requires `generation_details.generations`, containing one entry per action with `content` equal to its name and `parameters.probability` in `[0, 1]`. Highest probability selects the route. Ties preserve response order and are flagged. Empty, missing, duplicate, unknown or invalid scores are contract errors. Expected labels never enter this request.

This gateway contract has been exercised using customer-org JWT authentication. It is **not represented here as a documented generally available public API contract**. Availability may vary; the preflight makes exactly one classification request and checks the complete score schema. API access alone does not establish production Agentforce router parity, model version stability, or deployment support.

The documented [predictive Models API](https://developer.salesforce.com/docs/ai/agentforce/guide/access-predictive-endpoints-with-rest.html) provides a topic-classification operation with `texts` and `topicLabels`. That labels-only request does not preserve separate action-name/description pairs. This skill does not silently fall back to it.

## Description proposal

The optional automatic optimizer calls the documented Models API generations operation:

```text
POST https://api.salesforce.com/einstein/platform/v1/models/{model}/generations
{"prompt": "..."}
```

It reads `generation.generatedText` as proposal text. The default model identifier is an example; it must be available to the org. The candidate's score always comes from a separate full evaluation, never from the proposing model's claims.

The proposer sees the current descriptions, tuning metrics, up to 60 failing prediction rows, up to 20 passing controls, and the last five decisions. Full evaluation artifacts remain local. Holdout text is never sent to the proposer. Proposals are data, not executable code; valid proposals can replace at most two descriptions. The action set, order and evaluation labels remain fixed.

Public references: [Models API overview](https://developer.salesforce.com/docs/ai/agentforce/guide/models-api.html), [Models API authentication](https://developer.salesforce.com/docs/ai/agentforce/guide/models-api-authentication.html).
