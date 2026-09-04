/**
 * CMS identity + field-type primitives (FRAMEWORK-AGNOSTIC). Scaffolded once at
 * `src/cms/shared/cmsCore.types.ts`; safe to import, not regenerated. Owns ONLY the
 * app-level ref identity and the codegen field-type enum — delivery/runtime shapes
 * (CmsImageField, CmsContentBody, errors, …) live in the toolkit; do NOT redeclare.
 */

// Re-exported so generated `<type>.ts` import the image shape from one local path
// (relative to `<framework>/types/`) rather than the package specifier.
export type { CmsImageField } from "@salesforce/ui-bundle-template-feature-cms-toolkit";

/** Foreign-ref identity — content addressed by a public unauthenticatedUrl (CDN). */
export interface CmsExternalRef<K extends string = string> {
  /** Unique catalog name. Convention: EXT_<TITLE_SNAKE>. */
  readonly name: string;
  /** Fully-formed unauthenticatedUrl; immutable across deploys. */
  readonly url: string;
  /** Content-type discriminator (the fqn DeveloperName). REQUIRED and populated on
   *  every entry — it binds the ref to its renderer, so a wrong-typed ref is a
   *  compile error. Optional/absent would erase K and defeat that guard. */
  readonly cmsType: K;
  /** MEDIA-ONLY, direct-URL path. For standalone media (`image`/`audio`/`video`/
   *  `document`) a foreign `url` is the ASSET itself, so MediaRenderer sets it as the
   *  element `src`/`href` WITHOUT fetching — there is no body to read `altText`/`title`
   *  from. The skill threads these off the search hand-off (or asks the user) at Ref
   *  Registration so the accessible name survives. Ignored on non-media refs (news
   *  reads its title from the fetched envelope). Both optional; `altText` absent → `''`
   *  (decorative image, WCAG 1.1.1); `title` names the document download link. */
  readonly altText?: string;
  readonly title?: string;
}

/**
 * uiBundle-space identity — a `contentKey` read via the authenticated Connect API.
 * The baked-in value is the `sourceContentKey`; the toolkit remaps it to the org's
 * `targetContentKey` via content-metadata.json (fail-open to the baked-in key).
 */
export interface CmsRef<K extends string = string> {
  /** Unique catalog name. Convention: EXT_<TITLE_SNAKE>. */
  readonly name: string;
  /** sourceContentKey baked into app code; the catalog's remap fallback. */
  readonly contentKey: string;
  /** Content-type discriminator (the fqn DeveloperName). REQUIRED and populated on
   *  every entry — it binds the ref to its renderer, so a wrong-typed ref is a
   *  compile error. Optional/absent would erase K and defeat that guard. */
  readonly cmsType: K;
}

/** Union of every fetchable ref — branch on `url` (foreign) vs `contentKey`. */
export type AnyCmsRef<K extends string = string> = CmsExternalRef<K> | CmsRef<K>;

/** Codified Lightning field types — feeds the below-marker fieldTypes map per type. */
export type CmsFieldType =
  | "text"
  | "richText"
  | "image"
  | "date"
  | "dateTime"
  | "number"
  | "boolean"
  | "url"
  | "reference"
  | "unknown";

/**
 * Standalone-media discriminator — the fqn DeveloperName of a PREDEFINED CMS media
 * item (`sfdc_cms__{image,audio,video,document}`), stored on the ref as `cmsType`.
 * Media is a predefined type parallel to `news`: the ref binds to `MediaRenderer` at
 * registration time, so dispatch is by `cmsType`, NEVER by body shape (SKILL.md §B1).
 */
export type CmsMediaType = "image" | "audio" | "video" | "document";

/** The `sfdc_cms:media` field every media body carries (key is LITERALLY
 *  "sfdc_cms:media", colon, across all four types). `url` is a loadable src; `source`
 *  describes the underlying file (`mimeType` picks finer intra-medium choices). */
export interface CmsMediaField {
  readonly url?: string;
  readonly source?: {
    readonly mimeType?: string;
    readonly ref?: string;
    readonly type?: string;
    readonly fileSize?: number;
  };
}

/**
 * Predefined body for standalone CMS media — UNIFORM across all four media types;
 * they differ only by the envelope fqn (→ `cmsType`) and `source.mimeType`. `title`
 * is envelope-level, lifted into the body by the toolkit (as news); `altText` is
 * optional and absent on audio. The `<TBody>` for `getCmsContentByKey<CmsMediaBody>`.
 */
export interface CmsMediaBody {
  readonly altText?: string;
  readonly title?: string;
  readonly "sfdc_cms:media": CmsMediaField;
}
