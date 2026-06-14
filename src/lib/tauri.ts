import type { ModRegistry, Settings } from "./types";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri()) {
    throw new Error("LoadoutForge must run inside the Tauri desktop app.");
  }
  const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
  return tauriInvoke<T>(cmd, args);
}

export async function getSettings(): Promise<Settings> {
  return invoke<Settings>("get_settings");
}

export async function setWorkspace(workspace: string): Promise<Settings> {
  return invoke<Settings>("set_workspace", { workspace });
}

export async function pickWorkspace(): Promise<string | null> {
  return invoke<string | null>("pick_workspace");
}

export async function scanMods(workspace?: string): Promise<ModRegistry> {
  const json = await invoke<string>("scan_mods", { workspace: workspace ?? null });
  return JSON.parse(json) as ModRegistry;
}

export async function buildLoadout(
  payload: { loadout_number: number; mods: string[] },
  workspace?: string,
): Promise<string> {
  return invoke<string>("build_loadout", {
    workspace: workspace ?? null,
    payload: JSON.stringify(payload),
  });
}

export async function readPreviewImage(path: string): Promise<string> {
  return invoke<string>("read_preview_image", { path });
}

export async function readGlbBytes(path: string): Promise<Uint8Array> {
  const bytes = await invoke<number[]>("read_glb_bytes", { path });
  return new Uint8Array(bytes);
}

export async function revealInFinder(path: string): Promise<void> {
  return invoke<void>("reveal_in_finder", { path });
}

export function previewLoadoutName(number: number, abbrevs: string[]): string {
  const num = String(number).padStart(2, "0");
  const gear = abbrevs.join("-");
  return `Cohen Concepts > Loadout ${num} - ${gear}`;
}
