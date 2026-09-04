#!/usr/bin/env python3
"""Deterministic date validation for Academic Year / Term / Session records.

Reads calendar data as JSON on stdin, shape:
{
  "academicYear": {"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"},
  "terms": [
    {"name": "Fall 2025", "startDate": "...", "endDate": "...", "registrationOpenDate": "..."}
  ],
  "sessions": [
    {"name": "Summer Session 1", "termName": "Summer 2026",
     "classStartDate": "...", "classEndDate": "...", "addDropDeadline": "..."}
  ]
}

Writes JSON to stdout:
{
  "valid": bool,
  "errors": [{"field": str, "message": str}],
  "warnings": [{"field": str, "message": str}],
  "computedRegistrationCloseDates": {"<termName>": "YYYY-MM-DD"}
}

Exit code 0 if no errors (warnings, e.g. intentional session overlaps, do not fail the run), 1 otherwise.
"""

import json
import sys
from datetime import date, timedelta


def parse_date(value):
    return date.fromisoformat(value)


def safe_parse(value, field, errors):
    """Parse an ISO date, routing missing/malformed values into `errors` instead of raising."""
    if value is None:
        errors.append({"field": field, "message": "Required date value is missing"})
        return None
    try:
        return parse_date(value)
    except (TypeError, ValueError):
        errors.append({"field": field, "message": f"Invalid date value: {value!r}"})
        return None


def validate(data):
    errors = []
    warnings = []
    computed_close_dates = {}

    year = data.get("academicYear", {})
    terms = data.get("terms", [])
    sessions = data.get("sessions", [])

    year_start = safe_parse(year.get("startDate"), "academicYear.startDate", errors)
    year_end = safe_parse(year.get("endDate"), "academicYear.endDate", errors)

    term_bounds = {}

    for term in terms:
        name = term.get("name", "<unnamed term>")
        start = safe_parse(term.get("startDate"), f"terms[{name}].startDate", errors)
        end = safe_parse(term.get("endDate"), f"terms[{name}].endDate", errors)
        if start is None or end is None:
            continue
        term_bounds[name] = (start, end)

        if end <= start:
            errors.append({"field": f"terms[{name}].endDate", "message": "Term end date must be after start date"})

        if year_start and start < year_start:
            errors.append({"field": f"terms[{name}].startDate", "message": "Term starts before Academic Year start date"})
        if year_end and end > year_end:
            errors.append({"field": f"terms[{name}].endDate", "message": "Term ends after Academic Year end date"})

        reg_open = term.get("registrationOpenDate")
        if reg_open:
            reg_open_date = safe_parse(reg_open, f"terms[{name}].registrationOpenDate", errors)
            if reg_open_date is not None and reg_open_date >= start:
                errors.append({"field": f"terms[{name}].registrationOpenDate", "message": "Registration window must open before term start date"})

        computed_close_dates[name] = (start - timedelta(days=1)).isoformat()

    sessions_by_term = {}
    for session in sessions:
        name = session.get("name", "<unnamed session>")
        term_name = session.get("termName")
        start = safe_parse(session.get("classStartDate"), f"sessions[{name}].classStartDate", errors)
        end = safe_parse(session.get("classEndDate"), f"sessions[{name}].classEndDate", errors)
        if start is None or end is None:
            continue

        if end <= start:
            errors.append({"field": f"sessions[{name}].classEndDate", "message": "Session end date must be after start date"})

        bounds = term_bounds.get(term_name)
        if bounds is None:
            errors.append({"field": f"sessions[{name}].termName", "message": f"No term named '{term_name}' found for this session"})
        else:
            term_start, term_end = bounds
            if start < term_start or end > term_end:
                errors.append({"field": f"sessions[{name}]", "message": "Session dates must fall within parent term date range"})

        deadline = session.get("addDropDeadline")
        if deadline:
            deadline_date = safe_parse(deadline, f"sessions[{name}].addDropDeadline", errors)
            if deadline_date is not None:
                if deadline_date < start or deadline_date >= end:
                    errors.append({"field": f"sessions[{name}].addDropDeadline", "message": "Add/drop deadline must be on or after session start and before session end"})

        sessions_by_term.setdefault(term_name, []).append((name, start, end))

    for term_name, entries in sessions_by_term.items():
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                name_a, start_a, end_a = entries[i]
                name_b, start_b, end_b = entries[j]
                if start_a <= end_b and start_b <= end_a:
                    warnings.append({
                        "field": f"sessions[{name_a},{name_b}]",
                        "message": f"'{name_a}' and '{name_b}' overlap within term '{term_name}' — confirm with user whether intentional",
                    })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "computedRegistrationCloseDates": computed_close_dates,
    }


def main():
    data = json.load(sys.stdin)
    result = validate(data)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
