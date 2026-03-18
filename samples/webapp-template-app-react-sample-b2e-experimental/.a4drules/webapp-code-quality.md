---
description: Code quality and build validation standards
paths:
  - "**/webapplications/**/*"
---

# Code Quality & Build Validation

Enforces ESLint, TypeScript, and build validation for consistent, maintainable code.

## MANDATORY Quality Gates

**Before completing any coding session** (from the web app directory `force-app/main/default/webapplications/<appName>/`):

```bash
npm run lint   # MUST result in 0 errors
npm run build  # MUST succeed (includes TypeScript check)
npm run graphql:codegen # MUST succeed (verifies graphql queries)
```

**Must Pass:**
- `npm run build` completes successfully
- No TypeScript compilation errors
- No critical ESLint errors (0 errors)

**Can Be Warnings:**
- ESLint warnings (fix when convenient)
- Minor TypeScript warnings