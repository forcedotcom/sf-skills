import fs from "node:fs";
import path from "node:path";

// Check the nearest existing destination parent before any planned writes.
export function requireProjectDestination(projectRoot, destination) {
  let parent = path.dirname(destination);
  while (!fs.lstatSync(parent, { throwIfNoEntry: false })) parent = path.dirname(parent);
  const actualRoot = fs.realpathSync(projectRoot);
  const actualParent = fs.realpathSync(parent);
  if (actualParent !== actualRoot && !actualParent.startsWith(actualRoot + path.sep)) {
    throw new Error("ABORT: metadata destination resolves outside the project root");
  }
}
