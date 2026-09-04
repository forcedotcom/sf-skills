/**
 * heuristicRenderer — schema-less body renderer (Init → src/cms/react/heuristicRenderer.tsx).
 * Picks fields by priority (title/image/excerpt), dispatches each value by shape via
 * RenderField, and holds the ONE RichText injection site (Rule 4). Angular parallel:
 * cms-content.component.ts. Rules: references/heuristic-render-rules.md.
 */
import { type ComponentType, type ReactNode } from 'react';
import {
  resolveCmsImageUrl,
  decodeRichHtmlEntities,
} from '@salesforce/ui-bundle-template-feature-cms-toolkit';
import type { CmsImageField } from '../shared/cmsCore.types';

const IMAGE_PRIORITY = ['bannerImage', 'featuredImage', 'heroImage', 'coverImage', 'thumbnail', 'image'];
const EXCERPT_PRIORITY = ['excerpt', 'summary', 'description', 'subtitle'];

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}/;
const URL_RE = /^https?:\/\//;
// Match an HTML tag-open (`<tag`, `</`, `<!`) AND entity-encoded HTML (`&lt;`) — the
// encoded form has no literal `<`, so a `<`-only check would skip decode entirely, while
// a bare `<` in prose ("Q4 < projected") must NOT be treated as markup (Rule 4).
const RICH_TEXT_RE = /<[a-z!/]|&lt;|&#(?:60|x3c);/i;

// ISO_DATE_RE only checks the PREFIX, so unparseable strings ("2024-13-99") and SKUs
// ("1234-56-78") slip through; `Intl.DateTimeFormat.format` throws RangeError on an
// Invalid Date, which would crash the whole render. Return null on invalid so the
// caller falls through to the next classifier instead of formatting.
function formatCmsDate(value: string, options: Intl.DateTimeFormatOptions): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('en-US', options).format(date);
}

let sanitizer: (html: string) => string = defaultPassThroughSanitizer;

function defaultPassThroughSanitizer(html: string): string {
  // Pass-through: Delivery RichText is trusted and already decoded to real HTML;
  // escaping here would undo the decode (Rule 4). Apps add DOMPurify via
  // setRichTextSanitizer for defense-in-depth.
  return html;
}

// Swap in DOMPurify (or similar) at app entry: setRichTextSanitizer(DOMPurify.sanitize).
export function setRichTextSanitizer(fn: (html: string) => string): void {
  sanitizer = fn;
}

export function richTextSanitizer(html: string): string {
  return sanitizer(html);
}

/** Delivery image field → loadable `src` via the toolkit (resolves the relative
 *  Connect-API url; no options passed). Sync. */
export function resolveImageSrc(field: unknown): string | undefined {
  return resolveCmsImageUrl(field as CmsImageField | undefined);
}

function isImageObject(v: unknown): boolean {
  if (!v || typeof v !== 'object') return false;
  const o = v as { url?: unknown; source?: { type?: unknown } };
  return typeof o.url === 'string' || (o.source != null && typeof o.source.type === 'string');
}

/** Delivery image field → authored alt text. Empty string when the field carries none —
 *  a decorative image (WCAG 1.1.1), not a missing attribute. */
function resolveImageAlt(field: unknown): string {
  if (field && typeof field === 'object') {
    const alt = (field as { altText?: unknown }).altText;
    if (typeof alt === 'string') return alt;
  }
  return '';
}

// RenderField picks a rendering from the value's SHAPE (table:
// references/heuristic-render-rules.md) and holds the ONE RichText injection path
// (Rule 4). Do NOT inject RichText anywhere else.
interface RenderFieldProps {
  name: string;
  value: unknown;
  layout: 'list' | 'detail';
  /** Resolves a `references`-bag contentKey to its media field; undefined for foreign refs. */
  resolveRef?: (contentKey: string) => CmsImageField | undefined;
  TitleSlot?: ComponentType<{ value: string }>;
  ImageSlot?: ComponentType<{ src: string; alt?: string }>;
  RichTextSlot?: ComponentType<{ html: string }>;
}

function RenderField({
  name,
  value,
  layout,
  resolveRef,
  TitleSlot,
  ImageSlot,
  RichTextSlot,
}: RenderFieldProps): ReactNode {
  if (value == null) return null;

  if (typeof value === 'string') {
    if (RICH_TEXT_RE.test(value)) {
      // Decode entity-encoded HTML FIRST, THEN sanitize (Rule 4).
      const html = richTextSanitizer(decodeRichHtmlEntities(value));
      if (RichTextSlot) return <RichTextSlot html={html} />;
      // Trusted, decoded HTML → default sanitizer is pass-through (Rule 4).
      return <div dangerouslySetInnerHTML={{ __html: html }} />;
    }
    if (ISO_DATE_RE.test(value)) {
      const label = formatCmsDate(value, { dateStyle: 'medium' });
      // Valid date → <time>; invalid (matched the prefix but unparseable) → fall through.
      if (label) return <time dateTime={value}>{label}</time>;
    }
    if (URL_RE.test(value)) {
      return <a href={value} target="_blank" rel="noopener noreferrer" aria-label={`External link: ${value}`}>{value}</a>;
    }
    if (/title/i.test(name)) {
      return TitleSlot
        ? <TitleSlot value={value} />
        : (layout === 'detail' ? <h1>{value}</h1> : <h2>{value}</h2>);
    }
    return <p>{value}</p>;
  }

  if (typeof value === 'number') {
    return <span>{new Intl.NumberFormat().format(value)}</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="badge">{value ? 'Yes' : 'No'}</span>;
  }

  if (Array.isArray(value)) {
    return (
      <>
        {value.map((v, i) => (
          <RenderField
            key={i}
            name={`${name}[${i}]`}
            value={v}
            layout={layout}
            resolveRef={resolveRef}
            TitleSlot={TitleSlot}
            ImageSlot={ImageSlot}
            RichTextSlot={RichTextSlot}
          />
        ))}
      </>
    );
  }

  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;

    // dateTime shape
    if (typeof obj.dateTime === 'string') {
      const label = formatCmsDate(obj.dateTime, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: typeof obj.timeZone === 'string' ? obj.timeZone : undefined,
      });
      // Invalid dateTime → skip this field rather than crash the render.
      return label ? <time dateTime={obj.dateTime}>{label}</time> : null;
    }

    // image-shaped object — the toolkit resolves the src synchronously.
    if (isImageObject(obj)) {
      const src = resolveImageSrc(obj);
      if (!src) return null;
      const alt = resolveImageAlt(obj);
      return ImageSlot
        ? <ImageSlot src={src} alt={alt} />
        : <img src={src} alt={alt} loading="lazy" />;
    }

    // contentReference shape
    const refObj = (obj as { ref?: { contentKey?: string } }).ref;
    if (refObj && typeof refObj.contentKey === 'string' && resolveRef) {
      const resolved = resolveRef(refObj.contentKey);
      if (!resolved) return null;
      return <span>{(resolved as { title?: string }).title ?? refObj.contentKey}</span>;
    }

    return null;
  }

  return null;
}

export interface HeuristicRendererProps {
  body: Record<string, unknown> | undefined;
  loading: boolean;
  error: Error | undefined;
  layout?: 'list' | 'detail' | string;
  /** Optional whitelist — bypasses priority lists and renders only these fields in order. */
  fields?: ReadonlyArray<string>;
  components?: {
    Title?: ComponentType<{ value: string }>;
    Image?: ComponentType<{ src: string; alt?: string }>;
    RichText?: ComponentType<{ html: string }>;
  };
  className?: string;
  resolveRef?: (contentKey: string) => CmsImageField | undefined;
}

export function heuristicRenderer({
  body,
  loading,
  error,
  layout = 'detail',
  fields,
  components,
  className,
  resolveRef,
}: HeuristicRendererProps): ReactNode {
  if (loading) return <div role="status">Loading…</div>;
  if (error) return <div role="alert">{error.message}</div>;
  if (!body) return null;

  const normalizedLayout: 'list' | 'detail' = layout === 'list' ? 'list' : 'detail';
  const TitleSlot = components?.Title;
  const ImageSlot = components?.Image;
  const RichTextSlot = components?.RichText;

  // Whitelist mode.
  if (fields && fields.length > 0) {
    return (
      <article className={className}>
        {fields.map((name) => {
          const value = body[name];
          if (value == null) return null;
          return (
            <RenderField
              key={name}
              name={name}
              value={value}
              layout={normalizedLayout}
              resolveRef={resolveRef}
              TitleSlot={TitleSlot}
              ImageSlot={ImageSlot}
              RichTextSlot={RichTextSlot}
            />
          );
        })}
      </article>
    );
  }

  // Heuristic mode.
  const title = pickTitle(body);
  const imageField = pickFirstField(body, IMAGE_PRIORITY, isImageObject);
  const excerpt = pickFirstField(body, EXCERPT_PRIORITY, (v) => typeof v === 'string' && v.length > 0);

  const consumed = new Set<string>();
  if (title?.name) consumed.add(title.name);
  if (imageField?.name) consumed.add(imageField.name);
  if (excerpt?.name) consumed.add(excerpt.name);

  return (
    <article className={className}>
      {title && (TitleSlot
        ? <TitleSlot value={title.value} />
        : (normalizedLayout === 'detail' ? <h1>{title.value}</h1> : <h2>{title.value}</h2>))}

      {imageField && (() => {
        const src = resolveImageSrc(imageField.value);
        if (!src) return null;
        const alt = resolveImageAlt(imageField.value);
        return ImageSlot
          ? <ImageSlot src={src} alt={alt} />
          : <img src={src} alt={alt} loading="lazy" />;
      })()}

      {excerpt && <p>{excerpt.value as string}</p>}

      {normalizedLayout === 'detail' && Object.entries(body)
        .filter(([k]) => !consumed.has(k))
        .map(([k, v]) => (
          <RenderField
            key={k}
            name={k}
            value={v}
            layout={normalizedLayout}
            resolveRef={resolveRef}
            TitleSlot={TitleSlot}
            ImageSlot={ImageSlot}
            RichTextSlot={RichTextSlot}
          />
        ))}
    </article>
  );
}

function pickTitle(body: Record<string, unknown>): { name: string; value: string } | undefined {
  if (typeof body.title === 'string') return { name: 'title', value: body.title };
  for (const [k, v] of Object.entries(body)) {
    if (typeof v === 'string' && /title/i.test(k)) return { name: k, value: v };
  }
  return undefined;
}

function pickFirstField<T = unknown>(
  body: Record<string, unknown>,
  priority: string[],
  predicate: (v: unknown) => boolean,
): { name: string; value: T } | undefined {
  for (const k of priority) {
    const v = body[k];
    if (v != null && predicate(v)) return { name: k, value: v as T };
  }
  return undefined;
}
