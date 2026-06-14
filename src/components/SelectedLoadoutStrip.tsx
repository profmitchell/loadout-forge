"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { ModEntry, SlotId } from "@/lib/types";
import { loadGlbBlobUrl } from "@/lib/glb";
import { readPreviewImage } from "@/lib/tauri";

const ModelViewer = dynamic(
  () => import("./ModelViewer").then((m) => m.ModelViewer),
  { ssr: false },
);

interface SelectedLoadoutStripProps {
  slotOrder: SlotId[];
  selectedBySlot: Partial<Record<SlotId, ModEntry>>;
  onClearSlot: (slot: SlotId) => void;
  onOpenViewer?: (mod: ModEntry, glbUrl: string) => void;
}

function SlotThumb({
  slot,
  mod,
  onClear,
  onOpenViewer,
}: {
  slot: SlotId;
  mod?: ModEntry;
  onClear: () => void;
  onOpenViewer?: (mod: ModEntry, glbUrl: string) => void;
}) {
  const [glbUrl, setGlbUrl] = useState<string | null>(null);
  const [thumb, setThumb] = useState<string | null>(null);

  useEffect(() => {
    if (!mod?.glb) return;
    let active = true;
    loadGlbBlobUrl(mod.glb)
      .then((url) => {
        if (active) setGlbUrl(url);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [mod?.glb]);

  useEffect(() => {
    if (!mod) return;
    const path = mod.preview_front ?? mod.previews?.three_quarter;
    if (!path) return;
    let active = true;
    readPreviewImage(path)
      .then((src) => {
        if (active) setThumb(src);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [mod]);

  const onDoubleClick = async () => {
    if (!mod?.glb || !onOpenViewer) return;
    const url = glbUrl ?? (await loadGlbBlobUrl(mod.glb));
    onOpenViewer(mod, url);
  };

  return (
    <button
      type="button"
      onClick={mod ? onClear : undefined}
      onDoubleClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void onDoubleClick();
      }}
      title={mod ? `${mod.display_name} — click to remove, double-click 3D` : `Empty ${slot}`}
      className={[
        "group flex w-[4.5rem] shrink-0 flex-col items-center gap-1 rounded-lg border p-1 transition",
        mod
          ? "border-crimson-500/60 bg-crimson-950/30 hover:border-crimson-400"
          : "border-dashed border-zinc-800 bg-zinc-900/40",
      ].join(" ")}
    >
      <div className="relative h-14 w-full overflow-hidden rounded-md bg-black">
        {mod && glbUrl ? (
          <ModelViewer url={glbUrl} slot={mod.slot} className="h-full w-full" autoRotate interactive={false} />
        ) : mod && thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt="" className="h-full w-full object-cover object-center" />
        ) : (
          <div className="flex h-full items-center justify-center text-lg text-zinc-700">—</div>
        )}
      </div>
      <span className="text-[8px] font-semibold uppercase tracking-wider text-zinc-500">{slot}</span>
      <span className="max-w-full truncate text-[10px] font-medium text-zinc-300">{mod?.abbrev ?? "empty"}</span>
    </button>
  );
}

export function SelectedLoadoutStrip({
  slotOrder,
  selectedBySlot,
  onClearSlot,
  onOpenViewer,
}: SelectedLoadoutStripProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {slotOrder.map((slot) => (
        <SlotThumb
          key={`${slot}:${selectedBySlot[slot]?.id ?? "empty"}`}
          slot={slot}
          mod={selectedBySlot[slot]}
          onClear={() => onClearSlot(slot)}
          onOpenViewer={onOpenViewer}
        />
      ))}
    </div>
  );
}
