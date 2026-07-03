#!/usr/bin/env python3
"""
Parse Apex test results and format for Claude auto-fix loop.

This hook parses the JSON output from `sf apex run test` and provides
structured feedback that enables Claude to automatically fix failing tests.

Environment Variables:
    TOOL_OUTPUT: The stdout from the Bash command
    TOOL_INPUT: The command that was executed

Output:
    Formatted test results with failure analysis and fix suggestions
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime

# Only process sf apex run test commands
def should_process():
    """Check if this is an apex test command we should process."""
    tool_input = os.environ.get('TOOL_INPUT', '')
    return 'sf apex run test' in tool_input or 'sf apex get test' in tool_input

def parse_test_results(output: str) -> dict:
    """
    Parse test results from sf CLI JSON output.

    Returns:
        dict with summary, failures, and coverage data
    """
    try:
        # Try to parse as JSON (if --result-format json was used)
        data = json.loads(output)
        return parse_json_results(data)
    except json.JSONDecodeError:
        # Parse human-readable output
        return parse_text_results(output)

def parse_json_results(data: dict) -> dict:
    """Parse JSON format test results."""
    result = data.get('result', data)

    summary = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'total': 0,
        'duration_ms': 0,
        'coverage_percent': 0
    }

    failures = []
    coverage = []

    # Parse test results
    tests = result.get('tests', [])
    for test in tests:
        outcome = test.get('Outcome', test.get('outcome', '')).lower()
        if outcome == 'pass':
            summary['passed'] += 1
        elif outcome == 'fail':
            summary['failed'] += 1
            failures.append({
                'class': test.get('ApexClass', {}).get('Name', test.get('className', 'Unknown')),
                'method': test.get('MethodName', test.get('methodName', 'Unknown')),
                'message': test.get('Message', test.get('message', '')),
                'stack_trace': test.get('StackTrace', test.get('stackTrace', '')),
                'run_time': test.get('RunTime', test.get('runTime', 0))
            })
        elif outcome == 'skip':
            summary['skipped'] += 1

    summary['total'] = summary['passed'] + summary['failed'] + summary['skipped']

    # Parse coverage
    coverage_data = result.get('coverage', {}).get('coverage', [])
    if not coverage_data:
        coverage_data = result.get('codecoverage', [])

    total_lines = 0
    covered_lines = 0

    for cov in coverage_data:
        class_name = cov.get('name', cov.get('apexClassOrTriggerName', 'Unknown'))
        num_lines = cov.get('totalLines', cov.get('numLinesCovered', 0) + cov.get('numLinesUncovered', 0))
        num_covered = cov.get('coveredLines', cov.get('numLinesCovered', 0))
        if isinstance(num_covered, list):
            num_covered = len(num_covered)

        uncovered = cov.get('uncoveredLines', [])
        if isinstance(uncovered, int):
            uncovered = []

        pct = (num_covered / num_lines * 100) if num_lines > 0 else 0

        coverage.append({
            'class': class_name,
            'total_lines': num_lines,
            'covered_lines': num_covered,
            'uncovered_lines': uncovered[:10] if uncovered else [],  # Limit to first 10
            'percent': round(pct, 1)
        })

        total_lines += num_lines
        covered_lines += num_covered if isinstance(num_covered, int) else 0

    summary['coverage_percent'] = round(covered_lines / total_lines * 100, 1) if total_lines > 0 else 0

    return {
        'summary': summary,
        'failures': failures,
        'coverage': coverage
    }

def parse_text_results(output: str) -> dict:
    """Parse human-readable test output."""
    summary = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'total': 0,
        'duration_ms': 0,
        'coverage_percent': 0
    }

    failures = []

    # Look for pass/fail patterns
    pass_match = re.search(r'(\d+)\s+(?:test[s]?\s+)?pass(?:ed|ing)?', output, re.IGNORECASE)
    fail_match = re.search(r'(\d+)\s+(?:test[s]?\s+)?fail(?:ed|ing|ure)?', output, re.IGNORECASE)

    if pass_match:
        summary['passed'] = int(pass_match.group(1))
    if fail_match:
        summary['failed'] = int(fail_match.group(1))

    summary['total'] = summary['passed'] + summary['failed']

    # Look for failure details
    failure_pattern = re.compile(
        r'([\w]+)\.([\w]+)\s*[-:]\s*(.*?)(?=\n\n|\n[A-Z]|$)',
        re.MULTILINE | re.DOTALL
    )

    for match in failure_pattern.finditer(output):
        if 'fail' in match.group(3).lower() or 'error' in match.group(3).lower():
            failures.append({
                'class': match.group(1),
                'method': match.group(2),
                'message': match.group(3).strip(),
                'stack_trace': ''
            })

    return {
        'summary': summary,
        'failures': failures,
        'coverage': []
    }

def analyze_failure(failure: dict) -> dict:
    """
    Analyze a test failure and suggest fix strategy.

    Returns:
        dict with error_type, root_cause, and suggested_fix
    """
    message = failure.get('message', '')
    stack_trace = failure.get('stack_trace', '')

    analysis = {
        'error_type': 'Unknown',
        'root_cause': 'Unable to determine root cause',
        'suggested_fix': 'Review the test and code under test',
        'auto_fixable': False
    }

    # Assertion failures
    if 'AssertException' in message or 'Assertion Failed' in message:
        analysis['error_type'] = 'Assertion Failure'

        # Extract expected vs actual
        expected_match = re.search(r'[Ee]xpected[:\s]+(\S+)', message)
        actual_match = re.search(r'[Aa]ctual[:\s]+(\S+)', message)

        if expected_match and actual_match:
            analysis['root_cause'] = f"Expected {expected_match.group(1)} but got {actual_match.group(1)}"
            analysis['suggested_fix'] = "Check if the test expectation is correct, or if the code logic needs fixing"
        else:
            analysis['root_cause'] = "Test assertion did not match expected outcome"
            analysis['suggested_fix'] = "Review the assertion and verify expected vs actual values"

        analysis['auto_fixable'] = True

    # Null pointer
    elif 'NullPointerException' in message:
        analysis['error_type'] = 'Null Pointer Exception'

        # Try to extract line number
        line_match = re.search(r'[Ll]ine[:\s]+(\d+)', stack_trace or message)
        if line_match:
            analysis['root_cause'] = f"Null reference at line {line_match.group(1)}"
        else:
            analysis['root_cause'] = "Attempting to access a property or method on a null reference"

        analysis['suggested_fix'] = "Add null check before accessing the object, or ensure test data setup creates required records"
        analysis['auto_fixable'] = True

    # DML exceptions
    elif 'DmlException' in message:
        analysis['error_type'] = 'DML Exception'

        if 'REQUIRED_FIELD_MISSING' in message:
            analysis['root_cause'] = "Required field not populated in test data"
            analysis['suggested_fix'] = "Add the missing required field to TestDataFactory or test setup"
        elif 'FIELD_CUSTOM_VALIDATION_EXCEPTION' in message:
            analysis['root_cause'] = "Record fails validation rule"
            analysis['suggested_fix'] = "Modify test data to meet validation rule requirements"
        elif 'DUPLICATE_VALUE' in message:
            analysis['root_cause'] = "Unique field constraint violation"
            analysis['suggested_fix'] = "Use unique values in test data (e.g., add timestamp or random suffix)"
        else:
            analysis['root_cause'] = "DML operation failed"
            analysis['suggested_fix'] = "Review the DML error message and adjust test data accordingly"

        analysis['auto_fixable'] = True

    # Query exceptions
    elif 'QueryException' in message:
        analysis['error_type'] = 'Query Exception'
        analysis['root_cause'] = "SOQL query returned no results or too many results"
        analysis['suggested_fix'] = "Ensure test data exists before querying, or handle empty results"
        analysis['auto_fixable'] = True

    # Limit exceptions
    elif 'LimitException' in message:
        analysis['error_type'] = 'Governor Limit Exception'

        if 'Too many SOQL' in message:
            analysis['root_cause'] = "SOQL query limit exceeded (100 queries)"
            analysis['suggested_fix'] = "Bulkify queries - query before loops, use maps for lookups"
        elif 'Too many DML' in message:
            analysis['root_cause'] = "DML statement limit exceeded (150 statements)"
            analysis['suggested_fix'] = "Bulkify DML - collect records in list, single DML after loop"
        else:
            analysis['root_cause'] = "Governor limit exceeded"
            analysis['suggested_fix'] = "Review code for bulkification issues"

        analysis['auto_fixable'] = True

    # Mixed DML
    elif 'MIXED_DML_OPERATION' in message:
        analysis['error_type'] = 'Mixed DML Exception'
        analysis['root_cause'] = "Setup and non-setup objects modified in same transaction"
        analysis['suggested_fix'] = "Use System.runAs() to separate User operations from data operations"
        analysis['auto_fixable'] = True

    return analysis

def format_output(results: dict) -> str:
    """Format test results for Claude consumption."""
    summary = results['summary']
    failures = results['failures']
    coverage = results['coverage']

    lines = []
    lines.append("=" * 60)
    lines.append("📊 APEX TEST RESULTS")
    lines.append("=" * 60)
    lines.append("")

    # Summary
    status_icon = "✅" if summary['failed'] == 0 else "❌"
    lines.append(f"{status_icon} SUMMARY")
    lines.append("-" * 60)
    lines.append(f"   Passed:   {summary['passed']}")
    lines.append(f"   Failed:   {summary['failed']}")
    lines.append(f"   Skipped:  {summary['skipped']}")
    lines.append(f"   Total:    {summary['total']}")

    if summary['coverage_percent'] > 0:
        cov_icon = "✅" if summary['coverage_percent'] >= 75 else "⚠️"
        lines.append(f"   Coverage: {summary['coverage_percent']}% {cov_icon}")

    lines.append("")

    # Failures with analysis
    if failures:
        lines.append("❌ FAILED TESTS")
        lines.append("-" * 60)

        for i, failure in enumerate(failures, 1):
            analysis = analyze_failure(failure)

            lines.append(f"\n{i}. {failure['class']}.{failure['method']}")
            lines.append(f"   Error Type: {analysis['error_type']}")
            lines.append(f"   Message: {failure['message'][:200]}...")
            lines.append(f"   Root Cause: {analysis['root_cause']}")
            lines.append(f"   Suggested Fix: {analysis['suggested_fix']}")

            if analysis['auto_fixable']:
                lines.append("   🤖 AUTO-FIXABLE: Yes - Claude can attempt automatic fix")

        lines.append("")
        lines.append("=" * 60)
        lines.append("🤖 AGENTIC FIX INSTRUCTIONS")
        lines.append("=" * 60)
        lines.append("")
        lines.append("To automatically fix these failures:")
        lines.append("1. Read the failing test class")
        lines.append("2. Read the class under test")
        lines.append("3. Apply the suggested fix")
        lines.append("4. Re-run: sf apex run test --tests [ClassName].[methodName]")
        lines.append("")

    # Coverage details (if below threshold)
    low_coverage = [c for c in coverage if c['percent'] < 75]
    if low_coverage:
        lines.append("⚠️ LOW COVERAGE CLASSES (<75%)")
        lines.append("-" * 60)

        for cov in sorted(low_coverage, key=lambda x: x['percent']):
            lines.append(f"   {cov['class']}: {cov['percent']}%")
            if cov.get('uncovered_lines'):
                lines.append(f"      Uncovered lines: {cov['uncovered_lines']}")

        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)

def main():
    """Main entry point."""
    if not should_process():
        # Not an apex test command, exit silently
        sys.exit(0)

    output = os.environ.get('TOOL_OUTPUT', '')

    if not output:
        sys.exit(0)

    # Check if this looks like test output
    if 'test' not in output.lower() and 'coverage' not in output.lower():
        sys.exit(0)

    try:
        results = parse_test_results(output)

        # Only output if there were tests or failures
        if results['summary']['total'] > 0 or results['failures']:
            formatted = format_output(results)
            print(formatted)
    except Exception as e:
        # Silently fail - don't block on parsing errors
        sys.exit(0)

if __name__ == "__main__":
    main()
