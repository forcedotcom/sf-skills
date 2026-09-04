/**
 * {{Type}}RendererComponent — per-type wrapper for Angular (codegen-managed;
 * regenerated on schema sync). Counterpart of React's {{Type}}Renderer. No user
 * region — customize via {{type}}Layouts/{{type}}Slots in
 * `src/cms/angular/types/{{type}}.ts`.
 *
 * SMART container: injects CmsItemService, loads the ref, hands the body to the DUMB
 * `<cms-content>` where all rendering (incl. the one RichText path) lives — do NOT
 * inject HTML here (Rule 4); never unwrap `.value` (Rule 5). `ref` is typed
 * `AnyCmsRef<'{{type}}'>` — a ref whose `cmsType` differs is a compile error.
 * Tokens: {{Type}} PascalCase, {{type}} camelCase.
 */
import { Component, Input, type OnChanges, signal } from '@angular/core';
import { CmsContentComponent } from '../cms-content.component';
import { CmsItemService } from '../cms-item.service';
import type { AnyCmsRef } from '../../shared/cmsCore.types';
import { {{type}}Layouts, type {{Type}}Body, type {{Type}}Layout } from './{{type}}';

@Component({
  selector: 'cms-{{type}}',
  standalone: true,
  imports: [CmsContentComponent],
  template: `
    <cms-content
      [body]="body()"
      [loading]="loading()"
      [error]="error()"
      [layout]="rendererLayout"
      [fields]="resolvedFields"
      [className]="resolvedClassName"
    ></cms-content>
  `,
})
export class {{Type}}RendererComponent implements OnChanges {
  @Input({ required: true }) ref!: AnyCmsRef<'{{type}}'>;
  @Input() layout: {{Type}}Layout = 'card';
  /** Whitelist of {{Type}}Body field names. Bypasses the layout's default field list. */
  @Input() fields?: ReadonlyArray<keyof {{Type}}Body & string>;
  @Input() className?: string;

  readonly body = signal<{{Type}}Body | undefined>(undefined);
  readonly loading = signal(true);
  readonly error = signal<Error | undefined>(undefined);

  // Name of the ref the signals currently describe. Lets ngOnChanges tell a ref
  // switch (clear + reload) apart from a same-ref prop change (layout/fields).
  private loadedRefName?: string;

  // 'detail' layout key routes to detail-mode rendering; every other custom
  // layout falls through to list-mode. Add more layouts in `{{type}}.ts`.
  get rendererLayout(): 'list' | 'detail' {
    return this.layout === 'detail' ? 'detail' : 'list';
  }

  // Resolution order for `fields`: per-embed prop → layout preset → undefined
  // (heuristic mode). Cast mirrors the React renderer's ReadonlyArray<string>.
  get resolvedFields(): ReadonlyArray<string> | undefined {
    return (this.fields ?? {{type}}Layouts[this.layout].fields) as
      | ReadonlyArray<string>
      | undefined;
  }

  get resolvedClassName(): string {
    return this.className ?? {{type}}Layouts[this.layout].className;
  }

  constructor(private readonly cms: CmsItemService) {}

  ngOnChanges(): void {
    const ref = this.ref;
    // Only (re)load when the ref identity changes — a layout/fields-only change
    // must not drop the already-resolved body back into a loading state.
    if (ref.name === this.loadedRefName) return;
    this.loadedRefName = ref.name;

    // Ref switched: drop the previous item's body/error so its content can't stay
    // visible under the new ref, and show loading until this ref resolves. The
    // service dedups by ref.name, so a shared ref reuses the in-flight/cached result.
    this.body.set(undefined);
    this.error.set(undefined);
    this.loading.set(true);
    void this.cms.load<{{Type}}Body>(ref).then((result) => {
      // Ignore a stale resolution if the ref changed while this was in flight.
      if (this.ref !== ref) return;
      this.body.set(result.body);
      this.error.set(result.error);
      this.loading.set(false);
    });
  }
}
