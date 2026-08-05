"""Generate Remote Site Settings XML for HTTP callout targets."""

from __future__ import annotations

import re


def safe_domain_name(domain: str) -> str:
    """Sanitize a domain for use as a Remote Site Setting name.

    Replaces dots and hyphens with underscores.
    e.g. 'api.github.com' -> 'api_github_com'
    """
    return re.sub(r"[.\-]", "_", domain)


def generate_remote_site_xml(domain: str, description: str = "") -> str:
    """Generate a .remoteSite-meta.xml file for a Remote Site Setting.

    Args:
        domain: The domain to allow (e.g. 'api.github.com').
        description: Human-readable description.

    Returns:
        Remote Site Setting XML string.
    """
    url = f"https://{domain}"
    if not description:
        description = f"Remote site for {domain}"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<RemotesiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        f'    <disableProtocolSecurity>false</disableProtocolSecurity>\n'
        f'    <description>{_escape_xml(description)}</description>\n'
        f'    <isActive>true</isActive>\n'
        f'    <url>{url}</url>\n'
        '</RemotesiteSetting>\n'
    )


def _escape_xml(text: str) -> str:
    """Escape special characters for XML content."""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;"))
