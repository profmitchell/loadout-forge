#!/usr/bin/env node
/** Copy Python tooling into src-tauri/resources for standalone .app bundles. */
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const workspace = join(appRoot, "..");
const dest = join(appRoot, "src-tauri/resources/scripts");

mkdirSync(dest, { recursive: true });

const copies = [
  [join(workspace, "shared_tools/mod_registry.py"), join(dest, "mod_registry.py")],
  [join(workspace, "CohenConcepts_Loadouts/tools/build_loadout.py"), join(dest, "build_loadout.py")],
];

for (const [src, dst] of copies) {
  cpSync(src, dst);
  console.log(`synced ${dst}`);
}
