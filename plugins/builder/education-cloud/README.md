# Salesforce Education Cloud

Five workflows for Education Cloud foundation, academic calendars, course catalogs,
institutional hierarchies, and the packaged Student Recruitment Agent.

## Installation

Once Education Cloud is available in the Salesforce public marketplace, install and activate it:

```text
/plugin marketplace add forcedotcom/sf-skills
/plugin install education-cloud@salesforce
/reload-plugins
```

Confirm these five skills in the refreshed host inventory before starting a task:

| Skill | Capability |
| --- | --- |
| `education-cloud-domain-configure` | Enable Education Cloud foundation and domains |
| `education-cloud-academic-calendar-generate` | Generate academic years, terms, sessions and registration windows |
| `education-cloud-course-catalog-migrate` | Migrate courses into LearningCourse records |
| `education-cloud-multi-campus-configure` | Configure institutional hierarchies and BusinessProfile records |
| `education-cloud-student-recruitment-agent-configure` | Configure the packaged Student Recruitment Agent |

Version 0.1.0 is pending public publication. Marketplace registration alone does not establish availability.
This plugin adds no agents, commands, hooks or MCP servers.

## Example requests

- Enable Education Cloud recruitment and admissions domains.
- Generate an academic calendar with semester terms and sessions.
- Migrate our course catalog into Education Cloud LearningCourse records.
- Configure a multi-campus institutional hierarchy with Business Profiles.
- Set up the Education Cloud Student Recruitment Agent for admissions and campus tours.
- Set up student enrollment.

Salesforce Development can recommend this plugin for matching tasks. Installation requires
user acceptance, followed by reload and a refreshed inventory. An installed Education Cloud
plugin is excluded from installation recommendations.

## Prerequisites

Use an authenticated, appropriately licensed Education Cloud org with the required edition,
foundation settings and running-user access. Each workflow checks its own prerequisites.
Student Recruitment Agent also requires Agentforce provisioning, Einstein for Education Cloud,
Data Cloud and beta access. Some grounding, Builder and channel deployment steps require
manual Setup UI work.

Choose a transport that supports the selected skill's operations and follow that skill's
execution rules. Multi-campus configuration permits authenticated Salesforce CLI as a
fallback when its preferred transport is unavailable. This does not establish CLI support
for the other workflows.

## Related capabilities

`relatedSkills` metadata does not install or load another plugin. Before delegating to an
optional skill, check the host inventory. If it is absent, propose installation of its owning
plugin, obtain user acceptance, reload and confirm the refreshed inventory.

| Capability | Owning plugin |
| --- | --- |
| Generic Agentforce authoring with `agentforce-generate` | `agentforce-adlc@salesforce` |
| Platform custom fields, objects, validation rules, permission sets, metadata deployment and sharing configuration | `salesforce-development@salesforce` |
| Education foundation and multi-campus configuration | Included in this plugin |

## Discovery scope

Recommendations cover the bundled Education Cloud workflows. Generic office calendars,
commerce catalogs, employee recruiting and field-service territory hierarchies are outside
this plugin's scope. Student enrollment requests lead to the packaged recruitment workflow;
they do not imply a general enrollment-management capability.

Education domain anchors apply to proactive recommendations, explicit discovery and bypass
advice. Ambiguous anchors require a qualifying companion. Companions are tokens anywhere in
the prompt; they do not require adjacent phrases. Specific object names such as LearningCourse,
BusinessProfile and StudentRecruitmentAgent can qualify alone.
