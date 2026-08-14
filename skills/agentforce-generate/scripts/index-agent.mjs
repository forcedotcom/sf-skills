#!/usr/bin/env node

import fs from "node:fs"
import path from "node:path"
import process from "node:process"
import { loadAgentScriptSdk } from "./agentscript-sdk-loader.mjs"

let sdk
try {
  sdk = await loadAgentScriptSdk()
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(2)
}
const { compileSource } = sdk.sdk

const file = process.argv[2]
if (!file || process.argv.length > 3) {
  console.error("Usage: node scripts/index-agent.mjs <path-to-agent-file>")
  process.exit(2)
}

const absoluteFile = path.resolve(file)
const source = fs.readFileSync(absoluteFile, "utf8")
const result = compileSource(source)
const version = result.output.agent_version

function rangeOf(node) {
  const range = node?.__cst?.range
  if (!range) return undefined
  return {
    startLine: range.start.line + 1,
    endLine: range.end.line + 1,
  }
}

function namedRanges(collection) {
  if (!collection?.__children) return []
  return collection.__children.map((child) => ({
    name: child.name,
    kind: child.value?.__kind,
    ...rangeOf(child.value),
  }))
}

const sourceNodes = new Map(
  [
    ...namedRanges(result.document.ast.start_agent),
    ...namedRanges(result.document.ast.subagent),
  ].map((node) => [node.name, node]),
)

const lifecycleNames = [
  "before_reasoning",
  "before_reasoning_iteration",
  "after_reasoning",
]

const nodes = (version?.nodes ?? []).map((node) => {
  const lifecycle = {}
  for (const name of lifecycleNames) {
    if (Array.isArray(node[name]) && node[name].length > 0) {
      lifecycle[name] = node[name].map((step) => ({
        type: step.type,
        target: step.target,
        enabled: step.enabled,
      }))
    }
  }

  return {
    name: node.developer_name,
    type: node.type,
    reasoningType: node.reasoning_type,
    source: sourceNodes.get(node.developer_name),
    tools: (node.tools ?? []).map((tool) => ({
      name: tool.name,
      target: tool.target,
      enabled: tool.enabled,
      llmInputs: tool.llm_inputs ?? [],
      stateUpdates: tool.state_updates ?? [],
    })),
    actionDefinitions: (node.action_definitions ?? []).map((action) => ({
      name: action.developer_name,
      targetType: action.invocation_target_type,
      targetName: action.invocation_target_name,
      inputs: (action.input_type ?? []).map((input) => input.developer_name),
      outputs: (action.output_type ?? []).map(
        (output) => output.developer_name,
      ),
    })),
    lifecycle,
  }
})

const index = {
  compiler: {
    provider: sdk.provider,
    package: sdk.package,
    version: sdk.version,
    sourceRevision: sdk.sourceRevision,
    entry: sdk.entry,
  },
  file: absoluteFile,
  diagnostics: result.diagnostics.map((diagnostic) => ({
    severity: diagnostic.severity,
    code: diagnostic.code,
    message: diagnostic.message,
    line: diagnostic.range.start.line + 1,
    column: diagnostic.range.start.character + 1,
  })),
  blocks: Object.entries(result.document.ast)
    .filter(([name, value]) => !name.startsWith("__") && value?.__cst)
    .map(([name, value]) => ({ name, ...rangeOf(value) })),
  variables: (version?.state_variables ?? []).map((variable) => ({
    name: variable.developer_name,
    type: variable.data_type,
    isList: variable.is_list,
    visibility: variable.visibility,
    default: variable.default,
  })),
  initialNode: version?.initial_node,
  nodes,
  transitions: nodes.flatMap((node) =>
    Object.entries(node.lifecycle).flatMap(([lifecycle, steps]) =>
      steps
        .filter((step) => step.type === "handoff")
        .map((step) => ({
          from: node.name,
          to: step.target,
          lifecycle,
          enabled: step.enabled,
        })),
    ),
  ),
}

console.log(JSON.stringify(index, null, 2))
process.exit(
  result.diagnostics.some((diagnostic) => diagnostic.severity === 1) ? 1 : 0,
)
