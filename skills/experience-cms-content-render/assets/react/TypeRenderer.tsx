/**
 * {{Type}}Renderer — per-type wrapper (codegen-managed; regenerated on schema sync).
 * No user region — customize via {{type}}Layouts/{{type}}Slots in `./{{type}}.ts`.
 * Delegates ALL field rendering to heuristicRenderer — do NOT inject HTML here
 * (Rule 4). `ref` is typed `AnyCmsRef<'{{type}}'>` — a ref whose `cmsType` differs is
 * a compile error. Fields are read directly, never `.value` (Rule 5).
 * Tokens: {{Type}} PascalCase, {{type}} camelCase.
 */
import type { ReactNode, ComponentType } from 'react';
import type { AnyCmsRef } from '../../shared/cmsCore.types';
import { useCmsItem } from '../useCmsItem';
import { heuristicRenderer } from '../heuristicRenderer';
import { {{type}}Layouts, {{type}}Slots, type {{Type}}Body, type {{Type}}Layout } from './{{type}}';

export interface {{Type}}RendererProps {
  ref: AnyCmsRef<'{{type}}'>;
  layout?: {{Type}}Layout;
  /** Whitelist of {{Type}}Body field names. Bypasses layout's default field list. */
  fields?: ReadonlyArray<keyof {{Type}}Body & string>;
  components?: {
    Title?: ComponentType<{ value: string }>;
    Image?: ComponentType<{ src: string; alt?: string }>;
    RichText?: ComponentType<{ html: string }>;
  };
  className?: string;
}

export function {{Type}}Renderer(props: {{Type}}RendererProps): ReactNode {
  const {
    ref,
    layout = 'card',
    fields,
    components,
    className,
  } = props;

  const { body, loading, error } = useCmsItem<{{Type}}Body>(ref);

  // fields: per-embed prop → layout preset → undefined (heuristic mode).
  const layoutPreset = {{type}}Layouts[layout];
  const resolvedFields = fields ?? layoutPreset.fields;

  // components: per-embed prop → type-level slot defaults.
  const resolvedComponents = {
    ...(( {{type}}Slots as unknown) as {{Type}}RendererProps['components']),
    ...components,
  };

  const resolvedClassName = className ?? layoutPreset.className;

  // 'detail' layout key routes to detail-mode rendering; every other custom
  // layout falls through to list-mode. Add more layouts in `{{type}}.ts`.
  const rendererLayout = layout === 'detail' ? 'detail' : 'list';

  return heuristicRenderer({
    body: body as Record<string, unknown> | undefined,
    loading,
    error,
    layout: rendererLayout,
    fields: resolvedFields as ReadonlyArray<string> | undefined,
    components: resolvedComponents,
    className: resolvedClassName,
  });
}
