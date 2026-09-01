---
name: sf-skill-sanitizer-test
description: "Throwaway skill used to test the public-repo frontmatter sanitizer end to end; use this to verify metadata.distribution is stripped before publishing to the public sf-skills staging branch."
metadata:
  version: "1.0"
---

# Sanitizer test skill

This is a disposable skill used only to exercise the release-to-public
sanitizer. Its `metadata.distribution` block above is internal-only and MUST
be stripped before this file reaches the public repo. The body is preserved
verbatim.
