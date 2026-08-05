# Engine Reference

## Engine File Type Support

| Engine | File Extensions |
|---|---|
| **pmd** | `.cls`, `.trigger`, `.js`, `.html`, `.htm`, `.vfp`, `.component`, `.page`, `.xml` |
| **eslint** | `.js`, `.ts`, `.jsx`, `.tsx` |
| **cpd** | `.cls`, `.trigger`, `.js`, `.ts`, `.html`, `.htm`, `.vfp`, `.component`, `.page`, `.xml` |
| **retire-js** | `.js`, `.ts`, `package.json`, `package-lock.json` |
| **regex** | Configurable per rule via `file_extensions` |
| **flow** | `.flow-meta.xml` |
| **sfge** | `.cls`, `.trigger` |
| **apexguru** | `.cls`, `.trigger` |

## Common Rule Tags

These tags can be used in rule selectors:

| Tag | Meaning |
|---|---|
| `Recommended` | Default ruleset — curated for most projects |
| `Security` | Security vulnerabilities (CRUD, XSS, injection, crypto) |
| `Performance` | Performance anti-patterns (SOQL in loops, limits) |
| `BestPractices` | Coding standards and conventions |
| `CodeStyle` | Naming, formatting, braces |
| `Design` | Complexity, coupling, architecture |
| `ErrorProne` | Common bug patterns |
| `Documentation` | Missing docs, comments |
| `Apex` | Rules applying to Apex language |
| `JavaScript` | Rules applying to JavaScript |
| `TypeScript` | Rules applying to TypeScript |
| `HTML` | Rules applying to HTML/Visualforce |
| `Custom` | User-defined rules |
