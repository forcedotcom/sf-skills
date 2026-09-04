/**
 * useCmsItem — single-content React hook (Init → src/cms/react/useCmsItem.ts).
 * Owns fetch state + a per-ref cache + inflight dedup (keyed by `ref.name`; never
 * throws — errors → state). Dispatches on ref type: CmsExternalRef (`url`) →
 * getCmsContentByUrl (CDN); CmsRef (`contentKey`) → getCmsContentByKey (Connect).
 *
 * StrictMode-safe (Rule 3): the request is SHARED, so cleanup only sets a local
 * `cancelled` flag gating setState — it never aborts; shared requests get no
 * AbortSignal; `inflight` self-cleans via `.finally(delete)`.
 */
import { useEffect, useState, useRef } from 'react';
import {
  getCmsContentByUrl,
  getCmsContentByKey,
  CmsDeliveryError,
  CmsDeliveryNotFoundError,
  ConnectApiError,
  CmsNotFoundError,
} from '@salesforce/ui-bundle-template-feature-cms-toolkit';
import type { AnyCmsRef, CmsRef } from '../shared/cmsCore.types';
import { CMS_CHANNEL_ID_FALLBACK } from '../shared/externalRefs';

interface UseCmsItemState<TBody> {
  body: TBody | undefined;
  loading: boolean;
  error: Error | undefined;
}

// Module-scoped: shared across every consumer of the hook in the app.
const cache = new Map<string, unknown>();
const inflight = new Map<string, Promise<unknown>>();

/** Shared request for a ref — NO abort signal. `CMS_CHANNEL_ID_FALLBACK` is passed
 *  as `options.channelId` only when set (empty → catalog supplies it). */
function createItemRequest<TBody>(ref: AnyCmsRef): Promise<TBody> {
  // Foreign ref — public delivery URL fetched AS-IS (Rule 1).
  if ('url' in ref && typeof ref.url === 'string') {
    return getCmsContentByUrl<TBody>(ref.url);
  }
  // uiBundle-space ref — toolkit remaps the contentKey (fail-open) and reads Connect.
  const channelId = CMS_CHANNEL_ID_FALLBACK || undefined;
  return getCmsContentByKey<TBody>((ref as CmsRef).contentKey, { channelId });
}

export function useCmsItem<TBody = unknown>(
  ref: AnyCmsRef,
): UseCmsItemState<TBody> {
  const [state, setState] = useState<UseCmsItemState<TBody>>(() => {
    const cached = cache.get(ref.name) as TBody | undefined;
    return {
      body: cached,
      loading: cached === undefined,
      error: undefined,
    };
  });

  // Track the ref name so object-identity churn doesn't re-fetch.
  const nameRef = useRef(ref.name);
  nameRef.current = ref.name;

  useEffect(() => {
    // Local guard only — cleanup suppresses stale setState, never the shared
    // request (Rule 3).
    let cancelled = false;
    const name = ref.name;

    const cached = cache.get(name) as TBody | undefined;
    if (cached !== undefined) {
      setState({ body: cached, loading: false, error: undefined });
      return () => {
        cancelled = true;
      };
    }

    setState((prev) => ({ ...prev, loading: true, error: undefined }));

    // In-flight dedup: reuse a pending promise for this ref (shared, no signal).
    let promise = inflight.get(name) as Promise<TBody> | undefined;
    if (!promise) {
      promise = createItemRequest<TBody>(ref);
      inflight.set(name, promise);
      // Self-cleaning: settled or failed, the entry is always removed so an
      // unmounted consumer can't leave a dead promise to poison retries.
      promise
        .then((body) => {
          cache.set(name, body);
        })
        .catch(() => {
          /* surfaced per-consumer below; swallow to avoid unhandled rejection */
        })
        .finally(() => {
          if (inflight.get(name) === promise) inflight.delete(name);
        });
    }

    promise
      .then((body) => {
        if (cancelled) return;
        setState({ body, loading: false, error: undefined });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // Pass the toolkit's typed errors through as-is; wrap anything else.
        const error =
          err instanceof CmsDeliveryNotFoundError ||
          err instanceof CmsDeliveryError ||
          err instanceof CmsNotFoundError ||
          err instanceof ConnectApiError
            ? err
            : err instanceof Error
              ? err
              // Retain the original non-Error rejection as the cause for debugging.
              : new Error('Unknown CMS fetch error', { cause: err });
        setState({ body: undefined, loading: false, error });
      });

    return () => {
      cancelled = true;
    };
  }, [ref.name]); // Ref-name is the identity — object churn is ignored.

  return state;
}

/** Test-only — reset the module cache between runs. */
export function __resetCmsCacheForTests(): void {
  cache.clear();
  inflight.clear();
}
