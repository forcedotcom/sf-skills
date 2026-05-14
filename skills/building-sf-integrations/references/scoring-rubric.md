<!-- Parent: building-sf-integrations/SKILL.md -->

# Scoring System (120 Points)

## Category Breakdown

| Category | Points | Evaluation Criteria |
|----------|--------|---------------------|
| **Security** | 30 | Named Credentials used (no hardcoded secrets), OAuth scopes minimized, certificate auth where applicable |
| **Error Handling** | 25 | Retry logic present, timeout handling (120s max), specific exception types, logging implemented |
| **Bulkification** | 20 | Batch callouts considered, CDC bulk handling, event batching for Platform Events |
| **Architecture** | 20 | Async patterns for DML-triggered callouts, proper service layer separation, single responsibility |
| **Best Practices** | 15 | Governor limit awareness, proper HTTP methods, idempotency for retries |
| **Documentation** | 10 | Clear intent documented, endpoint versioning noted, API contract documented |

## Scoring Thresholds

| Rating | Score Range | Description |
|--------|------------|-------------|
| Excellent | 108-120 | Production-ready, follows all best practices |
| Very Good | 90-107 | Minor improvements suggested |
| Good | 72-89 | Acceptable with noted improvements |
| Needs Work | 54-71 | Address issues before deployment |
| Block | <54 | CRITICAL issues, do not deploy |

## Scoring Output Format

```
📊 INTEGRATION SCORE: XX/120 ⭐⭐⭐⭐ Rating
════════════════════════════════════════════════════

🔐 Security           XX/30  ████████░░ XX%
├─ Named Credentials used: ✅
├─ No hardcoded secrets: ✅
└─ OAuth scopes minimal: ✅

⚠️ Error Handling     XX/25  ████████░░ XX%
├─ Retry logic: ✅
├─ Timeout handling: ✅
└─ Logging: ✅

📦 Bulkification      XX/20  ████████░░ XX%
├─ Batch callouts: ✅
└─ Event batching: ✅

🏗️ Architecture       XX/20  ████████░░ XX%
├─ Async patterns: ✅
└─ Service separation: ✅

✅ Best Practices     XX/15  ████████░░ XX%
├─ Governor limits: ✅
└─ Idempotency: ✅

📝 Documentation      XX/10  ████████░░ XX%
├─ Clear intent: ✅
└─ API versioning: ✅

════════════════════════════════════════════════════
```
