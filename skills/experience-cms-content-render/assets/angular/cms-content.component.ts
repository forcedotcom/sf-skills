/**
 * CmsContentComponent — schema-less body renderer for Angular (Init →
 * src/cms/angular/cms-content.component.ts). Counterpart of React's heuristicRenderer.
 * Picks fields by priority (title/image/excerpt) or a `fields` whitelist, then
 * classifies each by shape. Holds the ONE RichText injection path (Rule 4): decode,
 * then `[innerHTML]` — Angular's DomSanitizer sanitizes it, so NEVER
 * bypassSecurityTrustHtml. Rules: references/heuristic-render-rules.md.
 */
import { Component, Input, type OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  decodeRichHtmlEntities,
  resolveCmsImageUrl,
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
// Invalid Date, which would break the whole render. Return null on invalid so the
// caller falls through to the next classifier / skips the field.
function formatCmsDate(value: string, options: Intl.DateTimeFormatOptions): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('en-US', options).format(date);
}

/** One renderable cell — a discriminated union the template switches on. */
type Cell =
  | { kind: 'title'; text: string }
  | { kind: 'richText'; html: string }
  | { kind: 'date'; iso: string; label: string }
  | { kind: 'url'; href: string }
  | { kind: 'image'; src: string; alt: string }
  | { kind: 'number'; text: string }
  | { kind: 'boolean'; label: string }
  | { kind: 'text'; text: string };

@Component({
  selector: 'cms-content',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (loading) {
      <div role="status">Loading…</div>
    } @else if (error) {
      <div role="alert">{{ error.message }}</div>
    } @else if (body) {
      <article [class]="className">
        @for (cell of cells; track $index) {
          @switch (cell.kind) {
            @case ('title') {
              @if (layout === 'detail') { <h1>{{ cell.text }}</h1> }
              @else { <h2>{{ cell.text }}</h2> }
            }
            <!-- Decoded, then Angular's DomSanitizer sanitizes the [innerHTML] binding. -->
            @case ('richText') { <div [innerHTML]="cell.html"></div> }
            @case ('date') { <time [attr.dateTime]="cell.iso">{{ cell.label }}</time> }
            @case ('url') {
              <a [href]="cell.href" target="_blank" rel="noopener noreferrer"
                 [attr.aria-label]="'External link: ' + cell.href">{{ cell.href }}</a>
            }
            @case ('image') { <img [src]="cell.src" [alt]="cell.alt" loading="lazy" /> }
            @case ('number') { <span>{{ cell.text }}</span> }
            @case ('boolean') { <span class="badge">{{ cell.label }}</span> }
            @case ('text') { <p>{{ cell.text }}</p> }
          }
        }
      </article>
    }
  `,
})
export class CmsContentComponent implements OnChanges {
  @Input() body: Record<string, unknown> | undefined;
  @Input() loading = false;
  @Input() error: Error | undefined;
  @Input() layout: 'list' | 'detail' = 'detail';
  /** Optional whitelist — bypasses priority lists and renders only these fields in order. */
  @Input() fields?: ReadonlyArray<string>;
  @Input() className?: string;
  /** Resolve a `references`-bag contentKey to its media field (rare payload shape). */
  @Input() resolveRef?: (contentKey: string) => CmsImageField | undefined;

  /** Recomputed on every input change — the template reads this. */
  cells: Cell[] = [];

  ngOnChanges(): void {
    this.cells = this.body ? this.buildCells(this.body) : [];
  }

  private buildCells(body: Record<string, unknown>): Cell[] {
    // Whitelist mode — render exactly these fields, in order, by shape.
    if (this.fields && this.fields.length > 0) {
      const out: Cell[] = [];
      for (const name of this.fields) {
        const cell = this.classify(name, body[name]);
        if (cell) out.push(cell);
      }
      return out;
    }

    // Heuristic mode — title, then first image, then first excerpt, then the rest.
    const out: Cell[] = [];
    const consumed = new Set<string>();

    const title = this.pickTitle(body);
    if (title) {
      out.push({ kind: 'title', text: title.value });
      consumed.add(title.name);
    }

    const imageField = this.pickFirstField(body, IMAGE_PRIORITY, isImageObject);
    if (imageField) {
      consumed.add(imageField.name);
      const src = this.resolveImageSrc(imageField.value);
      if (src) out.push({ kind: 'image', src, alt: resolveImageAlt(imageField.value) });
    }

    const excerpt = this.pickFirstField<string>(
      body,
      EXCERPT_PRIORITY,
      (v) => typeof v === 'string' && v.length > 0,
    );
    if (excerpt) {
      consumed.add(excerpt.name);
      out.push({ kind: 'text', text: excerpt.value });
    }

    if (this.layout === 'detail') {
      for (const [k, v] of Object.entries(body)) {
        if (consumed.has(k)) continue;
        const cell = this.classify(k, v);
        if (cell) out.push(cell);
      }
    }

    return out;
  }

  /** Value-shape dispatcher — the Angular parallel of RenderField. */
  private classify(name: string, value: unknown): Cell | null {
    if (value == null) return null;

    if (typeof value === 'string') {
      if (RICH_TEXT_RE.test(value)) {
        // Decode first (else tags render as literal text); [innerHTML] is then
        // sanitized by Angular's DomSanitizer. Rule 4.
        return { kind: 'richText', html: decodeRichHtmlEntities(value) };
      }
      if (ISO_DATE_RE.test(value)) {
        const label = formatCmsDate(value, { dateStyle: 'medium' });
        // Valid date → date cell; invalid (matched the prefix but unparseable) → fall through.
        if (label) return { kind: 'date', iso: value, label };
      }
      if (URL_RE.test(value)) return { kind: 'url', href: value };
      if (/title/i.test(name)) return { kind: 'title', text: value };
      return { kind: 'text', text: value };
    }

    if (typeof value === 'number') {
      return { kind: 'number', text: new Intl.NumberFormat().format(value) };
    }

    if (typeof value === 'boolean') {
      return { kind: 'boolean', label: value ? 'Yes' : 'No' };
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
        return label ? { kind: 'date', iso: obj.dateTime, label } : null;
      }
      // image-shaped object
      if (isImageObject(obj)) {
        const src = this.resolveImageSrc(obj);
        return src ? { kind: 'image', src, alt: resolveImageAlt(obj) } : null;
      }
      // contentReference shape
      const refObj = (obj as { ref?: { contentKey?: string } }).ref;
      if (refObj && typeof refObj.contentKey === 'string' && this.resolveRef) {
        const resolved = this.resolveRef(refObj.contentKey);
        if (!resolved) return null;
        return { kind: 'text', text: (resolved as { title?: string }).title ?? refObj.contentKey };
      }
      return null;
    }

    return null;
  }

  /** Delivery image field → loadable `src` via the toolkit (resolves the relative
   *  Connect-API url; no options passed). */
  private resolveImageSrc(field: unknown): string | undefined {
    return resolveCmsImageUrl(field as CmsImageField | undefined);
  }

  private pickTitle(body: Record<string, unknown>): { name: string; value: string } | undefined {
    if (typeof body['title'] === 'string') return { name: 'title', value: body['title'] };
    for (const [k, v] of Object.entries(body)) {
      if (typeof v === 'string' && /title/i.test(k)) return { name: k, value: v };
    }
    return undefined;
  }

  private pickFirstField<T = unknown>(
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
