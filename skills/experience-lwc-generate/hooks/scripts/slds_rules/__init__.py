"""
SLDS 2 Validation Rules Package.

This package contains modular validation rules for SLDS 2 compliance:
- class_validator: SLDS utility class validation
- a11y_validator: Accessibility checks
- darkmode_validator: Dark mode compatibility
- migration_validator: SLDS 1 → 2 migration detection
- styling_hooks: CSS variable validation

Main validation logic is in validate_slds.py which uses these modules
as optional extensions.
"""

__version__ = "1.0.0"
__all__ = [
    'class_validator',
    'a11y_validator',
    'darkmode_validator',
    'migration_validator',
    'styling_hooks'
]
