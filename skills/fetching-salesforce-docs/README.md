# fetching-salesforce-docs

## What it is

`fetching-salesforce-docs` is a **prompt-only skill**.

It gives a practical retrieval playbook for official Salesforce docs on the public web, especially when:
- `developer.salesforce.com` pages are JS-heavy
- `help.salesforce.com` pages return shell content
- `architect.salesforce.com` / `admin.salesforce.com` pages need browser-rendered extraction
- `lightningdesignsystem.com` pages contain official SLDS guidance
- the real answer is on a child page, not the guide homepage

## What it is not

This skill does not include:
- local corpus workflows
- indexing
- benchmark workflows
- any required helper CLI dependency
- PDF fallback guidance

## Use it for

- official Salesforce docs lookup
- hard-to-fetch Help articles
- Apex / API / LWC / Agentforce documentation grounding
- deciding when to follow child links from broad official guide pages
- rejecting weak results such as shells, landing pages, and third-party summaries

## Optional utility

A tiny wrapper is available for official Salesforce doc URLs:

```bash
python3 skills/fetching-salesforce-docs/scripts/extract_salesforce_doc.py \
  --url "https://help.salesforce.com/s/articleView?id=service.miaw_security.htm&type=5" \
  --pretty
```

Behavior:
- automatically routes `help.salesforce.com` URLs into the dedicated Help extractor
- supports official Salesforce-owned doc hosts such as `developer.salesforce.com`, `architect.salesforce.com`, `admin.salesforce.com`, `lightningdesignsystem.com`, and other official Salesforce documentation pages
- supports optional best-effort stealth mode via `--stealth`

Dependencies for the helper scripts live in:
- `skills/fetching-salesforce-docs/requirements.txt`

The installer sets up an isolated runtime under `~/.claude/.fetching-salesforce-docs-runtime`, installs those Python packages there, and installs the Playwright Chromium browser automatically during install/update.

The underlying Help extractor is also available directly at:

```bash
python3 skills/fetching-salesforce-docs/scripts/extract_help_salesforce.py \
  --url "https://help.salesforce.com/s/articleView?id=service.miaw_security.htm&type=5" \
  --pretty
```

## Key idea

Keep retrieval:
- **official-source-first**
- **HTML-only**
- **targeted**
- **child-link aware**
- **strict about exact concept matching**
