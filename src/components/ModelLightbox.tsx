"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";
import type { ModEntry } from "@/lib/types";

const ModelViewer = dynamic(
  () => import("./ModelViewer").then((m) => m.ModelViewer),
  { ssr: false, loading: () => <div className="flex h-full items-center justify-center text-zinc-500">Loading 3D…</div> },
);

interface ModelLightboxProps {
  mod: ModEntry;
  glbUrl: string;
  onClose: () => void;
}

export function ModelLightbox({ mod, glbUrl, onClose }: ModelLightboxProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-6 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`3D preview: ${mod.display_name}`}
    >
      <div
        className="relative flex h-[min(88vh,900px)] w-[min(92vw,1200px)] flex-col overflow-hidden rounded-2xl border border-zinc-700 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-zinc-800 px-5 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-zinc-100">{mod.display_name}</h2>
            <p className="truncate text-xs text-zinc-500">
              {mod.category_label ? `${mod.category_label} · ` : ""}
              {mod.equip} · drag to orbit · scroll to zoom
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800"
          >
            Close
          </button>
        </header>
        <div className="relative min-h-0 flex-1">
          <ModelViewer url={glbUrl} slot={mod.slot} className="h-full w-full" interactive autoRotate={false} />
        </div>
        <footer className="border-t border-zinc-800 px-5 py-2 text-center text-[10px] text-zinc-600">
          Double-click any card preview to open · Esc to close
        </footer>
      </div>
    </div>
  );
}
