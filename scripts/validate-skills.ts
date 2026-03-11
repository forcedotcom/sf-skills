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

const SKILLS_DIR = path.join(__dirname, "..", "skills")

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SkillContext {
  dirName: string
  dirPath: string
  content: string
  frontmatter: Record<string, string> | null
  body: string
}

interface CheckResult {
  errors: string[]
  /** When true and errors is non-empty, skip remaining checks for this entry. */
  fatal?: boolean
}

interface StructureCheck {
  description: string
  run(dirName: string, dirPath: string): CheckResult
}

interface ContentCheck {
  description: string
  run(ctx: SkillContext): CheckResult
}

// ---------------------------------------------------------------------------
// Structure checks — run on every entry in skills/ before reading SKILL.md.
// Fatal errors abort content checks for that entry.
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Content checks — run only on entries that have SKILL.md.
// Fatal errors abort remaining content checks for that entry.
// ---------------------------------------------------------------------------

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
]

// ---------------------------------------------------------------------------
// Changed-skills detection
// ---------------------------------------------------------------------------

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
  ]
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseFrontmatter(content: string): Record<string, string> | null {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/)
  if (!match) return null
  const result: Record<string, string> = {}
  for (const line of match[1].split(/\r?\n/)) {
    const colonIdx = line.indexOf(":")
    if (colonIdx === -1) continue
    const key = line.slice(0, colonIdx).trim()
    // Strip wrapping single or double quotes to match how consumers read values
    const raw = line.slice(colonIdx + 1).trim()
    result[key] = raw.replace(/^(['"])([\s\S]*)\1$/, "$2")
  }
  return result
}

function getFrontmatterEnd(content: string): number {
  const match = content.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/)
  return match ? match[0].length : -1
}

// ---------------------------------------------------------------------------
// Main validation loop
// ---------------------------------------------------------------------------

function validateSkill(dirName: string, dirPath: string): string[] {
  if (!fs.existsSync(dirPath)) {
    return [`skills/${dirName}: directory not found`]
  }

  const errors: string[] = []

  for (const check of STRUCTURE_CHECKS) {
    const { errors: checkErrors, fatal } = check.run(dirName, dirPath)
    errors.push(...checkErrors)
    if (fatal && checkErrors.length > 0) return errors
  }

  const content = fs.readFileSync(path.join(dirPath, "SKILL.md"), "utf8")
  const frontmatter = parseFrontmatter(content)
  const frontmatterEnd = getFrontmatterEnd(content)
  const body = frontmatterEnd !== -1 ? content.slice(frontmatterEnd) : ""
  const ctx: SkillContext = { dirName, dirPath, content, frontmatter, body }

  for (const check of CONTENT_CHECKS) {
    const { errors: checkErrors, fatal } = check.run(ctx)
    errors.push(...checkErrors)
    if (fatal && checkErrors.length > 0) return errors
  }

  return errors
}

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
  let passed = 0

  for (const entry of entries) {
    const entryErrors = validateSkill(entry, path.join(SKILLS_DIR, entry))
    allErrors.push(...entryErrors)
    if (entryErrors.length === 0) passed++
  }

  if (allErrors.length > 0) {
    console.error(`\nSkill validation failed with ${allErrors.length} error(s):\n`)
    for (const err of allErrors) {
      console.error(`  ✗ ${err}`)
    }
    console.error("")
    process.exit(1)
  } else {
    console.log(`Skill validation passed: ${passed} of ${entries.length} skill(s) checked.`)
  }
}

main()
