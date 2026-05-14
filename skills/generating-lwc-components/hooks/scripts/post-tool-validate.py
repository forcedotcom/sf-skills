#!/usr/bin/env python3
"""
Post-Tool Validation Hook for generating-lwc-components plugin.

This hook runs AFTER Write or Edit tool completes and provides SLDS 2
validation feedback for LWC files (*.html, *.css, *.js).

Integrates:
1. Custom 140-point SLDS 2 scoring (7 categories)
2. Official SLDS Linter (if available via npm)
3. Salesforce Code Analyzer V5 (ESLint + retire-js engines for JS files)

Hook Input (stdin): JSON with tool_input and tool_response
Hook Output (stdout): JSON with optional output message

This hook is ADVISORY - it provides feedback but does not block operations.
"""

import sys
import os
import json
from pathlib import Path

# Add script directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Find shared modules — try installed path first, then dev repo path
_CLAUDE_DIR = os.path.join(os.path.expanduser("~"), ".claude")
_CODE_ANALYZER_CANDIDATES = [
    os.path.join(_CLAUDE_DIR, "code_analyzer"),           # Installed path
    os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "shared", "code_analyzer"),  # Dev repo
]
for _ca_path in _CODE_ANALYZER_CANDIDATES:
    _ca_path = os.path.normpath(_ca_path)
    if os.path.isdir(_ca_path):
        sys.path.insert(0, os.path.dirname(_ca_path))
        break

# Also add shared dir for other shared modules
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # generating-lwc-components/
SKILLS_ROOT = os.path.dirname(PLUGIN_ROOT)
SHARED_DIR = os.path.join(SKILLS_ROOT, "shared")
if os.path.isdir(SHARED_DIR):
    sys.path.insert(0, SHARED_DIR)

# Supported LWC file extensions
LWC_EXTENSIONS = {'.html', '.css', '.js'}


def is_lwc_file(file_path: str) -> bool:
    """
    Check if file is an LWC component file.

    We validate .html (templates), .css (styles), and .js (controllers).
    """
    ext = Path(file_path).suffix.lower()
    return ext in LWC_EXTENSIONS


def validate_lwc_file(file_path: str) -> dict:
    """
    Run comprehensive SLDS 2 validation on an LWC file.

    Args:
        file_path: Path to .html, .css, or .js file

    Returns:
        dict with validation results and output message
    """
    output_parts = []
    file_name = os.path.basename(file_path)
    ext = Path(file_path).suffix.lower()

    try:
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: Custom 140-point SLDS 2 validation
        # ═══════════════════════════════════════════════════════════════════
        from validate_slds import SLDSValidator

        validator = SLDSValidator(file_path)
        results = validator.validate()

        score = results.get('score', 0)
        max_score = results.get('max_score', 140)
        issues = results.get('issues', [])
        scores = results.get('scores', {})
        rating = results.get('rating', '')

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1.5: LWC Template Anti-Pattern Validation (for HTML files)
        # ═══════════════════════════════════════════════════════════════════
        if ext == '.html':
            try:
                from template_validator import LWCTemplateValidator
                template_validator = LWCTemplateValidator(file_path)
                template_results = template_validator.validate()
                template_issues = template_results.get('issues', [])

                # Add template issues to main issues list
                for tpl_issue in template_issues:
                    issues.append({
                        'severity': tpl_issue.get('severity', 'WARNING'),
                        'category': 'template_' + tpl_issue.get('category', 'pattern'),
                        'message': tpl_issue.get('message', ''),
                        'line': tpl_issue.get('line', 0),
                        'fix': tpl_issue.get('fix', ''),
                        'source': 'template-validator'
                    })

                    # Deduct from score for critical template issues
                    if tpl_issue.get('severity') == 'CRITICAL':
                        scores['component_structure'] = max(0, scores['component_structure'] - 3)
            except ImportError:
                pass  # Template validator not available
            except Exception:
                pass  # Don't fail validation on template check errors

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: Official SLDS Linter (if available)
        # ═══════════════════════════════════════════════════════════════════
        linter_available = False
        linter_violations = []

        try:
            from slds_linter_wrapper import SLDSLinterWrapper

            linter = SLDSLinterWrapper()
            if linter.is_available() and ext in {'.html', '.css'}:
                linter_available = True
                linter_result = linter.lint_file(file_path)

                if linter_result.get('success'):
                    linter_violations = linter_result.get('violations', [])

                    # Merge linter violations with issues
                    for v in linter_violations:
                        issues.append({
                            'severity': v.get('severity', 'WARNING'),
                            'category': 'slds_linter',
                            'message': f"[{v.get('rule', 'slds')}] {v.get('message', '')}",
                            'line': v.get('line', 0),
                            'source': 'slds-linter'
                        })
        except ImportError:
            pass
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2.5: Code Analyzer V5 scanning (ESLint + retire-js for JS files)
        # ═══════════════════════════════════════════════════════════════════
        ca_violations = []
        ca_engines_used = []
        ca_engines_unavailable = []
        ca_available = False
        scan_time_ms = 0

        # Only run CA on .js files (ESLint/retire-js don't apply to HTML/CSS)
        if ext == '.js':
            try:
                from code_analyzer.scanner import CodeAnalyzerScanner, SkillType

                scanner = CodeAnalyzerScanner()

                if scanner.is_available():
                    ca_available = True
                    scan_result = scanner.scan(file_path, SkillType.LWC)

                    if scan_result.success:
                        ca_violations = scan_result.violations
                        ca_engines_used = scan_result.engines_used
                        ca_engines_unavailable = scan_result.engines_unavailable
                        scan_time_ms = scan_result.scan_time_ms

                        # Merge CA violations with issues
                        for v in ca_violations:
                            issues.append({
                                'severity': v.get('severity_label', 'WARNING'),
                                'category': 'code_analyzer',
                                'message': f"[{v.get('engine', 'CA')}:{v.get('rule', '')}] {v.get('message', '')}",
                                'line': v.get('line', 0),
                                'source': f"CA:{v.get('engine', '')}"
                            })
                    else:
                        ca_engines_unavailable = ["Error: " + (scan_result.error_message or "Unknown")]
                else:
                    ca_engines_unavailable = ["sf CLI with Code Analyzer not installed"]

            except ImportError as e:
                ca_engines_unavailable = [f"Module not available: {e}"]
            except Exception as e:
                ca_engines_unavailable = [f"Scanner error: {e}"]

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 3: Calculate rating
        # ═══════════════════════════════════════════════════════════════════
        pct = (score / max_score * 100) if max_score > 0 else 0
        if pct >= 90:
            rating_stars = 5
            rating = "Production-ready SLDS 2"
        elif pct >= 80:
            rating_stars = 4
            rating = "Good"
        elif pct >= 70:
            rating_stars = 3
            rating = "Functional"
        elif pct >= 60:
            rating_stars = 2
            rating = "Needs work"
        else:
            rating_stars = 1
            rating = "Critical issues"

        stars = "⭐" * rating_stars + "☆" * (5 - rating_stars)

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 4: Format output
        # ═══════════════════════════════════════════════════════════════════
        output_parts.append("")
        output_parts.append(f"🎨 SLDS 2 Validation: {file_name}")
        output_parts.append("═" * 60)
        output_parts.append(f"📊 Score: {score}/{max_score} {stars} {rating}")

        # Category breakdown
        if scores:
            output_parts.append("")
            output_parts.append("📋 Category Breakdown:")
            for cat, cat_score in scores.items():
                max_cat = validator.max_scores.get(cat, 0)
                if max_cat > 0:
                    icon = "✅" if cat_score == max_cat else ("⚠️" if cat_score >= max_cat * 0.7 else "❌")
                    diff = f" (-{max_cat - cat_score})" if cat_score < max_cat else ""
                    display_name = cat.replace("_", " ").title()
                    output_parts.append(f"   {icon} {display_name}: {cat_score}/{max_cat}{diff}")

        # SLDS Linter status
        output_parts.append("")
        if linter_available:
            output_parts.append("🔧 SLDS Linter: Active")
        else:
            output_parts.append("💡 SLDS Linter: Not installed")
            output_parts.append("   Install: npm i -g @salesforce-ux/slds-linter")

        # Code Analyzer status (for JS files only)
        if ext == '.js':
            output_parts.append("")
            if ca_engines_used:
                output_parts.append(f"🔍 Code Analyzer: {', '.join(ca_engines_used)}")
                if scan_time_ms > 0:
                    output_parts.append(f"   Scan time: {scan_time_ms}ms")
            elif ca_available:
                output_parts.append("🔍 Code Analyzer: No engines ran")
            else:
                output_parts.append("💡 Code Analyzer: Not available")
                if ca_engines_unavailable:
                    for unavail in ca_engines_unavailable[:2]:
                        output_parts.append(f"   ⚠️ {unavail}")

        # Issues list
        if issues:
            output_parts.append("")
            output_parts.append(f"⚠️ Issues Found ({len(issues)}):")

            # Sort by severity
            severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MODERATE': 2, 'WARNING': 3, 'LOW': 4, 'INFO': 5}
            issues.sort(key=lambda x: severity_order.get(x.get('severity', 'INFO'), 5))

            # Display up to 10 issues
            for issue in issues[:10]:
                sev = issue.get('severity', 'INFO')
                icon = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MODERATE': '🟡', 'WARNING': '🟡', 'LOW': '🔵', 'INFO': '⚪'}.get(sev, '⚪')
                line_info = f"L{issue.get('line', '?')}" if issue.get('line') else ""
                message = issue.get('message', '')[:60]
                output_parts.append(f"   {icon} {line_info} {message}")

                if issue.get('fix'):
                    fix = issue['fix'][:55] + "..." if len(issue['fix']) > 55 else issue['fix']
                    output_parts.append(f"      💡 Fix: {fix}")

            if len(issues) > 10:
                output_parts.append(f"   ... and {len(issues) - 10} more issues")
        else:
            output_parts.append("")
            output_parts.append("✅ No SLDS issues found!")

        output_parts.append("═" * 60)

        return {
            "continue": True,
            "output": "\n".join(output_parts)
        }

    except ImportError as e:
        return {
            "continue": True,
            "output": f"⚠️ SLDS validator not available: {e}"
        }
    except Exception as e:
        return {
            "continue": True,
            "output": f"⚠️ SLDS validation error: {e}"
        }


def main():
    """
    Main hook entry point.

    Reads hook input from stdin, validates LWC files.
    """
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract file path from tool input
        tool_input = hook_input.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Check if operation was successful
        tool_response = hook_input.get("tool_response", {})
        if not tool_response.get("success", True):
            print(json.dumps({"continue": True}))
            return 0

        # Only validate LWC files
        result = {"continue": True}

        if is_lwc_file(file_path):
            result = validate_lwc_file(file_path)

        print(json.dumps(result))
        return 0

    except json.JSONDecodeError:
        print(json.dumps({"continue": True}))
        return 0
    except Exception as e:
        print(json.dumps({
            "continue": True,
            "output": f"⚠️ Hook error: {e}"
        }))
        return 0


if __name__ == "__main__":
    sys.exit(main())
