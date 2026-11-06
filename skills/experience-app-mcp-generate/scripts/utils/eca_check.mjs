import fs from "node:fs";
import path from "node:path";
import { isValidDeveloperName } from "./developer_name.mjs";

const METADATA_NAMESPACE = "http://soap.sforce.com/2006/04/metadata";

function decode(text) {
  if (/&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[\da-fA-F]+);)/.test(text)) throw new Error("Invalid entity");
  return text.replace(/&(amp|lt|gt|quot|apos|#\d+|#x[\da-fA-F]+);/g, (_, entity) => {
    if (!entity.startsWith("#")) return { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" }[entity];
    const point = entity.startsWith("#x") ? parseInt(entity.slice(2), 16) : Number(entity.slice(1));
    if (![9, 10, 13].includes(point) && !(point >= 0x20 && point <= 0xD7FF) &&
        !(point >= 0xE000 && point <= 0xFFFD) && !(point >= 0x10000 && point <= 0x10FFFF)) {
      throw new Error("Invalid XML character");
    }
    return String.fromCodePoint(point);
  });
}

// ECA templates have a single metadata root and scalar child fields. Reject
// unsupported XML rather than guessing field values or resolving entities.
function fields(xml) {
  if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error("Unsupported declarations");
  if (/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/.test(xml)) throw new Error("Invalid XML character");
  let text = xml.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").trim();
  text = text.replace(/^<\?xml\s[^?]*\?>\s*/, "")
    .replace(/<!\[CDATA\[[\s\S]*?\]\]>|<!--(?:[^-]|-(?!-))*-->/g,
      (part) => part.startsWith("<!--") ? "" : part).trim();
  const open = text.match(/^<([A-Za-z_][\w.-]*)([^<>]*?)(\/?)>/);
  if (!open) throw new Error("Invalid root");
  const attributes = new Map();
  const attribute = /\s+([A-Za-z_][\w:.-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/y;
  let offset = 0;
  while (open[2].slice(offset).trim()) {
    attribute.lastIndex = offset;
    const match = attribute.exec(open[2]);
    if (!match || attributes.has(match[1]) || !/^xmlns(?::[\w.-]+)?$/.test(match[1])) throw new Error("Unsupported root attributes");
    attributes.set(match[1], decode(match[2] ?? match[3]));
    offset = attribute.lastIndex;
  }
  if (attributes.get("xmlns") !== METADATA_NAMESPACE) throw new Error("Invalid namespace");
  let body = text.slice(open[0].length);
  if (open[3]) {
    if (body.trim()) throw new Error("Trailing XML");
  } else {
    const close = body.slice(body.lastIndexOf("</")).match(/^<\/([A-Za-z_][\w.-]*)\s*>$/);
    if (!close || close[1] !== open[1]) throw new Error("Invalid closing root");
    body = body.slice(0, body.lastIndexOf("</"));
  }
  const result = new Map();
  const field = /\s*<([A-Za-z_][\w.-]*)\s*(?:\/>|>([\s\S]*?)<\/\1\s*>)/y;
  offset = 0;
  while (body.slice(offset).trim()) {
    field.lastIndex = offset;
    const match = field.exec(body);
    if (!match || result.has(match[1])) throw new Error("Invalid or duplicate field");
    let value = "";
    for (const part of (match[2] ?? "").split(/(<!\[CDATA\[[\s\S]*?\]\]>)/)) {
      if (part.startsWith("<![CDATA[")) value += part.slice(9, -3);
      else {
        if (part.includes("<") || part.includes("]]>")) throw new Error("Invalid scalar field");
        value += decode(part);
      }
    }
    result.set(match[1], value.trim());
    offset = field.lastIndex;
  }
  return { root: open[1], values: result };
}

function componentFile(dest, baseline) {
  if (!baseline.values.has("externalClientApplication")) return dest;
  const folder = path.dirname(dest);
  const suffix = path.basename(dest).match(/\.eca[A-Za-z]*-meta\.xml$/)?.[0];
  if (!suffix) throw new Error("Unknown component suffix");
  let names;
  try {
    names = fs.readdirSync(folder).filter((name) => name.endsWith(suffix));
  } catch (error) {
    if (error.code === "ENOENT") return dest;
    throw error;
  }
  const owned = [];
  for (const name of names) {
    const candidate = path.join(folder, name);
    if (!fs.lstatSync(candidate).isFile()) throw new Error("Ambiguous component file");
    const parsed = fields(fs.readFileSync(candidate, "utf8"));
    if (parsed.root !== baseline.root) throw new Error("Wrong metadata type");
    if (!isValidDeveloperName(parsed.values.get("externalClientApplication"))) {
      const error = new Error("Unresolved parent reference");
      error.file = candidate;
      error.missingParent = !parsed.values.has("externalClientApplication");
      throw error;
    }
    if (parsed.values.get("externalClientApplication") === baseline.values.get("externalClientApplication")) owned.push(candidate);
  }
  if (owned.length > 1) throw new Error("Multiple associated components");
  return owned[0] ?? dest;
}

function literalExpectedValues(templateFields, names) {
  return Object.fromEntries(names.filter((name) => !/__ECA_[A-Z_]+__/.test(templateFields.get(name)))
    .sort().map((name) => [name, templateFields.get(name)]));
}

export function checkEcaPlan(plan) {
  const files = plan.map(({ src, dest, template, expected }) => {
    const report = { file: dest, template: src, status: "unknown", missingFields: [], differentFields: [], unverifiedFields: [], expectedValues: {} };
    try {
      const templateFields = fields(template).values;
      const baseline = fields(expected);
      report.file = componentFile(dest, baseline);
      const entry = fs.lstatSync(report.file, { throwIfNoEntry: false });
      if (!entry) {
        report.status = "missing";
        report.missingFields = [...baseline.values.keys()].sort();
        report.expectedValues = literalExpectedValues(templateFields, report.missingFields);
        return report;
      }
      if (!entry.isFile()) throw new Error("Not a regular file");
      const actual = fields(fs.readFileSync(report.file, "utf8"));
      if (actual.root !== baseline.root) throw new Error("Wrong metadata type");
      for (const [name, value] of baseline.values) {
        if (!actual.values.has(name)) report.missingFields.push(name);
        else if (/__ECA_[A-Z_]+__/.test(value)) report.unverifiedFields.push(name);
        else if (actual.values.get(name) !== value) report.differentFields.push(name);
      }
      for (const key of ["missingFields", "differentFields", "unverifiedFields"]) report[key].sort();
      report.expectedValues = literalExpectedValues(templateFields, [...report.missingFields, ...report.differentFields]);
      report.status = report.missingFields.length || report.differentFields.length
        ? "different" : report.unverifiedFields.length ? "unverified" : "match";
    } catch (error) {
      if (error.file) {
        report.file = error.file;
        report[error.missingParent ? "missingFields" : "unverifiedFields"] = ["externalClientApplication"];
      }
      report.reason = "Unreadable, malformed, duplicate-field, ambiguously associated, or unsupported scalar metadata XML; no absence or repair is inferred.";
    }
    return report;
  });
  const statuses = files.map((file) => file.status);
  const comparisonStatus = statuses.includes("unknown") ? "unknown"
    : statuses.some((status) => status === "different" || status === "missing") ? "different"
      : statuses.includes("unverified") ? "unverified" : "match";
  return {
    comparisonStatus, files,
    scope: "Read-only comparison of template-defined scalar ECA fields, not deployment or access validation. expectedValues contains literal template values for missing or different fields; actual and input-derived values are omitted.",
    nextActions: [
      "Review missing files/fields and differentFields using expectedValues and confirmed inputs; expected values are template baselines, not platform defaults or authorization to write.",
      "For unverifiedFields, recover confirmed label, description, contact and callbacks; rerun the normal render command with the same inputs plus --check. Never infer approval from existing values.",
      "Compare only template-defined fields and leave other fields unchanged. Preserve intentional overrides; use references/eca-fields.md for ownership and editing invariants, show the diff and follow Phase 2 confirmation rules before changes.",
      "For missing files, use the named template and confirmed renderer inputs to create only that component. Never delete existing files or bypass overwrite protection to rerender a partial set.",
      "Resolve unknown files before repair. Exit 0 means comparison ran, not that all fields match or policies were reviewed; `comparisonStatus: unknown` means some files could not be checked.",
    ],
  };
}
