/**
 * MediaRenderer — dedicated renderer for standalone CMS media (React; Init →
 * src/cms/react/MediaRenderer.tsx). Media is a PREDEFINED type parallel to `news`:
 * a media ref binds here at registration time and dispatches by `ref.cmsType`
 * (`image`/`audio`/`video`/`document`) — NEVER by body shape, so audio/video/document
 * can't be mis-caught by the heuristic renderer's `isImageObject` path (SKILL.md §B1).
 *
 * Dispatch is by `cmsType` AND ref shape (Rule 1/Rule 2):
 *  - Foreign ref (`url`): a media `unauthenticatedUrl` is the ASSET itself, so the url
 *    goes straight onto the element `src`/`href` — NO fetch, NO toolkit resolver. Alt
 *    text / document label ride on the ref (threaded from the search hand-off or asked
 *    at Ref Registration), since there is no fetched body to read them from.
 *  - uiBundle-space ref (`contentKey`): fetch the body via useCmsItem, then resolve the
 *    src by medium (image → resolveCmsImageUrl; audio/video/document → resolveMediaUrl).
 *
 * A media item is a single asset, not a field bag, so neither path delegates to
 * heuristicRenderer. Players/links are elements, never injected HTML (Rule 4).
 */
import type { ReactNode } from 'react';
import {
  resolveCmsImageUrl,
  resolveMediaUrl,
} from '@salesforce/ui-bundle-template-feature-cms-toolkit';
import { useCmsItem } from './useCmsItem';
import {
  type AnyCmsRef,
  type CmsMediaBody,
  type CmsMediaType,
} from '../shared/cmsCore.types';

export interface MediaRendererProps {
  /** A media ref — `cmsType` selects the element; a non-media ref is a compile error. */
  ref: AnyCmsRef<CmsMediaType>;
  className?: string;
}

/**
 * Emit the one element for a resolved media `src`. Shared by both paths so the element
 * markup (and its a11y contract) lives in exactly one place.
 */
function mediaElement(
  cmsType: CmsMediaType,
  src: string,
  alt: string,
  docLabel: string,
  className?: string,
): ReactNode {
  switch (cmsType) {
    case 'image':
      return <img className={className} src={src} alt={alt} loading="lazy" />;
    case 'audio':
      // altText is typically absent on audio → aria-label only when present.
      return <audio className={className} controls src={src} aria-label={alt || undefined} />;
    case 'video':
      return <video className={className} controls src={src} aria-label={alt || undefined} />;
    case 'document':
      // Download link only — no inline preview (SKILL.md §B3). Name the link so it
      // identifies WHAT downloads (WCAG 2.4.4), never a bare "Download" that is
      // ambiguous when several media links share a page.
      return <a className={className} href={src} download>{docLabel}</a>;
    default:
      return null;
  }
}

/**
 * Foreign media ref — the `url` IS the asset (Rule 1/Rule 2). No fetch, no resolver:
 * set it as the element src directly. `altText`/`title` come off the ref.
 */
function DirectMedia(props: {
  cmsType: CmsMediaType;
  url: string;
  alt: string;
  title?: string;
  className?: string;
}): ReactNode {
  const { cmsType, url, alt, title, className } = props;
  const docLabel = alt || title || 'Download';
  return mediaElement(cmsType, url, alt, docLabel, className);
}

/**
 * uiBundle-space media ref — fetch the body, then resolve the src by medium. This is the
 * authenticated-Connect path; identical behaviour to before the direct-URL fork.
 */
function FetchedMedia(props: { ref: AnyCmsRef<CmsMediaType>; className?: string }): ReactNode {
  const { ref, className } = props;
  const { body, loading, error } = useCmsItem<CmsMediaBody>(ref);

  if (loading) return <div role="status">Loading…</div>;
  if (error) return <div role="alert">{error.message}</div>;
  if (!body) return null;

  const media = body['sfdc_cms:media'];
  const alt = body.altText ?? '';
  const docLabel = body.altText || body.title || 'Download';

  // Src resolution SPLITS by medium (Rule 2): image → resolveCmsImageUrl;
  // audio/video/document → resolveMediaUrl. Both toolkit helpers resolve the
  // relative Connect-API url; no options are passed.
  const src =
    ref.cmsType === 'image' ? resolveCmsImageUrl(media) : media?.url ? resolveMediaUrl(media.url) : undefined;
  if (!src) return null;

  return mediaElement(ref.cmsType, src, alt, docLabel, className);
}

export function MediaRenderer(props: MediaRendererProps): ReactNode {
  const { ref, className } = props;

  // Foreign media ref: the unauthenticatedUrl is the asset src directly — no fetch
  // (Rule 1). alt/title ride on the ref (search hand-off or Ref Registration ask).
  if ('url' in ref && typeof ref.url === 'string') {
    return (
      <DirectMedia
        cmsType={ref.cmsType}
        url={ref.url}
        alt={ref.altText ?? ''}
        title={ref.title}
        className={className}
      />
    );
  }

  // uiBundle-space ref (contentKey): fetch + resolve by medium.
  return <FetchedMedia ref={ref} className={className} />;
}

export default MediaRenderer;
