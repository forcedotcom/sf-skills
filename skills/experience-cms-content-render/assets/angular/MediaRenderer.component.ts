/**
 * MediaRendererComponent — dedicated renderer for standalone CMS media (Angular;
 * Init → src/cms/angular/MediaRenderer.component.ts). Counterpart of React's
 * MediaRenderer. Media is a PREDEFINED type parallel to `news`: a media ref binds
 * here at registration time and the template switches by `ref.cmsType`
 * (`image`/`audio`/`video`/`document`) — NEVER by body shape, so audio/video/document
 * can't be mis-caught by cms-content's image path (SKILL.md §B1).
 *
 * Dispatch is by `cmsType` AND ref shape (Rule 1/Rule 2):
 *  - Foreign ref (`url`): a media `unauthenticatedUrl` is the ASSET itself, so the url
 *    goes straight onto the element `src`/`href` — NO load, NO toolkit resolver. Alt
 *    text / document label ride on the ref (threaded from the search hand-off or asked
 *    at Ref Registration), since there is no fetched body to read them from.
 *  - uiBundle-space ref (`contentKey`): load the body via CmsItemService, then resolve
 *    the src by medium (image via resolveCmsImageUrl; audio/video/document via
 *    resolveMediaUrl).
 *
 * A media item is a single asset, not a field bag, so this does NOT delegate to
 * <cms-content>. Players/links are elements, never injected HTML (Rule 4).
 */
import { Component, Input, type OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  resolveCmsImageUrl,
  resolveMediaUrl,
} from '@salesforce/ui-bundle-template-feature-cms-toolkit';
import { CmsItemService } from './cms-item.service';
import {
  type AnyCmsRef,
  type CmsMediaBody,
  type CmsMediaType,
} from '../shared/cmsCore.types';

@Component({
  selector: 'cms-media',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (loading) {
      <div role="status">Loading…</div>
    } @else if (error) {
      <div role="alert">{{ error.message }}</div>
    } @else if (src) {
      <!-- Gate on `src`, not `body`: the foreign-url path resolves a src with no
           fetched body (Rule 1); the contentKey path sets both. -->
      @switch (ref.cmsType) {
        @case ('image') {
          @if (src) { <img [class]="className" [src]="src" [alt]="alt" loading="lazy" /> }
        }
        @case ('audio') {
          @if (src) { <audio [class]="className" controls [src]="src" [attr.aria-label]="alt || null"></audio> }
        }
        @case ('video') {
          @if (src) { <video [class]="className" controls [src]="src" [attr.aria-label]="alt || null"></video> }
        }
        @case ('document') {
          <!-- Download link only — no inline preview (SKILL.md §B3). Named with the
               document's altText/title so it identifies WHAT downloads (WCAG 2.4.4),
               never a bare "Download" that is ambiguous among sibling media links. -->
          @if (src) { <a [class]="className" [href]="src" download>{{ docLabel }}</a> }
        }
      }
    }
  `,
})
export class MediaRendererComponent implements OnChanges {
  /** A media ref — `cmsType` selects the element; a non-media ref is a compile error. */
  @Input({ required: true }) ref!: AnyCmsRef<CmsMediaType>;
  @Input() className?: string;

  loading = true;
  error: Error | undefined;
  body: CmsMediaBody | undefined;

  /** Resolved src + alt for the template (recomputed after each load). */
  src: string | undefined;
  alt = '';
  /** Accessible name for the document download link (altText → title → "Download"). */
  docLabel = 'Download';

  private loadedRefName?: string;

  constructor(private readonly cms: CmsItemService) {}

  ngOnChanges(): void {
    const ref = this.ref;
    // Only (re)load when the ref identity changes (mirrors TypeRendererComponent).
    if (ref.name === this.loadedRefName) return;
    this.loadedRefName = ref.name;

    this.body = undefined;
    this.error = undefined;
    this.src = undefined;
    this.alt = '';
    this.docLabel = 'Download';

    // Foreign media ref: the unauthenticatedUrl is the asset src directly — no load
    // (Rule 1). alt/title ride on the ref (search hand-off or Ref Registration ask).
    if ('url' in ref && typeof ref.url === 'string') {
      this.src = ref.url;
      this.alt = ref.altText ?? '';
      this.docLabel = ref.altText || ref.title || 'Download';
      this.loading = false;
      return;
    }

    // uiBundle-space ref (contentKey): load the body, then resolve the src by medium.
    this.loading = true;
    void this.cms.load<CmsMediaBody>(ref).then((result) => {
      // Ignore a stale resolution if the ref changed while this was in flight.
      if (this.ref !== ref) return;
      this.body = result.body;
      this.error = result.error;
      this.loading = false;
      if (result.body) this.resolveSrc(ref.cmsType, result.body);
    });
  }

  /** Src resolution SPLITS by medium (Rule 2): image → resolveCmsImageUrl;
   *  audio/video/document → resolveMediaUrl. Both toolkit helpers resolve the
   *  relative Connect-API url; no options are passed. Reached only on the contentKey
   *  path — a foreign `url` ref sets `src` directly in ngOnChanges without a body. */
  private resolveSrc(cmsType: CmsMediaType, body: CmsMediaBody): void {
    const media = body['sfdc_cms:media'];
    this.alt = body.altText ?? '';
    this.docLabel = body.altText || body.title || 'Download';
    if (cmsType === 'image') {
      this.src = resolveCmsImageUrl(media);
      return;
    }
    this.src = media?.url ? resolveMediaUrl(media.url) : undefined;
  }
}
