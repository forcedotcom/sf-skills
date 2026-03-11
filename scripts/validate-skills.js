#!/usr/bin/env node
// Validates the skills/ directory structure and SKILL.md format.
// Exits with code 1 if any violations are found.

const fs = require("fs")
const path = require("path")

const SKILLS_DIR = path.join(__dirname, "..", "skills")

let errors = []
let checked = 0

function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/)
  if (!match) return null
  const raw = match[1]
  const result = {}
  for (const line of raw.split(/\r?\n/)) {
    const colonIdx = line.indexOf(":")
    if (colonIdx === -1) continue
    const key = line.slice(0, colonIdx).trim()
    const value = line.slice(colonIdx + 1).trim()
    result[key] = value
  }
  return result
}

function getFrontmatterEnd(content) {
  const match = content.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/)
  if (!match) return -1
  return match[0].length
}

const topLevelEntries = fs.readdirSync(SKILLS_DIR)

for (const entry of topLevelEntries) {
  const entryPath = path.join(SKILLS_DIR, entry)
  const stat = fs.statSync(entryPath)

  if (!stat.isDirectory()) {
    errors.push(`Loose file in skills/: ${entry} (expected only directories)`)
    continue
  }

  const skillMdPath = path.join(entryPath, "SKILL.md")
  if (!fs.existsSync(skillMdPath)) {
    errors.push(`Missing SKILL.md in skills/${entry}/`)
    continue
  }

  // Check for nested subdirectories that also contain SKILL.md
  const subEntries = fs.readdirSync(entryPath)
  for (const sub of subEntries) {
    const subPath = path.join(entryPath, sub)
    if (fs.statSync(subPath).isDirectory()) {
      const nestedSkillMd = path.join(subPath, "SKILL.md")
      if (fs.existsSync(nestedSkillMd)) {
        errors.push(
          `Nested skill detected: skills/${entry}/${sub}/SKILL.md — skill directories must be exactly one level deep under skills/`
        )
      }
    }
  }

  // Validate SKILL.md frontmatter and body
  const content = fs.readFileSync(skillMdPath, "utf8")

  const frontmatter = parseFrontmatter(content)
  if (!frontmatter) {
    errors.push(`skills/${entry}/SKILL.md: missing or malformed YAML frontmatter (expected --- ... --- block at top)`)
    continue
  }

  if (!frontmatter.name) {
    errors.push(`skills/${entry}/SKILL.md: missing "name" field in frontmatter`)
  } else if (frontmatter.name !== entry) {
    errors.push(
      `skills/${entry}/SKILL.md: "name" field ("${frontmatter.name}") does not match directory name ("${entry}")`
    )
  }

  if (!frontmatter.description || frontmatter.description.trim() === "") {
    errors.push(`skills/${entry}/SKILL.md: missing or empty "description" field in frontmatter`)
  }

  const frontmatterEnd = getFrontmatterEnd(content)
  const body = frontmatterEnd !== -1 ? content.slice(frontmatterEnd).trim() : ""
  if (!body) {
    errors.push(`skills/${entry}/SKILL.md: body (instructions after frontmatter) is empty`)
  }

  checked++
}

if (errors.length > 0) {
  console.error(`\nSkill validation failed with ${errors.length} error(s):\n`)
  for (const err of errors) {
    console.error(`  ✗ ${err}`)
  }
  console.error("")
  process.exit(1)
} else {
  console.log(`Skill validation passed: ${checked} skill(s) checked.`)
}
