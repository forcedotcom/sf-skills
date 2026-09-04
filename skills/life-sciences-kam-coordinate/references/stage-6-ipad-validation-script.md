# On-Device (iPad) Validation Script (KAM)

Shown to the admin at the very end of the workflow — **after the mobile metadata cache reaches `Status='Active'`** (Stage 6 gate passed) and the final summary is displayed. Display the script **verbatim** to the admin so they can hand it to the KAM user, then **wait for the user to confirm** each step succeeded on the device. Once the user confirms, the setup is complete.

The credentials in Step 1 are the KAM user created in Stage 6 (the user whose username contains `kam`). The account (`Partners Healthcare`), the objective/template (`Immunexis: Secure Q3 Formulary Position`), and its Assessment Tasks are the records created in Stage 5 — present them exactly as named below.

## Script (display verbatim)

```markdown
Here are the refined steps to validate on the Life Sciences Mobile Application (iPad).

Step 1 — Log in to the Life Sciences Mobile Application
Open the application on your iPad, enter your credentials, and verify that the home screen loads successfully.

Step 2 — Create a new Account Plan
Tap Account Plan in the top navigation bar, then tap New.
Enter an Account Plan Name.
Search for and select your target account (for example, Partners Healthcare).
Fill out the SWOT Analysis, Customer Landscape, and Competitive Landscape sections as needed.
Tap Save. You should now see your newly created Account Plan.

Step 3 — Import an objective template
Navigate to the Account Plan Objectives tab and tap Import Template.
Locate the template you want to use (such as Immunexis: Secure Q3 Formulary Position) and tap to expand the hierarchy.
Tap Select All, then tap Next.
Review your selections and tap Import.
The assessment tasks from the template will now appear under your Action Plan.

Step 4 — Complete a task and sync your data
Tap to edit any of your new tasks, change the status to Completed, and tap Done.
Once you are finished updating tasks, initiate a data sync on your device.
Note: Because your data calculates securely on the server, the progress bar on your Action Plan won't move the exact instant you tap "Completed." It will advance as soon as your sync finishes.
```

Once the user confirms, this is the end of the setup.
