/**
 * {{Type}}ListComponent — opt-in list/grid wrapper over N same-type refs (Angular;
 * codegen-managed; scaffolded ONLY on a list/grid prompt, not by Init). Lands in
 * src/cms/angular/types/. Counterpart of React's {{Type}}List. One `cms-{{type}}` per
 * ref → each item keeps its own service read + error branch (mixed contentKey/url
 * refs are fine). List vs grid is `className` CSS (references/styling-scopes.md). For
 * a single-round-trip batch read, call `getCmsContentByKeys` directly instead
 * (references/bulk-loading.md).
 *
 * Tokens: {{Type}} PascalCase, {{type}} camelCase.
 */
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { {{Type}}RendererComponent } from './{{Type}}Renderer.component';
import type { AnyCmsRef } from '../../shared/cmsCore.types';
import type { {{Type}}Layout } from './{{type}}';

@Component({
  selector: 'cms-{{type}}-list',
  standalone: true,
  imports: [CommonModule, {{Type}}RendererComponent],
  template: `
    <div role="list" [class]="className ?? 'cms-{{type}}-list'">
      @for (r of refs; track r.name) {
        <div role="listitem">
          <cms-{{type}} [ref]="r" [layout]="layout"></cms-{{type}}>
        </div>
      }
    </div>
  `,
})
export class {{Type}}ListComponent {
  /** The group to render, one renderer per entry (e.g. `[ref('EXT_A'), ref('EXT_B')]`). */
  @Input({ required: true }) refs!: ReadonlyArray<AnyCmsRef<'{{type}}'>>;
  /** Per-item layout (default `list`). Grid is achieved via `className` CSS. */
  @Input() layout: {{Type}}Layout = 'list';
  @Input() className?: string;
}
