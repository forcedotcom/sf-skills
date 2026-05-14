#!/usr/bin/env python3
"""
building-sf-integrations Validation Script

Validates integration-related files against best practices.
Scoring: 120 points across 6 categories.

Categories:
- Security (30 points)
- Error Handling (25 points)
- Bulkification (20 points)
- Architecture (20 points)
- Best Practices (15 points)
- Documentation (10 points)
"""

import sys
import re
import os
from pathlib import Path

# Scoring configuration
MAX_SCORE = 120
CATEGORIES = {
    'security': {'max': 30, 'score': 0, 'issues': []},
    'error_handling': {'max': 25, 'score': 0, 'issues': []},
    'bulkification': {'max': 20, 'score': 0, 'issues': []},
    'architecture': {'max': 20, 'score': 0, 'issues': []},
    'best_practices': {'max': 15, 'score': 0, 'issues': []},
    'documentation': {'max': 10, 'score': 0, 'issues': []}
}

# File type patterns
APEX_PATTERN = re.compile(r'\.cls$|\.trigger$')
XML_PATTERN = re.compile(r'\.xml$')
NAMED_CRED_PATTERN = re.compile(r'namedCredential.*\.xml$', re.IGNORECASE)


def validate_apex_file(content: str, filename: str) -> None:
    """Validate Apex class/trigger for integration patterns."""

    # Security checks (30 points)
    security_score = 30

    # Check for hardcoded credentials
    if re.search(r'Authorization.*Bearer\s+[a-zA-Z0-9_\-]{20,}', content):
        security_score -= 15
        CATEGORIES['security']['issues'].append('❌ Hardcoded Bearer token detected')

    if re.search(r'api[_-]?key\s*=\s*[\'"][a-zA-Z0-9]{10,}', content, re.IGNORECASE):
        security_score -= 15
        CATEGORIES['security']['issues'].append('❌ Hardcoded API key detected')

    if re.search(r'password\s*=\s*[\'"][^\'"]{5,}', content, re.IGNORECASE):
        security_score -= 15
        CATEGORIES['security']['issues'].append('❌ Hardcoded password detected')

    # Check for Named Credential usage
    if 'HttpRequest' in content:
        if 'callout:' in content:
            if not CATEGORIES['security']['issues']:
                CATEGORIES['security']['issues'].append('✅ Named Credential used')
        else:
            security_score -= 10
            CATEGORIES['security']['issues'].append('⚠️ HttpRequest without Named Credential')

    CATEGORIES['security']['score'] = max(0, security_score)

    # Error Handling checks (25 points)
    error_score = 25

    if 'HttpRequest' in content or 'Http().send' in content:
        # Check for try-catch
        if 'try' not in content or 'catch' not in content:
            error_score -= 10
            CATEGORIES['error_handling']['issues'].append('❌ Missing try-catch for callout')
        else:
            CATEGORIES['error_handling']['issues'].append('✅ Try-catch present')

        # Check for CalloutException handling
        if 'CalloutException' in content:
            CATEGORIES['error_handling']['issues'].append('✅ CalloutException handled')
        else:
            error_score -= 5
            CATEGORIES['error_handling']['issues'].append('⚠️ CalloutException not explicitly caught')

        # Check for status code handling
        if 'getStatusCode()' in content:
            CATEGORIES['error_handling']['issues'].append('✅ Status code checked')
        else:
            error_score -= 5
            CATEGORIES['error_handling']['issues'].append('⚠️ Status code not checked')

        # Check for timeout setting
        if 'setTimeout' in content:
            CATEGORIES['error_handling']['issues'].append('✅ Timeout configured')
        else:
            error_score -= 5
            CATEGORIES['error_handling']['issues'].append('⚠️ No timeout set (default may be too short)')

    CATEGORIES['error_handling']['score'] = max(0, error_score)

    # Bulkification checks (20 points)
    bulk_score = 20

    # Check for SOQL in loops
    if re.search(r'for\s*\([^)]+\)\s*\{[^}]*\[SELECT', content, re.DOTALL | re.IGNORECASE):
        bulk_score -= 10
        CATEGORIES['bulkification']['issues'].append('❌ SOQL in loop')

    # Check for DML in loops
    if re.search(r'for\s*\([^)]+\)\s*\{[^}]*(insert|update|delete)\s+', content, re.DOTALL | re.IGNORECASE):
        bulk_score -= 10
        CATEGORIES['bulkification']['issues'].append('❌ DML in loop')

    # Check for HTTP callout in loops (expensive)
    if re.search(r'for\s*\([^)]+\)\s*\{[^}]*\.send\(', content, re.DOTALL):
        bulk_score -= 5
        CATEGORIES['bulkification']['issues'].append('⚠️ HTTP callout in loop (consider batching)')

    if bulk_score == 20:
        CATEGORIES['bulkification']['issues'].append('✅ No obvious bulkification issues')

    CATEGORIES['bulkification']['score'] = max(0, bulk_score)

    # Architecture checks (20 points)
    arch_score = 20

    # Check if class implements proper interfaces for callouts
    if 'implements Queueable' in content and 'Database.AllowsCallouts' in content:
        CATEGORIES['architecture']['issues'].append('✅ Proper Queueable + AllowsCallouts pattern')
    elif 'Queueable' in content and 'AllowsCallouts' not in content:
        if 'HttpRequest' in content or 'Http(' in content:
            arch_score -= 10
            CATEGORIES['architecture']['issues'].append('❌ Queueable with callout missing AllowsCallouts')

    # Check for trigger context callout (should be async)
    if '.trigger' in filename.lower():
        if 'Http(' in content or 'HttpRequest' in content:
            arch_score -= 15
            CATEGORIES['architecture']['issues'].append('❌ Synchronous callout in trigger (must use async)')

    CATEGORIES['architecture']['score'] = max(0, arch_score)

    # Best Practices checks (15 points)
    bp_score = 15

    # Check for logging
    if 'System.debug' in content:
        CATEGORIES['best_practices']['issues'].append('✅ Debug logging present')
    else:
        bp_score -= 5
        CATEGORIES['best_practices']['issues'].append('⚠️ No debug logging')

    # Check for proper HTTP methods
    if re.search(r'setMethod\s*\(\s*[\'"](?:GET|POST|PUT|PATCH|DELETE)[\'"]\s*\)', content):
        CATEGORIES['best_practices']['issues'].append('✅ Standard HTTP method used')

    CATEGORIES['best_practices']['score'] = max(0, bp_score)

    # Documentation checks (10 points)
    doc_score = 10

    # Check for ApexDoc
    if '/**' in content and '@description' in content:
        CATEGORIES['documentation']['issues'].append('✅ ApexDoc present')
    else:
        doc_score -= 5
        CATEGORIES['documentation']['issues'].append('⚠️ Missing ApexDoc comments')

    # Check for class-level documentation
    if re.search(r'/\*\*[\s\S]*?\*/\s*public\s+(with sharing\s+)?class', content):
        CATEGORIES['documentation']['issues'].append('✅ Class-level documentation')

    CATEGORIES['documentation']['score'] = max(0, doc_score)


def validate_named_credential(content: str) -> None:
    """Validate Named Credential XML."""

    # Security checks
    security_score = 30

    # Check for hardcoded password in XML (should never be there)
    if '<password>' in content and re.search(r'<password>[^<]+</password>', content):
        password_value = re.search(r'<password>([^<]+)</password>', content)
        if password_value and len(password_value.group(1)) > 0:
            security_score -= 15
            CATEGORIES['security']['issues'].append('⚠️ Password value in metadata (should be empty, set via UI)')

    # Check for protocol
    if '<protocol>Oauth</protocol>' in content:
        CATEGORIES['security']['issues'].append('✅ OAuth authentication configured')
    elif '<protocol>Password</protocol>' in content:
        CATEGORIES['security']['issues'].append('✅ Password authentication configured')
        security_score -= 5  # OAuth preferred over password
    elif '<protocol>NoAuthentication</protocol>' in content:
        CATEGORIES['security']['issues'].append('⚠️ No authentication (verify this is intentional)')
        security_score -= 10

    CATEGORIES['security']['score'] = max(0, security_score)

    # Best practices
    bp_score = 15

    if '<allowMergeFieldsInBody>true</allowMergeFieldsInBody>' in content:
        CATEGORIES['best_practices']['issues'].append('✅ Merge fields in body enabled')

    if '<allowMergeFieldsInHeader>true</allowMergeFieldsInHeader>' in content:
        CATEGORIES['best_practices']['issues'].append('✅ Merge fields in header enabled')

    CATEGORIES['best_practices']['score'] = bp_score

    # Named Credential XML files are configuration-only — Error Handling,
    # Bulkification, Architecture, and Documentation categories are not
    # applicable. Grant full marks for non-applicable categories so that
    # valid XML files are not penalized by the Apex-oriented rubric.
    CATEGORIES['error_handling']['score'] = CATEGORIES['error_handling']['max']
    CATEGORIES['bulkification']['score'] = CATEGORIES['bulkification']['max']
    CATEGORIES['architecture']['score'] = CATEGORIES['architecture']['max']
    CATEGORIES['documentation']['score'] = CATEGORIES['documentation']['max']


def validate_platform_event(content: str) -> None:
    """Validate Platform Event definition."""

    # Check event type
    if '<eventType>HighVolume</eventType>' in content:
        CATEGORIES['best_practices']['issues'].append('✅ High Volume event type')
        CATEGORIES['best_practices']['score'] = 15
    elif '<eventType>StandardVolume</eventType>' in content:
        CATEGORIES['best_practices']['issues'].append('✅ Standard Volume event type')
        CATEGORIES['best_practices']['score'] = 15

    # Check publish behavior
    if '<publishBehavior>PublishAfterCommit</publishBehavior>' in content:
        CATEGORIES['architecture']['issues'].append('✅ PublishAfterCommit (recommended)')
        CATEGORIES['architecture']['score'] = 20
    elif '<publishBehavior>PublishImmediately</publishBehavior>' in content:
        CATEGORIES['architecture']['issues'].append('⚠️ PublishImmediately (verify this is intentional)')
        CATEGORIES['architecture']['score'] = 15


def calculate_total_score() -> int:
    """Calculate total score from all categories."""
    return sum(cat['score'] for cat in CATEGORIES.values())


def get_rating(score: int) -> str:
    """Get star rating based on score."""
    percentage = (score / MAX_SCORE) * 100
    if percentage >= 90:
        return '⭐⭐⭐⭐⭐ Excellent'
    elif percentage >= 80:
        return '⭐⭐⭐⭐ Very Good'
    elif percentage >= 70:
        return '⭐⭐⭐ Good'
    elif percentage >= 60:
        return '⭐⭐ Needs Work'
    else:
        return '⭐ Critical'


def print_score_report(filename: str) -> None:
    """Print formatted score report."""
    total = calculate_total_score()
    rating = get_rating(total)

    print(f'\n📊 INTEGRATION SCORE: {total}/{MAX_SCORE} {rating}')
    print('═' * 50)

    category_icons = {
        'security': '🔐',
        'error_handling': '⚠️',
        'bulkification': '📦',
        'architecture': '🏗️',
        'best_practices': '✅',
        'documentation': '📝'
    }

    for cat_name, cat_data in CATEGORIES.items():
        icon = category_icons.get(cat_name, '•')
        max_score = cat_data['max']
        score = cat_data['score']
        pct = (score / max_score * 100) if max_score > 0 else 0
        bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))

        print(f'\n{icon} {cat_name.replace("_", " ").title():18} {score:2}/{max_score:2}  {bar} {pct:.0f}%')

        for issue in cat_data['issues']:
            print(f'   {issue}')

    print('\n' + '═' * 50)

    if total < 54:
        print('🚫 DEPLOYMENT BLOCKED - Score below 45% threshold')
    elif total < 72:
        print('⚠️ WARNING - Review issues before deployment')
    else:
        print('✅ PASSED - Ready for deployment')


def main():
    import json

    file_path = None

    # Mode 1: Hook mode - read from stdin JSON (PostToolUse hooks)
    if not sys.stdin.isatty():
        try:
            hook_input = json.load(sys.stdin)
            tool_input = hook_input.get("tool_input", {})
            file_path = tool_input.get("file_path", "")
        except (json.JSONDecodeError, EOFError):
            pass

    # Mode 2: CLI mode - read from command-line argument
    if not file_path and len(sys.argv) >= 2:
        file_path = sys.argv[1]

    # Skip if no file path
    if not file_path:
        print('Usage: validate_integration.py <file_path>')
        sys.exit(1)

    filename = os.path.basename(file_path)

    # Determine file type and validate
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f'Error reading file: {e}')
        sys.exit(1)

    # Skip if file is too small (likely not a real integration file)
    if len(content) < 50:
        sys.exit(0)

    # Skip template files (contain placeholders)
    if '{{' in content and '}}' in content:
        print(f'ℹ️ Skipping template file: {filename}')
        sys.exit(0)

    # Validate based on file type
    if APEX_PATTERN.search(filename):
        # Only validate if it looks like integration code
        if any(keyword in content for keyword in ['HttpRequest', 'Http(', 'callout:', 'EventBus', 'ChangeEvent']):
            validate_apex_file(content, filename)
            print_score_report(filename)
    elif NAMED_CRED_PATTERN.search(filename):
        validate_named_credential(content)
        print_score_report(filename)
    elif '__e.object-meta.xml' in filename:
        validate_platform_event(content)
        print_score_report(filename)
    else:
        # Not an integration file we validate
        sys.exit(0)


if __name__ == '__main__':
    main()
