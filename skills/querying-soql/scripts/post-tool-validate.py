#!/usr/bin/env python3
"""
Post-Tool Validation Hook for querying-soql skill.

This hook runs AFTER Write or Edit tool completes and provides validation
feedback for SOQL files (*.soql).

Integrates:
1. Static SOQL validation (syntax, best practices)
2. Live Query Plan Analysis (if org connected)

Hook Input (stdin): JSON with tool_input and tool_response
Hook Output (stdout): JSON with optional output message

This hook is ADVISORY - it provides feedback but does not block operations.
"""

import sys
import os
import json

# Add script directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Find shared modules (../../shared relative to querying-soql)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # querying-soql/
SKILLS_ROOT = os.path.dirname(PLUGIN_ROOT)  # sf-skills/
SHARED_DIR = os.path.join(SKILLS_ROOT, "shared")
sys.path.insert(0, SHARED_DIR)


def validate_soql_file(file_path: str) -> dict:
    """
    Validate a .soql file with static analysis and live query plan.

    Args:
        file_path: Path to .soql file

    Returns:
        dict with validation results and output message
    """
    output_parts = []
    file_name = os.path.basename(file_path)
    issues = []
    recommendations = []

    try:
        # Read file content
        with open(file_path, 'r') as f:
            content = f.read()

        if not content.strip():
            return {"continue": True}

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: Static SOQL Validation
        # ═══════════════════════════════════════════════════════════════════
        static_result = validate_soql_static(content)
        issues.extend(static_result.get('issues', []))
        recommendations.extend(static_result.get('recommendations', []))

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: Live Query Plan Analysis (if org connected)
        # ═══════════════════════════════════════════════════════════════════
        live_result = None
        org_name = None

        try:
            from code_analyzer.live_query_plan import LiveQueryPlanAnalyzer

            analyzer = LiveQueryPlanAnalyzer()
            if analyzer.is_org_available():
                org_name = analyzer.get_target_org()
                live_result = analyzer.analyze(content)

                if live_result.success:
                    # Add live plan insights as issues/recommendations
                    if not live_result.is_selective:
                        issues.append({
                            'severity': 'WARNING',
                            'message': f'Non-selective query (cost: {live_result.relative_cost:.1f})',
                            'source': 'LivePlan'
                        })

                    # Add notes as recommendations
                    for note in live_result.notes:
                        recommendations.append(str(note))

                    # Get optimization suggestions
                    suggestions = analyzer.get_optimization_suggestions(live_result)
                    recommendations.extend(suggestions)

        except ImportError:
            pass  # Live analysis not available
        except Exception as e:
            pass  # Don't fail on live analysis errors

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 3: Format Output
        # ═══════════════════════════════════════════════════════════════════
        output_parts.append("")
        output_parts.append(f"🔍 SOQL Validation: {file_name}")
        output_parts.append("═" * 55)

        # Static analysis summary
        if static_result.get('has_where_clause'):
            output_parts.append("✅ Has WHERE clause")
        else:
            output_parts.append("⚠️ Missing WHERE clause")

        if static_result.get('has_limit'):
            output_parts.append("✅ Has LIMIT clause")
        else:
            output_parts.append("⚠️ Missing LIMIT clause")

        if static_result.get('has_hardcoded_ids'):
            output_parts.append("⚠️ Contains hardcoded IDs")

        # Live Query Plan section
        output_parts.append("")
        if live_result and live_result.success:
            output_parts.append(f"🌐 Live Query Plan Analysis")
            output_parts.append(f"   Org: {org_name}")
            output_parts.append(f"   {live_result.icon} Selective: {live_result.is_selective}")
            output_parts.append(f"   📊 Relative Cost: {live_result.relative_cost:.2f} ({live_result.selectivity_rating})")
            output_parts.append(f"   📈 Operation: {live_result.leading_operation}")

            if live_result.cardinality > 0:
                output_parts.append(f"   📋 Cardinality: {live_result.cardinality:,} / {live_result.sobject_cardinality:,}")

            if live_result.notes:
                output_parts.append("")
                output_parts.append("   📝 Query Plan Notes:")
                for note in live_result.notes[:3]:
                    output_parts.append(f"      • {str(note)[:70]}")
        elif org_name is None:
            output_parts.append("🌐 Live Query Plan: No org connected")
            output_parts.append("   Run 'sf org login web' to enable live analysis")
        elif live_result and not live_result.success:
            output_parts.append(f"🌐 Live Query Plan: Error")
            output_parts.append(f"   {live_result.error[:60]}")

        # Issues
        if issues:
            output_parts.append("")
            output_parts.append(f"⚠️ Issues ({len(issues)}):")
            severity_icons = {
                'CRITICAL': '🔴', 'HIGH': '🟠', 'MODERATE': '🟡',
                'WARNING': '⚠️', 'LOW': '🔵', 'INFO': 'ℹ️'
            }
            for issue in issues[:5]:
                icon = severity_icons.get(issue.get('severity', 'INFO'), 'ℹ️')
                source = f"[{issue.get('source', '')}]" if issue.get('source') else ""
                output_parts.append(f"   {icon} {source} {issue.get('message', '')[:60]}")

        # Recommendations
        unique_recs = list(dict.fromkeys(recommendations))  # Remove duplicates
        if unique_recs:
            output_parts.append("")
            output_parts.append("💡 Recommendations:")
            for rec in unique_recs[:5]:
                output_parts.append(f"   • {rec[:65]}")

        output_parts.append("═" * 55)

        return {
            "continue": True,
            "output": "\n".join(output_parts)
        }

    except Exception as e:
        return {
            "continue": True,
            "output": f"⚠️ SOQL validation error: {e}"
        }


def validate_soql_static(content: str) -> dict:
    """
    Perform static validation on SOQL content.

    Args:
        content: SOQL query string

    Returns:
        dict with validation flags and issues
    """
    import re

    result = {
        'is_valid': True,
        'has_where_clause': False,
        'has_limit': False,
        'has_order_by': False,
        'has_hardcoded_ids': False,
        'uses_indexed_fields': False,
        'issues': [],
        'recommendations': []
    }

    # Remove comments
    clean = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
    clean = re.sub(r'//.*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'/\*[\s\S]*?\*/', '', clean)

    # Check for WHERE clause
    result['has_where_clause'] = bool(re.search(r'\bWHERE\b', clean, re.IGNORECASE))

    # Check for LIMIT
    result['has_limit'] = bool(re.search(r'\bLIMIT\s+\d+', clean, re.IGNORECASE))

    # Check for ORDER BY
    result['has_order_by'] = bool(re.search(r'\bORDER\s+BY\b', clean, re.IGNORECASE))

    # Check for hardcoded IDs (15 or 18 char alphanumeric in quotes)
    result['has_hardcoded_ids'] = bool(
        re.search(r"'[a-zA-Z0-9]{15}'", clean) or
        re.search(r"'[a-zA-Z0-9]{18}'", clean)
    )

    # Check for indexed fields in WHERE
    indexed_fields = ['Id', 'Name', 'OwnerId', 'CreatedDate', 'LastModifiedDate', 'RecordTypeId']
    where_match = re.search(r'\bWHERE\b(.*?)(?:\bORDER\b|\bGROUP\b|\bLIMIT\b|$)', clean, re.IGNORECASE | re.DOTALL)
    if where_match:
        where_clause = where_match.group(1)
        for field in indexed_fields:
            if re.search(rf'\b{field}\b', where_clause, re.IGNORECASE):
                result['uses_indexed_fields'] = True
                break

    # Syntax validation
    # Check for SELECT without FROM
    if re.search(r'\bSELECT\b', clean, re.IGNORECASE):
        if not re.search(r'\bFROM\b', clean, re.IGNORECASE):
            result['issues'].append({
                'severity': 'HIGH',
                'message': 'SELECT statement missing FROM clause'
            })
            result['is_valid'] = False

    # Check for SELECT *
    if re.search(r'\bSELECT\s+\*', clean, re.IGNORECASE):
        result['issues'].append({
            'severity': 'HIGH',
            'message': 'SELECT * is not valid in SOQL - specify field names'
        })
        result['is_valid'] = False

    # Check for == instead of =
    if re.search(r'==', clean):
        result['issues'].append({
            'severity': 'HIGH',
            'message': 'Invalid operator "==" - use "=" in SOQL'
        })

    # Check for unbalanced parentheses
    if clean.count('(') != clean.count(')'):
        result['issues'].append({
            'severity': 'HIGH',
            'message': 'Unbalanced parentheses'
        })

    # Add recommendations
    if not result['has_where_clause']:
        result['recommendations'].append('Add WHERE clause for better query selectivity')

    if not result['has_limit']:
        result['recommendations'].append('Add LIMIT clause to prevent large result sets')

    if result['has_hardcoded_ids']:
        result['recommendations'].append('Avoid hardcoded IDs - use bind variables instead')

    if result['has_where_clause'] and not result['uses_indexed_fields']:
        result['recommendations'].append('Add an indexed field (Id, Name, CreatedDate) to WHERE for better performance')

    return result


def main():
    """
    Main hook entry point.

    Reads hook input from stdin, validates SOQL files.
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

        # Only validate .soql files
        result = {"continue": True}

        if file_path.lower().endswith(".soql"):
            result = validate_soql_file(file_path)

        # Output result
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
