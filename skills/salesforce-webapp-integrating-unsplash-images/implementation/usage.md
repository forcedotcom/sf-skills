# Unsplash Images — Implementation Guide

## URL Format

Always use the direct `images.unsplash.com` format with explicit sizing:

```
https://images.unsplash.com/photo-{PHOTO_ID}?w={WIDTH}&q={QUALITY}
```

| Parameter | Purpose | Recommended values |
|-----------|---------|--------------------|
| `w` | Pixel width served by the CDN | `600` card, `800` section, `1200` hero, `1920` full-bleed |
| `q` | JPEG quality 1–100 | `80`–`85` (good balance of quality vs size) |

### Deprecated / broken formats — do NOT use

| Format | Why it fails |
|--------|-------------|
| `source.unsplash.com/random` | Deprecated; returns 404 |
| `source.unsplash.com/{WIDTH}x{HEIGHT}` | Deprecated; returns 404 |
| `source.unsplash.com/featured/?{query}` | Deprecated; returns 404 |

---

## How to find a valid photo ID

1. Go to [unsplash.com](https://unsplash.com) and search for the subject (e.g. "modern apartment").
2. Open a photo. The URL will look like `unsplash.com/photos/{slug}-{PHOTO_ID}` or `unsplash.com/photos/{PHOTO_ID}`.
3. The `PHOTO_ID` is the last hyphen-separated segment (e.g. `photo-1600596542815-ffad4c1539a9`).
4. Build your URL: `https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200&q=85`
5. **Test the URL** in a browser before committing.

---

## Declaring image constants

Define all Unsplash URLs as named constants at the top of the file. Never inline URLs in JSX.

```tsx
const HERO_IMAGE = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200&q=85";
const SECTION_IMAGE = "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=800&q=85";
```

---

## Rendering images in JSX

### Hero / banner (decorative — empty alt)

```tsx
<div className="relative w-full overflow-hidden rounded-2xl">
  <div className="relative aspect-[21/9] min-h-[280px] w-full md:aspect-[3/1]">
    <img
      src={HERO_IMAGE}
      alt=""
      className="h-full w-full object-cover"
      loading="eager"
      fetchPriority="high"
    />
    <div className="absolute inset-0 bg-black/40" />
    <div className="absolute inset-0 flex flex-col items-center justify-center px-4">
      {/* overlay content */}
    </div>
  </div>
</div>
```

Key points:
- `alt=""` for decorative images (screen readers skip them).
- `loading="eager"` and `fetchPriority="high"` for above-the-fold heroes.
- `object-cover` prevents stretching.
- Semi-transparent overlay (`bg-black/40`) ensures text readability.

### Section accent (meaningful — descriptive alt)

```tsx
<div className="relative min-h-[240px] overflow-hidden rounded-2xl">
  <img src={SECTION_IMAGE} alt="City skyline at sunset" className="h-full w-full object-cover" />
  <div className="absolute inset-0 bg-gradient-to-r from-black/20 to-transparent" />
</div>
```

### Card thumbnail

```tsx
<div className="aspect-[4/3] overflow-hidden bg-muted">
  <img
    src={imageUrl}
    alt=""
    className="h-full w-full object-cover transition-transform hover:scale-105"
    loading="lazy"
  />
</div>
```

Key points:
- `loading="lazy"` for below-the-fold images.
- `hover:scale-105` subtle zoom on hover.
- `bg-muted` fallback color while loading.

---

## Fallback when no image is available

Always provide a placeholder when the image URL may be null:

```tsx
{imageUrl ? (
  <img src={imageUrl} alt="" className="h-full w-full object-cover" />
) : (
  <div className="flex h-full items-center justify-center text-muted-foreground">
    No image
  </div>
)}
```

---

## Content Security Policy (CSP)

If the application enforces CSP headers, add `images.unsplash.com` to `img-src`:

```
img-src 'self' https://images.unsplash.com;
```

Other commonly needed origins for stock images:

| Origin | Purpose |
|--------|---------|
| `images.unsplash.com` | Unsplash photos |
| `images.pexels.com` | Pexels photos |
| `fonts.googleapis.com` | Google Fonts CSS |
| `fonts.gstatic.com` | Google Fonts files |

---

## Accessibility checklist

- [ ] Decorative images have `alt=""`
- [ ] Meaningful images have descriptive `alt` text
- [ ] Hero images use `loading="eager"` and `fetchPriority="high"`
- [ ] Below-fold images use `loading="lazy"`
- [ ] Text over images has sufficient contrast (use overlay like `bg-black/40`)
- [ ] All URLs verified to return a valid image (no 404s)

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using `source.unsplash.com` | Replace with `images.unsplash.com/photo-{id}?w=…&q=…` |
| Hardcoding an unverified URL | Open URL in browser first; replace if broken |
| Missing `w` parameter | Always set width — CDN returns full-res (5000px+) otherwise |
| `loading="lazy"` on hero | Use `loading="eager"` for above-the-fold images |
| No fallback for nullable URLs | Wrap in conditional with placeholder div |
| Inline URLs in JSX | Extract to named constants at file top |
