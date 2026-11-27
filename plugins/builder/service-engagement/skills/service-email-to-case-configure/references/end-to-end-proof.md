# End-to-end proof (Act 3)

On a direct run, offer once to prove that inbound email creates Cases; on a delegated run only if the user asks. It is a live round-trip; skip it if declined. The skill never sends email. It orchestrates two human actions, then verifies with read-only queries.

1. **Address ownership.** Salesforce emails a confirmation link; `isVerified` flips only when the human clicks it. Tell the user to click it and **wait**.
2. **Send a test email.** Ask the user to send one real email from an external mailbox to the routing address's Salesforce-generated **email services address** (not the customer-facing address, which only receives mail once forwarding is configured). Ask who the sender was, and **wait**.
3. **Verify with evidence.** Run `requests cases [--supplied-email <external-sender-address>]` and dispatch it. Then run `requests messages --cases-response <file>`, dispatch that, and run:

```bash
python3 scripts/apply-casesettings.py cases --cases <cases-file> --messages <messages-file> \
    [--supplied-email <external-sender-address>]
```

Read-only (`dispatch_readonly` only). It checks `Case` where `Origin='Email'` (last 3 days, optionally narrowed by sender) plus the linked incoming `EmailMessage` rows (`Incoming=true`, `ParentId` = the new Case). It exits **non-zero if no matching Case has a linked incoming email**: the mail isn't processed yet (wait and re-run), or the address isn't verified. On success it prints the `Case` + `EmailMessage` evidence with `proven: true`.
