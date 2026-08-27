/*
 * Anonymous Apex — Experience Cloud self-registration records (idempotent).
 *
 * Ported verbatim from reference org-setup.mjs enableSelfRegistration
 * (Account create lines 647-651, NetworkSelfRegistration create lines 710-717).
 * Apply this template as-is; do NOT invent your own self-reg Apex.
 *
 * These are substeps 4 of SKILL.md step 6. The network-meta.xml edits
 * (Edit A pre-main-deploy, Edit B + redeploy in step 6) happen FIRST — see
 * assets/network-selfreg-xml-recipe.md. Run the idempotency queries described in
 * references/self-registration.md BEFORE each snippet so you skip work that
 * already exists.
 *
 * Blocks 4a and 4b are SEPARATE `sf apex run` invocations — run 4a, capture the
 * Account Id from its ACCOUNT_CREATED: debug line (or the idempotency query),
 * then run 4b. Do NOT paste both blocks into one execution.
 *
 * accountName is a free-form display value that may contain punctuation
 * (e.g. "O'Brien Rentals & Co."). It is created via Apex (NOT
 * `sf data create record --values`) precisely because the CLI parses --values as
 * space-separated key=value pairs and cannot safely carry a name with a space,
 * quote, or &. Encode accountName as an Apex string literal: single-quote it and
 * escape \ -> \\ and ' -> \'.
 */

/* ---- 4a. Create the membership Account (skip if the idempotency query already
 *          found one). <AccountNameLiteral> = apex-escaped accountName. ---- */
Account acct = new Account(Name = <AccountNameLiteral>);
insert acct;
System.debug('ACCOUNT_CREATED:' + acct.Id);

/* ---- 4b. Create NetworkSelfRegistration linking that Account to the site's
 *          Network (skip if the idempotency query found one for this NetworkId).
 *          Run as a SEPARATE execution from 4a.
 *          <AccountId>  = the Account Id from 4a (or the pre-existing one).
 *          <NetworkId>  = SELECT Id FROM Network WHERE Name = '<siteName>'. ---- */
NetworkSelfRegistration nsr = new NetworkSelfRegistration();
nsr.AccountId = '<AccountId>';
nsr.NetworkId = '<NetworkId>';
insert nsr;
System.debug('NSR_CREATED:' + nsr.Id);
