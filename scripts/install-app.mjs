#!/usr/bin/env node
import { cpSync, existsSync, mkdirSync, renameSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(appRoot, "src-tauri/target/release/bundle/macos/LoadoutForge.app");
const dst = join(appRoot, "..", "LoadoutForge.app");

if (!existsSync(src)) {
  console.error("Build output not found:", src);
  process.exit(1);
}

if (existsSync(dst)) {
  const bak = `${dst}.before_install.bak`;
  if (existsSync(bak)) {
    renameSync(bak, `${bak}.${Date.now()}`);
  }
  renameSync(dst, bak);
  console.log("backed up previous app to", bak);
}

mkdirSync(dirname(dst), { recursive: true });
cpSync(src, dst, { recursive: true });
console.log("installed", dst);
