# Expected Output

## Agent Behavior

1. Agent calls `search_brands` to find available brands
2. Agent finds 3 brands and presents options to user using `ask_followup_question`:
   - "I found 3 brands in your CMS. Which one should I apply?
     1. Nova Enterprise Brand
     2. Nova Startup Brand
     3. Nova Internal Communications
     Which brand would you like to use?"
3. User selects "Nova Enterprise Brand"
4. Agent calls `get_brand_instructions` with managedContentId "9Pn5g000000AAA111"
5. Agent applies brand guidelines to the product description

## Expected Branded Product Description

The generated description should:
- Lead with outcomes, not features
- Use power verbs (accelerate, transform, empower, unlock)
- Have a bold, authoritative, forward-thinking voice
- Be confident, aspirational, and direct in tone
- Keep paragraphs to 3 sentences maximum
- Use second person ("you", "your team")
- Not use "simple", "easy", or clichés
- Incorporate key messages where natural

## Example Branded Output

"Your Team, Unleashed.

Accelerate collaboration across your entire organization. Track progress, share files, and communicate in real time — all from one platform your team already knows how to use.

Enterprise-grade reliability. Startup-speed agility. Built for teams that move fast."

## Evaluation Criteria

- [ ] Agent searched for brands before generating content
- [ ] Agent presented all brand options to user (did not auto-select)
- [ ] Agent waited for user selection before proceeding
- [ ] Agent extracted brand instructions for the selected brand
- [ ] Output leads with outcomes, not features
- [ ] Output uses power verbs
- [ ] Output matches brand voice (bold, authoritative, forward-thinking)
- [ ] Output matches brand tone (confident, aspirational, direct)
- [ ] Guardrails are respected (no passive headlines, no "simple"/"easy", no clichés)
- [ ] Agent summarized which guidelines were applied
