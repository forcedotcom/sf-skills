# Expected Output

## Agent Behavior

1. Agent calls `search_brands` to find available brands
2. Agent receives empty results (no brands found)
3. Agent does NOT attempt to generate branded content without guidelines
4. Agent informs the user and offers alternatives:
   - "No brands found in Salesforce CMS. To use branding:
     1. Create a brand in Salesforce CMS (Content Type: sfdc_cms__brand)
     2. Provide brand guidelines directly in this conversation
     Would you like to proceed without CMS branding, or provide guidelines manually?"

## Expected Content Output

No branded content should be generated. The agent should:
- Clearly communicate that no brands were found
- Explain how to create a brand in CMS
- Offer the alternative of providing guidelines manually
- Wait for user direction before proceeding

## Evaluation Criteria

- [ ] Agent searched for brands before attempting to generate content
- [ ] Agent did NOT generate branded content without guidelines
- [ ] Agent informed user that no brands were found
- [ ] Agent offered actionable alternatives (create in CMS or provide manually)
- [ ] Agent did NOT hallucinate or assume brand guidelines
- [ ] Agent waited for user response before proceeding
- [ ] Error message was clear and helpful (not technical/confusing)
