/**
 * CmsItemService — single-content data layer for Angular (Init →
 * src/cms/angular/cms-item.service.ts). Counterpart of React's `useCmsItem`.
 * Owns a per-ref cache + inflight dedup and dispatches on ref type (CmsExternalRef
 * `url` → getCmsContentByUrl / CDN; CmsRef `contentKey` → getCmsContentByKey /
 * Connect). `providedIn: 'root'` → one instance app-wide, so the maps are shared.
 * `load()` never rejects — failures resolve with `error` set.
 */
import { Injectable } from '@angular/core';
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

/** Resolved state for one ref read — the component maps this onto signals. */
export interface CmsItemResult<TBody> {
  body: TBody | undefined;
  error: Error | undefined;
}

@Injectable({ providedIn: 'root' })
export class CmsItemService {
  // Shared across every consumer of this singleton service.
  private readonly cache = new Map<string, unknown>();
  private readonly inflight = new Map<string, Promise<unknown>>();

  /**
   * Read one item by ref — resolves the unwrapped body or a typed error, never
   * rejects. Deduped by `ref.name`; the shared request carries NO AbortSignal, so a
   * component torn down mid-flight ignores the late result rather than aborting.
   */
  async load<TBody = unknown>(ref: AnyCmsRef): Promise<CmsItemResult<TBody>> {
    const name = ref.name;

    const cached = this.cache.get(name) as TBody | undefined;
    if (cached !== undefined) {
      return { body: cached, error: undefined };
    }

    let promise = this.inflight.get(name) as Promise<TBody> | undefined;
    if (!promise) {
      promise = this.createItemRequest<TBody>(ref);
      this.inflight.set(name, promise);
      // Self-cleaning: cache on success, always drop the inflight entry.
      promise
        .then((body) => {
          this.cache.set(name, body);
        })
        .catch(() => {
          /* surfaced to the caller below; swallow to avoid unhandled rejection */
        })
        .finally(() => {
          if (this.inflight.get(name) === promise) this.inflight.delete(name);
        });
    }

    try {
      const body = await promise;
      return { body, error: undefined };
    } catch (err: unknown) {
      return { body: undefined, error: this.normalizeError(err) };
    }
  }

  /** Dispatch on ref type. NO abort signal — the request is shared (see `load`). */
  private createItemRequest<TBody>(ref: AnyCmsRef): Promise<TBody> {
    // Foreign ref — public delivery URL fetched AS-IS (Rule 1).
    if ('url' in ref && typeof ref.url === 'string') {
      return getCmsContentByUrl<TBody>(ref.url);
    }
    // uiBundle-space ref — toolkit remaps the contentKey (fail-open) and reads Connect.
    const channelId = CMS_CHANNEL_ID_FALLBACK || undefined;
    return getCmsContentByKey<TBody>((ref as CmsRef).contentKey, { channelId });
  }

  /** Pass through the toolkit's typed errors as-is; wrap anything else. */
  private normalizeError(err: unknown): Error {
    if (
      err instanceof CmsDeliveryNotFoundError ||
      err instanceof CmsDeliveryError ||
      err instanceof CmsNotFoundError ||
      err instanceof ConnectApiError
    ) {
      return err;
    }
    return err instanceof Error ? err : new Error('Unknown CMS fetch error');
  }

  /** Test-only escape hatch — reset the cache between test runs. */
  __resetForTests(): void {
    this.cache.clear();
    this.inflight.clear();
  }
}
