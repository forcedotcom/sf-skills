<!-- Parent: generating-visual-diagrams/SKILL.md -->
# Iteration Workflow: Draft → Final

Best practices for cost-effective image generation with generating-visual-diagrams.

## Why Iterate at Low Resolution?

| Resolution | Time | API Cost | Use Case |
|------------|------|----------|----------|
| **1K** | ~3s | $ | Drafts, prompt refinement, layout testing |
| **2K** | ~5s | $$ | Medium quality, quick presentations |
| **4K** | ~10s | $$$ | Production, documentation, final deliverables |

**Key Insight**: Get the prompt right at 1K before spending on 4K generation.

---

## The Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                     DRAFT PHASE (1K)                        │
│                                                             │
│  1. Generate initial image with CLI                         │
│     gemini --yolo "/generate 'Your prompt...'"              │
│                                                             │
│  2. Review in Preview                                       │
│     open ~/nanobanana-output/*.png                          │
│                                                             │
│  3. Is the layout correct? ─────────────────┐               │
│     │                                       │               │
│     ▼ No                                    ▼ Yes           │
│     Refine prompt or use /edit              Continue        │
│     └──────────────────────────────────────►│               │
└─────────────────────────────────────────────┼───────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FINAL PHASE (4K)                         │
│                                                             │
│  4. Generate production quality with Python script          │
│     uv run scripts/generate_image.py \                      │
│       -p "Your refined prompt" \                            │
│       -f "final-output.png" \                               │
│       -r 4K                                                 │
│                                                             │
│  5. Open and use                                            │
│     open ~/nanobanana-output/*final-output*.png             │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Iteration Patterns

### Pattern 1: Prompt Refinement

```bash
# Attempt 1: Too generic
gemini --yolo "/generate 'Account ERD'"
# Result: Missing relationships, wrong colors

# Attempt 2: Add specifics
gemini --yolo "/generate 'Account ERD with Contact and Opportunity, blue boxes'"
# Result: Better, but legend missing

# Attempt 3: Add styling details
gemini --yolo "/generate 'Salesforce ERD: Account (blue, center), Contact (green),
Opportunity (yellow). Master-detail = thick arrow. Lookup = dashed. Include legend.'"
# Result: Perfect layout!

# Final: Generate at 4K
uv run scripts/generate_image.py \
  -p "Salesforce ERD: Account (blue, center)..." \
  -f "crm-erd-final.png" \
  -r 4K
```

### Pattern 2: Edit-Based Iteration

```bash
# Start with basic ERD
gemini --yolo "/generate 'Account-Contact ERD'"

# Edit to add more objects
gemini --yolo "/edit 'Add Opportunity linked to Account with master-detail'"

# Edit to improve styling
gemini --yolo "/edit 'Add legend, use Salesforce Lightning blue (#0176D3)'"

# Final at 4K
uv run scripts/generate_image.py \
  -p "Account-Contact-Opportunity ERD with legend, SLDS colors" \
  -f "final-erd.png" \
  -r 4K
```

### Pattern 3: Python Script for Editing

```bash
# Generate at 1K
uv run scripts/generate_image.py \
  -p "Dashboard mockup with charts" \
  -f "dashboard-v1.png"

# Edit with resolution control
uv run scripts/generate_image.py \
  -p "Add a KPI summary bar at the top" \
  -i ~/nanobanana-output/*dashboard-v1*.png \
  -f "dashboard-v2.png" \
  -r 2K

# Final version
uv run scripts/generate_image.py \
  -p "Polish: add subtle shadows, round corners on cards" \
  -i ~/nanobanana-output/*dashboard-v2*.png \
  -f "dashboard-final.png" \
  -r 4K
```

---

## Timestamp Filenames

The Python script automatically adds timestamps for easy versioning:

```
~/nanobanana-output/
├── 2026-01-13-10-30-15-erd-v1.png      # First attempt
├── 2026-01-13-10-32-45-erd-v2.png      # After edit
├── 2026-01-13-10-35-00-erd-final.png   # Production 4K
```

**Tip**: Use descriptive filenames like `crm-erd.png` - the timestamp is auto-prepended.

---

## When to Use Each Method

| Method | Best For |
|--------|----------|
| **CLI (`gemini --yolo`)** | Quick drafts, simple edits, style exploration |
| **CLI `/edit`** | Iterative refinements of existing images |
| **Python script** | 4K output, precise resolution control, automated workflows |

---

## Cost Optimization Tips

1. **Never generate 4K on first attempt** - always draft at 1K first
2. **Use `/edit` for small changes** - cheaper than regenerating
3. **Batch similar requests** - get all ERDs right before final generation
4. **Save working prompts** - reuse successful prompt patterns
5. **Use `--seed` for reproducibility** - same seed = similar output

---

## Troubleshooting

### Image doesn't match prompt
- Add more specific details (colors, positions, relationships)
- Use SLDS color codes: `#0176D3` (blue), `#04844B` (green), `#FFB75D` (yellow)
- Specify layout: "center", "top-right", "below parent"

### Edit not applying correctly
- Be specific about what to change
- Reference existing elements: "Move the Account box to center"
- One change at a time for precision

### 4K output looks different from 1K draft
- Use exact same prompt text
- Consider using `--seed` for consistency
- Minor variations are normal due to model behavior
