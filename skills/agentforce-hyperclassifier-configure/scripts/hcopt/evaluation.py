"""Immutable evaluation inputs, strict prediction parsing, and local reports."""

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time

from .client import CLASSIFIER_MODEL, CLASSIFIER_PATH, ServiceError


def write_json(path, value):
    """Replace a local JSON artifact atomically."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(value):
    """Fingerprint canonical values while preserving meaningful list order."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_topics(topics):
    """Validate ordered action/description pairs without rewriting their meaning."""
    if not isinstance(topics, list) or len(topics) < 2:
        raise ValueError("Descriptions must be a list containing at least two single-action objects")
    names = []
    for topic in topics:
        if not isinstance(topic, dict) or len(topic) != 1:
            raise ValueError("Each description item must contain exactly one action")
        name, description = next(iter(topic.items()))
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or name in names:
            raise ValueError("Action names must be unique identifiers")
        if not isinstance(description, str) or not description.strip() or len(description) > 12000:
            raise ValueError("Each description must contain 1–12000 characters")
        names.append(name)
    return names


def load_inputs(evals_path, descriptions_path):
    """Load CSV or JSONL cases and validate expected labels against the action set."""
    topics = json.loads(Path(descriptions_path).read_text(encoding="utf-8-sig"))
    names = validate_topics(topics)
    path = Path(evals_path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".csv":
            reader = csv.DictReader(stream, strict=True)
            try:
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ValueError("CSV requires unique column headers")
                records = list(reader)
            except csv.Error as error:
                raise ValueError(f"Malformed CSV near line {reader.line_num}: {error}") from None
        elif path.suffix.lower() == ".jsonl":
            records = [json.loads(line) for line in stream if line.strip()]
        else:
            raise ValueError("Evaluation input must be .csv or .jsonl")
    if not records:
        raise ValueError("Evaluation file has no cases")
    cases, ids = [], set()
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict) or None in record:
            raise ValueError(f"Case {index} is malformed")
        utterance, expected = record.get("utterance"), record.get("expected_action")
        raw_id = record.get("id")
        case_id = str(index if raw_id is None or raw_id == "" else raw_id)
        group = record.get("group") or "default"
        if not isinstance(utterance, str) or not utterance.strip():
            raise ValueError(f"Case {index} has no utterance")
        if expected not in names:
            raise ValueError(f"Case {index} has an unknown expected action")
        if case_id in ids or not case_id.strip() or not isinstance(group, str):
            raise ValueError(f"Case {index} has a duplicate id or invalid group")
        ids.add(case_id)
        cases.append({"id": case_id, "utterance": utterance, "expected_action": expected, "group": group})
    return cases, topics


def parse_prediction(envelope, names):
    """Require one finite probability for every action in the gateway response."""
    details = envelope.get("generation_details") if isinstance(envelope, dict) else None
    generations = details.get("generations") if isinstance(details, dict) else None
    if not isinstance(generations, list) or not generations:
        raise ServiceError("Classifier response has no generation_details.generations")
    probabilities = {}
    for generation in generations:
        if not isinstance(generation, dict):
            raise ServiceError("Malformed classifier generation")
        action = generation.get("content")
        parameters = generation.get("parameters")
        probability = parameters.get("probability") if isinstance(parameters, dict) else None
        if not isinstance(action, str) or action not in names or action in probabilities:
            raise ServiceError("Classifier returned an unknown or duplicate action")
        if (isinstance(probability, bool) or not isinstance(probability, (int, float))
                or not 0 <= probability <= 1 or not math.isfinite(probability)):
            raise ServiceError("Classifier returned an invalid probability")
        probabilities[action] = probability
    if set(probabilities) != set(names):
        raise ServiceError("Classifier omitted actions; full probability output is required")
    ranked = sorted(probabilities, key=probabilities.get, reverse=True)
    top, second = ranked[:2]
    return {"actual_action": top, "probability": probabilities[top], "probabilities": probabilities,
            "margin": probabilities[top] - probabilities[second],
            "top_tie": probabilities[top] == probabilities[second]}


def summarize(rows):
    """Report call accuracy, group/class breakdowns and repeated-case stability."""
    counts = {status: sum(row["status"] == status for row in rows) for status in ("pass", "fail", "error")}
    groups, classes, confusion, by_case = {}, {}, {}, {}
    for row in rows:
        for buckets, label in ((groups, row["group"]), (classes, row["expected_action"])):
            bucket = buckets.setdefault(label, {"total": 0, "pass": 0, "fail": 0, "error": 0})
            bucket["total"] += 1
            bucket[row["status"]] += 1
        bucket = confusion.setdefault(row["expected_action"], {})
        # Angle brackets cannot collide with a validated action identifier.
        actual = row["actual_action"] or "<service_error>"
        bucket[actual] = bucket.get(actual, 0) + 1
        by_case.setdefault(row["id"], []).append(row)
    for bucket in list(groups.values()) + list(classes.values()):
        bucket["accuracy"] = bucket["pass"] / bucket["total"]
    stable = sum(all(row["status"] == "pass" for row in case) for case in by_case.values())
    return {"total": len(rows), **counts, "accuracy": counts["pass"] / len(rows) if rows else None,
            "unique_cases": len(by_case), "cases_passing_every_repeat": stable,
            "cases_with_varying_predictions": sum(len({r["actual_action"] for r in case}) > 1 for case in by_case.values()),
            "ties": sum(bool(r.get("top_tie")) for r in rows), "groups": groups,
            "expected_actions": classes, "confusion_matrix": confusion}


def _csv_value(value):
    # Keep raw strings in JSONL; escape spreadsheet formulas in human-facing CSV.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def save_reports(folder, rows):
    """Write expected/actual CSVs and an aggregate JSON and Markdown summary."""
    fields = ["id", "group", "iteration", "utterance", "expected_action", "actual_action", "status",
              "probability", "margin", "top_tie", "http_attempts", "elapsed_seconds", "error"]
    for filename, subset in (("results.csv", rows), ("failures.csv", [r for r in rows if r["status"] != "pass"])):
        with (folder / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: _csv_value(row.get(key, "")) for key in fields} for row in subset)
    summary = summarize(rows)
    write_json(folder / "summary.json", summary)
    accuracy = f"{summary['accuracy']:.2%}" if rows else "n/a"
    (folder / "summary.md").write_text(
        f"# Classification results\n\n{summary['pass']}/{summary['total']} correct ({accuracy}); "
        f"{summary['fail']} routing mismatches; {summary['error']} service/contract errors.\n\n"
        f"{summary['cases_passing_every_repeat']}/{summary['unique_cases']} cases passed every completed repeat. "
        f"{summary['cases_with_varying_predictions']} cases had varying predictions.\n\n"
        "See summary.json for group/class accuracy and expected-versus-actual confusion counts. "
        "These measurements describe this dataset, not generalization to unseen requests.\n", encoding="utf-8")
    return summary


def evaluate(client, cases, topics, folder, repeats=1, stop_on_error=True):
    """Checkpoint each prediction and stop on infrastructure errors by default."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    names = validate_topics(topics)
    write_json(folder / "cases.json", cases)
    write_json(folder / "descriptions.json", topics)
    metadata = {"created_at": datetime.now(timezone.utc).isoformat(), "state": "running",
                "cases_sha256": digest(cases), "descriptions_sha256": digest(topics),
                "model": CLASSIFIER_MODEL, "endpoint_path": CLASSIFIER_PATH,
                "repeats": repeats, "planned_predictions": repeats * len(cases),
                "timeout_seconds": getattr(client, "timeout", None),
                "retries": getattr(client, "retries", None)}
    write_json(folder / "run.json", metadata)
    rows = []
    try:
        with (folder / "results.jsonl").open("w", encoding="utf-8") as stream:
            for iteration in range(1, repeats + 1):
                for case in cases:
                    started, before = time.monotonic(), client.http_attempts
                    row = {**case, "iteration": iteration, "actual_action": None, "status": "error"}
                    try:
                        row.update(parse_prediction(client.classify(case["utterance"], topics), names))
                        row["status"] = "pass" if row["actual_action"] == case["expected_action"] else "fail"
                    except ServiceError as error:
                        row["error"] = str(error)
                    row.update(elapsed_seconds=round(time.monotonic() - started, 3),
                               http_attempts=client.http_attempts - before)
                    rows.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                    stream.flush()
                    print(f"Prediction {len(rows)}/{metadata['planned_predictions']}: {row['status']}", flush=True)
                    if row["status"] == "error" and stop_on_error:
                        metadata["state"] = "service_error"
                        return rows
        metadata["state"] = "complete"
        return rows
    finally:
        if metadata["state"] == "running":
            metadata["state"] = "interrupted"
        metadata["completed_predictions"] = len(rows)
        write_json(folder / "run.json", metadata)
        save_reports(folder, rows)
