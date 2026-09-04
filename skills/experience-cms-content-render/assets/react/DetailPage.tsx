/**
 * {{PageName}} — auto-generated detail page for one {{type}} item (codegen-managed;
 * regenerated in full). Customize via {{type}}Layouts/{{type}}Slots in
 * `src/cms/react/types/{{type}}.ts`.
 *
 * Tokens: {{TypeRenderer}} renderer name · {{Type}} PascalCase · {{type}} camelCase ·
 * {{REF_CONST}} ref catalog key · {{PageName}} export name · {{urlSlug}} route slug.
 */
import { {{TypeRenderer}} } from '../types/{{TypeRenderer}}';
import { ref } from '../../shared/externalRefs';

export function {{PageName}}() {
  return (
    <main className="cms-detail-page cms-{{type}}-detail-page">
      <{{TypeRenderer}} ref={ref('{{REF_CONST}}')} layout="detail" />
    </main>
  );
}

export default {{PageName}};
