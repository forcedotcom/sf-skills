---
name: service-de-channel-activate-phone-verification
description: "Load when service-de-channel-activate's Stage 3 read comes back with MessagingChannelUsage.ErrorReason === \"VERIFICATION_REQUIRED\" (WhatsApp channels only). Covers the phone-number OTP verification sub-flow: prompting for SMS/voice, requesting and validating the verification code via the Connect livemessage/whatsapp/verification endpoints, and retrying activation once verification succeeds. DO NOT load this for any other ErrorReason, for non-WhatsApp message types, or during the normal happy-path activation run."
metadata:
  version: "1.0"
  related-skills: service-de-channel-activate
---

# Stage 3.2: WhatsApp phone number verification (only if ErrorReason === "VERIFICATION_REQUIRED")

**This stage only runs for WhatsApp channels when activation fails with `VERIFICATION_REQUIRED`.** The phone number must be verified with Meta before it can be registered. We use the two Connect REST verification endpoints via `sf api request rest`, which manages OAuth internally — no token extraction needed.

#### Step 1: Prompt for verification method

Ask the user:

```text
WhatsApp phone number verification required.

How should we send the verification code?

  [1] SMS (text message)
  [2] Voice call

Choice [1/2]:
```

Record `{CODE_METHOD}` as `"SMS"` or `"VOICE"` based on response.

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

`{PHONE_NUMBER_ID}` is `{MESSAGING_PLATFORM_KEY}` from Stage 1. `--include` prints the HTTP status/headers block ahead of the body — read the status from that block rather than a trailing marker line.

**Important:** The endpoint expects query parameters, not a JSON body. Pass `numberId` and `codeMethod` as URL parameters. Still send `--body '{}'` (not `--body ''`): `sf api request rest` treats an empty body string as no body and fails locally with `No 'mode' found in 'body' entry` before the request is issued, so an empty `{}` object is the way to make a body-less POST reach the endpoint.

| HTTP status | Body | Handling |
| --- | --- | --- |
| 200 or 204 | Empty or `{"success": true, "displayNumber": "..."}` | Success. Continue to Step 3. Optionally extract `displayNumber` from response to show user which phone will receive the code. |
| 400 | `[{errorCode: "...", message: "..."}]` | Business error. Common: code already requested recently (Meta rate limit). Emit `{ok:false, kind:"verification-request-failed", errorCode, message, hint:"Meta may be rate-limiting requests. Wait a few minutes and retry."}`. |
| 401 | (empty) | Bearer token invalid. Emit `{ok:false, kind:"auth"}`. |
| 404 | HTML | Endpoint unavailable. Emit `{ok:false, kind:"transport", status:404, hint:"Verification endpoint not available — check API version"}`. |

#### Step 3: Prompt for verification code

```text
A {CODE_METHOD} verification code has been sent to the phone number.
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

| HTTP status | Body | Handling |
| --- | --- | --- |
| 200 or 204 | Empty or `{"success": true}` | Success. Number is now verified. Continue to Step 5 (retry activation). |
| 400 | `[{errorCode: "...", message: "..."}]` | Invalid code or rate limit. Parse error message: if "wrong code" or "guessing too fast", prompt: "Invalid verification code. Try again? [y/n]". If `y`, repeat Step 3 (up to 3 total attempts). If `n` or after 3 failures, emit `{ok:false, kind:"verification-failed", hint:"Verification code validation failed"}`. |
| 401 | (empty) | Bearer token invalid. Emit `{ok:false, kind:"auth"}`. |

Common Meta error codes from the UI component:
- `136024`: Too many recent attempts (rate limit). Emit `{ok:false, kind:"verification-failed", hint:"Too many verification attempts. Wait a few minutes and retry activation."}`.
- `136025`: Wrong code or guessing too fast. Allow retry (up to 3 attempts total).

#### Step 5: Retry activation after verification

The phone number is now verified. Return to Stage 2 (PATCH activation) with a retry counter to avoid infinite loops. Maximum 1 retry after verification.

If the second activation attempt also fails with `VERIFICATION_REQUIRED`, emit `{ok:false, kind:"verification-failed", hint:"Phone number verification succeeded but activation still reports VERIFICATION_REQUIRED — unusual, check Meta Business Manager"}`.

If the second activation succeeds (`Active`), proceed to Stage 4 as normal.
