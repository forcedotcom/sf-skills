#!/usr/bin/env python3
"""
sf-data Validation Module
=========================

Validates data operation files against the 130-point scoring system:
- Query Efficiency (25 points)
- Bulk Safety (25 points)
- Data Integrity (20 points)
- Security & FLS (20 points)
- Test Patterns (15 points)
- Cleanup & Isolation (15 points)
- Documentation (10 points)
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class DataOperationValidator:
    """Validates data operation files."""

    # Scoring categories
    CATEGORIES = {
        'query_efficiency': {
            'name': 'Query Efficiency',
            'max': 25,
            'score': 25,
            'issues': []
        },
        'bulk_safety': {
            'name': 'Bulk Safety',
            'max': 25,
            'score': 25,
            'issues': []
        },
        'data_integrity': {
            'name': 'Data Integrity',
            'max': 20,
            'score': 20,
            'issues': []
        },
        'security_fls': {
            'name': 'Security & FLS',
            'max': 20,
            'score': 20,
            'issues': []
        },
        'test_patterns': {
            'name': 'Test Patterns',
            'max': 15,
            'score': 15,
            'issues': []
        },
        'cleanup_isolation': {
            'name': 'Cleanup & Isolation',
            'max': 15,
            'score': 15,
            'issues': []
        },
        'documentation': {
            'name': 'Documentation',
            'max': 10,
            'score': 10,
            'issues': []
        }
    }

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.content = ''
        self.file_type = ''
        self.issues: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []
        self.categories = self._init_categories()

    def _init_categories(self) -> Dict[str, Dict[str, Any]]:
        """Initialize fresh category scores."""
        import copy
        return copy.deepcopy(self.CATEGORIES)

    def validate(self) -> Optional[Dict[str, Any]]:
        """Run validation and return results."""
        if not self.file_path.exists():
            return None

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
        except Exception:
            return None

        # Determine file type
        self.file_type = self.file_path.suffix.lower()

        # Run type-specific validation
        if self.file_type == '.apex':
            self._validate_apex()
        elif self.file_type == '.soql':
            self._validate_soql()
        elif self.file_type == '.csv':
            self._validate_csv()
        elif self.file_type == '.json':
            self._validate_json()
        else:
            return None

        # Calculate total score
        total_score = sum(cat['score'] for cat in self.categories.values())
        max_score = sum(cat['max'] for cat in self.categories.values())

        return {
            'score': total_score,
            'max_score': max_score,
            'categories': {cat['name']: {'score': cat['score'], 'max': cat['max']}
                          for cat in self.categories.values()},
            'issues': self.issues,
            'recommendations': self.recommendations
        }

    def _validate_apex(self):
        """Validate Apex data operation file."""
        content = self.content

        # Query Efficiency (25 points)
        self._check_query_efficiency(content)

        # Bulk Safety (25 points)
        self._check_bulk_safety(content)

        # Data Integrity (20 points)
        self._check_data_integrity(content)

        # Security & FLS (20 points)
        self._check_security(content)

        # Test Patterns (15 points)
        self._check_test_patterns(content)

        # Cleanup & Isolation (15 points)
        self._check_cleanup(content)

        # Documentation (10 points)
        self._check_documentation(content)

    def _validate_soql(self):
        """Validate SOQL query file."""
        content = self.content

        # Import SOQL validator
        try:
            from soql_validator import SOQLValidator
            soql_validator = SOQLValidator(content)
            soql_result = soql_validator.validate()

            # Apply SOQL-specific scoring
            if soql_result.get('has_where_clause', False):
                pass  # Good
            else:
                self._deduct('query_efficiency', 5, 'Missing WHERE clause')

            if soql_result.get('has_limit', False):
                pass  # Good
            else:
                self._deduct('query_efficiency', 3, 'Missing LIMIT clause')

            if soql_result.get('has_hardcoded_ids', False):
                self._deduct('query_efficiency', 5, 'Hardcoded record IDs found')

        except ImportError:
            # Basic SOQL validation
            if 'WHERE' not in content.upper():
                self._deduct('query_efficiency', 5, 'Missing WHERE clause')
            if 'LIMIT' not in content.upper():
                self._deduct('query_efficiency', 3, 'Missing LIMIT clause')

        # Documentation check for SOQL
        if not content.strip().startswith('--'):
            self._deduct('documentation', 5, 'Missing SOQL documentation/comments')

    def _validate_csv(self):
        """Validate CSV import file."""
        lines = self.content.strip().split('\n')

        if len(lines) < 2:
            self._deduct('data_integrity', 10, 'CSV file has no data rows')
            return

        # Check for header row
        header = lines[0]
        if not header or ',' not in header:
            self._deduct('data_integrity', 5, 'CSV missing proper header row')

        # Check for consistent column count
        expected_cols = len(header.split(','))
        for i, line in enumerate(lines[1:], 2):
            if line.strip() and len(line.split(',')) != expected_cols:
                self._deduct('data_integrity', 2, f'Inconsistent column count on line {i}')
                break

        # Check for potential PII patterns
        self._check_csv_security(self.content)

    def _validate_json(self):
        """Validate JSON tree import file."""
        import json as json_lib

        try:
            data = json_lib.loads(self.content)
        except json_lib.JSONDecodeError as e:
            self._deduct('data_integrity', 20, f'Invalid JSON: {str(e)}')
            return

        # Check for proper sObject tree format
        if 'records' not in data:
            self._deduct('data_integrity', 10, 'Missing "records" array')
            return

        records = data.get('records', [])

        for i, record in enumerate(records):
            if 'attributes' not in record:
                self._deduct('data_integrity', 5, f'Record {i+1} missing "attributes"')
            else:
                attrs = record['attributes']
                if 'type' not in attrs:
                    self._deduct('data_integrity', 3, f'Record {i+1} missing object type')
                if 'referenceId' not in attrs:
                    self._deduct('data_integrity', 2, f'Record {i+1} missing referenceId')

    def _check_query_efficiency(self, content: str):
        """Check for query efficiency issues."""
        # Check for queries in loops
        if re.search(r'for\s*\([^)]*\)\s*\{[^}]*\[SELECT', content, re.IGNORECASE | re.DOTALL):
            self._deduct('query_efficiency', 10, 'SOQL query inside for loop (N+1 pattern)')

        # Check for hardcoded IDs
        if re.search(r"'[a-zA-Z0-9]{15,18}'", content):
            self._deduct('query_efficiency', 5, 'Hardcoded Salesforce ID found')

        # Check for SELECT * equivalent (all fields)
        if re.search(r'SELECT\s+\*', content, re.IGNORECASE):
            self._deduct('query_efficiency', 5, 'SELECT * is not valid in SOQL')

    def _check_bulk_safety(self, content: str):
        """Check for bulk safety issues."""
        # Check for DML in loops
        dml_in_loop = re.search(
            r'for\s*\([^)]*\)\s*\{[^}]*(insert|update|delete|upsert)\s+',
            content, re.IGNORECASE | re.DOTALL
        )
        if dml_in_loop:
            self._deduct('bulk_safety', 10, 'DML operation inside for loop')

        # Check for single-record operations when bulk would be better
        single_record_pattern = re.search(
            r'(insert|update|delete)\s+\w+\s*;(?!\s*//\s*single)',
            content, re.IGNORECASE
        )
        # This is a soft check - single records are sometimes intentional

        # Check for list-based DML (good pattern)
        if re.search(r'(insert|update|delete)\s+\w+List', content, re.IGNORECASE):
            pass  # Good - using list-based DML
        elif re.search(r'(insert|update|delete)\s+new\s+List<', content, re.IGNORECASE):
            pass  # Good - using list

    def _check_data_integrity(self, content: str):
        """Check for data integrity issues."""
        # Check for required field handling
        if 'required' in content.lower() or 'mandatory' in content.lower():
            pass  # Awareness of required fields

        # Check for null checks
        if re.search(r'!=\s*null|!= null', content):
            pass  # Good - null checking

    def _check_security(self, content: str):
        """Check for security issues."""
        # Check for PII patterns
        pii_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN pattern detected'),
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'Credit card pattern detected'),
            (r'\b[A-Za-z0-9._%+-]+@(gmail|yahoo|hotmail|outlook)\.(com|net|org)\b',
             'Personal email domain in test data')
        ]

        for pattern, message in pii_patterns:
            if re.search(pattern, content):
                self._deduct('security_fls', 10, message)

        # Check for WITH USER_MODE usage (good practice)
        if 'WITH USER_MODE' in content.upper():
            pass  # Good - respecting FLS

    def _check_test_patterns(self, content: str):
        """Check for good test data patterns."""
        # Check for bulk record creation (200+)
        bulk_patterns = [
            r'(\d{3,})\s*[;,)]',  # Numbers 100+
            r'count\s*[=:]\s*(\d{3,})',
            r'recordCount\s*[=:]\s*(\d{3,})'
        ]

        has_bulk = False
        for pattern in bulk_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    num = int(match.group(1))
                    if num >= 200:
                        has_bulk = True
                except ValueError:
                    pass

        # Check for edge case handling
        edge_cases = ['null', 'empty', 'boundary', 'special character', 'unicode']
        has_edge_cases = any(ec in content.lower() for ec in edge_cases)

        if not has_bulk and 'bulk' not in self.file_path.stem.lower():
            self._deduct('test_patterns', 5, 'Consider testing with 200+ records for bulkification')

    def _check_cleanup(self, content: str):
        """Check for cleanup and isolation patterns."""
        # Check for cleanup provisions
        cleanup_patterns = ['cleanup', 'delete', 'rollback', 'Savepoint', 'Database.rollback']
        has_cleanup = any(pattern.lower() in content.lower() for pattern in cleanup_patterns)

        if not has_cleanup:
            self._deduct('cleanup_isolation', 5, 'No cleanup mechanism found')
            self.recommendations.append('Add cleanup script or savepoint for test isolation')

        # Check for ID tracking
        if re.search(r'Set<Id>|List<Id>|createdIds|recordIds', content):
            pass  # Good - tracking created IDs

    def _check_documentation(self, content: str):
        """Check for documentation."""
        # Check for file header comment
        if not (content.strip().startswith('/*') or
                content.strip().startswith('//') or
                content.strip().startswith('/**')):
            self._deduct('documentation', 3, 'Missing file header documentation')

        # Check for method documentation
        if re.search(r'/\*\*[\s\S]*?\*/', content):
            pass  # Has JSDoc-style comments
        elif re.search(r'//.*description|//.*purpose|//.*usage', content, re.IGNORECASE):
            pass  # Has inline documentation
        else:
            self._deduct('documentation', 2, 'Consider adding method/section documentation')

    def _check_csv_security(self, content: str):
        """Check CSV content for security issues."""
        # Check for PII patterns in CSV
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # SSN pattern
            if re.search(r'\b\d{3}-\d{2}-\d{4}\b', line):
                self._deduct('security_fls', 10, f'SSN pattern on line {i}')
                break
            # Credit card pattern
            if re.search(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', line):
                self._deduct('security_fls', 10, f'Credit card pattern on line {i}')
                break

    def _deduct(self, category: str, points: int, message: str):
        """Deduct points from a category and record the issue."""
        if category in self.categories:
            current = self.categories[category]['score']
            self.categories[category]['score'] = max(0, current - points)
            self.categories[category]['issues'].append(message)

        self.issues.append({
            'category': self.categories.get(category, {}).get('name', category),
            'severity': 'error' if points >= 10 else 'warning',
            'message': message,
            'points': points
        })
