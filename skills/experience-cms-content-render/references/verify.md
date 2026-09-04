# Verify — bounded typecheck + fix policy

Detail for Embed pipeline step 5 (SKILL.md → *Embed pipeline* → *5. Verify*).
SKILL.md holds the one-pass rule; this file holds the full fix policy and the report
checklist.

## Typecheck ONLY the files this skill wrote or edited — bounded, never a loop

Run `npx tsc --noEmit` ONCE (React/Vite) or `npx tsc --noEmit -p tsconfig.json` ONCE
(Angular). Then read ONLY the diagnostics whose file path the skill touched this run:
foundation files, `<framework>/types/<type>.ts` + renderer, `externalRefs.ts`, the
render target, detail pages. Every diagnostic in a file the skill did NOT touch is
pre-existing; ignore it, do not fix it, do not open it.

If no TypeScript is configured (no `tsc`/`tsconfig`), skip and note it.

## Fix policy — at most ONE fix pass, then stop

- Diagnostic in a file the skill **generated** this run (`<type>.ts` below-marker
  `<Type>Body`, a ref entry, an import specifier, an unused symbol, a `.value`
  unwrap) → fix it, then re-run tsc **once** to confirm. One pass, one re-run, no
  more.
- Diagnostic in a **verbatim foundation file** (`useCmsItem.ts`,
  `heuristicRenderer.tsx`, `cms-item.service.ts`, `cms-content.component.ts`,
  `cmsCore.types.ts`, …) → **do NOT edit or rewrite it.** These are copied
  byte-for-byte and correct by construction; a diagnostic here is almost always the
  toolkit not resolvable yet (install / tsconfig-paths / JSX config), NOT a code
  defect. Report it as an environment/install note ("toolkit unresolved — confirm
  `npm i` ran and tsconfig resolves `@salesforce/…`"); if certain it is a genuine
  template bug, REPORT it, never patch in place.
- Do NOT run `lint`, `build`, `ng build`, or the dev server; do NOT re-derive the
  toolkit contract from `references/*` to "fix" a template. If errors remain after
  the single fix pass, report them verbatim and stop.

## Report

Report: files written/modified (paths + inserted line ranges); the `npm install` if
run; the typecheck result (clean / fixed N in generated files / skipped) plus any
environment or pre-existing notes; ref name + identity; renderer type; chosen render
target; and any HALTs. The skill does NOT run lint, a build, or the dev server.

**Media on an authenticated channel — temporary-limitation note.** When this run
scaffolds media (`sfdc_cms__{image,audio,video,document}`) whose ref is a `CmsRef`
(a `contentKey`, read via authenticated Connect / a uiBundle channel), add a note to
the report: *rendering that media inside an internal app is not supported yet — this
is a temporary platform limitation planned for a future release; media served from a
public delivery URL (a `CmsExternalRef`) renders today.* Scaffold normally and do not
HALT — the note is informational only. Media registered as a `CmsExternalRef` (public
URL) needs no note.
