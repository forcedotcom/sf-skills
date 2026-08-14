import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

export const PUBLIC_PACKAGE = "@sf-agentscript/agentforce"
export const PUBLIC_VERSION = "2.9.27"
export const LEGACY_PACKAGE = "@agentscript/agentforce"
export const SOURCE_REPOSITORY = "https://github.com/salesforce/agentscript.git"
export const SOURCE_REF = "main"

export function sdkCacheDirectory(explicitDirectory) {
  if (explicitDirectory) return path.resolve(explicitDirectory)
  if (process.env.AGENTFORCE_GENERATE_CACHE) {
    return path.resolve(process.env.AGENTFORCE_GENERATE_CACHE)
  }

  const cacheRoot = process.env.XDG_CACHE_HOME
    ? path.resolve(process.env.XDG_CACHE_HOME)
    : path.join(os.homedir(), ".cache")
  return path.join(cacheRoot, "agentforce-generate")
}

export function sdkManifestPath(cacheDirectory) {
  return path.join(cacheDirectory, "agentscript-sdk", "current.json")
}

function resolvePackage(packageName, baseFile) {
  const basePath = baseFile.startsWith("file:")
    ? fileURLToPath(baseFile)
    : baseFile
  let directory =
    fs.existsSync(basePath) && fs.statSync(basePath).isDirectory()
      ? basePath
      : path.dirname(basePath)

  while (true) {
    const packageRoot = path.join(
      directory,
      "node_modules",
      ...packageName.split("/"),
    )
    const packageFile = path.join(packageRoot, "package.json")
    if (fs.existsSync(packageFile)) {
      try {
        const manifest = JSON.parse(fs.readFileSync(packageFile, "utf8"))
        const relativeEntry = manifest.exports?.["."]?.import || manifest.main
        if (relativeEntry) {
          return {
            entry: path.join(packageRoot, relativeEntry),
            version: manifest.version,
          }
        }
      } catch {
        return undefined
      }
    }

    const parent = path.dirname(directory)
    if (parent === directory) return undefined
    directory = parent
  }
}

function packageCandidates() {
  const cwdBase = path.join(process.cwd(), "package.json")
  return [
    [PUBLIC_PACKAGE, cwdBase],
    [LEGACY_PACKAGE, cwdBase],
    [PUBLIC_PACKAGE, import.meta.url],
    [LEGACY_PACKAGE, import.meta.url],
  ]
}

async function loadEntry(entry, provenance) {
  if (!entry || !fs.existsSync(entry)) return undefined

  try {
    const sdk = await import(pathToFileURL(entry).href)
    if (typeof sdk.compileSource !== "function") return undefined
    return { sdk, entry, ...provenance }
  } catch {
    return undefined
  }
}

export async function loadAgentScriptSdk(options = {}) {
  const cacheDirectory = sdkCacheDirectory(options.cacheDirectory)
  const explicitEntry = process.env.AGENTSCRIPT_SDK_ENTRY
  if (explicitEntry) {
    const loaded = await loadEntry(path.resolve(explicitEntry), {
      provider: "explicit",
    })
    if (loaded) return loaded
    throw new Error(
      `AGENTSCRIPT_SDK_ENTRY does not expose compileSource(): ${explicitEntry}`,
    )
  }

  const manifestPath = sdkManifestPath(cacheDirectory)
  if (fs.existsSync(manifestPath)) {
    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"))
      const loaded = await loadEntry(manifest.entry, {
        provider: manifest.provider,
        package: manifest.package,
        version: manifest.version,
        sourceRevision: manifest.sourceRevision,
        manifestPath,
      })
      if (loaded) return loaded
    } catch {
      // Continue to ambient package resolution and return one actionable error.
    }
  }

  for (const [packageName, baseFile] of packageCandidates()) {
    const resolved = resolvePackage(packageName, baseFile)
    const loaded = await loadEntry(resolved?.entry, {
      provider: "ambient-npm",
      package: packageName,
      version: resolved?.version,
    })
    if (loaded) return loaded
  }

  const setupScript = fileURLToPath(
    new URL("./setup-agentscript-sdk.mjs", import.meta.url),
  )
  throw new Error(
    `AgentScript SDK not found. Run \`node "${setupScript}" --npm --json\`, then retry.`,
  )
}
