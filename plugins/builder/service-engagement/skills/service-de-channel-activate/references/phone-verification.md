---
name: service-de-channel-activate-phone-verification
description: "Load when service-de-channel-activate's Stage 3 read comes back DeploymentStatus=Error on a WhatsApp channel with MessagingChannelUsage.ErrorDetails containing NUMBER_NOT_VERIFIED or REVERIFICATION. Covers the phone-number OTP verification sub-flow: prompting for SMS/voice, requesting and validating the verification code via the Connect livemessage/whatsapp/verification endpoints (classified by the body's success field), and retrying activation once verification succeeds. DO NOT load this for any other ErrorDetails reason, for non-WhatsApp message types, or during the normal happy-path activation run."
metadata:
  version: "1.0"
  related-skills: service-de-channel-activate
---

# Stage 3.2: WhatsApp phone number verification (only if ErrorDetails contains NUMBER_NOT_VERIFIED or REVERIFICATION)

**This stage only runs for WhatsApp channels whose activation failed because Meta hasn't verified the phone number.** The MCU shows `DeploymentStatus=Error`, `ErrorReason=ProvisioningError` (there is no dedicated `ErrorReason` for this), and `ErrorDetails` like:

```text
WhatsAppNumberRegistrationError__WhatsApp number registration failed <phone-id>: NUMBER_NOT_VERIFIED (code 100, subcode 2593005) [fbtrace_id …]: Phone number is not verified through sms or voice, …
```

Expect the string to be truncated: `ErrorDetails` is capped at 255 chars and Meta's message comes last, so it usually ends mid-word (as above). Don't treat the cut-off as an error or try to recover the rest — all the skill needs is the `NUMBER_NOT_VERIFIED (code 100, subcode 2593005)` part (or `REVERIFICATION (code 133006, …)`), which sits right after the phone id and always survives. Match on that, never on the Meta message text. We use the two Connect REST verification endpoints via `sf api request rest`, which manages OAuth internally — no token extraction needed.

**Both endpoints return the same body: `{"success": <bool>, "errorMessage": <string|null>}`** — nothing else. There is no `displayNumber` and no Meta error code in the Connect response (the Setup UI gets those over a different, Aura-only path). Meta-side failures come back as a **2xx with `success:false`**, not as a 4xx, so classify by `success` first and status second.

#### Step 1: Prompt for verification method

Go straight from the Stage 3 read into this prompt, in the same response — don't emit a `provisioning-error` first, and don't present the activation failure as the end of the run. This is a planned pause for user input, not a failure. Ask:

```text
Activation paused: Meta hasn't verified this WhatsApp phone number yet
(NUMBER_NOT_VERIFIED). We can verify it now with a one-time code sent to the number.

How should we send the verification code?

  [1] SMS (text message)
  [2] Voice call
  [3] Cancel — leave the channel inactive for now

Choice [1/2/3]:
```

Record `{CODE_METHOD}` as `"SMS"` or `"VOICE"`. Show the reason token actually seen (`NUMBER_NOT_VERIFIED` or `REVERIFICATION`). On `3`, emit `{ok:false, kind:"verification-declined", mcuId, errorDetails, hint:"Phone number not verified. Re-run activation when ready to verify — the MCU stays in Error, which is a valid retry source."}` and stop.

#### Step 2: Request verification code

```bash
sf api request rest \
  "/services/data/v{API_VERSION}/connect/livemessage/whatsapp/verification/request?numberId={PHONE_NUMBER_ID}&codeMethod={CODE_METHOD}" \
  --method POST \
  --target-org '{ORG_ALIAS}' \
  --header 'Accept: application/json' \
  --body '{}' \
  --include \
  > /tmp/amc-verify-request.txt 2>&1
```

`{PHONE_NUMBER_ID}` is `{MESSAGING_PLATFORM_KEY}` from Stage 1. `--include` prints the HTTP status/headers block ahead of the body — read the status from the `HTTP/x.y NNN` line (as in Stage 2), not `head -1`. There's no blank line between headers and body, so take the body from the first line starting with `{`:

```bash
HTTP_CODE=$(grep -m1 -oE '^HTTP/[0-9.]+ [0-9]{3}' /tmp/amc-verify-request.txt | awk '{print $2}')
SUCCESS=$(sed -n '/^{/,$p' /tmp/amc-verify-request.txt | jq -r '.success')
```

Verified live on sdb6 (2026-10-20, `codeMethod=SMS`): `HTTP/1.1 201` with body `{"errorMessage": null, "success": true}`.

**Important:** The endpoint expects query parameters, not a JSON body. Pass `numberId` and `codeMethod` as URL parameters. Still send `--body '{}'` (not `--body ''`): `sf api request rest` treats an empty body string as no body and fails locally with `No 'mode' found in 'body' entry` before the request is issued, so an empty `{}` object is the way to make a body-less POST reach the endpoint.

| HTTP status | Body | Handling |
| --- | --- | --- |
| 2xx | `{"success": true, "errorMessage": null}` | Code sent. Continue to Step 3. |
| 2xx | `{"success": false, "errorMessage": "..."}` | Meta rejected the request (commonly: a code was requested too recently). Emit `{ok:false, kind:"verification-request-failed", message:"<errorMessage>", hint:"Meta may be rate-limiting code requests. Wait a few minutes, then retry activation."}`. Surface `errorMessage` verbatim — don't paraphrase or guess a Meta code. |
| 400 | `[{"errorCode":"INVALID_API_INPUT", ...}]` | A query param is missing (`numberId is required` / `Either codeMethod or verificationCode is required`) — a skill bug, not a user error. Emit `{ok:false, kind:"transport", status:400, message}`. |
| 401 | (empty) / `INVALID_SESSION_ID` | SF session invalid. Emit `{ok:false, kind:"auth"}`. |
| 404 | HTML | Endpoint unavailable. Emit `{ok:false, kind:"transport", status:404, hint:"Verification endpoint not available — check API version"}`. |
| 500 | `[{"errorCode":"UNKNOWN_EXCEPTION", "message":"Failed to process WhatsApp verification: ..."}]` | Server-side failure. Emit `{ok:false, kind:"transport", status:500, message}`. |

#### Step 3: Prompt for verification code

```text
A {CODE_METHOD} verification code has been sent to this channel's WhatsApp phone number.
Please check the device and enter the 6-digit code:

Code: 
```

Read user input, trim whitespace, **remove any hyphens**, record as `{VERIFICATION_CODE}`. Must be exactly 6 digits after hyphen removal. Users often enter codes like `123-456`; we must strip the hyphen and send `123456` in the request body.

#### Step 4: Validate verification code

```bash
sf api request rest \
  "/services/data/v{API_VERSION}/connect/livemessage/whatsapp/verification/validate?numberId={PHONE_NUMBER_ID}&verificationCode={VERIFICATION_CODE}" \
  --method POST \
  --target-org '{ORG_ALIAS}' \
  --header 'Accept: application/json' \
  --body '{}' \
  --include \
  > /tmp/amc-verify-validate.txt 2>&1
```

**Important:** The endpoint expects query parameters, not a JSON body. Pass `numberId` and `verificationCode` as URL parameters. Send `--body '{}'` rather than `--body ''` — an empty body string makes `sf api request rest` fail locally with `No 'mode' found in 'body' entry` before the POST is sent.

The response has the same shape as Step 2: a successful validate returns `HTTP/1.1 201` with exactly `{"errorMessage": null, "success": true}`. Parse it the same way and branch on `success`:

```bash
HTTP_CODE=$(grep -m1 -oE '^HTTP/[0-9.]+ [0-9]{3}' /tmp/amc-verify-validate.txt | awk '{print $2}')
SUCCESS=$(sed -n '/^{/,$p' /tmp/amc-verify-validate.txt | jq -r '.success')
```

| HTTP status | Body | Handling |
| --- | --- | --- |
| 2xx (201 expected) | `{"errorMessage": null, "success": true}` | Number is verified — nothing else comes back (no confirmation text, no display number). Continue to Step 5 (retry activation). |
| 2xx | `{"success": false, "errorMessage": "..."}` | Meta rejected the code (wrong code, guessing too fast, or too many attempts — the response doesn't say which beyond `errorMessage`). Show `errorMessage` verbatim and ask: "Try another code? [y/n]". If `y`, repeat Step 3 — **don't** request a new code — up to 3 validate attempts total. If `n` or after 3 failures, emit `{ok:false, kind:"verification-failed", message:"<last errorMessage>", hint:"Verification code validation failed. If Meta reports too many attempts, wait before retrying activation."}`. |
| 400 / 401 / 404 / 500 | as in Step 2 | Same handling as Step 2. |

> **Don't branch on Meta codes `136024` / `136025`.** The Setup UI distinguishes "too many attempts" from "wrong code" using those codes, but Connect returns only `errorMessage` — the codes never reach the skill.

#### Step 5: Retry activation after verification

The phone number is now verified. Return to Stage 2 (PATCH activation) with a retry counter to avoid infinite loops. Maximum 1 retry after verification.

If the second activation attempt fails again with `ErrorDetails` containing `NUMBER_NOT_VERIFIED` or `REVERIFICATION`, emit `{ok:false, kind:"verification-failed", errorDetails:"<ErrorDetails>", hint:"Phone number verification succeeded but Meta still reports the number unverified — check the number in Meta Business Manager"}`. Any other `Error` on the retry → the normal `provisioning-error` envelope (Stage 3).

If the second activation succeeds (`Active`), proceed to Stage 4 as normal.
