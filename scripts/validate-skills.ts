#!/usr/bin/env tsx
// Validates the skills/ directory structure and SKILL.md format.
// Exits with code 1 if any violations are found.
//
// Usage:
//   npm run validate:skills                                        # validate all skills
//   npm run validate:skills -- --changed --base=origin/main       # validate only skills changed vs base

import { execSync } from "child_process"
import fs from "fs"
import path from "path"
import { parseArgs } from "util"
import yaml from "js-yaml"

const SKILLS_DIR = path.join(__dirname, "..", "skills")

/** Parsed context for a single skill directory, built before content checks run. */
interface SkillContext {
  dirName: string
  dirPath: string
  content: string
  /** YAML source between `---` lines; `null` if the block is missing. */
  rawFrontmatter: string | null
  frontmatter: Record<string, string> | null
  body: string
}

/** Return value of every check function. */
interface CheckResult {
  errors: string[]
  /** When true and errors is non-empty, skip remaining checks for this entry. */
  fatal?: boolean
  /** Defaults to "error". Warnings are printed but do not cause a non-zero exit code. */
  severity?: "error" | "warning"
}

/** Collected results for a single skill entry. */
interface SkillResult {
  errors: string[]
  warnings: string[]
}

/** Runs before SKILL.md is read — validates directory layout. */
interface StructureCheck {
  description: string
  run(dirName: string, dirPath: string): CheckResult
}

/** Runs after SKILL.md is read — validates file content. */
interface ContentCheck {
  description: string
  run(ctx: SkillContext): CheckResult
}

/**
 * Structure checks run on every entry in `skills/` before SKILL.md is read.
 * A fatal error aborts content checks for that entry.
 */
const STRUCTURE_CHECKS: StructureCheck[] = [
  {
    description: "Entry must be a directory (no loose files in skills/)",
    run(dirName, dirPath) {
      if (!fs.statSync(dirPath).isDirectory()) {
        return { errors: [`Loose file in skills/: ${dirName} (expected only directories)`], fatal: true }
      }
      return { errors: [] }
    },
  },
  {
    description: "Skill directory must contain SKILL.md",
    run(dirName, dirPath) {
      if (!fs.existsSync(path.join(dirPath, "SKILL.md"))) {
        return { errors: [`Missing SKILL.md in skills/${dirName}/`], fatal: true }
      }
      return { errors: [] }
    },
  },
  {
    description: "Name must be kebab-case (lowercase letters, digits, and hyphens only)",
    run(dirName) {
      if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(dirName)) {
        return { errors: [`skills/${dirName}: name must be kebab-case (only lowercase letters, digits, and hyphens)`] }
      }
      return { errors: [] }
    },
  },
  {
    description: "Name must be at most 64 characters",
    run(dirName) {
      if (dirName.length > 64) {
        return { errors: [`skills/${dirName}: name is ${dirName.length} characters (maximum 64)`] }
      }
      return { errors: [] }
    },
  },
  {
    description: "Name should use gerund form — first word should end in -ing (e.g. generating-apex-tests)",
    run(dirName) {
      if (!dirName.split("-")[0].endsWith("ing")) {
        return {
          errors: [`skills/${dirName}: name should use gerund form (e.g. generating-apex-tests, refactoring-triggers)`],
          severity: "warning",
        }
      }
      return { errors: [] }
    },
  },
  {
    description: "Skills must be exactly one level deep (no nested category directories)",
    run(dirName, dirPath) {
      const errors: string[] = []
      for (const sub of fs.readdirSync(dirPath)) {
        const subPath = path.join(dirPath, sub)
        if (fs.statSync(subPath).isDirectory() && fs.existsSync(path.join(subPath, "SKILL.md"))) {
          errors.push(
            `Nested skill detected: skills/${dirName}/${sub}/SKILL.md — skill directories must be exactly one level deep under skills/`
          )
        }
      }
      return { errors }
    },
  },
]

/**
 * Content checks run only on entries that have a valid SKILL.md.
 * A fatal error aborts remaining content checks for that entry.
 */
const CONTENT_CHECKS: ContentCheck[] = [
  {
    description: "SKILL.md must have a valid YAML frontmatter block (--- ... ---)",
    run({ dirName, frontmatter }) {
      if (!frontmatter) {
        return {
          errors: [`skills/${dirName}/SKILL.md: missing or malformed YAML frontmatter (expected --- ... --- block at top)`],
          fatal: true,
        }
      }
      return { errors: [] }
    },
  },
  {
    description:
      "Frontmatter must parse as JSON-compatible YAML (js-yaml JSON_SCHEMA); unquoted colons in values break strict parsers",
    run({ dirName, rawFrontmatter }) {
      if (rawFrontmatter === null) return { errors: [] }
      try {
        yaml.load(rawFrontmatter, { schema: yaml.JSON_SCHEMA })
      } catch (e) {
        if (e instanceof yaml.YAMLException) {
          const detail = formatYamlFrontmatterParseError(e)
          return {
            errors: [
              `skills/${dirName}/SKILL.md: frontmatter is not valid YAML.
${detail}
Wrap values that contain \`: \` (colon + space), such as long descriptions with parenthetical hints, in single or double quotes.`,
            ],
          }
        }
        throw e
      }
      return { errors: [] }
    },
  },
  {
    description: 'Frontmatter "name" must be present and match the directory name',
    run({ dirName, frontmatter }) {
      if (!frontmatter) return { errors: [] }
      if (!frontmatter.name) {
        return { errors: [`skills/${dirName}/SKILL.md: missing "name" field in frontmatter`] }
      }
      if (frontmatter.name !== dirName) {
        return {
          errors: [
            `skills/${dirName}/SKILL.md: "name" value ("${frontmatter.name}") does not match directory name ("${dirName}")`,
          ],
        }
      }
      return { errors: [] }
    },
  },
  {
    description: 'Frontmatter "description" must be present and non-empty',
    run({ dirName, frontmatter }) {
      if (!frontmatter) return { errors: [] }
      if (!frontmatter.description?.trim()) {
        return { errors: [`skills/${dirName}/SKILL.md: missing or empty "description" field in frontmatter`] }
      }
      return { errors: [] }
    },
  },
  {
    description: "SKILL.md must have a non-empty body (instructions after the frontmatter block)",
    run({ dirName, body }) {
      if (!body.trim()) {
        return { errors: [`skills/${dirName}/SKILL.md: body (instructions after frontmatter) is empty`] }
      }
      return { errors: [] }
    },
  },
  {
    description: "Description must be at least 20 words to be information-rich",
    run({ dirName, frontmatter }) {
      if (!frontmatter) return { errors: [] }
      const words = frontmatter.description?.trim().split(/\s+/) ?? []
      if (words.length < 20) {
        return {
          errors: [`skills/${dirName}/SKILL.md: description too short (${words.length} word(s), minimum 20)`],
        }
      }
      return { errors: [] }
    },
  },
  {
    description: "Description must be at most 1024 characters",
    run({ dirName, frontmatter }) {
      if (!frontmatter) return { errors: [] }
      const len = frontmatter.description?.length ?? 0
      if (len > 1024) {
        return { errors: [`skills/${dirName}/SKILL.md: description is ${len} characters (maximum 1024)`] }
      }
      return { errors: [] }
    },
  },
  {
    description: 'Description must include trigger/activation language (contain "use")',
    run({ dirName, frontmatter }) {
      if (!frontmatter) return { errors: [] }
      if (!frontmatter.description?.toLowerCase().includes("use")) {
        return {
          errors: [
            `skills/${dirName}/SKILL.md: description must include trigger context (e.g. "Use this skill when...")`,
          ],
        }
      }
      return { errors: [] }
    },
  },
  {
    description: "Skill body should be under 500 lines for context efficiency",
    run({ dirName, body }) {
      const lines = body.split("\n").length
      if (lines > 500) {
        return {
          errors: [`skills/${dirName}/SKILL.md: body is ${lines} lines (recommended maximum is 500)`],
          severity: "warning",
        }
      }
      return { errors: [] }
    },
  },
]

/**
 * Returns the deduplicated list of top-level skill directory names that have
 * changed relative to `base` (e.g. `origin/main`) and still exist on disk.
 * Deleted skill directories are intentionally excluded — removing a skill is
 * valid and requires no structural validation.
 */
function getChangedSkillDirs(base: string): string[] {
  const output = execSync(`git diff --name-only ${base}...HEAD`, { encoding: "utf8" })
  return [
    ...new Set(
      output
        .split("\n")
        .filter((f) => f.startsWith("skills/"))
        .map((f) => f.split("/")[1])
        .filter(Boolean)
    ),
  ].filter((dir) => fs.existsSync(path.join(SKILLS_DIR, dir)))
}

/** Formats js-yaml YAMLException with guarded mark fields and optional snippet. */
function formatYamlFrontmatterParseError(e: yaml.YAMLException): string {
  const reason =
    typeof e.reason === "string" && e.reason.trim() !== "" ? e.reason : "YAML parse error"
  const m = e.mark
  if (!m) return reason

  const line = typeof m.line === "number" ? m.line + 1 : "?"
  const col = typeof m.column === "number" ? m.column + 1 : "?"
  const index = typeof m.position === "number" ? m.position + 1 : "?"
  const head = `${reason} — line ${line}, column ${col} (1-based), character index ${index} in frontmatter YAML`
  const snippet = typeof m.snippet === "string" && m.snippet.trim() !== "" ? m.snippet.trimEnd() : ""
  return snippet ? `${head}\n${snippet}` : head
}

/**
 * Raw YAML between the opening and closing `---` lines (no delimiters).
 * `null` if the block is missing.
 */
function parseFrontmatterBlock(content: string): { raw: string; fullMatchLen: number } | null {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/)
  if (!match) return null
  return { raw: match[1], fullMatchLen: match[0].length }
}

/**
 * Parses a SKILL.md file into its frontmatter fields and body.
 * `frontmatter` is `null` if the `--- ... ---` block is missing or malformed.
 * Wrapping quotes on frontmatter values are stripped.
 */
function parseSkillMd(content: string): {
  rawFrontmatter: string | null
  frontmatter: Record<string, string> | null
  body: string
} {
  const block = parseFrontmatterBlock(content)
  if (!block) return { rawFrontmatter: null, frontmatter: null, body: content }

  const frontmatter: Record<string, string> = {}
  for (const line of block.raw.split(/\r?\n/)) {
    const colonIdx = line.indexOf(":")
    if (colonIdx === -1) continue
    const key = line.slice(0, colonIdx).trim()
    const raw = line.slice(colonIdx + 1).trim()
    // Strip wrapping single or double quotes to match how consumers read values
    frontmatter[key] = raw.replace(/^(['"])([\s\S]*)\1$/, "$2")
  }

  return {
    rawFrontmatter: block.raw,
    frontmatter,
    body: content.slice(block.fullMatchLen),
  }
}

/**
 * Runs all structure and content checks for a single skill directory.
 * Returns errors (block CI) and warnings (advisory, printed but exit 0) separately.
 */
function validateSkill(dirName: string, dirPath: string): SkillResult {
  if (!fs.existsSync(dirPath)) {
    return { errors: [`skills/${dirName}: directory not found`], warnings: [] }
  }

  const errors: string[] = []
  const warnings: string[] = []

  const collectIssues = (result: CheckResult): boolean => {
    if (result.errors.length === 0) return false
    if (result.severity === "warning") {
      warnings.push(...result.errors)
    } else {
      errors.push(...result.errors)
    }
    return result.fatal === true && result.severity !== "warning"
  }

  for (const check of STRUCTURE_CHECKS) {
    if (collectIssues(check.run(dirName, dirPath))) return { errors, warnings }
  }

  const content = fs.readFileSync(path.join(dirPath, "SKILL.md"), "utf8")
  const { rawFrontmatter, frontmatter, body } = parseSkillMd(content)
  const ctx: SkillContext = { dirName, dirPath, content, rawFrontmatter, frontmatter, body }

  for (const check of CONTENT_CHECKS) {
    if (collectIssues(check.run(ctx))) return { errors, warnings }
  }

  return { errors, warnings }
}

/** CLI entry point. Parses flags, resolves the list of skills to check, and reports results. */
function main(): void {
  const { values } = parseArgs({
    args: process.argv.slice(2),
    options: {
      /** Validate only skill dirs touched in this branch vs the given base ref. */
      changed: { type: "boolean", default: false },
      /** Base ref for --changed (e.g. origin/main). Defaults to origin/HEAD. */
      base: { type: "string", default: "origin/HEAD" },
    },
  })

  let entries: string[]

  if (values.changed) {
    entries = getChangedSkillDirs(values.base!)
    if (entries.length === 0) {
      console.log("No skill directories changed — nothing to validate.")
      return
    }
    console.log(`Validating ${entries.length} changed skill(s): ${entries.join(", ")}`)
  } else {
    entries = fs.readdirSync(SKILLS_DIR)
  }

  const allErrors: string[] = []
  const allWarnings: string[] = []
  let passed = 0

  for (const entry of entries) {
    const { errors, warnings } = validateSkill(entry, path.join(SKILLS_DIR, entry))
    allErrors.push(...errors)
    allWarnings.push(...warnings)
    if (errors.length === 0) passed++
  }

  const hasIssues = allErrors.length > 0 || allWarnings.length > 0
  const footer = "Spec: https://agentskills.io/specification · Authoring guide: https://github.com/forcedotcom/afv-library#readme"

  if (allWarnings.length > 0) {
    console.warn(`\n${allWarnings.length} warning(s):\n`)
    for (const w of allWarnings) {
      console.warn(`  ⚠ ${w}`)
    }
    console.warn("")
  }

  if (allErrors.length > 0) {
    console.error(`\nSkill validation failed with ${allErrors.length} error(s):\n`)
    for (const err of allErrors) {
      console.error(`  ✗ ${err}`)
    }
    console.error("")
    console.error(footer)
    console.error("")
    process.exit(1)
  } else {
    console.log(`Skill validation passed: ${passed} of ${entries.length} skill(s) checked.`)
    if (hasIssues) console.warn(footer)
  }
}

main()
