#!/usr/bin/env python3
"""
Credential Setup Suggestion Hook for building-sf-integrations

Detects when credential metadata files are created and suggests
running the appropriate automation scripts.

File patterns detected:
- *.namedCredential-meta.xml → configure-named-credential.sh
- *.externalCredential-meta.xml → configure-named-credential.sh
- *cspTrustedSite-meta.xml → Endpoint security configured
- *remoteSite-meta.xml → Endpoint security configured

Called automatically via PostToolUse hook on Write operations.
"""

import json
import os
import re
import sys
from pathlib import Path

# File pattern matchers
PATTERNS = {
    'named_credential': re.compile(r'\.namedCredential-meta\.xml$', re.IGNORECASE),
    'external_credential': re.compile(r'\.externalCredential-meta\.xml$', re.IGNORECASE),
    'csp_trusted_site': re.compile(r'\.cspTrustedSite-meta\.xml$', re.IGNORECASE),
    'remote_site': re.compile(r'\.remoteSiteSetting-meta\.xml$|\.remoteSite-meta\.xml$', re.IGNORECASE),
    'external_service': re.compile(r'\.externalServiceRegistration-meta\.xml$', re.IGNORECASE),
}

# Script recommendations per file type
SCRIPT_RECOMMENDATIONS = {
    'named_credential': {
        'script': 'configure-named-credential.sh',
        'description': 'Set API key securely via ConnectApi (Enhanced Named Credentials)',
        'usage': './scripts/configure-named-credential.sh <org-alias>',
        'next_steps': [
            'Deploy metadata: sf project deploy start --metadata NamedCredential:<name>',
            'Run script to configure API key securely',
            'Test connection in Setup → Named Credentials'
        ]
    },
    'external_credential': {
        'script': 'configure-named-credential.sh',
        'description': 'Configure External Credential with ConnectApi',
        'usage': './scripts/configure-named-credential.sh <org-alias>',
        'next_steps': [
            'Deploy External Credential first',
            'Deploy associated Named Credential',
            'Run script to set authentication parameters'
        ]
    },
    'csp_trusted_site': {
        'script': None,
        'description': 'CSP Trusted Site created for endpoint security',
        'usage': None,
        'next_steps': [
            'Deploy: sf project deploy start --metadata CspTrustedSite:<name>',
            'Verify in Setup → CSP Trusted Sites'
        ]
    },
    'remote_site': {
        'script': None,
        'description': 'Remote Site Setting created (legacy endpoint security)',
        'usage': None,
        'next_steps': [
            'Deploy: sf project deploy start --metadata RemoteSiteSetting:<name>',
            'Consider migrating to CSP Trusted Sites for modern approach'
        ]
    },
    'external_service': {
        'script': None,
        'description': 'External Service registration created',
        'usage': None,
        'next_steps': [
            'Ensure Named Credential is configured first',
            'Deploy: sf project deploy start --metadata ExternalServiceRegistration:<name>',
            'Apex classes will be auto-generated from OpenAPI spec'
        ]
    }
}


def detect_file_type(file_path: str) -> str | None:
    """Detect the credential file type from the file path."""
    filename = os.path.basename(file_path)

    for file_type, pattern in PATTERNS.items():
        if pattern.search(filename):
            return file_type

    return None


def extract_credential_name(file_path: str, file_type: str) -> str:
    """Extract the credential name from the file path."""
    filename = os.path.basename(file_path)

    # Remove the metadata suffix to get the credential name
    patterns = {
        'named_credential': r'(.+)\.namedCredential-meta\.xml$',
        'external_credential': r'(.+)\.externalCredential-meta\.xml$',
        'csp_trusted_site': r'(.+)\.cspTrustedSite-meta\.xml$',
        'remote_site': r'(.+)\.(?:remoteSiteSetting|remoteSite)-meta\.xml$',
        'external_service': r'(.+)\.externalServiceRegistration-meta\.xml$',
    }

    pattern = patterns.get(file_type)
    if pattern:
        match = re.match(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)

    return filename


def analyze_file_content(file_path: str) -> dict:
    """Analyze the file content for additional context."""
    context = {
        'auth_protocol': None,
        'endpoint_url': None,
        'has_oauth': False,
        'has_certificate': False
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Detect authentication protocol
        if '<authProtocol>OAuth</authProtocol>' in content:
            context['auth_protocol'] = 'OAuth 2.0'
            context['has_oauth'] = True
        elif '<authProtocol>Jwt</authProtocol>' in content:
            context['auth_protocol'] = 'JWT Bearer'
        elif '<authProtocol>Custom</authProtocol>' in content:
            context['auth_protocol'] = 'Custom (API Key)'
        elif '<authProtocol>Certificate</authProtocol>' in content:
            context['auth_protocol'] = 'Certificate'
            context['has_certificate'] = True

        # Extract endpoint URL
        url_match = re.search(r'<endpoint>([^<]+)</endpoint>', content)
        if url_match:
            context['endpoint_url'] = url_match.group(1)

        # Check for Named Credential URL pattern
        url_match = re.search(r'<url>([^<]+)</url>', content)
        if url_match:
            context['endpoint_url'] = url_match.group(1)

    except Exception:
        pass  # File analysis is optional

    return context


def generate_suggestion_message(file_type: str, cred_name: str, file_context: dict) -> str:
    """Generate the suggestion message for Claude."""
    recommendation = SCRIPT_RECOMMENDATIONS.get(file_type, {})

    lines = [
        '',
        '═' * 60,
        '🔐 CREDENTIAL CONFIGURATION DETECTED',
        '═' * 60,
        '',
        f'📄 File Type: {file_type.replace("_", " ").title()}',
        f'📛 Name: {cred_name}',
    ]

    if file_context.get('auth_protocol'):
        lines.append(f'🔑 Auth Protocol: {file_context["auth_protocol"]}')

    if file_context.get('endpoint_url'):
        lines.append(f'🌐 Endpoint: {file_context["endpoint_url"]}')

    lines.append('')

    if recommendation.get('script'):
        lines.extend([
            '┌─────────────────────────────────────────────────────────┐',
            '│  🚀 AUTOMATION SCRIPT AVAILABLE                         │',
            '├─────────────────────────────────────────────────────────┤',
            f'│  Script: {recommendation["script"]:<46} │',
            f'│  Purpose: {recommendation["description"][:44]:<44} │',
            '├─────────────────────────────────────────────────────────┤',
            '│  💡 OFFER TO RUN:                                       │',
            f'│  {recommendation["usage"]:<55} │',
            '└─────────────────────────────────────────────────────────┘',
            '',
        ])

    lines.extend([
        '📋 NEXT STEPS:',
        '─' * 60,
    ])

    for i, step in enumerate(recommendation.get('next_steps', []), 1):
        lines.append(f'   {i}. {step}')

    # Add OAuth-specific suggestion
    if file_context.get('has_oauth'):
        lines.extend([
            '',
            '⚠️  OAuth detected: Consider using /configuring-connected-apps to',
            '    create the Connected App for this credential.',
        ])

    lines.extend([
        '',
        '═' * 60,
    ])

    return '\n'.join(lines)


def main():
    """Main entry point for the hook."""
    # Get file path from command line or stdin
    file_path = None

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Try to read from stdin (hook input)
        try:
            hook_input = json.load(sys.stdin)
            tool_input = hook_input.get('tool_input', {})
            file_path = tool_input.get('file_path', '')
        except (json.JSONDecodeError, IOError):
            pass

    if not file_path:
        # No file path, exit silently
        print(json.dumps({'continue': True}))
        return 0

    # Detect file type
    file_type = detect_file_type(file_path)

    if not file_type:
        # Not a credential file, exit silently
        print(json.dumps({'continue': True}))
        return 0

    # Extract credential name
    cred_name = extract_credential_name(file_path, file_type)

    # Analyze file content
    file_context = analyze_file_content(file_path)

    # Generate suggestion message
    message = generate_suggestion_message(file_type, cred_name, file_context)

    # Output hook result
    result = {
        'continue': True,
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': message
        }
    }

    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
