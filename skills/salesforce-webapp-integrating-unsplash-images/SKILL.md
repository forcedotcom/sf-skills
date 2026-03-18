---
name: salesforce-webapp-integrating-unsplash-images
description: Adds high-quality Unsplash images to React pages. Use when the user asks to add a hero image, background image, placeholder image, stock photo, decorative image, or any Unsplash-sourced imagery to the web application.
---

# Unsplash Images

## When to Use

Use this skill when:
- Adding hero banners, section backgrounds, or decorative images
- The user asks for stock photography or placeholder images
- A page needs visual appeal without custom assets

---

## Step 1 — Determine image purpose

Identify what the image is for:

- **Hero / banner** — full-width background behind text or a CTA
- **Section accent** — smaller image alongside content (stats, testimonials, features)
- **Card thumbnail** — image inside a card component
- **Background texture** — subtle decorative background

If unclear, ask:

> "Where should the image appear — as a hero banner, a section accent, or a card thumbnail?"

---

## Step 2 — Select the right Unsplash URL format

Read `implementation/usage.md` for the full reference. Key rules:

1. **Always use `images.unsplash.com/photo-{id}` format** with explicit `w` and `q` parameters.
2. **Never use `source.unsplash.com`** — it is deprecated and returns 404s.
3. **Pin every image by its photo ID** — never rely on random or search endpoints.

---

## Step 3 — Validate image URLs

Before using any Unsplash URL in code:

1. Open the URL in a browser or fetch it to confirm it returns a 200 status and a valid image.
2. If the URL returns a 404, redirect loop, or broken image, **discard it** and pick a different photo ID.
3. Never ship a URL you have not personally verified.

---

## Step 4 — Implementation

Read `implementation/usage.md` and follow the instructions there.

---

## Verification

Before completing:

1. Confirm every Unsplash URL loads a valid image (no 404, no redirect loops).
2. Confirm `alt` text is set appropriately (empty `alt=""` for decorative, descriptive for meaningful).
3. Run from the web app directory:

```bash
cd force-app/main/default/webapplications/<appName> && npm run lint && npm run build
```

- **Lint:** MUST result in 0 errors.
- **Build:** MUST succeed.
