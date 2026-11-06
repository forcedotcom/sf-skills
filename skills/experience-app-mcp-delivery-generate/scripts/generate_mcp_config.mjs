#!/usr/bin/env node
// Preview or create a standalone connection file without plugin metadata or org writes.
import fs from "node:fs";
import path from "node:path";
import { createMcpConfig } from "./mcp_config.mjs";

try {
  const args = process.argv.slice(2);
  if (args.length !== 1 && !(args.length === 2 && args[1] === "--write")) throw new Error("Usage: generate_mcp_config.mjs <CONFIG_JSON> [--write]");
  const config = JSON.parse(fs.readFileSync(args[0], "utf8"));
  if (typeof config.destination !== "string" || !path.isAbsolute(config.destination)) throw new Error("destination must be an absolute path to a new MCP configuration file");
  const destination = path.resolve(config.destination);
  // lstat also detects dangling symlinks; exclusive creation protects against races.
  try {
    fs.lstatSync(destination);
    throw new Error("Destination already exists; select a new file");
  } catch (error) { if (error.code !== "ENOENT") throw error; }
  const mcpConfig = createMcpConfig(config);
  if (args[1] === "--write") {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, JSON.stringify(mcpConfig, null, 2) + "\n", { flag: "wx", mode: 0o644 });
  }
  console.log(JSON.stringify({ status: args[1] === "--write" ? "created" : "preview", destination, mcpConfig, runtimeVerified: false }, null, 2));
} catch (error) {
  console.log(JSON.stringify({ status: "blocked", error: error.message }, null, 2));
  process.exitCode = 1;
}
