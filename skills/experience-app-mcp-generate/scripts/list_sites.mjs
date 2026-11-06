#!/usr/bin/env node
// List local Experience Sites with readiness and support status.
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
if (args.length > 1) {
  console.error("Usage: list_sites.mjs [project-root]");
  process.exit(1);
}

function entries(dir) {
  return fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }) : [];
}

function* files(dir) {
  for (const entry of entries(dir)) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && !["node_modules", "dist", "build"].includes(entry.name) && !entry.name.startsWith(".")) {
      yield* files(full);
    } else if (entry.isFile()) {
      yield full;
    }
  }
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function* componentNames(value) {
  if (Array.isArray(value)) {
    for (const child of value) yield* componentNames(child);
  } else if (value && typeof value === "object") {
    if (typeof value.componentName === "string") yield value.componentName;
    for (const child of Object.values(value)) yield* componentNames(child);
  }
}

function hasAuraComponents(names, roots) {
  if (names.some((name) => /^(community_builder|community_layout|community_login):/.test(name))) return false;
  return names.some((name) => /^(forceCommunity|siteforce):/.test(name) ||
    (/^c:[a-zA-Z][a-zA-Z0-9_]*$/.test(name) && roots.some((root) => fs.existsSync(path.join(root, "aura", name.slice(2), `${name.slice(2)}.cmp`)))));
}

function tag(xml, name) {
  return (xml.match(new RegExp(`<${name}>\\s*([^<]*?)\\s*</${name}>`))?.[1] ?? "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'").replace(/&amp;/g, "&");
}

function matchesUrlPathPrefix(surface, network) {
  return !!network.urlPathPrefix && surface.urlPathPrefixes.some((prefix) => prefix === network.urlPathPrefix || prefix.replace(/\/s\/?$/, "") === network.urlPathPrefix);
}

function matchesSiteBundleName(surface, network) {
  // Use the same site-name-to-bundle derivation as Core and SF CLI.
  let decodedName;
  try {
    decodedName = decodeURIComponent(network.name);
  } catch (error) {
    if (error instanceof URIError) return false;
    throw error;
  }
  const name = decodedName
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/_$/, "")
    .replace(/^([0-9])/, "X$1");
  return !!name && surface.bundle === `${name}1`;
}

function assignNetworkBundles(links) {
  for (const { network, surface } of links) {
    const matches = links.filter((link) => link.surface === surface);
    if (matches.length > 1) surface.reason = `Multiple Networks match bundle ${surface.bundle}: ${matches.map((link) => link.network.name).join(", ")}`;
    network.bundle = surface.bundle;
  }
}

function recordAmbiguity(network, surfaces) {
  network.reason = `Ambiguous bundles for Network ${network.name}: ${surfaces.map((surface) => surface.bundle).join(", ")}`;
  network.candidateSurfaces = surfaces;
  for (const surface of surfaces) surface.reason = network.reason;
}

function mergeSourceConflicts(surfaces) {
  const conflicts = new Set(surfaces.filter((site) => surfaces.some((other) => other.bundle === site.bundle && other.sourceFormat !== site.sourceFormat)).map((site) => site.bundle));
  return surfaces.filter((site, index) => {
    if (!conflicts.has(site.bundle)) return true;
    const sources = surfaces.filter((other) => other.bundle === site.bundle);
    if (index !== surfaces.indexOf(sources[0])) return false;
    site.sourceFormat = null;
    site.reason = `Conflicting source formats for bundle ${site.bundle}`;
    for (const key of ["uiRoots", "entryFiles", "urlPathPrefixes", "evidence"]) site[key] = sources.flatMap((source) => source[key]);
    return true;
  });
}

function listSites(projectRoot) {
  const project = readJson(path.join(projectRoot, "sfdx-project.json"));
  if (!project.packageDirectories?.length || project.packageDirectories.some((pkg) => typeof pkg.path !== "string" || !pkg.path)) {
    throw new Error("sfdx-project.json must contain packageDirectories with paths");
  }
  const roots = project.packageDirectories.map((pkg) => path.resolve(projectRoot, pkg.path, "main/default"));
  const networks = [];
  const configs = [];
  let surfaces = [];
  for (const root of roots) {
    for (const file of files(path.join(root, "networks"))) {
      if (!file.endsWith(".network-meta.xml")) continue;
      const xml = fs.readFileSync(file, "utf8");
      networks.push({ file, bundle: tag(xml, "picassoSite"), name: path.basename(file, ".network-meta.xml"), urlPathPrefix: tag(xml, "urlPathPrefix") });
    }
    for (const file of files(path.join(root, "digitalExperienceConfigs"))) {
      if (!file.endsWith(".digitalExperienceConfig-meta.xml")) continue;
      const xml = fs.readFileSync(file, "utf8");
      configs.push({ file, sourceFormat: "digital-experience", bundle: tag(xml, "space").replace(/^site\//, ""), name: tag(xml, "label") || path.basename(file, ".digitalExperienceConfig-meta.xml"), urlPathPrefix: tag(xml, "urlPathPrefix") });
    }
    const experienceBundles = new Set(entries(path.join(root, "experiences")).flatMap((entry) => entry.isDirectory() ? [entry.name] : entry.name.endsWith(".site-meta.xml") ? [entry.name.slice(0, -14)] : []));
    for (const bundle of experienceBundles) {
      const dir = path.join(root, "experiences", bundle);
      const metadataFile = `${dir}.site-meta.xml`;
      const metadata = fs.existsSync(metadataFile) ? fs.readFileSync(metadataFile, "utf8") : "";
      const entryFiles = [...files(path.join(dir, "routes")), ...files(path.join(dir, "views"))].filter((file) => file.endsWith(".json"));
      const viewComponents = [];
      let reason;
      for (const file of entryFiles) {
        try {
          const definition = readJson(file);
          if (file.includes(`${path.sep}views${path.sep}`)) viewComponents.push(...componentNames(definition));
        } catch (error) {
          reason = `Cannot read ExperienceBundle JSON in ${file}: ${error.message}`;
          break;
        }
      }
      surfaces.push({ name: tag(metadata, "label") || bundle, bundle, sourceFormat: "experience-bundle", auraComponents: hasAuraComponents(viewComponents, roots), uiRoots: [dir], entryFiles, urlPathPrefixes: [tag(metadata, "urlPathPrefix")].filter(Boolean), evidence: metadata ? [metadataFile] : [], ...(reason ? { reason } : {}) });
    }
    for (const entry of entries(path.join(root, "digitalExperiences/site"))) {
      if (!entry.isDirectory()) continue;
      const dir = path.join(root, "digitalExperiences/site", entry.name);
      const siteFiles = [...files(path.join(dir, "sfdc_cms__site"))].filter((file) => path.basename(file) === "content.json");
      surfaces.push({ name: entry.name, bundle: entry.name, sourceFormat: "digital-experience", uiRoots: [], entryFiles: [], urlPathPrefixes: [], evidence: siteFiles });
    }
  }
  surfaces = mergeSourceConflicts(surfaces);
  for (const config of configs) {
    const surface = surfaces.find((site) => config.bundle && site.bundle === config.bundle);
    if (surface) {
      if (surface.sourceFormat === "experience-bundle") {
        surface.sourceFormat = null;
        surface.reason = `Conflicting source formats for bundle ${surface.bundle}`;
      }
      if (surface.sourceFormat === "digital-experience") surface.name = config.name;
      if (config.urlPathPrefix) surface.urlPathPrefixes.push(config.urlPathPrefix);
    } else if (config.bundle) {
      surfaces.push({ name: config.name, bundle: config.bundle, sourceFormat: config.sourceFormat, uiRoots: [], entryFiles: [], urlPathPrefixes: [config.urlPathPrefix].filter(Boolean), evidence: [] });
    }
  }
  const directLinks = [];
  for (const network of networks) {
    if (network.bundle) continue;
    const matches = surfaces.filter((surface) => surface.bundle &&
      !networks.some((other) => other.bundle === surface.bundle) &&
      (!network.urlPathPrefix || !surface.urlPathPrefixes.length || matchesUrlPathPrefix(surface, network)) && (
        surface.bundle === network.name || surface.name === network.name ||
        matchesUrlPathPrefix(surface, network)
      ));
    if (matches.length > 1) recordAmbiguity(network, matches);
    if (matches.length === 1) directLinks.push({ network, surface: matches[0] });
  }
  assignNetworkBundles(directLinks);
  const inferredLinks = [];
  for (const network of networks) {
    if (network.bundle || network.reason) continue;
    const matches = surfaces.filter((surface) => surface.bundle &&
      !networks.some((other) => other.bundle === surface.bundle) &&
      (!network.urlPathPrefix || !surface.urlPathPrefixes.length || matchesUrlPathPrefix(surface, network)) &&
      matchesSiteBundleName(surface, network));
    if (matches.length > 1) recordAmbiguity(network, matches);
    if (matches.length === 1) inferredLinks.push({ network, surface: matches[0] });
  }
  assignNetworkBundles(inferredLinks);
  const records = [...networks, ...configs];
  for (const surface of surfaces) {
    const links = records.filter((record) => (record.bundle && record.bundle === surface.bundle) || record.candidateSurfaces?.includes(surface));
    surface.networkNames = networks.filter((record) => links.includes(record)).map((record) => record.name);
    surface.urlPathPrefixes = [...new Set([...surface.urlPathPrefixes, ...links.map((record) => record.urlPathPrefix)].filter(Boolean))];
    surface.evidence.push(...links.map((record) => record.file));
  }
  for (const record of records) {
    if (record.candidateSurfaces?.length) continue;
    if (surfaces.some((surface) => record.bundle && surface.bundle === record.bundle)) continue;
    const links = record.bundle ? records.filter((other) => other.bundle === record.bundle) : [record];
    surfaces.push({ name: record.name, bundle: record.bundle || null, sourceFormat: links.find((link) => link.sourceFormat)?.sourceFormat ?? null, networkNames: networks.filter((network) => links.includes(network)).map((network) => network.name), urlPathPrefixes: [...new Set(links.map((link) => link.urlPathPrefix).filter(Boolean))], uiRoots: [], entryFiles: [], evidence: links.map((link) => link.file), ...(record.reason ? { reason: record.reason } : {}) });
  }
  return { sites: surfaces.map((surface) => {
    const { entryFiles, sourceFormat, auraComponents, ...site } = surface;
    const supported = sourceFormat === "experience-bundle" && !!auraComponents;
    const found = entryFiles.some((file) => file.includes(`${path.sep}views${path.sep}`));
    const status = sourceFormat === null ? "metadata-incomplete" : sourceFormat !== "experience-bundle" ? "unsupported" : site.reason ? "metadata-incomplete" : !found ? "ui-not-found" : supported ? "ready" : "unsupported";
    return { ...site, uiFileCount: entryFiles.length, status };
  }).sort((a, b) => a.name.localeCompare(b.name)) };
}

try {
  const result = listSites(path.resolve(args[0] ?? process.cwd()));
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error(`ERROR: ${error.message}`);
  process.exitCode = 1;
}
