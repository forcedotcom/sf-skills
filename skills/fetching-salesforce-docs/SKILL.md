---
name: fetching-salesforce-docs
description: "Official Salesforce documentation retrieval skill. Use when you need authoritative Salesforce docs from developer.salesforce.com, help.salesforce.com, architect.salesforce.com, admin.salesforce.com, or lightningdesignsystem.com, especially when pages are JS-heavy, shell-rendered, or hard to extract with naive fetching. Use to ground answers in official Salesforce sources instead of third-party blogs or summaries. TRIGGER when: user asks for official Salesforce documentation, Apex or API reference, LWC docs, Agentforce docs, setup or help articles, or any doc from a Salesforce-owned domain. DO NOT TRIGGER when: user is asking for a code change, deployment task, or anything not requiring documentation retrieval — use the appropriate sf-* skill instead."
license: LICENSE.txt has complete terms
metadata:
  version: "1.1"
---

# fetching-salesforce-docs

Use this skill to retrieve and ground answers in **official Salesforce documentation on the public web**.

This skill provides a **reliable online retrieval playbook** for Salesforce docs that are hard to fetch, especially `help.salesforce.com`, JS-heavy `developer.salesforce.com`, Lightning Design System docs on `lightningdesignsystem.com`, and other official Salesforce-owned doc pages such as `architect.salesforce.com` and `admin.salesforce.com`.

Optional extraction scripts are available in `scripts/` — see the Reference File Index below.

## Scope

| | |
|---|---|
| **In scope** | Official Salesforce doc retrieval: Apex, API, LWC, metadata, Agentforce, setup articles, SLDS, architect/admin guidance |
| **Out of scope** | Third-party blogs, PDF fallback, local corpus indexing, benchmark workflows, generating code or metadata |

## Required Inputs

Before fetching, identify:
- The exact concept, identifier, class, method, or feature name being requested
- The likely doc family (developer docs, help articles, design system, architect/admin)

No additional setup is required to use the retrieval playbook in this skill. The optional extraction scripts require `playwright` — see `requirements.txt`.

## Official Sources Only

Prefer Salesforce-owned documentation sources:
- `developer.salesforce.com`
- `help.salesforce.com`
- `architect.salesforce.com`
- `admin.salesforce.com`
- `lightningdesignsystem.com`
- other official Salesforce documentation pages when Salesforce uses them as the source of truth

Avoid third-party blogs, videos, or summary articles unless the user explicitly asks for them.

Do **not** fall back to PDFs.

## Retrieval Workflow

### 1. Classify the request first

Before fetching anything, identify the likely doc family.

| Family | Typical Source | Use For |
|---|---|---|
| Developer docs | `developer.salesforce.com/docs/...` | Apex, APIs, LWC, metadata, Agentforce developer docs |
| Help docs | `help.salesforce.com/...` | setup, admin, product configuration |
| Architect/Admin docs | `architect.salesforce.com/...`, `admin.salesforce.com/...` | best practices, patterns, well-architected guidance, admin enablement |
| Design system docs | `lightningdesignsystem.com/...` | SLDS, Cosmos, design tokens, component and styling guidance |
| Legacy atlas docs | `developer.salesforce.com/docs/atlas.en-us.*` | older official guide and reference docs |

### 2. Identify the exact concept

Extract the real target before you search:
- exact API/class/method name
- exact feature name
- exact product phrase
- exact setup concept

Examples:
- `Lightning Message Service`
- `Wire Service`
- `System.StubProvider`
- `Agentforce Actions`
- `Messaging for In-App and Web allowed domains`

### 3. Prefer targeted official retrieval

Do **not** broad-crawl Salesforce docs.

Instead:
1. identify the most likely official guide root or article
2. if search is needed, restrict it to official Salesforce domains only
3. fetch that official page
4. check whether the **exact concept actually appears on the page**
5. if not, inspect and follow the most relevant **1–3 official child links**
6. stop once you have grounded evidence

### 4. Do not stop at broad landing pages

A guide landing page is **not enough** unless it clearly contains the exact requested concept.

This is especially important for:
- LWC docs
- Agentforce docs
- broad platform guide homepages
- help landing pages that link to the real article

### 5. For `developer.salesforce.com`

Use this playbook:
- start with the most likely official guide root
- if the page is JS-heavy, prefer browser-rendered extraction
- check whether the exact concept appears on the page
- if the concept is missing, inspect official child links and follow the best matching 1–3 links
- prefer exact concept pages over broad guide roots
- legacy atlas pages are valid if they are the real official reference for the concept

### 6. For `help.salesforce.com`

Help pages often fail with naive fetching.

Use this playbook:
- prefer exact `articleView?id=...` URLs when available
- use browser-rendered extraction when plain fetch returns shell content
- treat outputs like `Loading`, `Sorry to interrupt`, `CSS Error`, or mostly chrome/navigation text as **failed extraction**, not evidence
- look for the **real article body**, not just header, nav, or footer text
- reject shell pages and soft-404 pages such as:
  - "We looked high and low but couldn't find that page"
  - generic empty help shells
- if starting from a nearby guide or hub page, follow linked Help articles until you reach the real article body
- if extraction still fails after targeted retries, return the best official Help URLs you found and explicitly say that article-body extraction was unsuccessful

## Acceptance Rules

A page is good enough to answer from only when at least one of these is true:
- the exact identifier appears on the page
- the exact concept phrase appears on the page
- multiple query-specific phrases appear in the correct official context

A page is **not** good enough when:
- it is only a broad landing page
- it is a shell page with little real article text
- it is from the wrong product area
- it does not contain the requested identifier or concept
- it is a third-party explanation when an official page should exist

## Rejection Rules

Reject these as final evidence:
- broad guide homepages without the exact concept
- release notes when a concept/reference page is expected
- admin blog posts when developer docs are requested
- third-party blogs when official docs are available
- shell-rendered pages with no real article body
- pages whose titles sound right but whose body does not contain the requested concept

## Grounding Requirements

When answering, include:
1. guide/article title
2. exact official URL
3. source type:
   - developer doc page
   - atlas reference page
   - help article page
4. any caveat if extraction was partial or browser-rendered

If evidence is weak, say so plainly.

## Examples

### Example: Lightning Message Service
Do **not** stop at the general LWC guide root.
Find the exact LWC page for Lightning Message Service or follow the most relevant child links from the LWC docs until the exact concept appears.

### Example: Wire Service
Do **not** answer from the LWC homepage unless `Wire Service` is actually present there.
Follow the relevant child doc page for wire service or wire adapters.

### Example: Agentforce Actions
Do **not** answer from a broad Agentforce landing page or a blog post.
Find the official Agentforce developer page for actions, or follow the best matching child pages from the official Agentforce docs.

### Example: Messaging for In-App and Web allowed domains
Prefer official Help articles and browser-rendered extraction.
Reject generic help shells. Follow linked Help articles from nearby official messaging docs if needed.

### Example: System.StubProvider
Prefer the official Salesforce reference/developer page where the exact identifier appears.
Do not substitute a broader Apex landing page if the identifier is absent.

## Non-Goals

This skill should **not**:
- maintain a local documentation corpus
- rely on a local index
- use PDF fallback
- run benchmark workflows
- depend on repo-specific scripts to be useful

## Output Expectations

For each retrieval, include:
1. Guide or article title
2. Exact official URL
3. Source type (developer doc page / atlas reference page / help article page)
4. Any caveat if extraction was partial or browser-rendered

If evidence is weak, say so plainly rather than forcing an answer.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `scripts/extract_salesforce_doc.py` | Use to fetch any official Salesforce doc URL; automatically routes `help.salesforce.com` into the dedicated Help extractor and supports browser-rendered extraction for all Salesforce-owned doc hosts |
| `scripts/extract_help_salesforce.py` | Use directly when targeting `help.salesforce.com` `articleView` URLs; use when the wrapper is not appropriate |
| `scripts/runtime_bootstrap.py` | Imported by the extraction scripts to resolve the isolated fetching-salesforce-docs Python runtime and Playwright browser path; not called directly |
| `requirements.txt` | Lists Python dependencies (`playwright`, `playwright-stealth`) needed to run the extraction scripts |
