#!/usr/bin/env python3
"""
SLDS 2 Validator for Lightning Web Components.

Provides a 165-point scoring system across 9 categories:
1. SLDS Class Usage (25 pts)   - Valid SLDS 2 utility classes
2. Accessibility (25 pts)       - aria-*, role, alt-text
3. Dark Mode (25 pts)           - No hardcoded colors, uses CSS variables
4. SLDS Migration (20 pts)      - No deprecated SLDS 1 patterns
5. Styling Hooks (20 pts)       - Proper --slds-g-* variable usage
6. Component Structure (15 pts) - Uses lightning-* base components
7. Performance (10 pts)         - Efficient selectors, no !important
8. GraphQL Patterns (15 pts)    - Proper wire adapter usage, cursor pagination
9. Focus Management (10 pts)    - ESC handlers, focus trap for modals
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Script directory for loading data files
SCRIPT_DIR = Path(__file__).parent


class SLDSValidator:
    """SLDS 2 validation engine for LWC files."""

    # Maximum scores per category (165 total)
    max_scores = {
        'slds_class_usage': 25,
        'accessibility': 25,
        'dark_mode': 25,
        'slds_migration': 20,
        'styling_hooks': 20,
        'component_structure': 15,
        'performance': 10,
        'graphql_patterns': 15,
        'focus_management': 10,
    }

    def __init__(self, file_path: str):
        """
        Initialize validator with file path.

        Args:
            file_path: Path to .html, .css, or .js file
        """
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.ext = Path(file_path).suffix.lower()
        self.content = ""
        self.lines = []

        # Load file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                self.lines = self.content.splitlines()
        except Exception:
            pass

        # Load validation data
        self._load_data()

    def _load_data(self):
        """Load JSON data files for validation rules."""
        data_dir = SCRIPT_DIR / 'slds_data'

        # Valid SLDS classes
        self.valid_slds_classes = set()
        try:
            with open(data_dir / 'valid_slds_classes.json', 'r') as f:
                data = json.load(f)
                for category_classes in data.values():
                    if isinstance(category_classes, list):
                        self.valid_slds_classes.update(category_classes)
        except Exception:
            pass

        # Deprecated patterns
        self.deprecated_patterns = {}
        try:
            with open(data_dir / 'deprecated_patterns.json', 'r') as f:
                self.deprecated_patterns = json.load(f)
        except Exception:
            pass

        # Valid styling hooks
        self.valid_hooks = set()
        try:
            with open(data_dir / 'styling_hooks.json', 'r') as f:
                data = json.load(f)
                for category_hooks in data.values():
                    if isinstance(category_hooks, list):
                        self.valid_hooks.update(category_hooks)
        except Exception:
            pass

    def validate(self) -> Dict[str, Any]:
        """
        Run all validations and return results.

        Returns:
            dict with score, max_score, scores by category, issues, and rating
        """
        scores = {cat: max_score for cat, max_score in self.max_scores.items()}
        issues = []

        if not self.content:
            return {
                'score': 0,
                'max_score': sum(self.max_scores.values()),
                'scores': scores,
                'issues': [{'severity': 'CRITICAL', 'message': 'Could not read file'}],
                'rating': 'Error'
            }

        # Run validators based on file type
        if self.ext == '.html':
            self._validate_html(scores, issues)
        elif self.ext == '.css':
            self._validate_css(scores, issues)
        elif self.ext == '.js':
            self._validate_js(scores, issues)

        # Calculate total score
        total_score = sum(scores.values())
        max_total = sum(self.max_scores.values())

        return {
            'score': total_score,
            'max_score': max_total,
            'scores': scores,
            'issues': issues,
            'rating': self._get_rating(total_score, max_total)
        }

    def _get_rating(self, score: int, max_score: int) -> str:
        """Get rating string from score."""
        pct = (score / max_score * 100) if max_score > 0 else 0
        if pct >= 90:
            return "Production-ready SLDS 2"
        elif pct >= 80:
            return "Good"
        elif pct >= 70:
            return "Functional"
        elif pct >= 60:
            return "Needs work"
        else:
            return "Critical issues"

    # ═══════════════════════════════════════════════════════════════════════
    # HTML VALIDATION
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_html(self, scores: Dict[str, int], issues: List[Dict]):
        """Validate HTML template file."""
        self._check_slds_classes(scores, issues)
        self._check_accessibility(scores, issues)
        self._check_component_structure(scores, issues)

    def _check_slds_classes(self, scores: Dict[str, int], issues: List[Dict]):
        """Check SLDS class usage in HTML."""
        # Find all class attributes
        class_pattern = r'class\s*=\s*["\']([^"\']+)["\']'

        for i, line in enumerate(self.lines, 1):
            matches = re.findall(class_pattern, line)
            for class_attr in matches:
                classes = class_attr.split()
                for cls in classes:
                    if cls.startswith('slds-'):
                        # Check if it's a valid SLDS class
                        if self.valid_slds_classes and cls not in self.valid_slds_classes:
                            # Allow pattern-based classes we might not have in our list
                            if not self._is_valid_slds_pattern(cls):
                                scores['slds_class_usage'] = max(0, scores['slds_class_usage'] - 2)
                                issues.append({
                                    'severity': 'WARNING',
                                    'category': 'slds_class_usage',
                                    'message': f"Unknown SLDS class: {cls}",
                                    'line': i,
                                    'fix': f"Verify '{cls}' is a valid SLDS 2 class"
                                })

    def _is_valid_slds_pattern(self, cls: str) -> bool:
        """Check if class matches valid SLDS naming patterns."""
        patterns = [
            r'^slds-p-(around|horizontal|vertical|left|right|top|bottom)_',
            r'^slds-m-(around|horizontal|vertical|left|right|top|bottom)_',
            r'^slds-size_\d+-of-\d+$',
            # Responsive sizing: slds-small-size_, slds-medium-size_, slds-large-size_
            r'^slds-(small|medium|large|max-small|max-medium|max-large)-size_\d+-of-\d+$',
            r'^slds-text-(heading|body|color|align)_',
            r'^slds-grid(_|$)',
            r'^slds-col(_|$)',
            r'^slds-button(_|$)',
            r'^slds-input(_|$)',
            r'^slds-form(_|$)',
            r'^slds-card(_|$)',
            r'^slds-modal(_|$)',
            r'^slds-notify(_|$)',
            r'^slds-illustration(_|$)',
            r'^slds-table(_|$)',
            r'^slds-box(_|$)',
            r'^slds-badge(_|$)',
            r'^slds-spinner(_|$)',
            r'^slds-alert(_|$)',
            # Utility patterns
            r'^slds-has-',
            r'^slds-no-',
            r'^slds-var-',
            r'^slds-is-',
            r'^slds-theme_',
            r'^slds-icon(_|$)',
            r'^slds-media(_|$)',
            r'^slds-list(_|$)',
            r'^slds-tile(_|$)',
            r'^slds-popover(_|$)',
            r'^slds-dropdown(_|$)',
            r'^slds-tabs_',
            r'^slds-path(_|$)',
            r'^slds-progress(_|$)',
        ]
        return any(re.match(p, cls) for p in patterns)

    def _check_accessibility(self, scores: Dict[str, int], issues: List[Dict]):
        """Check accessibility requirements in HTML."""
        content = self.content

        # Check lightning-icon without alternative-text
        icon_pattern = r'<lightning-icon[^>]*>'
        for i, line in enumerate(self.lines, 1):
            for match in re.finditer(icon_pattern, line):
                icon_tag = match.group(0)
                if 'alternative-text' not in icon_tag:
                    scores['accessibility'] = max(0, scores['accessibility'] - 3)
                    issues.append({
                        'severity': 'WARNING',
                        'category': 'accessibility',
                        'message': 'lightning-icon missing alternative-text attribute',
                        'line': i,
                        'fix': 'Add alternative-text="description" for screen readers'
                    })

        # Check lightning-button-icon without label
        button_icon_pattern = r'<lightning-button-icon[^>]*>'
        for i, line in enumerate(self.lines, 1):
            for match in re.finditer(button_icon_pattern, line):
                tag = match.group(0)
                if 'aria-label' not in tag and 'alternative-text' not in tag:
                    scores['accessibility'] = max(0, scores['accessibility'] - 3)
                    issues.append({
                        'severity': 'WARNING',
                        'category': 'accessibility',
                        'message': 'lightning-button-icon missing aria-label or alternative-text',
                        'line': i,
                        'fix': 'Add aria-label="action description" for accessibility'
                    })

        # Check for slds-assistive-text usage (good practice)
        if 'slds-assistive-text' not in content and 'aria-live' not in content:
            # Only deduct if there's dynamic content indicators
            if '{' in content and '}' in content:
                scores['accessibility'] = max(0, scores['accessibility'] - 2)
                issues.append({
                    'severity': 'INFO',
                    'category': 'accessibility',
                    'message': 'Consider adding aria-live for dynamic content updates',
                    'line': 0,
                    'fix': 'Use aria-live="polite" for status updates'
                })

    def _check_component_structure(self, scores: Dict[str, int], issues: List[Dict]):
        """Check component structure for SLDS compliance."""
        # Check for lightning-* base components (good)
        lightning_components = re.findall(r'<lightning-[a-z-]+', self.content)
        if not lightning_components:
            scores['component_structure'] = max(0, scores['component_structure'] - 5)
            issues.append({
                'severity': 'INFO',
                'category': 'component_structure',
                'message': 'No lightning-* base components found',
                'line': 0,
                'fix': 'Consider using lightning-* components for SLDS consistency'
            })

    # ═══════════════════════════════════════════════════════════════════════
    # CSS VALIDATION
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_css(self, scores: Dict[str, int], issues: List[Dict]):
        """Validate CSS file."""
        self._check_dark_mode(scores, issues)
        self._check_styling_hooks(scores, issues)
        self._check_slds_migration(scores, issues)
        self._check_css_performance(scores, issues)

    def _check_dark_mode(self, scores: Dict[str, int], issues: List[Dict]):
        """Check for dark mode compatibility (no hardcoded colors)."""
        # Patterns for hardcoded colors
        color_patterns = [
            (r'#[0-9A-Fa-f]{3,8}(?![0-9A-Fa-f])', 'hex color'),
            (r'rgb\s*\([^)]+\)', 'RGB color'),
            (r'rgba\s*\([^)]+\)', 'RGBA color'),
            (r'hsl\s*\([^)]+\)', 'HSL color'),
            (r'hsla\s*\([^)]+\)', 'HSLA color'),
        ]

        for i, line in enumerate(self.lines, 1):
            # Skip comments
            if line.strip().startswith('/*') or line.strip().startswith('//'):
                continue

            # Skip if it's inside a var() - that's allowed
            line_without_vars = re.sub(r'var\s*\([^)]+\)', '', line)

            for pattern, color_type in color_patterns:
                matches = re.findall(pattern, line_without_vars)
                for match in matches:
                    # Skip transparent and common exceptions
                    if match.lower() in ['#fff', '#ffffff', '#000', '#000000']:
                        scores['dark_mode'] = max(0, scores['dark_mode'] - 5)
                        issues.append({
                            'severity': 'HIGH',
                            'category': 'dark_mode',
                            'message': f'Hardcoded {color_type} ({match}) breaks dark mode',
                            'line': i,
                            'fix': f'Use var(--slds-g-color-*) instead of {match}'
                        })
                    elif match.lower() not in ['transparent', 'inherit', 'currentcolor']:
                        scores['dark_mode'] = max(0, scores['dark_mode'] - 3)
                        issues.append({
                            'severity': 'MODERATE',
                            'category': 'dark_mode',
                            'message': f'Hardcoded {color_type} ({match}) may break dark mode',
                            'line': i,
                            'fix': f'Consider using var(--slds-g-color-*) instead'
                        })

    def _check_styling_hooks(self, scores: Dict[str, int], issues: List[Dict]):
        """Check for proper SLDS 2 styling hooks usage."""
        # Find all CSS variable references
        var_pattern = r'var\s*\(\s*(--[a-zA-Z0-9-]+)'

        for i, line in enumerate(self.lines, 1):
            matches = re.findall(var_pattern, line)
            for var_name in matches:
                # Check if it's an SLDS variable
                if var_name.startswith('--slds-'):
                    # SLDS 2 global hooks use --slds-g-
                    if var_name.startswith('--slds-c-'):
                        scores['styling_hooks'] = max(0, scores['styling_hooks'] - 3)
                        issues.append({
                            'severity': 'WARNING',
                            'category': 'styling_hooks',
                            'message': f'Component hooks ({var_name}) not yet supported in SLDS 2',
                            'line': i,
                            'fix': 'Use --slds-g-* global hooks or wait for SLDS 2 component hook support'
                        })
                    elif not var_name.startswith('--slds-g-'):
                        scores['styling_hooks'] = max(0, scores['styling_hooks'] - 2)
                        issues.append({
                            'severity': 'INFO',
                            'category': 'styling_hooks',
                            'message': f'Non-standard SLDS variable: {var_name}',
                            'line': i,
                            'fix': 'Use --slds-g-* for SLDS 2 compatibility'
                        })

    def _check_slds_migration(self, scores: Dict[str, int], issues: List[Dict]):
        """Check for deprecated SLDS 1 patterns."""
        deprecated_tokens = self.deprecated_patterns.get('tokens', {})
        deprecated_classes = self.deprecated_patterns.get('classes', {})

        for i, line in enumerate(self.lines, 1):
            # Check deprecated Sass tokens
            for old_token, replacement in deprecated_tokens.items():
                if old_token in line:
                    scores['slds_migration'] = max(0, scores['slds_migration'] - 5)
                    issues.append({
                        'severity': 'HIGH',
                        'category': 'slds_migration',
                        'message': f'Deprecated SLDS 1 token: {old_token}',
                        'line': i,
                        'fix': f'Replace with {replacement}'
                    })

            # Check --lwc- prefix (old format)
            if '--lwc-' in line:
                scores['slds_migration'] = max(0, scores['slds_migration'] - 3)
                issues.append({
                    'severity': 'MODERATE',
                    'category': 'slds_migration',
                    'message': 'Old --lwc-* token format detected',
                    'line': i,
                    'fix': 'Migrate to --slds-g-* styling hooks'
                })

    def _check_css_performance(self, scores: Dict[str, int], issues: List[Dict]):
        """Check for CSS performance issues."""
        for i, line in enumerate(self.lines, 1):
            # Check for !important
            if '!important' in line:
                scores['performance'] = max(0, scores['performance'] - 3)
                issues.append({
                    'severity': 'WARNING',
                    'category': 'performance',
                    'message': '!important override detected',
                    'line': i,
                    'fix': 'Avoid !important; use more specific selectors or SLDS utilities'
                })

        # Check for overly deep selectors (> 3 levels)
        selector_pattern = r'^[^{]+{'
        for i, line in enumerate(self.lines, 1):
            if '{' in line:
                # Count selector depth
                selector = line.split('{')[0]
                depth = len(re.findall(r'\s+', selector.strip()))
                if depth > 3:
                    scores['performance'] = max(0, scores['performance'] - 2)
                    issues.append({
                        'severity': 'INFO',
                        'category': 'performance',
                        'message': 'Deep CSS selector detected (>3 levels)',
                        'line': i,
                        'fix': 'Simplify selector for better performance'
                    })

    # ═══════════════════════════════════════════════════════════════════════
    # JAVASCRIPT VALIDATION
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_js(self, scores: Dict[str, int], issues: List[Dict]):
        """Validate JavaScript controller file."""
        # JS files have limited SLDS-specific validation
        # Focus on inline styles, classList manipulation, GraphQL, and focus management

        for i, line in enumerate(self.lines, 1):
            # Check for inline style manipulation with colors
            if '.style.' in line and any(c in line.lower() for c in ['color', 'background', 'border']):
                if re.search(r'#[0-9A-Fa-f]{3,8}|rgb\s*\(', line):
                    scores['dark_mode'] = max(0, scores['dark_mode'] - 5)
                    issues.append({
                        'severity': 'HIGH',
                        'category': 'dark_mode',
                        'message': 'Inline style with hardcoded color detected',
                        'line': i,
                        'fix': 'Use CSS classes or CSS variables instead of inline styles'
                    })

            # Check for classList with invalid SLDS classes
            if 'classList' in line and 'slds-' in line:
                # Extract class names from string literals
                classes = re.findall(r'["\']([slds-][^"\']+)["\']', line)
                for cls in classes:
                    if cls.startswith('slds-') and self.valid_slds_classes and cls not in self.valid_slds_classes:
                        if not self._is_valid_slds_pattern(cls):
                            scores['slds_class_usage'] = max(0, scores['slds_class_usage'] - 2)
                            issues.append({
                                'severity': 'WARNING',
                                'category': 'slds_class_usage',
                                'message': f"Unknown SLDS class in JS: {cls}",
                                'line': i,
                                'fix': f"Verify '{cls}' is a valid SLDS 2 class"
                            })

        # Check GraphQL patterns
        self._check_graphql_patterns(scores, issues)

        # Check focus management patterns
        self._check_focus_management(scores, issues)

    def _check_graphql_patterns(self, scores: Dict[str, int], issues: List[Dict]):
        """Check for proper GraphQL wire adapter usage."""
        content = self.content

        # Check if using GraphQL wire adapter
        has_graphql_import = 'lightning/uiGraphQLApi' in content
        has_gql_import = "import { gql" in content or "import { graphql" in content

        if has_graphql_import or has_gql_import:
            # Verify proper patterns

            # Check for storing wire result for refresh
            if '@wire(graphql' in content or '@wire(gql' in content:
                # Check if result is stored for refreshGraphQL
                if 'refreshGraphQL' in content:
                    # Good pattern - using refreshGraphQL
                    pass
                else:
                    # Check if the wire is used with a function that stores result
                    wire_pattern = r'@wire\s*\(\s*graphql[^)]*\)\s*(\w+)'
                    matches = re.findall(wire_pattern, content)
                    for match in matches:
                        # If it's a function pattern, check if it stores result
                        if f'wired{match[0].upper()}' not in content and 'Result' not in match:
                            scores['graphql_patterns'] = max(0, scores['graphql_patterns'] - 5)
                            issues.append({
                                'severity': 'INFO',
                                'category': 'graphql_patterns',
                                'message': 'GraphQL wire result not stored for potential refresh',
                                'line': 0,
                                'fix': 'Store wire result in a property for use with refreshGraphQL()'
                            })

            # Check for cursor-based pagination pattern
            if 'first:' in content and 'after:' not in content and 'pageInfo' not in content:
                scores['graphql_patterns'] = max(0, scores['graphql_patterns'] - 3)
                issues.append({
                    'severity': 'INFO',
                    'category': 'graphql_patterns',
                    'message': 'GraphQL query uses first: but missing pagination',
                    'line': 0,
                    'fix': 'Add pageInfo { hasNextPage endCursor } for cursor pagination'
                })

            # Check for proper error handling
            if 'graphQLErrors' not in content and '.errors' not in content:
                scores['graphql_patterns'] = max(0, scores['graphql_patterns'] - 2)
                issues.append({
                    'severity': 'INFO',
                    'category': 'graphql_patterns',
                    'message': 'GraphQL error handling not detected',
                    'line': 0,
                    'fix': 'Handle graphQLErrors in wire result or catch block'
                })

    def _check_focus_management(self, scores: Dict[str, int], issues: List[Dict]):
        """Check for proper focus management patterns in modals/dialogs."""
        content = self.content

        # Check if this appears to be a modal component
        is_modal = any(indicator in content.lower() for indicator in [
            'modal', 'dialog', 'overlay', 'popup', 'backdrop'
        ])

        if is_modal:
            # Check for ESC key handler
            has_esc_handler = any(pattern in content for pattern in [
                "'Escape'", '"Escape"', 'key === 27', 'keyCode === 27',
                "code === 'Escape'", 'code === "Escape"'
            ])

            if not has_esc_handler:
                scores['focus_management'] = max(0, scores['focus_management'] - 3)
                issues.append({
                    'severity': 'WARNING',
                    'category': 'focus_management',
                    'message': 'Modal component missing ESC key handler',
                    'line': 0,
                    'fix': "Add window.addEventListener('keyup', handler) to close on Escape"
                })

            # Check for focus trap pattern
            has_focus_trap = any(pattern in content for pattern in [
                'focusable', 'tabbable', '.focus()', 'tabindex',
                'querySelectorAll', 'firstElementChild'
            ])

            if not has_focus_trap:
                scores['focus_management'] = max(0, scores['focus_management'] - 3)
                issues.append({
                    'severity': 'INFO',
                    'category': 'focus_management',
                    'message': 'Modal may need focus trap for accessibility',
                    'line': 0,
                    'fix': 'Implement focus trap to keep focus within modal'
                })

            # Check for cleanup in disconnectedCallback
            if 'addEventListener' in content:
                if 'removeEventListener' not in content and 'disconnectedCallback' not in content:
                    scores['focus_management'] = max(0, scores['focus_management'] - 4)
                    issues.append({
                        'severity': 'HIGH',
                        'category': 'focus_management',
                        'message': 'Event listener added but not cleaned up',
                        'line': 0,
                        'fix': 'Add disconnectedCallback to remove event listeners'
                    })


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python validate_slds.py <file.html|file.css|file.js>")
        sys.exit(1)

    validator = SLDSValidator(sys.argv[1])
    results = validator.validate()
    print(json.dumps(results, indent=2))
