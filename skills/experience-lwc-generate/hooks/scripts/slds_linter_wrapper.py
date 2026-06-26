#!/usr/bin/env python3
"""
Wrapper for official @salesforce-ux/slds-linter npm package.

Provides integration with SLDS Linter for:
- HTML template validation
- CSS styling hooks validation
- Automated linting with structured output

The SLDS Linter is optional - if not installed, validation gracefully
degrades to custom Python-based validators.

Installation:
    npm install -g @salesforce-ux/slds-linter
"""

import subprocess
import json
import os
from typing import Dict, List, Any, Optional


class SLDSLinterWrapper:
    """Wrapper for npm-based SLDS Linter."""

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the SLDS Linter wrapper.

        Args:
            project_root: Root directory for linting context (optional)
        """
        self.project_root = project_root or os.getcwd()
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """
        Check if slds-linter is installed and available.

        Returns:
            True if linter is available, False otherwise
        """
        if self._available is not None:
            return self._available

        try:
            result = subprocess.run(
                ['npx', '@salesforce-ux/slds-linter', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            self._available = False

        return self._available

    def lint_file(self, file_path: str) -> Dict[str, Any]:
        """
        Lint a single file using SLDS Linter.

        Args:
            file_path: Path to HTML or CSS file to lint

        Returns:
            dict with success status, violations list, and any errors
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'slds-linter not installed. Install with: npm i -g @salesforce-ux/slds-linter',
                'violations': []
            }

        try:
            # Run SLDS Linter with JSON output
            result = subprocess.run(
                [
                    'npx', '@salesforce-ux/slds-linter', 'lint',
                    file_path,
                    '--format', 'json'
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )

            violations = self._parse_output(result.stdout, result.stderr)

            return {
                'success': True,
                'violations': violations,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'slds-linter timed out after 30 seconds',
                'violations': []
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': 'npx not found - ensure Node.js is installed',
                'violations': []
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'violations': []
            }

    def lint_directory(self, dir_path: str, extensions: List[str] = None) -> Dict[str, Any]:
        """
        Lint all matching files in a directory.

        Args:
            dir_path: Directory path to lint
            extensions: File extensions to lint (default: ['.html', '.css'])

        Returns:
            dict with success status, file_results, and total violations
        """
        if extensions is None:
            extensions = ['.html', '.css']

        if not self.is_available():
            return {
                'success': False,
                'error': 'slds-linter not installed',
                'file_results': {},
                'total_violations': 0
            }

        file_results = {}
        total_violations = 0

        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    result = self.lint_file(file_path)
                    file_results[file_path] = result
                    total_violations += len(result.get('violations', []))

        return {
            'success': True,
            'file_results': file_results,
            'total_violations': total_violations
        }

    def _parse_output(self, stdout: str, stderr: str) -> List[Dict]:
        """
        Parse SLDS Linter JSON output into structured violations.

        Args:
            stdout: Standard output from linter
            stderr: Standard error from linter

        Returns:
            List of violation dictionaries
        """
        violations = []

        # Try to parse JSON output
        try:
            if stdout.strip():
                data = json.loads(stdout)

                # Handle ESLint-style JSON output
                if isinstance(data, list):
                    for file_result in data:
                        for message in file_result.get('messages', []):
                            violations.append({
                                'rule': message.get('ruleId', 'unknown'),
                                'message': message.get('message', ''),
                                'line': message.get('line', 0),
                                'column': message.get('column', 0),
                                'severity': self._map_severity(message.get('severity', 1)),
                                'source': 'slds-linter',
                                'file': file_result.get('filePath', '')
                            })

                # Handle single object output
                elif isinstance(data, dict):
                    for message in data.get('messages', []):
                        violations.append({
                            'rule': message.get('ruleId', 'unknown'),
                            'message': message.get('message', ''),
                            'line': message.get('line', 0),
                            'column': message.get('column', 0),
                            'severity': self._map_severity(message.get('severity', 1)),
                            'source': 'slds-linter'
                        })

        except json.JSONDecodeError:
            # If not valid JSON, try to extract violations from text output
            violations.extend(self._parse_text_output(stdout))
            violations.extend(self._parse_text_output(stderr))

        return violations

    def _parse_text_output(self, output: str) -> List[Dict]:
        """
        Parse plain text linter output for violations.

        Args:
            output: Text output from linter

        Returns:
            List of violation dictionaries
        """
        violations = []

        if not output:
            return violations

        # Common patterns for linter output
        # Example: "filename.html:10:5: error - message"
        import re
        pattern = r'(\S+):(\d+):(\d+):\s*(error|warning|info)\s*[-:]\s*(.+)'

        for line in output.splitlines():
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                violations.append({
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'column': int(match.group(3)),
                    'severity': match.group(4).upper(),
                    'message': match.group(5).strip(),
                    'rule': 'slds',
                    'source': 'slds-linter'
                })

        return violations

    def _map_severity(self, level: int) -> str:
        """
        Map ESLint severity levels to our labels.

        Args:
            level: ESLint severity (1=warning, 2=error)

        Returns:
            Severity label string
        """
        return {
            0: 'INFO',
            1: 'WARNING',
            2: 'HIGH'
        }.get(level, 'INFO')


def is_slds_linter_available() -> bool:
    """
    Convenience function to check if SLDS Linter is available.

    Returns:
        True if available, False otherwise
    """
    wrapper = SLDSLinterWrapper()
    return wrapper.is_available()


def lint_lwc_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to lint a single LWC file.

    Args:
        file_path: Path to file to lint

    Returns:
        Linting results dictionary
    """
    wrapper = SLDSLinterWrapper()
    return wrapper.lint_file(file_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python slds_linter_wrapper.py <file.html|file.css>")
        print("\nChecking SLDS Linter availability...")
        print(f"Available: {is_slds_linter_available()}")
        sys.exit(0)

    result = lint_lwc_file(sys.argv[1])
    print(json.dumps(result, indent=2))
