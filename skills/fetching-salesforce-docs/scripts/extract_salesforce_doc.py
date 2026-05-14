#!/usr/bin/env python3
"""
Tiny wrapper for Salesforce documentation extraction.

Behavior:
- If the URL is on help.salesforce.com, automatically route to the dedicated
  Help extractor with shadow DOM heuristics.
- Otherwise, use a lightweight browser-rendered extractor for official
  Salesforce-owned documentation sites such as developer.salesforce.com,
  architect.salesforce.com, admin.salesforce.com, lightningdesignsystem.com,
  and other supported official documentation hosts.

Examples:
  python3 skills/fetching-salesforce-docs/scripts/extract_salesforce_doc.py \
    --url "https://help.salesforce.com/s/articleView?id=service.miaw_security.htm&type=5" \
    --pretty

  python3 skills/fetching-salesforce-docs/scripts/extract_salesforce_doc.py \
    --url "https://developer.salesforce.com/docs/platform/lwc/guide/use-message-channel-intro.html" \
    --pretty

  python3 skills/fetching-salesforce-docs/scripts/extract_salesforce_doc.py \
    --url "https://architect.salesforce.com/well-architected/overview" \
    --stealth --pretty
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any, Dict
from urllib.parse import urlparse

from runtime_bootstrap import maybe_reexec_in_sf_docs_runtime

maybe_reexec_in_sf_docs_runtime(__file__)

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import Stealth
except ImportError:
    Stealth = None

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

from extract_help_salesforce import extract as extract_help_salesforce


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

STRONG_SHELL_TOKENS = [
    "loading",
    "sorry to interrupt",
    "css error",
    "enable javascript",
    "we looked high and low",
    "couldn't find that page",
    "404 error",
]

WEAK_SHELL_TOKENS = [
    "sign in",
    "cookie preferences",
]

OFFICIAL_DOC_EXACT_HOSTS = {
    "salesforce.com",
    "lightningdesignsystem.com",
}

OFFICIAL_DOC_SUFFIXES = (
    ".salesforce.com",
    ".lightningdesignsystem.com",
)


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def looks_like_shell(title: str, text: str) -> bool:
    haystack = f"{title}\n{text}".lower()
    if any(token in haystack for token in STRONG_SHELL_TOKENS):
        return True
    if any(token in haystack for token in WEAK_SHELL_TOKENS):
        return len(text.strip()) < 600
    return False


def apply_stealth(page) -> bool:
    if stealth_sync is not None:
        try:
            stealth_sync(page)
            return True
        except Exception:
            pass
    if Stealth is not None:
        try:
            Stealth().apply_stealth_sync(page)
            return True
        except Exception:
            return False
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract official Salesforce documentation from a URL")
    parser.add_argument("--url", required=True, help="Official Salesforce doc URL")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")
    parser.add_argument("--stealth", action="store_true", help="Best-effort stealth mode for bot-sensitive pages")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser.parse_args()


def is_official_salesforce_host(host: str) -> bool:
    host = (host or "").lower()
    return host in OFFICIAL_DOC_EXACT_HOSTS or any(host.endswith(suffix) for suffix in OFFICIAL_DOC_SUFFIXES)


def route_kind(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("help.salesforce.com"):
        return "help"
    if is_official_salesforce_host(host):
        return "official"
    raise SystemExit(f"Unsupported host for fetching-salesforce-docs extractor: {host or url}")


def extract_official_salesforce_doc(url: str, timeout_seconds: int, use_stealth: bool = False) -> Dict[str, Any]:
    timeout_ms = timeout_seconds * 1000
    host = (urlparse(url).hostname or "").lower()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1400})
        stealth_used = apply_stealth(page) if use_stealth else False

        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            http_status = response.status if response else None
            page.wait_for_timeout(1500)
            try:
                page.wait_for_function(
                    r"""
                    () => {
                      const el = document.querySelector('main, article, [role="main"]');
                      const text = (el?.innerText || el?.textContent || '').trim();
                      return text.length > 200;
                    }
                    """,
                    timeout=min(timeout_ms, 15000),
                )
            except PlaywrightTimeoutError:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 15000))
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(500)

            payload = page.evaluate(
                r"""
                () => {
                  function normalize(text) {
                    return String(text || '')
                      .replace(/\u00a0/g, ' ')
                      .replace(/\r/g, '')
                      .replace(/\n{3,}/g, '\n\n')
                      .trim();
                  }

                  function isVisible(el) {
                    if (!el || !el.getBoundingClientRect) return false;
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                  }

                  function allRoots() {
                    const roots = [document];
                    const queue = [document];
                    while (queue.length) {
                      const current = queue.shift();
                      if (!current || !current.querySelectorAll) continue;
                      const elements = current.querySelectorAll('*');
                      for (const el of elements) {
                        if (el.shadowRoot) {
                          roots.push(el.shadowRoot);
                          queue.push(el.shadowRoot);
                        }
                      }
                    }
                    return roots;
                  }

                  function deepQueryAll(selector) {
                    const results = [];
                    const seen = new Set();
                    for (const root of allRoots()) {
                      if (!root.querySelectorAll) continue;
                      for (const el of root.querySelectorAll(selector)) {
                        if (!seen.has(el)) {
                          seen.add(el);
                          results.push(el);
                        }
                      }
                    }
                    return results;
                  }

                  function collectLinks(scope) {
                    const urls = new Set();
                    const nodes = scope && scope.querySelectorAll ? scope.querySelectorAll('a[href]') : [];
                    for (const a of nodes) {
                      const href = a.href || a.getAttribute('href') || '';
                      if (!href) continue;
                      if (href.startsWith('javascript:') || href.startsWith('mailto:')) continue;
                      urls.add(href);
                    }
                    return Array.from(urls);
                  }

                  const title = document.title || normalize(document.querySelector('title')?.innerText || 'Untitled');
                  const childLinks = new Set();
                  for (const root of allRoots()) {
                    for (const link of collectLinks(root)) childLinks.add(link);
                  }

                  const selectorConfigs = [
                    { selector: 'article', strategy: 'article', base: 260 },
                    { selector: 'main', strategy: 'main', base: 220 },
                    { selector: '[role="main"]', strategy: 'role-main', base: 220 },
                    { selector: '.slds-text-longform', strategy: 'longform', base: 200 },
                    { selector: '.markdown-content', strategy: 'markdown-content', base: 190 },
                    { selector: '.content-body', strategy: 'content-body', base: 180 },
                    { selector: '.article-body', strategy: 'article-body', base: 180 },
                    { selector: '.article-content', strategy: 'article-content', base: 180 },
                    { selector: '.post-content', strategy: 'post-content', base: 170 },
                    { selector: '.main-content', strategy: 'main-content', base: 170 },
                    { selector: '.tds-content', strategy: 'tds-content', base: 165 },
                    { selector: '.siteforceContentArea .content', strategy: 'siteforce-content', base: 160 },
                    { selector: 'doc-content-layout', strategy: 'legacy-doc-layout', base: 150 },
                    { selector: 'doc-xml-content', strategy: 'legacy-doc-xml', base: 145 },
                    { selector: 'doc-amf-reference .markdown-content', strategy: 'legacy-amf-markdown', base: 150 },
                    { selector: 'main .content, article .content', strategy: 'nested-content', base: 140 },
                  ];

                  const candidates = [];
                  for (const cfg of selectorConfigs) {
                    const nodes = deepQueryAll(cfg.selector);
                    for (const node of nodes) {
                      if (!isVisible(node)) continue;
                      const text = normalize(node.innerText || node.textContent || '');
                      if (text.length < 200) continue;
                      let score = cfg.base + Math.min(text.length, 5000) / 30;
                      const lowered = text.toLowerCase();
                      if (lowered.includes(title.toLowerCase())) score += 50;
                      if (lowered.includes('table of contents')) score -= 80;
                      if (lowered.includes('cookie preferences')) score -= 120;
                      if (lowered.includes('sign in')) score -= 120;
                      candidates.push({
                        strategy: cfg.strategy,
                        selector: cfg.selector,
                        score,
                        text,
                        links: collectLinks(node).slice(0, 200),
                      });
                    }
                  }

                  const bodyText = normalize(document.body?.innerText || '');
                  if (bodyText.length >= 200) {
                    candidates.push({
                      strategy: 'body',
                      selector: 'body',
                      score: Math.min(bodyText.length, 5000) / 50,
                      text: bodyText,
                      links: Array.from(childLinks).slice(0, 200),
                    });
                  }

                  candidates.sort((a, b) => b.score - a.score);
                  const best = candidates[0] || null;

                  return {
                    url: window.location.href,
                    title,
                    strategy: best ? best.strategy : 'none',
                    selector: best ? best.selector : null,
                    text: best ? best.text : '',
                    contentLinks: best ? best.links : [],
                    childLinks: Array.from(childLinks).slice(0, 200),
                    candidateCount: candidates.length,
                  };
                }
                """
            )

            text = normalize_text(payload.get("text", ""))
            likely_shell = looks_like_shell(payload.get("title", ""), text)
            ok = bool(text) and len(text) >= 300 and not likely_shell

            return {
                "ok": ok,
                "url": payload.get("url", url),
                "httpStatus": http_status,
                "title": payload.get("title") or "Untitled",
                "host": host,
                "hostKind": "official-salesforce",
                "strategy": payload.get("strategy"),
                "selector": payload.get("selector"),
                "likelyShell": likely_shell,
                "stealthRequested": use_stealth,
                "stealthAvailable": stealth_sync is not None or Stealth is not None,
                "stealthUsed": stealth_used,
                "text": text,
                "contentLinks": payload.get("contentLinks", []),
                "childLinks": payload.get("childLinks", []),
                "candidateCount": payload.get("candidateCount", 0),
            }
        finally:
            page.close()
            browser.close()


def main() -> int:
    args = parse_args()
    kind = route_kind(args.url)

    if kind == "help":
        result = extract_help_salesforce(args.url, args.timeout, use_stealth=args.stealth)
        result["routedVia"] = "extract_help_salesforce"
        result.setdefault("hostKind", "help")
    else:
        result = extract_official_salesforce_doc(args.url, args.timeout, use_stealth=args.stealth)
        result["routedVia"] = "generic_official_salesforce_extractor"

    dump = json.dumps(result, indent=2 if args.pretty else None)
    print(dump)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
