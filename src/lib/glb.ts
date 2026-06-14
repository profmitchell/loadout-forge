import { invoke } from "@tauri-apps/api/core";

const blobCache = new Map<string, string>();

export async function loadGlbBlobUrl(path: string): Promise<string> {
  const cached = blobCache.get(path);
  if (cached) return cached;

  const bytes = await invoke<number[]>("read_glb_bytes", { path });
  const blob = new Blob([new Uint8Array(bytes)], { type: "model/gltf-binary" });
  const url = URL.createObjectURL(blob);
  blobCache.set(path, url);
  return url;
}

export function releaseGlbBlobUrl(path: string): void {
  const url = blobCache.get(path);
  if (!url) return;
  URL.revokeObjectURL(url);
  blobCache.delete(path);
}
