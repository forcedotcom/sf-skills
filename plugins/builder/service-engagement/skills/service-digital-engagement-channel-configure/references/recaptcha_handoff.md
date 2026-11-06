# reCAPTCHA handoff

The reCAPTCHA key is not exposed through any API or Metadata field, so this skill cannot read, set, or verify it. An admin completes it in Setup; the skill hands over a link and the steps.

## Rules

- Never write `captchaKey` or `isCaptchaEnabled` in the channel XML. A full-document deploy preserves a key the admin already set in Setup, so redeploying never clobbers it.
- Never say reCAPTCHA is configured or enabled, or that it is not. Say this skill does not set or check it; the admin completes the steps below and sees the result in Setup.
- Give a plain Setup link only. Never run `sf org open --url-only` or output any URL carrying a session token (`frontdoor`, `sid=`); those are credentials.
- The reCAPTCHA Verification section is hidden for Mobile-only channels. Do not offer these steps for a channel the user says is Mobile-only.

## When to raise it

- The user asks about reCAPTCHA, captcha, or bot protection: give the full handoff.
- Standalone, at the end of the output, unless the user said the channel is Mobile-only: one line, "This skill does not set or check reCAPTCHA; ask me for the Setup steps."
- Delegated: do not raise it.

## Build the link

1. Get the channel Id:
   ```bash
   sf data query -o <org> --json -q "SELECT Id FROM MessagingChannel WHERE DeveloperName='<CHANNEL_DEV_NAME>'"
   ```
2. Path: `/lightning/setup/LiveMessageSetup/<ChannelId>/view?lightning__channelType=EmbeddedMessaging`. Prefix it with the org's `instanceUrl` if known (`result.instanceUrl` from `sf org display --json`; never print or copy the access token), otherwise give the path.

3. No channel Id yet (the query returns no row, or the channel is not deployed): never deploy only to get one. Give the generic route, Setup → Messaging Settings → open the channel, with the admin steps below, and carry on with the rest of the flow.

## Limitation to tell the user

The link is plain, so it works only if the admin is already logged in to the org with Setup access. If not, they should log in first and then open the link, or go to Setup → Messaging Settings and open the channel.

## Admin steps

1. Have the reCAPTCHA key pair from Google ready.
2. Open the link and find the **reCAPTCHA Verification** section.
3. Check **Use reCAPTCHA** first. The **reCAPTCHA API Key Pair** field and **New API Key Pair** button stay greyed out until it is checked.
4. Select an existing key in **reCAPTCHA API Key Pair**, or click **New API Key Pair** and add yours.
5. Save. Setup does not allow saving with the box checked until a key pair is set.
