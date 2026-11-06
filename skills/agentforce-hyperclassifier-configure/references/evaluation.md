# Evaluation inputs and outputs

CSV headers are `id,group,utterance,expected_action`. Only `utterance` and `expected_action` are mandatory. JSONL uses one object with the same fields per line. Missing IDs become one-based record numbers; missing groups become `default`. Explicit IDs must be unique. Stable IDs are recommended when comparing revisions. UTF-8 BOM is accepted. Each expected action must exist in the descriptions JSON; action identifiers use letters, digits and underscores and start with a letter.

Descriptions preserve their order and full text. Supply a JSON list of objects, each with exactly one action/description pair. At least two actions and nonempty descriptions are required. Synthetic assets demonstrate the format; they are not a production evaluation set.

Preview exactly those inputs with `report_hyperclassifier.py --evals <file> --descriptions <file>`. It displays the complete utterance/expected table and class counts. After a run, `report_hyperclassifier.py --run <run-or-experiment-directory>` displays expected/actual rows, group and class scores, repeat stability, completion status and baseline-versus-best metrics. Experiments include a distinct holdout section when requested, even when it failed or never started. `--failures-only` filters tuning and holdout rows independently; `--output <new-file.md>` saves a report without overwriting an earlier one. Missing/corrupt artifacts return a controlled error. Original evaluation files are unchanged.

## Reports

Each evaluation creates a new directory:

- `cases.json`, `descriptions.json`: exact normalized input snapshots.
- `run.json`: fingerprints, model/endpoint, requested repeats, planned/completed predictions and completion state.
- `results.jsonl`: incrementally flushed predictions with raw utterances, expected/actual actions, all probabilities, ties, margins and timing.
- `results.csv`, `failures.csv`: human-readable expected/actual rows. Formula-like cell values are prefixed with an apostrophe for spreadsheet safety; JSONL preserves raw strings.
- `summary.json`, `summary.md`: overall accuracy, mismatches, errors and repeat stability. JSON also contains per-group/per-expected-action scores and a confusion matrix.

The confusion matrix uses `<service_error>` for infrastructure/contract failures; this cannot collide with an action identifier. Numeric JSONL IDs, including zero, are preserved as strings. Malformed CSV quoting is rejected; properly quoted multiline utterances are supported.

Accuracy is correct predictions divided by all completed predictions, including service errors. A partially completed run is **not** a full-set accuracy result: check `run.json.state` and planned/completed counts. Runs stop on the first service/contract error to avoid treating infrastructure failures as routing feedback. Strict accuracy uses one expected action; ambiguous and multi-intent cases need separate adjudication. Tied top scores use response order and are counted normally but explicitly flagged.

`--repeats N` repeats the entire corpus N times with the same descriptions. Group/class counts aggregate all repeats. `cases_passing_every_repeat` and `cases_with_varying_predictions` show consistency across completed repeats. With a single repeat they do not establish stability.

## Optimization

An experiment contains `baseline/`, `round_001/` etc., `experiment.json`, `best_candidate.json`, `best_descriptions.json` and `best_summary.json`. Each round includes feedback, a validated proposal, the description diff, the candidate's full evaluation and an adoption decision. Invalid/duplicate proposals have no evaluation. Source inputs are never modified.

`best_candidate.json` atomically commits the selected round, complete descriptions and measured summary together. It is authoritative. The other two best files are convenience exports, reconciled on handled interruption. A forced kill or filesystem failure can leave those exports or `experiment.json` stale; the report uses the atomic winner record. Before applying descriptions after such a stop, compare the exports with that record and extract its `descriptions` value into a fresh JSON file if needed. Before baseline evaluation, the winner's summary is null and no accuracy is claimed.

The loop changes descriptions only. It requires strictly more correct predictions with no loss of an earlier passing `(case ID, repeat)`, which implies no group/class decline. Repeat indices are independent observations, not matched random seeds: a case improving from 1/3 to 2/3 passes can still be rejected if its previously passing repeat now fails. This conservative policy intentionally preserves the strict regression contract; replacing it with per-case counts or statistical testing would change that contract. Repeated trials can still have selection bias; re-evaluate the winner independently before making a reliability claim.

Optional `--holdout separate.csv` runs once after selection, using the same repeat count. Identical normalized utterances across tuning and holdout are rejected; semantic near-duplicates remain the user's responsibility. Holdout results are reported separately and never drive selection. A tuning target does not imply holdout success.

Optimization first makes a synthetic proposer availability call before the baseline, including when the baseline might already meet the target. The dry run reports a worst-case logical call count: tuning cases × repeats × (1 + max rounds), plus one proposer call per round, plus holdout cases × repeats, plus that initial proposer check. It refuses plans above `--max-calls`. Standalone preflight costs one classifier call, or two calls with `--check-proposer`. No background process is started. Interruption preserves completed rows and the committed winner. There is no automatic resume or reuse of incomplete results: begin a new run with the saved best descriptions and a new output directory.

## Exit status

| Code | Meaning |
| --- | --- |
| 0 | Dry run/preflight succeeded; evaluation all passed; or optimization reached its tuning target |
| 1 | Evaluation has routing mismatches; or optimizer stopped at plateau/round limit below target |
| 2 | Invalid input, authentication, transport or response-contract failure |
| 130 | User interrupted the process |

Results contain customer utterances. Keep run directories private and outside the skill package. Inspect reports before sharing them. The scripts store neither credentials nor raw HTTP response bodies.
