#!/usr/bin/env python3
"""Evaluate and optimize HyperClassifier descriptions through a customer org."""

import argparse
import json
import math
from pathlib import Path
import re
import sys

from hcopt.client import Client, ServiceError
from hcopt.onboarding import credentials_for_run
from hcopt.evaluation import evaluate, load_inputs, parse_prediction, summarize
from hcopt.optimizer import optimize


def build_parser():
    """Expose the same command-line contract to every agent runtime."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "evaluate", "optimize"))
    parser.add_argument("--evals", type=Path, required=True, help="CSV or JSONL with utterance and expected_action")
    parser.add_argument("--descriptions", type=Path, required=True, help="JSON list of {action: description} objects")
    parser.add_argument("--env-file", type=Path, help="Private ECA credentials file; values override environment")
    parser.add_argument("--target-org", help="CLI alias; reuse the ECA credentials saved during onboarding")
    parser.add_argument("--workspace", type=Path, help="Private onboarding workspace containing profile.json and credentials.env")
    parser.add_argument("--output-dir", type=Path, help="New output directory; never overwrite an existing run")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and call budget without credentials or network")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--retries", type=int, default=1, help="Extra attempts for HTTP 429/5xx or connection errors (0–3)")
    parser.add_argument("--max-calls", type=int, default=10000, help="Logical inference budget, excluding HTTP retries and OAuth")
    parser.add_argument("--max-rounds", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3, help="Stop after this many consecutive rejected proposals")
    parser.add_argument("--target-accuracy", type=float, default=1.0)
    parser.add_argument("--proposer-model", default="sfdc_ai__DefaultOpenAIGPT4OmniMini")
    parser.add_argument("--check-proposer", action="store_true", help="Include a generation call in preflight; optimize always checks before its baseline")
    parser.add_argument("--holdout", type=Path, help="Separate CSV/JSONL used once at the end of optimization")
    return parser


def prepare(args):
    """Validate all inputs and bound planned inference before obtaining credentials."""
    if not 1 <= args.repeats <= 100 or not 1 <= args.max_rounds <= 100 or not 1 <= args.patience <= 100:
        raise ValueError("repeats, max-rounds and patience must be 1–100")
    if not 0 <= args.retries <= 3 or not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
        raise ValueError("retries must be 0–3 and timeout must be finite, positive and at most 300 seconds")
    if not math.isfinite(args.target_accuracy) or not 0 < args.target_accuracy <= 1:
        raise ValueError("target-accuracy must be in (0, 1]")
    if args.max_calls < 1 or not re.fullmatch(r"[A-Za-z0-9_.-]+", args.proposer_model):
        raise ValueError("Invalid max-calls or proposer-model")
    if args.command != "preflight" and args.output_dir is None:
        raise ValueError("evaluate and optimize require --output-dir")
    if args.output_dir and args.output_dir.exists():
        raise ValueError("Output directory already exists; choose a fresh path")
    if args.holdout and args.command != "optimize":
        raise ValueError("--holdout is only valid for optimize")
    if args.check_proposer and args.command != "preflight":
        raise ValueError("--check-proposer is only valid for preflight; optimize checks automatically")
    cases, topics = load_inputs(args.evals, args.descriptions)
    holdout = load_inputs(args.holdout, args.descriptions)[0] if args.holdout else None
    if holdout:
        tuning_text = {" ".join(case["utterance"].casefold().split()) for case in cases}
        if any(" ".join(case["utterance"].casefold().split()) in tuning_text for case in holdout):
            raise ValueError("Holdout overlaps tuning utterances; use genuinely separate cases")
    planned = len(cases) * args.repeats
    if args.command == "preflight":
        planned = 2 if args.check_proposer else 1
    elif args.command == "optimize":
        planned = planned * (args.max_rounds + 1) + args.max_rounds + len(holdout or []) * args.repeats + 1
    if planned > args.max_calls:
        raise ValueError(f"Worst-case plan needs {planned} inference calls; increase --max-calls or reduce the run")
    return cases, topics, holdout, planned


def main(argv=None):
    """Validate, preflight, evaluate, or optimize without modifying source inputs."""
    args = build_parser().parse_args(argv)
    try:
        cases, topics, holdout, planned = prepare(args)
        print(f"Validated {len(cases)} cases, {len(topics)} actions; at most {planned} logical inference calls.", flush=True)
        if args.dry_run:
            print("Dry run complete: no credentials read, no requests made, no files written.")
            return 0
        client = Client(credentials_for_run(args), args.timeout, args.retries, args.max_calls)
        if args.command == "preflight":
            if args.check_proposer:
                client.check_proposer(args.proposer_model)
            prediction = parse_prediction(client.classify(cases[0]["utterance"], topics),
                                          [next(iter(topic)) for topic in topics])
            print(json.dumps({"available": True, **prediction, "proposer_checked": args.check_proposer,
                              "inference_calls": client.calls}))
            return 0
        if args.command == "evaluate":
            rows = evaluate(client, cases, topics, args.output_dir, args.repeats)
            summary = summarize(rows)
            print(json.dumps(summary, indent=2))
            return 2 if summary["error"] else (1 if summary["fail"] else 0)
        state = optimize(client, args, cases, topics, holdout)
        print(f"Stopped: {state['state']}; best round {state['best_round']}; artifacts: {args.output_dir}")
        return 0 if state["state"] == "target_reached" else 1
    except KeyboardInterrupt:
        print("Interrupted; completed predictions and best candidate are preserved.", file=sys.stderr)
        return 130
    except (ValueError, OSError, ServiceError) as error:
        # Transport errors deliberately carry no service body, headers or credentials.
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
