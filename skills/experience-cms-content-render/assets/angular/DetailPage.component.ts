/**
 * {{PageName}}Component — auto-generated detail page for one {{type}} item (Angular;
 * codegen-managed; regenerated in full). Customize via {{type}}Layouts/{{type}}Slots
 * in `src/cms/angular/types/{{type}}.ts`.
 *
 * Tokens: {{Type}} PascalCase · {{type}} camelCase · {{REF_CONST}} ref catalog key ·
 * {{PageName}} export name · {{urlSlug}} route slug.
 */
import { Component } from '@angular/core';
import { {{Type}}RendererComponent } from '../types/{{Type}}Renderer.component';
import { ref } from '../../shared/externalRefs';

@Component({
  selector: '{{urlSlug}}-detail-page',
  standalone: true,
  imports: [{{Type}}RendererComponent],
  template: `
    <main class="cms-detail-page cms-{{type}}-detail-page">
      <cms-{{type}} [ref]="itemRef" layout="detail"></cms-{{type}}>
    </main>
  `,
})
export class {{PageName}}Component {
  readonly itemRef = ref('{{REF_CONST}}');
}
