#!/usr/bin/env python3
"""
SOQL Validator Module
=====================

Validates SOQL query syntax and patterns.
Used by the main validation module for query-specific checks.
"""

import re
from typing import Dict, List, Any, Optional

class SOQLValidator:
    """Validates SOQL queries for best practices."""

    # Common SOQL keywords
    KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE',
        'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT', 'OFFSET',
        'ASC', 'DESC', 'NULLS FIRST', 'NULLS LAST',
        'WITH', 'TYPEOF', 'WHEN', 'THEN', 'ELSE', 'END',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COUNT_DISTINCT',
        'CALENDAR_MONTH', 'CALENDAR_YEAR', 'DAY_IN_WEEK', 'WEEK_IN_YEAR',
        'TODAY', 'YESTERDAY', 'TOMORROW', 'THIS_WEEK', 'LAST_WEEK',
        'THIS_MONTH', 'LAST_MONTH', 'THIS_QUARTER', 'LAST_QUARTER',
        'THIS_YEAR', 'LAST_YEAR', 'NEXT_N_DAYS', 'LAST_N_DAYS'
    ]

    # Indexed standard fields for selectivity
    INDEXED_FIELDS = [
        'Id', 'Name', 'OwnerId', 'CreatedDate', 'LastModifiedDate',
        'SystemModstamp', 'RecordTypeId', 'IsDeleted'
    ]

    def __init__(self, content: str):
        self.content = content
        self.issues: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []

    def validate(self) -> Dict[str, Any]:
        """Validate the SOQL content and return results."""
        result = {
            'is_valid': True,
            'has_where_clause': False,
            'has_limit': False,
            'has_order_by': False,
            'has_hardcoded_ids': False,
            'uses_indexed_fields': False,
            'has_subquery': False,
            'has_relationship': False,
            'issues': [],
            'recommendations': []
        }

        # Clean content (remove comments)
        clean_content = self._remove_comments(self.content)

        # Check for WHERE clause
        result['has_where_clause'] = self._has_where_clause(clean_content)

        # Check for LIMIT
        result['has_limit'] = self._has_limit(clean_content)

        # Check for ORDER BY
        result['has_order_by'] = bool(re.search(r'\bORDER\s+BY\b', clean_content, re.IGNORECASE))

        # Check for hardcoded IDs
        result['has_hardcoded_ids'] = self._has_hardcoded_ids(clean_content)

        # Check for indexed fields in WHERE
        result['uses_indexed_fields'] = self._uses_indexed_fields(clean_content)

        # Check for subqueries
        result['has_subquery'] = self._has_subquery(clean_content)

        # Check for relationship queries
        result['has_relationship'] = self._has_relationship(clean_content)

        # Syntax validation
        syntax_issues = self._validate_syntax(clean_content)
        result['issues'].extend(syntax_issues)

        # Add recommendations
        if not result['has_where_clause']:
            result['recommendations'].append('Add WHERE clause for better query selectivity')

        if not result['has_limit']:
            result['recommendations'].append('Add LIMIT clause to prevent large result sets')

        if result['has_hardcoded_ids']:
            result['recommendations'].append('Avoid hardcoded IDs - use bind variables')

        result['is_valid'] = len([i for i in result['issues'] if i.get('severity') == 'error']) == 0

        self.issues = result['issues']
        self.recommendations = result['recommendations']

        return result

    def _remove_comments(self, content: str) -> str:
        """Remove SQL comments from content."""
        # Remove single-line comments
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        return content

    def _has_where_clause(self, content: str) -> bool:
        """Check if query has a WHERE clause."""
        return bool(re.search(r'\bWHERE\b', content, re.IGNORECASE))

    def _has_limit(self, content: str) -> bool:
        """Check if query has a LIMIT clause."""
        return bool(re.search(r'\bLIMIT\s+\d+', content, re.IGNORECASE))

    def _has_hardcoded_ids(self, content: str) -> bool:
        """Check for hardcoded Salesforce IDs."""
        # Salesforce IDs are 15 or 18 character alphanumeric
        # Starting with specific prefixes: 001 (Account), 003 (Contact), etc.
        id_pattern = r"'[a-zA-Z0-9]{15}'"  # 15-char ID
        id_pattern_18 = r"'[a-zA-Z0-9]{18}'"  # 18-char ID

        return bool(re.search(id_pattern, content) or re.search(id_pattern_18, content))

    def _uses_indexed_fields(self, content: str) -> bool:
        """Check if WHERE clause uses indexed fields."""
        # Extract WHERE clause
        where_match = re.search(r'\bWHERE\b(.*?)(?:\bORDER\b|\bGROUP\b|\bLIMIT\b|$)',
                                content, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return False

        where_clause = where_match.group(1)

        # Check for indexed fields
        for field in self.INDEXED_FIELDS:
            if re.search(rf'\b{field}\b', where_clause, re.IGNORECASE):
                return True

        return False

    def _has_subquery(self, content: str) -> bool:
        """Check if query has subqueries."""
        # Look for nested SELECT in parentheses
        return bool(re.search(r'\(\s*SELECT\b', content, re.IGNORECASE))

    def _has_relationship(self, content: str) -> bool:
        """Check if query uses relationship queries."""
        # Look for dot notation (child-to-parent) or __r suffix
        return bool(re.search(r'\w+\.\w+|__r\.', content))

    def _validate_syntax(self, content: str) -> List[Dict[str, Any]]:
        """Validate SOQL syntax and return issues."""
        issues = []

        # Check for SELECT without FROM
        if re.search(r'\bSELECT\b', content, re.IGNORECASE):
            if not re.search(r'\bFROM\b', content, re.IGNORECASE):
                issues.append({
                    'severity': 'error',
                    'message': 'SELECT statement missing FROM clause'
                })

        # Check for invalid operators
        if re.search(r'==', content):
            issues.append({
                'severity': 'error',
                'message': 'Invalid operator "==" - use "=" in SOQL'
            })

        if re.search(r'!=\s*null', content, re.IGNORECASE):
            pass  # Valid
        elif re.search(r'<>', content):
            issues.append({
                'severity': 'warning',
                'message': 'Consider using "!=" instead of "<>" for consistency'
            })

        # Check for SELECT *
        if re.search(r'\bSELECT\s+\*', content, re.IGNORECASE):
            issues.append({
                'severity': 'error',
                'message': 'SELECT * is not valid in SOQL - specify field names'
            })

        # Check for proper string quoting
        if re.search(r"=\s*\"[^\"]*\"", content):
            issues.append({
                'severity': 'warning',
                'message': 'Use single quotes for string literals in SOQL'
            })

        # Check for unbalanced parentheses
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens != close_parens:
            issues.append({
                'severity': 'error',
                'message': f'Unbalanced parentheses: {open_parens} open, {close_parens} close'
            })

        # Check for TYPEOF without END
        if re.search(r'\bTYPEOF\b', content, re.IGNORECASE):
            if not re.search(r'\bEND\b', content, re.IGNORECASE):
                issues.append({
                    'severity': 'error',
                    'message': 'TYPEOF expression missing END keyword'
                })

        # Check for reserved words as field names (common issues)
        reserved = ['SELECT', 'FROM', 'WHERE', 'ORDER', 'GROUP', 'LIMIT']
        for word in reserved:
            # Look for patterns like "SELECT SELECT" or "field, SELECT"
            if re.search(rf'\b{word}\s*,|\,\s*{word}\b', content, re.IGNORECASE):
                issues.append({
                    'severity': 'warning',
                    'message': f'Possible misuse of reserved word "{word}"'
                })

        return issues

    def get_query_complexity(self, content: str) -> Dict[str, int]:
        """Analyze query complexity metrics."""
        clean = self._remove_comments(content)

        return {
            'select_fields': len(re.findall(r'\bSELECT\b.*?\bFROM\b', clean, re.IGNORECASE | re.DOTALL)),
            'where_conditions': len(re.findall(r'\b(AND|OR)\b', clean, re.IGNORECASE)) + 1 if self._has_where_clause(clean) else 0,
            'subqueries': len(re.findall(r'\(\s*SELECT\b', clean, re.IGNORECASE)),
            'joins': len(re.findall(r'__r\.|\.Name|\.Id', clean)),
            'aggregates': len(re.findall(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', clean, re.IGNORECASE))
        }

    def suggest_optimizations(self, content: str) -> List[str]:
        """Suggest query optimizations."""
        suggestions = []
        clean = self._remove_comments(content)

        # Check for missing indexed field in WHERE
        if self._has_where_clause(clean) and not self._uses_indexed_fields(clean):
            suggestions.append('Add an indexed field (Id, Name, CreatedDate) to WHERE for better performance')

        # Check for ORDER BY without LIMIT
        if re.search(r'\bORDER\s+BY\b', clean, re.IGNORECASE):
            if not self._has_limit(clean):
                suggestions.append('Consider adding LIMIT when using ORDER BY')

        # Check for SELECT with many fields
        select_match = re.search(r'\bSELECT\b(.*?)\bFROM\b', clean, re.IGNORECASE | re.DOTALL)
        if select_match:
            fields = select_match.group(1)
            field_count = len([f.strip() for f in fields.split(',') if f.strip()])
            if field_count > 20:
                suggestions.append(f'Query selects {field_count} fields - consider selecting only needed fields')

        # Check for deeply nested subqueries
        subquery_depth = len(re.findall(r'\(\s*SELECT\b', clean, re.IGNORECASE))
        if subquery_depth > 2:
            suggestions.append('Consider simplifying query - deeply nested subqueries may impact performance')

        return suggestions


# Standalone execution for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python soql_validator.py <soql_file>')
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        content = f.read()

    validator = SOQLValidator(content)
    result = validator.validate()

    print('SOQL Validation Results:')
    print('=' * 40)
    for key, value in result.items():
        if key not in ['issues', 'recommendations']:
            print(f'{key}: {value}')

    if result['issues']:
        print('\nIssues:')
        for issue in result['issues']:
            print(f"  [{issue['severity']}] {issue['message']}")

    if result['recommendations']:
        print('\nRecommendations:')
        for rec in result['recommendations']:
            print(f'  - {rec}')
