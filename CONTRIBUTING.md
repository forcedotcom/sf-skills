# Contributing Guide

Thank you for your interest in contributing. This project is open to
anyone, and the workflow below explains exactly how to submit changes
using a fork and a pull request.

## 1. Fork the Repository

To contribute, create your own copy:

1.  Open this repository on github.com.
2.  Click the **Fork** button in the top-right corner.
3.  Select your GitHub account as the destination.
4.  GitHub will create your personal fork at:
    `https://github.com/<your-username>/afv-library`.

## 2. Clone Your Fork

Clone your personal fork:

``` sh
git clone https://github.com/<your-username>/afv-library.git
cd afv-library
```

Add the original repository as the upstream remote:

``` sh
git remote add upstream https://github.com/forcedotcom/afv-library.git
```

## 3. Create a Branch

Create a new branch for your work:

``` sh
git checkout -b my-feature-name
```

Use a short, descriptive name.

## 4. Make Your Changes

Perform your edits or add new functionality. When ready:

``` sh
git add .
git commit -m "Describe your change clearly"
```

## 5. Push Your Branch

``` sh
git push origin my-feature-name
```

GitHub will display a **Compare & pull request** button.

## 6. Open a Pull Request

Once your branch is pushed to your fork, you can open a Pull Request
(PR) to propose merging your changes into this repository.

Unsure that your PR title is prefixed with  `feat:` or `fix:` as those will result in an update to the change log 
and inclusion in SF tooling. 

### 6.1 Start the Pull Request

**Option A --- From the GitHub banner (easiest)**\
After pushing your branch, GitHub shows a banner:

> "Compare & pull request"

Click it.

**Option B --- Manually**

1.  Go to your fork on GitHub:\
    `https://github.com/<your-username>/afv-library`
2.  Switch to your feature branch.
3.  Click the **Pull requests** tab.
4.  Click **New pull request**.
5.  Click **compare across forks**.

------------------------------------------------------------------------

### 6.2 Select the Correct Base and Compare Settings

Make sure GitHub is targeting the correct repositories and branches:

-   **Base repository:** `forcedotcom/afv-library`
-   **Base branch:** `main`
-   **Head repository:** `<your-username>/afv-library`
-   **Head branch:** your feature branch (`my-feature-name`)

Correct configuration:

    base: forcedotcom/afv-library → main
    compare: <your-username>/afv-library → my-feature-name

------------------------------------------------------------------------

### 6.3 Write the Pull Request Title

Use a clear, descriptive title. Examples:

-   "Add examples for Apex prompt templates"
-   "Fix typo in GPT-5 rule documentation"
-   "Improve structure of LWC prompt guidelines"

Avoid generic titles like "Update" or "Fix."

------------------------------------------------------------------------

### 6.4 Write a Detailed Pull Request Description

Include:

-   **What** you changed
-   **Why** you changed it
-   **How** it improves the library
-   **Any follow-ups or questions**

Suggested template:

    ### Summary
    Brief explanation of what this change adds or improves.

    ### Changes
    - List key changes
    - Mention new files or docs
    - Describe any refactoring

    ### Motivation
    Why this change is needed or helpful.

    ### Notes
    Anything reviewers should know or testing instructions.

------------------------------------------------------------------------

### 6.5 Submit the Pull Request

Click **Create pull request**.

------------------------------------------------------------------------

### 6.6 Automatic Checks

If the repository has CI or linting tools, GitHub will run checks.\
Fix any failures by updating your branch and pushing again.

------------------------------------------------------------------------

### 6.7 Discussion & Review

Maintainers may comment, request changes, or ask questions.

To update your PR:

``` sh
git add .
git commit -m "Address review feedback"
git push
```

Your PR updates automatically.

## 7. Address Review Feedback

If maintainers request changes:

``` sh
git add .
git commit -m "Update after review"
git push
```

Your PR updates automatically.

## 8. Keep Your Fork Updated

Sync your fork with the upstream repo before starting new work:

``` sh
git checkout main
git pull upstream main
git push origin main
```

## 9. Merge

A maintainer will merge your PR after approval.

## Summary

-   Fork the repo.
-   Clone your fork.
-   Create a branch.
-   Make changes.
-   Push the branch.
-   Open a PR.
-   Respond to feedback.
-   Keep your fork updated.