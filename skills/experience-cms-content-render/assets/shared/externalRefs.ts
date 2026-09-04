/**
 * Ref catalog for CMS content (FRAMEWORK-AGNOSTIC). Holds both ref types
 * (CmsExternalRef by `url`, CmsRef by `contentKey`). Scaffolded once at
 * src/cms/shared/externalRefs.ts; each embed appends one entry inside the marker block.
 * Names are EXT_<TITLE_SNAKE>, unique — object-literal keys collide at compile time.
 *
 * ⚠ Do NOT edit the marker block by hand. Add entries via the skill.
 */
// Only `AnyCmsRef` is used in the empty template; Ref Registration adds
// CmsExternalRef/CmsRef when it appends an entry (importing them eagerly trips
// noUnusedLocals TS6196 on a fresh scaffold).
import type { AnyCmsRef } from './cmsCore.types';

// channelId OVERRIDE for CmsRef reads — CAUTION, opt-in only. Prefer the catalog
// (public/content-metadata.json), which is primary and travels per-org. This constant
// is baked into SOURCE, so it does NOT travel per-org and will point at the WRONG
// channel after a cross-org deploy — set it only at your discretion for a local
// override. The skill does NOT auto-fill it (leave ''); the catalog supplies the
// channel. Precedence: explicit option > this override > catalog channelId > toolkit
// throws. Passed as options.channelId only when non-empty.
// <experience-cms-content-render:channel-fallback-begin>
export const CMS_CHANNEL_ID_FALLBACK = '';
// <experience-cms-content-render:channel-fallback-end>

// <experience-cms-content-render:external-refs-begin>
// Skill-managed. Each embed appends one entry here of the form:
//
//   Foreign ref (public unauthenticatedUrl):
//   EXT_FOOD_BERRIES: {
//     name: 'EXT_FOOD_BERRIES',
//     url: 'https://orgfarm-XXX.cdn.example.salesforce-experience.com/cms/delivery/v64.0/0apSG.../contents/MCABC...?oid=00D...&language=en_US',
//     cmsType: 'news',
//   } satisfies CmsExternalRef<'news'>,
//
//   uiBundle-space ref (contentKey — remapped via content-metadata.json):
//   EXT_LAUNCH_NEWS: {
//     name: 'EXT_LAUNCH_NEWS',
//     contentKey: 'M3ASD4KHASDB73',
//     cmsType: 'news',
//   } satisfies CmsRef<'news'>,
//
// `cmsType` MUST match the `<K>` in `satisfies` — it binds the ref to a per-type
// renderer at compile time, so a wrong-typed ref is a compile error.
export const externalRefs = {} as const satisfies Record<string, AnyCmsRef>;
// <experience-cms-content-render:external-refs-end>

/**
 * Typed accessor — prefer over `externalRefs['EXT_X']`: the `cmsType` discriminator
 * flows through, so a wrong-typed ref to a renderer fails at compile time.
 */
export function ref<Name extends keyof typeof externalRefs>(
  name: Name,
): (typeof externalRefs)[Name] {
  return externalRefs[name];
}
