# Bulk content loading — a direct `getCmsContentByKeys` call

To read a KNOWN set of `contentKey`s in ONE authenticated Connect round-trip, call
the toolkit's `getCmsContentByKeys` directly. There is no batch-loader seam to
scaffold and nothing to register — the per-item hook/service (`useCmsItem` /
`CmsItemService`) is unchanged. Rendering N `<Type>Renderer`/`cms-<type>` cards
still works (each reads individually); reach for bulk only when the extra round-
trips matter and you already hold the keys.

## When to use it

On an explicit prompt to batch a list — e.g. *"bulk/batch-load the list"*, *"load
these in one request"*, *"optimize the list fetching"*, AND the caller already
knows the `contentKey`s (a curated set). Otherwise render per-item.

## The call

```ts
import { getCmsContentByKeys } from '@salesforce/ui-bundle-template-feature-cms-toolkit';
import type { CmsBulkResult } from '@salesforce/ui-bundle-template-feature-cms-toolkit';

// Best-effort: never throws (except on abort). Each requested key comes back as a
// CmsBulkResult with EITHER `body` OR `error`, echoing the requested contentKey.
const results: CmsBulkResult<NewsBody>[] = await getCmsContentByKeys<NewsBody>(
  ['M3ASD4KHASDB73', 'MCABCDEF123456'],
  { channelId },   // optional; omit to let the catalog supply it
);

for (const r of results) {
  if (r.error) {
    // unpublished / wrong-channel / absent → CmsNotFoundError (per-key isolation)
    console.warn(r.contentKey, r.error.message);
  } else {
    render(r.body);   // already unwrapped, envelope title lifted in
  }
}
```

- **Best-effort:** only an `AbortError` (via `options.signal`) rejects; every other
  per-key failure comes back as `r.error` (a `CmsNotFoundError`).
- **Match BY `contentKey`, never positionally** — each result echoes the requested
  key even though the toolkit remaps source→target internally.
- Keys are catalog-remapped (fail-open) and the channel resolves exactly as the
  single-key read — `references/package-api.md`.

## contentKey-only + mixed pages

Only `contentKey`s batch. A `CmsExternalRef` (public `unauthenticatedUrl`) has no
contentKey and is often a different channel/org — for news/structured content read it
with `getCmsContentByUrl` individually. A mixed list becomes 1 bulk call for the key
subset + N individual CDN fetches; wire the results into your own components. When you
render one card per ref instead, each card's independent read already isolates failures.
(A foreign `url` **media** ref is not fetched at all — its url is the asset src directly,
Rule 1 — so it neither batches nor needs an individual read.)

## Out of scope

No DYNAMIC feed ("latest 10 news") — `getCmsContentByKeys` reads KNOWN keys; it
does not discover or query a collection. Endpoint + response contract:
`references/package-api.md`. Failure rows: `references/failure-modes.md`.
