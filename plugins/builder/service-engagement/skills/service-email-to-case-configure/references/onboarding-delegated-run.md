# Pre-scan, delegated runs, and wording

Read this at step 1 of the Workflow, in both entry modes. The generic delegation rules (skip the orientation menu, announce writes, hand control back, never fabricate a value) apply as the orchestrator defines them. This file holds only what is specific to Email-to-Case.

**Entry mode.** `delegationFrom` set means an orchestrator called you this turn and `intent` carries what to build; anything the `intent` states (a routing email, an owner, a toggle choice) counts as the user's answer and is not asked again. `delegationFrom` absent means a direct user: their first message plays the role of the `intent`, and anything it leaves out is asked. Either way, a value that is neither in the `intent` nor given by the user is asked for. It is never invented.

## 1. Pre-scan: what is already set up

After the org read (the read-only pre-scan does not wait for `gate`), run `requests settings`, dispatch it, save the response as the **initial read**, and run `read --response <file>`. The output is the whole `CaseSettings` record. Classify with these fields:

| Field in `read` output | Means |
|---|---|
| `emailToCase.enableEmailToCase` | Email-to-Case is on. Once true it stays on. |
| `emailToCase.enableOnDemandEmailToCase` | On-Demand is on. Addresses need it. |
| `emailToCase.enableHtmlEmail`, `notifyOwnerOnNewCaseEmail`, `enableE2CDeduplicateAttachments`, `showWordCountInComposer`, and top-level `enableDraftEmails` | The optional toggles as they are now. |
| `emailToCase.routingAddresses` (one object or a list) | Existing addresses. A requested address already exists when its `routingName` or `emailAddress` matches. |
| `defaultCaseOwner`, `defaultCaseUser`, `useSystemUserAsDefaultCaseUser` | Support Settings already configured. |

| Pre-scan finds | The intent says | Action |
|---|---|---|
| `enableEmailToCase` absent or false | n/a | Nothing set up. Proceed; announce each write. If only `enableOnDemandEmailToCase` is missing while Email-to-Case is on, proceed the same way and leave out the permanence sentence. |
| On, and every requested toggle and address is already there | n/a | **No change.** Say what is there, run `verify`, hand back. No write, no confirmation. |
| On, and the intent only adds an address that is not there | Implies "add" | Announce the existing setup and add it. No question beyond the single confirmation (§2). |
| On, and the intent wants a different value for a setting that already has one | Implies "override" | Ask once, naming the old and new value. |
| On, and the intent does not say what to do | Silent | Ask once: make no changes, override the previous settings, or just add to them. |

On an org that already has Email-to-Case, build the source file from **only what the user chose to change** plus the two required switches (already on). Do not copy the template's default toggles: they would switch back on a toggle an admin turned off. A source file that adds no address needs `--no-addresses-ok` on `validate-casesettings.py` (step 8), and `phase-b` then skips. Support Settings keep their current values unless the user asks to change one (`--overwrite-support-settings`). Editing or deleting an existing routing address is not supported here: say so and offer to add a new one.

## 2. One confirmation before the first write

Ask once, before the first write, in every mode and for every org type. Plan approval upstream does not replace it.

- Name the org and its type (`gate` read it): "I'll set up email support on `<org>` (`<sandbox | production>`)."
- Only when `enableEmailToCase` is not yet on, add that turning it on is permanent and affects the whole org.
- Production, or an org type `gate` cannot read: the same yes unlocks `--confirm-production`. Never add the flag before the user says yes in this run.
- Nothing to change: no write, so no confirmation.

## 3. Wording by `discoveryMode`

`"guided"` means ask about the process in the customer's words and keep Salesforce terms out of the question. Any other mode, or a direct user, uses the Salesforce terms in the Workflow. The writes are the same either way.

| Salesforce terms | Guided wording |
|---|---|
| Customer-facing email address for the routing address | What email address do your customers write to for support? |
| Address type `EmailToCase` / `Outlook` / `GmailOAuth` | Where does this mailbox live: will you forward its mail to Salesforce, or connect a Microsoft 365 or Gmail account? |
| Case origin and case priority for the address | What should show as the source of cases from this address (usually Email), and how urgent should they be by default? |
| Per-address Default Case Owner | Should emails to this address go to a specific person or team, or follow your usual case assignment? |
| Default Case Owner | When a new case arrives and no assignment rule claims it, who should it land with: a person or a team's queue? |
| Automated Case User | Automatic case actions such as escalations and rule-based assignment are recorded under one user. Should that be a named person or the standard system user? |
| Enable HTML email | Let agents send formatted emails with images and styling. |
| Eliminate duplicate email attachments | Don't save an attachment again if it is already on the case. |
| Show word count in composer | Show a word count while agents write a reply. |
| Notify case owners on new emails | Tell the case owner when a new email arrives on their case. |
| Enable Email Drafts | Let agents save a reply as a draft. |
| Turning on Email-to-Case is permanent and org-wide | Once email support is on it can't be switched off, and it applies to the whole org. |

Guided mode never says Metadata API, `CaseSettings`, On-Demand, or a field name. When you state the optional toggles that will be turned on, state them in the guided wording above.

## 4. Permission and availability messages

- **The user lacks the setup permission** (the Customize Application check fails, or a write is refused for permissions): "Please ask your admin to enable the setup permission for Email-to-Case for you, using https://help.salesforce.com/s/articleView?id=service.setting_up_email-to-case.htm&type=5". Make no further writes.
- **Email-to-Case is not available in the org** (the skill is unavailable or cannot run): give the same article so the user can set it up from Setup, and stop.

## 5. After the write: validate and hand back

Run `verify`, then report in the mode's wording: what is now set, what was left as it was, and what the user still has to do (forward mail to the generated address, verify the routing address). The inbound-email proof (`references/end-to-end-proof.md`) is optional: offer it once on a direct run, never on a delegated run (only if asked). When delegated, then hand control back: no "what next?", no offer to configure another feature.
