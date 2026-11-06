# Agentforce HyperClassifier Optimize

Evaluate labeled utterances against customer-org routing descriptions, inspect expected versus actual actions, and run bounded description optimization. The same standalone Python scripts work with Claude Code, Codex and OpenCode.

Start with [SKILL.md](SKILL.md) for the agent workflow and [installation](references/installation.md) for host setup. Requirements are Python 3.9+, Salesforce CLI for onboarding, a customer ECA with Models API permissions, and API 65.0+ for ECA JWT policy creation. Full-description classifier access is org-dependent and must pass preflight; see [the API contract](references/api-contract.md).

Validate the bundled synthetic inputs without credentials or network calls:

```bash
python3 scripts/hyperclassifier.py evaluate \
  --evals assets/sample_evals.csv \
  --descriptions assets/sample_descriptions.json \
  --output-dir ./sample-run --dry-run
```

Use [onboarding](references/onboarding.md) to discover an alias, find or prepare an ECA, and save credentials privately. Use [evaluation](references/evaluation.md) for budgets, reports, holdouts and recovery. Keep customer utterances and credentials outside this package. Optimization changes local description candidates; applying them requires semantic review and an agent-file backup.

The offline regression suite is bundled in `scripts/tests/` and runs from the skill directory, including an installed copy. Install `pytest` in your test environment, then run:

```bash
python3 -B -m pytest -q -p no:cacheprovider scripts/tests/test_hyperclassifier_skill.py
```

`pytest` is a test-only dependency; the skill's runtime scripts use the Python standard library.
