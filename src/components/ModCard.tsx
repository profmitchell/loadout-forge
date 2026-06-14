"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ModEntry } from "@/lib/types";
import { loadGlbBlobUrl } from "@/lib/glb";
import { readPreviewImage } from "@/lib/tauri";

const ModelViewer = dynamic(
  () => import("./ModelViewer").then((m) => m.ModelViewer),
  { ssr: false },
);

interface ModCardProps {
  mod: ModEntry;
  selected: boolean;
  disabled?: boolean;
  compact?: boolean;
  onSelect: () => void;
  onOpenViewer: (mod: ModEntry, glbUrl: string) => void;
}

export function ModCard({ mod, selected, disabled, compact, onSelect, onOpenViewer }: ModCardProps) {
  const [thumb, setThumb] = useState<string | null>(null);
  const [glbUrl, setGlbUrl] = useState<string | null>(null);
  const [inView, setInView] = useState(false);
  const [show3d, setShow3d] = useState(false);
  const previewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    const path = mod.preview_front ?? mod.previews?.three_quarter;
    if (!path) return;
    readPreviewImage(path)
      .then((src) => {
        if (active) setThumb(src);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [mod.preview_front, mod.previews]);

  useEffect(() => {
    const node = previewRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { rootMargin: "120px", threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!inView || !mod.glb || glbUrl) return;
    let active = true;
    loadGlbBlobUrl(mod.glb)
      .then((url) => {
        if (active) {
          setGlbUrl(url);
          setShow3d(true);
        }
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [inView, mod.glb, glbUrl]);

  const openViewer = useCallback(async () => {
    if (!mod.glb) return;
    try {
      const url = glbUrl ?? (await loadGlbBlobUrl(mod.glb));
      setGlbUrl(url);
      onOpenViewer(mod, url);
    } catch {
      /* no glb */
    }
  }, [mod, glbUrl, onOpenViewer]);

  const onPreviewDoubleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (mod.glb) void openViewer();
  };

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onSelect()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          onSelect();
        }
      }}
      className={[
        "group flex cursor-pointer flex-col overflow-hidden rounded-xl border text-left transition outline-none",
        selected
          ? "border-crimson-400 bg-crimson-950/60 ring-2 ring-crimson-500/50"
          : "border-zinc-800 bg-zinc-900/80 hover:border-zinc-600 hover:bg-zinc-900",
        disabled ? "cursor-not-allowed opacity-40" : "",
      ].join(" ")}
    >
      <div
        ref={previewRef}
        className="relative aspect-[4/3] w-full bg-zinc-950"
        onDoubleClick={onPreviewDoubleClick}
        title={mod.glb ? "Double-click for 3D viewer" : undefined}
      >
        {show3d && glbUrl ? (
          <ModelViewer url={glbUrl} slot={mod.slot} className="h-full w-full" autoRotate interactive={false} />
        ) : thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt={mod.display_name} className="h-full w-full object-cover object-center" />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-zinc-600">No preview</div>
        )}
        {mod.glb && (
          <span className="pointer-events-none absolute left-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-zinc-300 opacity-0 transition group-hover:opacity-100">
            3D · double-click
          </span>
        )}
        {!mod.built && (
          <span className="absolute right-2 top-2 rounded bg-amber-900/90 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
            Not built
          </span>
        )}
      </div>
      <div className={["flex flex-1 flex-col gap-1", compact ? "p-2" : "p-3"].join(" ")}>
        <div className="flex items-start justify-between gap-2">
          <h3 className={["font-semibold leading-tight text-zinc-100", compact ? "text-xs" : "text-sm"].join(" ")}>
            {mod.display_name}
          </h3>
          <span className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-crimson-300">
            {mod.abbrev}
          </span>
        </div>
        {!compact && (
          <>
            <p className="text-[11px] text-zinc-500">
              {mod.category_label ? (
                <span className="text-zinc-600">{mod.category_label} · </span>
              ) : null}
              {mod.equip}
            </p>
            <p className="truncate font-mono text-[10px] text-zinc-700">{mod.source_mod}</p>
          </>
        )}
      </div>
    </div>
  );
}
