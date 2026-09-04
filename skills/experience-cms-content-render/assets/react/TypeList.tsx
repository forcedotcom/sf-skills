/**
 * {{Type}}List — opt-in list/grid wrapper over N same-type refs (codegen-managed;
 * scaffolded ONLY on a list/grid prompt, not by Init). Lands in src/cms/react/types/.
 * One `{{Type}}Renderer` per ref → each item keeps its own useCmsItem + error branch
 * (mixed contentKey/url refs are fine). List vs grid is `className` CSS
 * (references/styling-scopes.md). For a single-round-trip batch read, call
 * `getCmsContentByKeys` directly instead (references/bulk-loading.md).
 *
 * Tokens: {{Type}} PascalCase, {{type}} camelCase, {{TypeRenderer}} renderer name.
 */
import type { ReactNode } from 'react';
import type { AnyCmsRef } from '../../shared/cmsCore.types';
import { {{TypeRenderer}} } from './{{TypeRenderer}}';
import type { {{Type}}Layout } from './{{type}}';

export interface {{Type}}ListProps {
  /** The group to render, one renderer per entry (e.g. `[ref('EXT_A'), ref('EXT_B')]`). */
  refs: ReadonlyArray<AnyCmsRef<'{{type}}'>>;
  /** Per-item layout (default `list`). Grid is achieved via `className` CSS. */
  layout?: {{Type}}Layout;
  className?: string;
}

export function {{Type}}List({
  refs,
  layout = 'list',
  className,
}: {{Type}}ListProps): ReactNode {
  return (
    <div role="list" className={className ?? 'cms-{{type}}-list'}>
      {refs.map((r) => (
        <div role="listitem" key={r.name}>
          <{{Type}}Renderer ref={r} layout={layout} />
        </div>
      ))}
    </div>
  );
}

export default {{Type}}List;
