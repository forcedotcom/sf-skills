# Channel branch — Voice *(Coming soon)*

> **When to read this file.** Load it only if the user selected **Voice** at Checkpoint 3.

## Coming-soon channel — do not build supporting metadata

Voice is **not yet supported** as a first-class channel. Do not provision a phone number, stand up routing, configure Amazon Connect, or create adjacent objects "toward" the feature — that produces broken half-configurations. **Do not write a Voice setup plan, a "here's what I would do" outline, or a "planning-only" scaffold either** — describing the steps is still treating a coming-soon channel as a build target. The only correct output for a Voice selection is the verbatim hard-stop message below, followed by re-presenting the channel options. The channel-selection step treats Voice as a coming-soon option alongside Help Portal; the safe response is to steer the user to Web Chat:

> *"This feature is coming soon, please select Web Chat."*

## If the user insists on an existing number

If the user provides an **existing** phone number and asks you to wire it up, you may attempt it — but exit gracefully the moment the APIs aren't there:

- If the org's APIs to procure or attach a phone number are not available, **gracefully exit this branch.** Say something like: *"I can't set up Voice automatically in this org right now, so I'll skip it. You can add Voice later from Setup."* — then continue with any other selected channels.

Do not abort the whole setup over Voice. If Voice was one of several selected channels, report the skip plainly and proceed with the others.
