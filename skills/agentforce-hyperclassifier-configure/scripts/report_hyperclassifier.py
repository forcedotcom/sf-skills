#!/usr/bin/env python3
"""Show evaluation inputs and measured expected/actual results without model calls."""

import argparse
from collections import Counter
import html
import json
from pathlib import Path
import sys

from hcopt.evaluation import load_inputs


def cell(value):
    """Escape input text so it cannot break the surrounding Markdown table."""
    return html.escape(str(value if value is not None else "")).replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>").replace("\r", "")


def table(headers, rows):
    """Render a Markdown table without truncating utterances."""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def read_object(path):
    """Identify an unreadable artifact without dumping its contents."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read JSON artifact {path}: {type(error).__name__}; check the path and run completion") from None
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def percentage(value):
    return "n/a" if value is None else f"{value:.2%}"


def run_report(folder, failures_only):
    """Render one evaluation, including incomplete runs and repeat stability."""
    run, summary = read_object(folder / "run.json"), read_object(folder / "summary.json")
    rows = []
    try:
        with (folder / "results.jsonl").open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if line.strip():
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("Expected an object")
                    rows.append(row)
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read results artifact {folder / 'results.jsonl'}: {type(error).__name__}; check run completion") from None
    lines = [f"Run state: {cell(run['state'])}; {run['completed_predictions']}/{run['planned_predictions']} predictions completed.",
             f"Correct: {summary['pass']}/{summary['total']} ({percentage(summary['accuracy'])}); "
             f"routing mismatches: {summary['fail']}; service errors: {summary['error']}."]
    for label, key in (("Group", "groups"), ("Expected action", "expected_actions")):
        if not isinstance(summary.get(key), dict):
            raise ValueError(f"Expected {key} to be an object in {folder / 'summary.json'}")
        lines.append(table([label, "Correct", "Completed", "Accuracy", "Errors"], [
            [name, data["pass"], data["total"], percentage(data["accuracy"]), data["error"]]
            for name, data in summary[key].items()]))
    lines.append(table(["Repeat stability", "Count"], [
        ["Unique cases with completed predictions", summary["unique_cases"]],
        ["Cases passing every completed repeat", summary["cases_passing_every_repeat"]],
        ["Cases with varying predictions", summary["cases_with_varying_predictions"]],
        ["Top-score ties", summary["ties"]],
    ]))
    shown = [row for row in rows if row["status"] != "pass"] if failures_only else rows
    lines.append(table(["ID", "Repeat", "Utterance", "Expected", "Actual", "Status", "Error"], [
        [r["id"], r["iteration"], r["utterance"], r["expected_action"], r["actual_action"], r["status"], r.get("error", "")]
        for r in shown]))
    return lines


def report(folder, failures_only=False):
    """Report tuning and holdout separately, using the atomic winner when present."""
    folder = Path(folder)
    if not (folder / "experiment.json").is_file():
        return "\n\n".join(run_report(folder, failures_only)) + "\n"
    experiment = read_object(folder / "experiment.json")
    winner = read_object(folder / "best_candidate.json") if (folder / "best_candidate.json").is_file() else None
    baseline = experiment.get("baseline")
    best = winner["summary"] if winner else experiment.get("best_summary")
    chosen = winner["round"] if winner else experiment.get("best_round", 0)
    if not isinstance(chosen, int) or isinstance(chosen, bool) or not 0 <= chosen <= 100:
        raise ValueError("Invalid selected round in experiment artifacts")
    lines = ["Stop state: " + cell(experiment["state"])]
    if experiment.get("error"):
        lines.append("Experiment error: " + cell(experiment["error"]))
    if baseline and best:
        lines.append(table(["Tuning metric", "Baseline", "Best candidate"], [
            ["Correct / completed", f"{baseline['pass']}/{baseline['total']}", f"{best['pass']}/{best['total']}"],
            ["Accuracy", percentage(baseline["accuracy"]), percentage(best["accuracy"])],
            ["Routing mismatches", baseline["fail"], best["fail"]],
            ["Service errors", baseline["error"], best["error"]],
        ]))
    selected = folder / (f"round_{chosen:03d}/evaluation" if chosen else "baseline")
    lines.append("## Tuning results")
    if best is not None or (selected / "run.json").is_file():
        lines.extend(run_report(selected, failures_only))
    else:
        lines.append("Tuning evaluation has not started; no accuracy is available.")
    holdout = folder / "holdout"
    if holdout.exists() or "holdout_sha256" in experiment or "holdout" in experiment:
        lines.append("## Independent holdout results")
        if (holdout / "run.json").is_file():
            lines.extend(run_report(holdout, failures_only))
        else:
            lines.append("Holdout evaluation has not produced a run; no holdout accuracy is available.")
    return "\n\n".join(lines) + "\n"


def main(argv=None):
    """Preview cases or render a complete saved results table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evals", type=Path)
    parser.add_argument("--descriptions", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--failures-only", action="store_true")
    parser.add_argument("--output", type=Path, help="New Markdown output file; omit to print")
    args = parser.parse_args(argv)
    if args.run and (args.evals or args.descriptions):
        parser.error("Choose either --run or --evals with --descriptions")
    if not args.run and not (args.evals and args.descriptions):
        parser.error("Supply --run or both --evals and --descriptions")
    try:
        if args.run:
            text = report(args.run, args.failures_only)
        else:
            cases, _ = load_inputs(args.evals, args.descriptions)
            counts = Counter(case["expected_action"] for case in cases)
            text = f"Cases: {len(cases)}\n\n" + table(["Expected action", "Count"], sorted(counts.items())) + "\n\n"
            text += table(["ID", "Group", "Utterance", "Expected"], [
                [c["id"], c["group"], c["utterance"], c["expected_action"]] for c in cases]) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Report error ({type(error).__name__}): {error}. Check input paths and completed run artifacts.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
