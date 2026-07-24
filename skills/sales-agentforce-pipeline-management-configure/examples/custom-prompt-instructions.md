# Custom Prompt Instructions for Pipeline Management Agent

This guide explains how to customize the Pipeline Management Agent's behavior through custom prompt instructions in Agentforce Builder.

## Overview

Custom prompt instructions let you:
- Focus the agent on specific business priorities
- Align suggestions with your sales methodology (MEDDIC, BANT, SPICED)
- Add company-specific context and terminology
- Control update aggressiveness and risk tolerance

## Where to Add Custom Instructions

**Setup → Einstein Agentforce → Agents → Sales Management Agent → Prompt Templates**

Or via deployed agent bundle: Edit `sales_management_agent.agent` file

## Template Structure

```yaml
customInstructions:
  - instruction: "[Your custom instruction here]"
    topic: "All Topics"  # Or specific topic like "Update Opportunity Fields"
```

---

## Example 1: Methodology Alignment (MEDDIC)

```text
When analyzing opportunities, strictly follow the MEDDIC framework:

Metrics: Always quantify business impact in dollar amounts or percentages
Economic Buyer: Identify the person with budget authority and highlight their involvement
Decision Criteria: Extract specific evaluation criteria the customer is using
Decision Process: Note approval steps, stakeholders, and timeline
Pain: Focus on business problems, not feature requests
Champion: Identify internal advocates and note their influence level

Prioritize suggestions that address gaps in these six areas. If an opportunity lacks Economic Buyer identification or quantified Metrics, flag this as high priority.
```

**Impact**: Agent will surface MEDDIC gaps and suggest fields like "Economic Buyer", "Champion", "Pain Statement"

---

## Example 2: Risk-Aware Recommendations

```text
Be conservative with opportunity stage progression:

- Only suggest stage advancement if explicit customer commitment exists
- Require written confirmation (email) for stages beyond Proposal
- Flag regression risks when activity decreases by 50%+ in 14 days
- Never suggest "Closed Won" without signed contract or PO evidence

For high-value opportunities (>$100k), require executive-level engagement evidence before advancing past Qualification.
```

**Impact**: Agent becomes more cautious, reducing false positives in pipeline progression

---

## Example 3: Industry-Specific Context

```text
Healthcare Industry Context:

Our sales cycle has these unique phases:
1. Clinical validation with medical staff (usually 60-90 days)
2. IT security review (30-60 days, often blocking)
3. Procurement/contracting (45-90 days)

When analyzing conversations:
- "IT security review" = likely 60-day delay, suggest stage hold
- Mention of "clinical trial" or "validation study" = 6-12 month cycle
- "HIPAA" or "compliance" keywords = route to legal review stage
- Fiscal year end for hospitals is typically June 30

Adjust close date estimates based on these industry timelines.
```

**Impact**: Agent provides healthcare-realistic timelines instead of generic estimates

---

## Example 4: Company Terminology Mapping

```text
Translate customer language to our internal fields:

Customer says → Map to field:
- "Go-live date" → Implementation_Start_Date__c
- "Business case" → ROI_Justification__c
- "Champion" → Internal_Advocate__c
- "Blocker" or "risk" → Risk_Assessment__c
- "Next steps" → Next_Step__c (always include dates and owners)
- "Decision maker" → Economic_Buyer__c

Ignore product feature discussions unless they relate to decision criteria or blockers.
```

**Impact**: Better field mapping for custom objects

---

## Example 5: Update Aggressiveness Control

```text
Autonomous Update Policy:

Fields approved for auto-update (no review needed):
- Next_Step__c (if mentioned explicitly in last 7 days)
- Last_Customer_Interaction__c (factual date)
- Competitor_Mentioned__c (list only)

Fields requiring user review (suggestive mode only):
- Stage (any change)
- Close_Date__c (if moved by >30 days)
- Amount (any change)
- Decision_Maker__c (name changes)

Never auto-update:
- Owner
- Record Type
- Custom checkbox fields affecting reporting
```

**Impact**: Balances automation with control for sensitive fields

---

## Example 6: Data Source Prioritization

```text
When conflicts exist across data sources, prioritize:

1. Email (most reliable, written commitment)
2. Einstein Conversation Insights (recorded calls)
3. Manual notes (may be subjective)

Weighting:
- An email saying "we'll sign next Tuesday" overrides a call where customer said "maybe next month"
- For close date: use latest communication's date if more recent than 48 hours
- For next steps: combine all sources, but flag if sources contradict

If sources fundamentally contradict (e.g., email says "no" but call says "yes"), flag for user review rather than auto-suggesting.
```

**Impact**: Reduces suggestion conflicts from multiple data sources

---

## Example 7: Opportunity Size Thresholds

```text
Opportunity Value Tiers:

Strategic (>$500k):
- Require executive engagement evidence
- Flag if no activity in 7 days
- Suggest bi-weekly check-ins minimum
- Never auto-update stage without explicit approval

Enterprise ($100k-$500k):
- Weekly activity expected
- Require decision process documentation
- Auto-update low-risk fields only

Standard (<$100k):
- Full autonomous update approved
- Focus on velocity and efficiency
- Suggest stage progression more aggressively if activity supports it
```

**Impact**: Differentiated agent behavior based on deal size

---

## Best Practices

### ✅ DO

- **Be specific**: "Extract budget approval date" not "Look for budget info"
- **Use examples**: Show the agent what good looks like
- **Set boundaries**: Explicitly state what NOT to do
- **Align to methodology**: Reference your sales framework (MEDDIC, BANT, etc.)
- **Test incrementally**: Add one instruction, test, refine, add next

### ❌ DON'T

- **Be vague**: "Improve opportunity quality" (how?)
- **Conflict with SF metadata**: Don't override field validation rules
- **Assume data exists**: "Always fill Economic Buyer" (what if unknown?)
- **Over-constrain**: Too many rules make agent overly cautious
- **Ignore testing**: Prompts that sound good may behave unexpectedly

---

## Testing Your Instructions

### Manual Test (Agentforce Builder)

1. **Setup → Einstein Agentforce → Agents → Sales Management Agent**
2. Click **Test** button
3. Enter test conversation:
```text
Customer: "We'll need board approval, but our CFO Sarah Johnson is supportive. We're targeting a January 15 go-live."
```
4. Review agent output for your custom instruction impact

### Production Test

1. Add a note to a real opportunity with test instructions keywords
2. Wait for scheduled flow run (or trigger manually)
3. Check **Opportunity History** for agent-generated suggestions
4. Verify suggestions align with your custom instructions

### A/B Test Different Instructions

1. Clone agent, add different instructions to each
2. Assign different users to each agent via permission sets
3. Compare suggestion quality after 2 weeks
4. Adopt winning instruction set

---

## Common Issues & Solutions

### Issue: Agent ignores custom instructions

**Solution**: 
- Check instruction is under correct topic
- Verify agent is activated
- Ensure instruction doesn't conflict with base system prompt
- Use imperative language ("Do X") not suggestive ("You might want to...")

### Issue: Suggestions become too cautious

**Solution**: Add explicit "approved scenarios" list where agent should be aggressive

### Issue: Agent hallucinates data

**Solution**: Add constraint: "Only use explicitly stated information. If data is unclear, flag for user review rather than guessing."

### Issue: Wrong fields get updated

**Solution**: List exact field API names in instructions with update permissions

---

## Advanced: Methodology-Specific Templates

### MEDDIC Sales

```text
Every opportunity must have MEDDIC qualification data:

Required fields to populate:
- Metrics: Business_Impact__c (quantified ROI)
- Economic Buyer: Decision_Maker__c (name + title)
- Decision Criteria: Evaluation_Criteria__c (list)
- Decision Process: Approval_Steps__c (timeline with stakeholders)
- Pain: Pain_Statement__c (business problem)
- Champion: Internal_Champion__c (name + influence level)

Suggest stage progression only when all 6 elements have data. Flag incomplete MEDDIC as "Risk: Qualification incomplete" in Next_Step__c.
```

### BANT Sales

```text
Focus on BANT qualification:

Budget: Extract dollar amounts and approval status → Budget_Status__c
Authority: Identify decision maker title and approval rights → Decision_Authority__c
Need: Summarize business problem and urgency → Business_Need__c
Timeline: Extract purchase timeline and fiscal constraints → Target_Close_Date__c

Disqualify opportunities early if any BANT element is clearly absent or negative.
```

### SPICED Sales

```text
Use SPICED for complex enterprise sales:

Situation: Current state and context → Customer_Situation__c
Pain: Business problem and impact → Pain_Points__c
Impact: Cost of inaction (quantified) → Cost_Of_Inaction__c
Critical Event: Forcing function or deadline → Critical_Event__c
Decision: Process and stakeholders → Decision_Process__c

Focus on Impact quantification - every opportunity needs a dollar value for cost of inaction.
```

---

## Integration with Stage Descriptions

Your custom instructions should align with stage descriptions (see `assets/stage-descriptions/`). 

Example alignment:
- **Stage**: Prospecting
- **Stage Description**: "Initial outreach and lead qualification. MEDDIC Focus: Begin gathering Metrics..."
- **Custom Instruction**: "In Prospecting stage, prioritize Metrics and Pain discovery..."

This creates consistency between what stages mean and what the agent looks for.

---

## Further Reading

- [Field Completion Prompt Templates](../references/field-completion-prompt-template.md) - For custom field prompts
- [Stage Descriptions](../assets/stage-descriptions/) - MEDDIC, BANT, SPICED stage definitions
- [Salesforce Agentforce Documentation](https://help.salesforce.com/s/articleView?id=sf.agentforce.htm)
