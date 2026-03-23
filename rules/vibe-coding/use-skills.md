# SKILLS REQUIREMENTS

## Mandatory Skill Usage
Before generating ANY Salesforce code or metadata, check available Skills and use the matching one. Never generate Salesforce code freehand when a relevant Skill exists.

## Skill Routing
- **Apex class requests** → Use Apex Class Writer skill. Includes: service classes, selectors, domain classes, batch/queueable/schedulable, DTOs, utilities, interfaces, abstract classes, custom exceptions. Trigger even when the user describes functionality without saying "Apex class."
- **Trigger requests** → Use Trigger Framework Scaffolder skill.
- **Validation rule requests** → Use Validation Rule Writer skill.
- **Permission/security questions** → Use Permission Set Auditor skill.
- **Package.xml/deployment requests** → Use Package.xml Generator skill.
- **Custom metadata questions** → Use Custom Metadata Advisor skill.
- **Field-level security requests** → Use FLS Matrix Generator skill.
- **Media search requests** → Use searching-media skill. When the request involves finding, searching, getting, fetching, retrieving, locating, or adding existing visual media (images, logos, icons, photos, graphics, banners, thumbnails, hero images, backgrounds, company-logo), invoke `Skill(skill_name="searching-media")`. Never bypass by calling MCP tools directly or choosing a source on behalf of the user. Applies even for indirect requests like "need a logo" or "add a hero image".

## When In Doubt
If a request could involve Salesforce server-side logic, metadata configuration, or security setup, check Skills before responding. Prefer a Skill over general knowledge — Skills contain curated best practices specific to this org's standards.
