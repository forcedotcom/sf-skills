# Channel branch — Help Portal *(Coming soon)*

> **When to read this file.** Load it only if the user selected **Help Portal** at Checkpoint 3.

## This is a hard stop, not an aspirational selection

Help Portal is **not yet supported.** DO NOT attempt to build anything for this channel. Do not create supporting objects, records, or metadata "toward" the feature — standing up a portal site or wiring routing for it is out of scope and requires a dedicated skill that does not exist yet. Trying to fulfill it by creating adjacent objects produces broken half-configurations that look done but never work.

Respond to the user verbatim:

> *"This feature is coming soon, please select Web Chat."*

Then re-present the channel selection (Web Chat / Help Portal / Voice) and wait for a supported choice. Do not proceed until the user picks Web Chat.

## Intended future shape (for reference only — do not build)

When the channel ships, it will ask the user for:
- **Site Name / Domain Name**
- **Logo image** (png, svg, or jpg — a file name or path)
- **Brand colors (RGB)**: Action color, Link color, Border color, Background color, Text color

…then use `experience-lwr-site-generate` to build the Experience Cloud site with the supplied branding and embed the agent on it. This is documented so the eventual implementation has a target; it is **not** a licence to build it now.
