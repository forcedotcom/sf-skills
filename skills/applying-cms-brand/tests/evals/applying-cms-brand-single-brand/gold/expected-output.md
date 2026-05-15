# Expected Output

## Agent Behavior

1. Agent calls `search_brands` with a general query
2. Agent finds one brand ("Acme Corp Brand") and confirms with user: "I found the brand 'Acme Corp Brand'. Should I apply this brand's guidelines to the content?"
3. After user confirms, agent calls `get_brand_instructions`
4. Agent applies brand guidelines and produces branded email content

## Expected Branded Email

The generated email should:
- Use a professional yet approachable voice
- Have a warm, encouraging, empowering tone
- Address the reader directly with "you"
- Use active voice
- Keep sentences under 20 words
- Contain no more than 1 exclamation mark per paragraph
- Not use superlatives ("best", "fastest", "most powerful")
- Incorporate key messages where natural (innovation made simple, your success is our priority)

## Example Branded Output

"Hi, welcome to Acme Corp. We're glad you're here.

You now have access to tools designed to help you succeed. Here's how to get started:

1. Set up your profile so we can personalize your experience.
2. Explore the dashboard to see what's available to you.
3. Reach out to our team if you need guidance along the way.

Your success drives everything we do. We're here to support you at every step."

## Evaluation Criteria

- [ ] Agent searched for brands before generating content
- [ ] Agent confirmed brand selection with user
- [ ] Agent extracted brand instructions before generating content
- [ ] Output matches brand voice (professional yet approachable)
- [ ] Output matches brand tone (warm, encouraging, empowering)
- [ ] Content rules are respected (active voice, short sentences, "you" addressing)
- [ ] Guardrails are not violated (no competitor names, no performance guarantees)
