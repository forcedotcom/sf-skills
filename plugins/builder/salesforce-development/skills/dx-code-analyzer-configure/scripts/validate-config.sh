#!/bin/bash
# validate-config.sh
# Validates a code-analyzer.yml configuration file.
# Usage: bash <skill_dir>/scripts/validate-config.sh [config-file]
#
# If no config file is specified, looks for code-analyzer.yml in current directory.
#
# Exit codes:
#   0 = Config is valid
#   1 = Config has errors

set -euo pipefail

CONFIG_FILE="${1:-code-analyzer.yml}"

echo "Validating: ${CONFIG_FILE}"
echo ""

# Check file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file not found: ${CONFIG_FILE}"
    echo ""
    echo "Expected locations:"
    echo "  - ./code-analyzer.yml"
    echo "  - ./code-analyzer.yaml"
    echo ""
    echo "Generate one with: sf code-analyzer config --output-file code-analyzer.yml"
    exit 1
fi

# Check file is not empty
if [ ! -s "$CONFIG_FILE" ]; then
    echo "ERROR: Config file is empty: ${CONFIG_FILE}"
    exit 1
fi

# Basic YAML syntax check (if python3 available)
if command -v python3 &> /dev/null; then
    echo "Checking YAML syntax..."
    if python3 -c "
import yaml, sys
try:
    with open('${CONFIG_FILE}', 'r') as f:
        config = yaml.safe_load(f)
    if config is None:
        print('WARNING: Config file is empty or contains only comments')
        sys.exit(0)
    if not isinstance(config, dict):
        print('ERROR: Config must be a YAML mapping (dictionary)')
        sys.exit(1)
    print('YAML syntax: OK')
except yaml.YAMLError as e:
    print(f'ERROR: Invalid YAML syntax')
    print(f'  {e}')
    sys.exit(1)
" 2>&1; then
        echo ""
    else
        echo ""
        echo "Fix YAML syntax errors before proceeding."
        exit 1
    fi
else
    echo "WARNING: python3 not found — skipping YAML syntax validation (install python3 for full checks)"
fi

# Validate known field names
echo "Checking known fields..."
VALID_TOP_LEVEL="config_root log_folder log_level rules engines ignores suppressions"

if command -v python3 &> /dev/null; then
    python3 -c "
import yaml, sys

with open('${CONFIG_FILE}', 'r') as f:
    config = yaml.safe_load(f)

if config is None:
    sys.exit(0)

valid_fields = set('${VALID_TOP_LEVEL}'.split())
unknown = set(config.keys()) - valid_fields
if unknown:
    print(f'WARNING: Unknown top-level fields: {sorted(unknown)}')
    print('  Valid fields: config_root, log_folder, log_level, rules, engines, ignores, suppressions')
else:
    print('Known fields: OK')

# Check engines section
if 'engines' in config and config['engines']:
    valid_engines = {'pmd', 'cpd', 'eslint', 'regex', 'retire-js', 'flow', 'sfge', 'apexguru'}
    configured_engines = set(config['engines'].keys())
    unknown_engines = configured_engines - valid_engines
    if unknown_engines:
        print(f'WARNING: Unknown engine names: {sorted(unknown_engines)}')
        print(f'  Valid engines: {sorted(valid_engines)}')
    else:
        print(f'Engines configured: {sorted(configured_engines)}')

# Check ignores section
if 'ignores' in config and config['ignores']:
    if 'files' not in config['ignores']:
        print('WARNING: ignores section should contain a \"files\" list')
    elif not isinstance(config['ignores']['files'], list):
        print('ERROR: ignores.files must be a list of glob patterns')
        sys.exit(1)
    else:
        print(f'Ignore patterns: {len(config[\"ignores\"][\"files\"])} patterns configured')

# Check rules section
if 'rules' in config and config['rules']:
    for engine, rules in config['rules'].items():
        if rules and isinstance(rules, dict):
            for rule_name, overrides in rules.items():
                if overrides and isinstance(overrides, dict):
                    if 'severity' in overrides:
                        sev = overrides['severity']
                        valid_sevs = [1, 2, 3, 4, 5, 'Critical', 'High', 'Moderate', 'Low', 'Info']
                        if sev not in valid_sevs:
                            print(f'WARNING: rules.{engine}.{rule_name}.severity = {sev} (expected 1-5 or Critical/High/Moderate/Low/Info)')

print('')
" 2>&1
fi

# Run sf code-analyzer config validation (if sf CLI available)
echo ""
echo "Running Code Analyzer validation..."
if command -v sf &> /dev/null; then
    if sf plugins --core 2>&1 | grep -qi "code-analyzer"; then
        if sf code-analyzer config --config-file "$CONFIG_FILE" > /dev/null 2>&1; then
            echo "Code Analyzer validation: PASSED"
            echo ""
            echo "Configuration is valid and ready to use."
            exit 0
        else
            echo "Code Analyzer validation: FAILED"
            echo ""
            echo "Running with verbose output:"
            sf code-analyzer config --config-file "$CONFIG_FILE" 2>&1 || true
            exit 1
        fi
    else
        echo "SKIP: Code Analyzer plugin not installed (cannot run full validation)"
        echo "Install: sf plugins install @salesforce/plugin-code-analyzer"
    fi
else
    echo "SKIP: sf CLI not available (cannot run full validation)"
fi

echo ""
echo "Basic validation passed. Install Code Analyzer for full validation."
exit 0
