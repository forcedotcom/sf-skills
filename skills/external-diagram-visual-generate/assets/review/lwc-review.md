# LWC Code Review Template

## Gemini Review Prompt

```
Review this Lightning Web Component for best practices:

JAVASCRIPT:
[paste JS code]

HTML TEMPLATE:
[paste HTML code]

REVIEW CATEGORIES:

1. ACCESSIBILITY (A11Y)
   - ARIA labels and roles
   - Keyboard navigation
   - Screen reader compatibility

2. PERFORMANCE
   - Wire service usage
   - Rendering optimization
   - Event handling

3. SECURITY
   - Locker Service compliance
   - XSS prevention

4. BEST PRACTICES
   - Component lifecycle
   - Error handling
   - Data binding

5. SALESFORCE PATTERNS
   - Lightning Data Service
   - Navigation service
   - Toast notifications

OUTPUT FORMAT:
JSON with summary, issues array, accessibility score, and overall score
```

## Usage

```bash
gemini "Review this LWC component: [paste code]" -o json
```
