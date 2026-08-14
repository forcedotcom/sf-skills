#!/usr/bin/env node

import fs from "node:fs"
import path from "node:path"
import process from "node:process"
import { spawnSync } from "node:child_process"
import { pathToFileURL } from "node:url"
import {
  PUBLIC_PACKAGE,
  PUBLIC_VERSION,
  SOURCE_REF,
  SOURCE_REPOSITORY,
  sdkCacheDirectory,
  sdkManifestPath,
} from "./agentscript-sdk-loader.mjs"

function usage() {
  console.error(
    "Usage: node scripts/setup-agentscript-sdk.mjs [--npm | --source] [--version <version>] [--source-ref <ref>] [--cache-dir <path>] [--force] [--json]",
  )
}

function parseArguments(argv) {
  const options = {
    provider: "npm",
    version: PUBLIC_VERSION,
    sourceRef: SOURCE_REF,
    force: false,
    json: false,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === "--npm") options.provider = "npm"
    else if (argument === "--source") options.provider = "source"
    else if (argument === "--force") options.force = true
    else if (argument === "--json") options.json = true
    else if (argument === "--version") options.version = argv[++index]
    else if (argument === "--source-ref") options.sourceRef = argv[++index]
    else if (argument === "--cache-dir") options.cacheDirectory = argv[++index]
    else throw new Error(`Unknown argument: ${argument}`)
  }

  if (!options.version || !options.sourceRef) {
    throw new Error("--version and --source-ref require non-empty values")
  }
  if (
    options.version !== "latest" &&
    !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(options.version)
  ) {
    throw new Error("--version must be an exact semantic version or latest")
  }
  if (
    !/^[0-9A-Za-z][0-9A-Za-z._/-]{0,200}$/.test(options.sourceRef) ||
    options.sourceRef.includes("..")
  ) {
    throw new Error("--source-ref must be a branch, tag, or commit name")
  }
  return options
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    encoding: "utf8",
    env: process.env,
    stdio: options.progress
      ? ["ignore", process.stderr, process.stderr]
      : "pipe",
  })
  if (result.error) throw result.error
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || "").trim()
    throw new Error(`${command} failed (${result.status}): ${detail}`)
  }
  return (result.stdout || "").trim()
}

function assertManagedPath(target, cacheDirectory) {
  const relative = path.relative(cacheDirectory, target)
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Refusing to modify path outside SDK cache: ${target}`)
  }
}

function replaceDirectory(target, replacement, cacheDirectory) {
  assertManagedPath(target, cacheDirectory)
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true })
  fs.mkdirSync(path.dirname(target), { recursive: true })
  fs.renameSync(replacement, target)
}

async function verifyCompiler(entry) {
  const sdk = await import(`${pathToFileURL(entry).href}?smoke=${Date.now()}`)
  if (typeof sdk.compileSource !== "function") {
    throw new Error(`SDK entry does not export compileSource(): ${entry}`)
  }

  const result = sdk.compileSource(`
system:
    instructions: "Answer questions about store hours."

config:
    developer_name: "Compiler_Smoke_Test"
    agent_label: "Compiler Smoke Test"
    description: "Validates the installed AgentScript SDK."

start_agent store_hours:
    label: "Store Hours"
    description: "Answers store-hours questions."
    reasoning:
        instructions: ->
            | Answer the latest store-hours question.
`)
  const errors = (result.diagnostics || []).filter((item) => item.severity <= 2)
  if (errors.length > 0 || !result.output?.global_configuration) {
    throw new Error("Installed SDK failed its AgentScript compiler smoke test")
  }
}

function writeManifest(cacheDirectory, manifest) {
  const manifestPath = sdkManifestPath(cacheDirectory)
  fs.mkdirSync(path.dirname(manifestPath), { recursive: true })
  const temporary = `${manifestPath}.${process.pid}.tmp`
  fs.writeFileSync(temporary, `${JSON.stringify(manifest, null, 2)}\n`)
  fs.renameSync(temporary, manifestPath)
  return manifestPath
}

async function installFromNpm(options, cacheDirectory) {
  const installRoot = path.join(
    cacheDirectory,
    "agentscript-sdk",
    "npm",
    `${PUBLIC_PACKAGE.replaceAll("/", "-").replaceAll("@", "")}-${options.version}`,
  )
  const packageFile = path.join(installRoot, "package.json")

  if (options.force && fs.existsSync(installRoot)) {
    assertManagedPath(installRoot, cacheDirectory)
    fs.rmSync(installRoot, { recursive: true, force: true })
  }
  fs.mkdirSync(installRoot, { recursive: true })
  if (!fs.existsSync(packageFile)) {
    fs.writeFileSync(
      packageFile,
      `${JSON.stringify({ private: true, type: "module" }, null, 2)}\n`,
    )
  }

  const packageSpec = `${PUBLIC_PACKAGE}@${options.version}`
  if (options.force || !fs.existsSync(path.join(installRoot, "node_modules"))) {
    console.error(`Installing ${packageSpec} in the AgentScript SDK cache...`)
    run(
      "npm",
      [
        "install",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        "--save-exact",
        packageSpec,
      ],
      { cwd: installRoot, progress: true },
    )
  }

  const installedRoot = path.join(
    installRoot,
    "node_modules",
    "@sf-agentscript",
    "agentforce",
  )
  const installedPackage = JSON.parse(
    fs.readFileSync(path.join(installedRoot, "package.json"), "utf8"),
  )
  const entry = path.join(installedRoot, installedPackage.exports["."].import)
  await verifyCompiler(entry)
  return {
    provider: "npm",
    package: PUBLIC_PACKAGE,
    requestedVersion: options.version,
    version: installedPackage.version,
    entry,
  }
}

function pnpmCommand() {
  const direct = spawnSync("pnpm", ["--version"], { encoding: "utf8" })
  if (direct.status === 0) return ["pnpm", []]

  const corepack = spawnSync("corepack", ["pnpm", "--version"], {
    encoding: "utf8",
  })
  if (corepack.status === 0) return ["corepack", ["pnpm"]]
  throw new Error("Source builds require pnpm or Corepack with pnpm enabled")
}

async function installFromSource(options, cacheDirectory) {
  const sourceRoot = path.join(
    cacheDirectory,
    "agentscript-sdk",
    "source",
    "checkout",
  )
  const temporary = path.join(
    cacheDirectory,
    "agentscript-sdk",
    "source",
    `checkout-${process.pid}.tmp`,
  )
  assertManagedPath(temporary, cacheDirectory)

  if (fs.existsSync(sourceRoot) && !options.force) {
    const entry = path.join(
      sourceRoot,
      "packages",
      "agentforce",
      "dist",
      "index.js",
    )
    if (!fs.existsSync(entry)) {
      throw new Error(
        "Cached source checkout is incomplete; rerun with --source --force",
      )
    }
    await verifyCompiler(entry)
    return {
      provider: "source",
      repository: SOURCE_REPOSITORY,
      requestedRef: options.sourceRef,
      sourceRevision: run("git", ["rev-parse", "HEAD"], { cwd: sourceRoot }),
      entry,
    }
  }

  if (fs.existsSync(temporary))
    fs.rmSync(temporary, { recursive: true, force: true })
  fs.mkdirSync(temporary, { recursive: true })
  try {
    console.error(`Fetching ${SOURCE_REPOSITORY} at ${options.sourceRef}...`)
    run("git", ["init", "--quiet"], { cwd: temporary })
    run("git", ["remote", "add", "origin", SOURCE_REPOSITORY], {
      cwd: temporary,
    })
    run(
      "git",
      ["fetch", "--quiet", "--depth", "1", "origin", options.sourceRef],
      {
        cwd: temporary,
        progress: true,
      },
    )
    run("git", ["checkout", "--quiet", "--detach", "FETCH_HEAD"], {
      cwd: temporary,
    })

    const [pnpm, prefix] = pnpmCommand()
    console.error(
      "Installing the public source checkout's pinned dependencies...",
    )
    run(pnpm, [...prefix, "install", "--frozen-lockfile"], {
      cwd: temporary,
      progress: true,
    })
    console.error(
      "Building the AgentScript Agentforce SDK and its dependencies...",
    )
    run(pnpm, [...prefix, "--filter", "@agentscript/agentforce...", "build"], {
      cwd: temporary,
      progress: true,
    })

    const temporaryEntry = path.join(
      temporary,
      "packages",
      "agentforce",
      "dist",
      "index.js",
    )
    await verifyCompiler(temporaryEntry)
    const sourceRevision = run("git", ["rev-parse", "HEAD"], {
      cwd: temporary,
    })
    replaceDirectory(sourceRoot, temporary, cacheDirectory)
    return {
      provider: "source",
      repository: SOURCE_REPOSITORY,
      requestedRef: options.sourceRef,
      sourceRevision,
      entry: path.join(
        sourceRoot,
        "packages",
        "agentforce",
        "dist",
        "index.js",
      ),
    }
  } catch (error) {
    if (fs.existsSync(temporary))
      fs.rmSync(temporary, { recursive: true, force: true })
    throw error
  }
}

async function main() {
  let options
  try {
    options = parseArguments(process.argv.slice(2))
  } catch (error) {
    usage()
    throw error
  }

  const cacheDirectory = sdkCacheDirectory(options.cacheDirectory)
  const installed =
    options.provider === "source"
      ? await installFromSource(options, cacheDirectory)
      : await installFromNpm(options, cacheDirectory)
  const manifest = {
    ...installed,
    installedAt: new Date().toISOString(),
  }
  const manifestPath = writeManifest(cacheDirectory, manifest)
  const result = { status: "ok", cacheDirectory, manifestPath, ...manifest }

  if (options.json) console.log(JSON.stringify(result, null, 2))
  else
    console.log(
      `AgentScript SDK ready: ${installed.provider} (${installed.entry})`,
    )
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
