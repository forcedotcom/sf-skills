---
name: service-de-channel-routing-configure-named-queue
description: "Load when the caller of service-de-channel-routing-configure supplied {QUEUE} (a queue the user already named) and it has to be validated on the Queue routing path. Covers matching it against the eligible list, the unfiltered lookup when it isn't eligible, the three-way prompt (use anyway / pick eligible / create new), and the warning added to the success envelope. DO NOT load when no {QUEUE} was supplied — the normal Stage 3-Queue list applies."
metadata:
  version: "1.0"
  related-skills: service-de-channel-routing-configure
---

# Validating a queue the user named (`{QUEUE}`)

Match `{QUEUE}` against the Stage 3-Queue eligible list by `Id`, `DeveloperName`, or `Name`.

- **Match** → record `{QUEUE_ID}`, skip to Stage 5, no prompt.
- **No match** → look it up without the eligibility filters:

  ```bash
  sf data query --target-org '{ORG_ALIAS}' \
    --query "SELECT Id, Name, DeveloperName, QueueRoutingConfigId FROM Group WHERE Type='Queue' AND (DeveloperName='{QUEUE}' OR Name='{QUEUE}')" \
    --json
  ```

  If `{QUEUE}` is an Id (15 or 18 chars starting with `00G`), filter on `Id='{QUEUE}'` instead. Don't combine the two: comparing `Id` to a name fails the whole query with `INVALID_QUERY_FILTER_OPERATOR` ("invalid ID field").

  If it exists, tell the user exactly what's missing. Never silently accept it, and never silently fall through to "create new":

  ```text
  Queue '{QUEUE}' exists but isn't set up for messaging: {"it doesn't list Messaging Session as a supported object" | "it has no Omni-Channel routing configuration"}.
  The server will accept it, but the skill can't confirm sessions will route there.

    1) Use it anyway
    2) Pick an eligible queue from the list
    3) Create a new messaging queue
  ```

  On (1), record `{QUEUE_ID}`, add `"warning": "queue is not MessagingSession-capable / Omni-enabled"` to the success envelope, and continue to Stage 5. (2) → the normal numbered list. (3) → `references/queue-creation.md`.

- **No queue matches `{QUEUE}` at all** → say so, then show the normal numbered list.

Why the rule and the server disagree: see `references/gotchas.md` #10.
