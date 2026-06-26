# Vendor File Handling

## Problem

Code Analyzer scans all JavaScript files, including third-party vendor libraries like jQuery, Bootstrap, Lodash, Handlebars, etc. These libraries often trigger thousands of violations, especially:

- **no-var** (legacy `var` declarations)
- **prefer-const** (variables that could be const)
- **code style** (indentation, quotes, semicolons)

A typical scan might find:
- **9,714 total violations**
- **9,089 in vendor files** (jQuery UI, Bootstrap, tablesorter)
- **634 in project source** (your Aura/LWC components)

## Why You Shouldn't Fix Vendor Files

| Risk | Impact |
|------|--------|
| **Breaks upgrades** | Modified vendor files can't be cleanly upgraded to newer versions |
| **Untested changes** | Libraries weren't designed for strict mode or modern JS patterns |
| **Subtle bugs** | Converting `var` to `let/const` can change scope/hoisting behavior in legacy code |
| **Maintainability** | Future developers won't know the file was modified and why |
| **Wasted effort** | The next library upgrade will overwrite your fixes anyway |

## Solutions

### Solution 1: Re-scan with --target (Fastest)

If you know your project source locations upfront:

```bash
sf code-analyzer run --rule-selector <selector> \
  --target "force-app/main/default/aura,force-app/main/default/lwc" \
  --output-file "./results-project-only.json" \
  --include-fixes
```

**Pros:**
- Only scans what you need
- Faster execution
- Cleaner results

**Cons:**
- Must know target directories upfront
- Doesn't show you what violations exist in vendor files (for awareness)

### Solution 2: Intelligent Filtering (Most Accurate)

Scan everything first, then use the intelligent filter script to separate vendor from project:

```bash
# 1. Run full scan
sf code-analyzer run --rule-selector <selector> \
  --output-file "./results-all.json" --include-fixes

# 2. Filter to project files only
node "<skill_dir>/scripts/filter-violations.js" \
  "./results-all.json" \
  "./results-project.json" \
  --report

# 3. Apply fixes to filtered results
node "<skill_dir>/scripts/apply-fixes.js" "./results-project.json"
```

**Pros:**
- Intelligent classification using multiple heuristics
- Shows you vendor vs project breakdown
- Handles uncertain files (30-70% confidence)
- No manual pattern maintenance

**Cons:**
- Scans more files than necessary
- Takes longer for large codebases

## How the Intelligent Filter Works

The `filter-violations.js` script uses a **multi-heuristic confidence scoring system**:

### 1. Path-Based Signals (30% weight)

```javascript
// High confidence vendor indicators
node_modules/          → 100% vendor
bower_components/      → 100% vendor
vendor/                → 95% vendor
third-party/           → 95% vendor
StaticResourceSources/ → 70% vendor

// Project source indicators
force-app/main/default/aura/    → Project
force-app/main/default/lwc/     → Project
```

### 2. Name-Based Signals (30% weight)

```javascript
// Filename patterns
*.min.js               → 95% vendor (minified)
*-1.12.1.js           → 85% vendor (version in name)
jquery*.js            → 85% vendor (known library)
bootstrap*.js         → 85% vendor (known library)

// Checked against package.json dependencies
```

### 3. Content-Based Signals (40% weight)

```javascript
// License headers
MIT License, Apache, BSD, GPL → 80% vendor

// Minification indicators
Average line length > 500 chars → 90% vendor
< 10 lines but > 5KB file     → 85% vendor

// Library patterns
UMD/AMD/CommonJS wrapper       → 70% vendor
@version x.x.x                 → 65% vendor
@author (non-project)          → 50% vendor
```

### Final Score

```
Weighted Score = (PathScore × 0.3) + (NameScore × 0.3) + (ContentScore × 0.4)

> 70% = Vendor file
< 30% = Project file
30-70% = Uncertain (manual review)
```

## Example Output

```
=== INTELLIGENT VENDOR FILE DETECTION ===

Original violations: 9714
Filtered violations: 634
Reduction: 9080 (93.5%)

📦 Vendor files excluded: 127
   610 violations | 95% confidence | jquery-ui-1.12.1.js
        located in vendor directory, version number in filename, minified file
   525 violations | 98% confidence | jquery-ui-1.12.1.min.js
        located in vendor directory, minified file (.min.js)
   ... and 125 more vendor files

✅ Project files included: 39
   157 violations | CRLP_RollupHelper.js
   103 violations | HH_ContainerHelper.js
   84 violations | CRLP_FilterGroupHelper.js
   ...

⚠️  Uncertain files: 2
    These files have 30-70% vendor confidence - review manually:
   45 violations | 55% vendor | customUtility.js
        located in vendor directory

✓ Filtered results written to: ./results-project.json
```

## Workflow Integration

### When to Use Each Approach

| Scenario | Recommended Approach |
|----------|---------------------|
| User says "fix no-var in my code" | Use intelligent filter (excludes vendor by default) |
| User says "fix all no-var" | Ask: "Including vendor files (jQuery, Bootstrap)?" |
| User specifies path | Use --target directly |
| User wants report first | Full scan → intelligent filter → show breakdown |

### Step-by-Step Workflow

```markdown
1. Run Code Analyzer scan
2. Parse results
3. **Check violation distribution:**
   - If 50%+ are in vendor files → offer intelligent filtering
   - If user said "my code" or "project" → automatically filter
4. Discover fixes (on filtered or unfiltered results)
5. Apply fixes
6. Summarize
```

## Edge Cases

### Case 1: Vendored Modified Libraries

**Scenario:** Your org has modified a copy of jQuery

**Solution:** The intelligent filter will classify it as vendor, but violations may be legitimate. Options:
1. Fix manually after filter identifies it
2. Re-run with --target excluding that specific file
3. Add to project exceptions in filter script

### Case 2: Project Code in Static Resources

**Scenario:** Your custom JavaScript is in `staticresources/` alongside vendor libs

**Solution:** The filter checks content + name, not just path. Custom code without vendor markers scores as "project" or "uncertain" for manual review.

### Case 3: Uncertain Classifications

**Scenario:** File scores 30-70% vendor confidence

**Action:** Filter script reports these separately. Review manually:
- Check file purpose
- Look for original source/documentation
- Decide whether to fix or exclude

## Configuration (Future Enhancement)

The filter script could accept custom patterns:

```bash
node filter-violations.js results.json filtered.json \
  --exclude-patterns "*.min.js,jquery*,bootstrap*" \
  --include-patterns "force-app/main/default/aura/**,force-app/main/default/lwc/**"
```

Currently uses intelligent defaults and doesn't require configuration.

## Testing the Filter

```bash
# Run with detailed report
node scripts/filter-violations.js \
  ./code-analyzer-results-20260519-133252.json \
  ./filtered-output.json \
  --report

# Check the output
node scripts/parse-results.js ./filtered-output.json
```

Compare before/after violation counts to verify filtering accuracy.
