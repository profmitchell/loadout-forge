"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ModCard } from "./ModCard";
import { ModelLightbox } from "./ModelLightbox";
import { SelectedLoadoutStrip } from "./SelectedLoadoutStrip";
import { ModMaker } from "./ModMaker";
import { buildModsBySlot, slotOrderFromRegistry } from "@/lib/slots";
import type { ModEntry, ModRegistry, SlotId } from "@/lib/types";
import {
  buildLoadout,
  getSettings,
  isTauri,
  pickWorkspace,
  previewLoadoutName,
  revealInFinder,
  scanMods,
  setWorkspace,
  syncOwnedGear,
} from "@/lib/tauri";

const CARD_SIZE_KEY = "loadout-forge-card-min-width";
const CARD_MIN = 160;
const CARD_MAX = 380;
const CARD_DEFAULT = 220;
const RESCAN_COOLDOWN_MS = 3000;

function formatScanStatus(reg: ModRegistry, updateStale?: boolean): string {
  const parts = [`Found ${reg.mods.length} mods`];
  if (reg.build_stale_count) parts.push(`${reg.build_stale_count} build stale`);
  if (reg.zip_stale_count) parts.push(`${reg.zip_stale_count} zip stale`);
  if (reg.unbuilt_count) parts.push(`${reg.unbuilt_count} unbuilt`);
  if (reg.skipped?.length) parts.push(`${reg.skipped.length} skipped`);
  const sync = reg._last_sync;
  if (updateStale && sync) {
    if (sync.rebuilt_count) parts.push(`rebuilt ${sync.rebuilt_count}`);
    if (sync.repacked_count) parts.push(`repacked ${sync.repacked_count}`);
    if (sync.rebuild_failed?.length) parts.push(`${sync.rebuild_failed.length} failed`);
  }
  if (reg.scanned_at) {
    parts.push(`scanned ${new Date(reg.scanned_at).toLocaleTimeString()}`);
  }
  return parts.join(" · ");
}

export function LoadoutForge() {
  const [page, setPage] = useState<"loadouts" | "maker">("loadouts");
  const [registry, setRegistry] = useState<ModRegistry | null>(null);
  const [workspace, setWorkspaceState] = useState("");
  const [selected, setSelected] = useState<Partial<Record<SlotId, string>>>({});
  const [activeSlot, setActiveSlot] = useState<SlotId | "all">("all");
  const [activeCategory, setActiveCategory] = useState<string | "all">("all");
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [loadoutNumber, setLoadoutNumber] = useState(4);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastZip, setLastZip] = useState<string | null>(null);
  const [viewer, setViewer] = useState<{ mod: ModEntry; glbUrl: string } | null>(null);
  const [cardMinWidth, setCardMinWidth] = useState(CARD_DEFAULT);
  const [skippedDetail, setSkippedDetail] = useState<string | null>(null);
  const lastScanAt = useRef(0);
  const workspaceRef = useRef(workspace);

  useEffect(() => {
    workspaceRef.current = workspace;
  }, [workspace]);

  useEffect(() => {
    const saved = localStorage.getItem(CARD_SIZE_KEY);
    if (!saved) return;

    const n = Number(saved);
    if (n < CARD_MIN || n > CARD_MAX) return;

    const frame = requestAnimationFrame(() => setCardMinWidth(n));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    localStorage.setItem(CARD_SIZE_KEY, String(cardMinWidth));
  }, [cardMinWidth]);

  const refresh = useCallback(async (ws?: string, updateStale = false) => {
    setBusy(true);
    setStatus(updateStale ? "Updating stale mods…" : "Scanning mod catalog…");
    try {
      const reg = await scanMods(ws, updateStale);
      setRegistry(reg);
      setWorkspaceState(reg.workspace);
      setLoadoutNumber(reg.next_loadout_number);
      lastScanAt.current = Date.now();
      setStatus(formatScanStatus(reg, updateStale));
      setSkippedDetail(
        reg.skipped?.length
          ? reg.skipped.map((s) => `${s.path} — ${s.reason}`).join(" · ")
          : null,
      );
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
      setSkippedDetail(null);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    getSettings()
      .then((s) => refresh(s.workspace))
      .catch((err) => setStatus(String(err)));
  }, [refresh]);

  useEffect(() => {
    if (!isTauri()) return;

    let disposed = false;
    let unlisten: (() => void) | undefined;

    void (async () => {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      unlisten = await getCurrentWindow().onFocusChanged(({ payload: focused }) => {
        if (!focused || disposed) return;
        const now = Date.now();
        if (now - lastScanAt.current < RESCAN_COOLDOWN_MS) return;
        void refresh(workspaceRef.current || undefined);
      });
    })();

    return () => {
      disposed = true;
      unlisten?.();
    };
  }, [refresh]);

  const slotOrder = useMemo(() => slotOrderFromRegistry(registry), [registry]);

  const modsBySlot = useMemo(() => buildModsBySlot(registry), [registry]);

  const modsByCategory = useMemo(() => {
    const map = new Map<string, ModEntry[]>();
    registry?.mods.forEach((m) => {
      const key = m.category ?? "_root";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    });
    return map;
  }, [registry]);

  const visibleMods = useMemo(() => {
    if (!registry) return [];
    return registry.mods.filter((m) => {
      if (activeSlot !== "all" && m.slot !== activeSlot) return false;
      if (activeCategory !== "all" && m.category !== activeCategory) return false;
      if (ownedOnly && registry.owned_gear?.available && !m.owned) return false;
      return true;
    });
  }, [registry, activeSlot, activeCategory, ownedOnly]);

  const groupedMods = useMemo(() => {
    if (activeCategory !== "all") return [{ label: null as string | null, mods: visibleMods }];
    const groups: { label: string | null; mods: ModEntry[] }[] = [];
    const order = registry?.categories?.map((c) => c.id) ?? [];
    for (const catId of order) {
      const mods = visibleMods.filter((m) => m.category === catId);
      if (mods.length) {
        const label = registry?.categories?.find((c) => c.id === catId)?.label ?? catId;
        groups.push({ label, mods });
      }
    }
    const root = visibleMods.filter((m) => !m.category);
    if (root.length) groups.push({ label: "Other", mods: root });
    return groups.length ? groups : [{ label: null, mods: visibleMods }];
  }, [visibleMods, activeCategory, registry]);

  const selectedMods = useMemo(() => {
    if (!registry) return [] as ModEntry[];
    return slotOrder.map((slot) => {
      const id = selected[slot];
      return id ? registry.mods.find((m) => m.id === id) : undefined;
    }).filter(Boolean) as ModEntry[];
  }, [registry, selected, slotOrder]);

  const selectedBySlot = useMemo(() => {
    const map: Partial<Record<SlotId, ModEntry>> = {};
    if (!registry) return map;
    for (const slot of slotOrder) {
      const id = selected[slot];
      const mod = id ? registry.mods.find((m) => m.id === id) : undefined;
      if (mod) map[slot] = mod;
    }
    return map;
  }, [registry, selected, slotOrder]);

  const abbrevs = selectedMods.map((m) => m.abbrev);
  const loadoutTitle = abbrevs.length
    ? previewLoadoutName(loadoutNumber, abbrevs)
    : "Pick gear to preview name…";

  const gridStyle = useMemo(
    () => ({ gridTemplateColumns: `repeat(auto-fill, minmax(${cardMinWidth}px, 1fr))` }),
    [cardMinWidth],
  );

  function pickMod(mod: ModEntry) {
    setSelected((prev) => {
      const next = { ...prev };
      if (next[mod.slot] === mod.id) {
        delete next[mod.slot];
      } else {
        next[mod.slot] = mod.id;
      }
      return next;
    });
  }

  function clearSlot(slot: SlotId) {
    setSelected((prev) => {
      const next = { ...prev };
      delete next[slot];
      return next;
    });
  }

  async function onChangeWorkspace() {
    setBusy(true);
    try {
      const next = await pickWorkspace();
      if (!next?.trim()) return;
      const s = await setWorkspace(next.trim());
      await refresh(s.workspace);
    } catch (err) {
      setStatus(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSyncOwned() {
    setBusy(true);
    setStatus("Reading save inventory…");
    try {
      const msg = await syncOwnedGear(workspace || undefined);
      await refresh(workspace || undefined);
      setStatus(msg.trim() || "Owned gear synced from save.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    if (!registry || selectedMods.length === 0) {
      setStatus("Select at least one mod.");
      return;
    }
    const unbuilt = selectedMods.filter((m) => !m.built);
    if (unbuilt.length) {
      setStatus(`Build these first: ${unbuilt.map((m) => m.source_mod).join(", ")}`);
      return;
    }
    setBusy(true);
    setStatus("Building loadout zip…");
    try {
      const out = await buildLoadout({
        loadout_number: loadoutNumber,
        mods: selectedMods.map((m) => m.id),
      });
      const match = out.match(/Built: (.+\.zip)/);
      const zip = match?.[1] ?? null;
      setLastZip(zip);
      setStatus(zip ? `Exported and staged for CDUMM: ${zip}` : out);
      if (zip) await refresh(registry.workspace);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="shrink-0 border-b border-zinc-800 bg-zinc-900/80 px-6 py-4 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Loadout<span className="text-crimson-400">Forge</span>
            </h1>
            <p className="text-xs text-zinc-500">Cohen Concepts · scans category folders automatically</p>
            <div className="mt-3 flex gap-1 rounded-lg bg-zinc-950 p-1">
              <button onClick={() => setPage("loadouts")} className={`rounded-md px-3 py-1 text-xs ${page === "loadouts" ? "bg-zinc-800 text-white" : "text-zinc-500"}`}>Loadout Forge</button>
              <button onClick={() => setPage("maker")} className={`rounded-md px-3 py-1 text-xs ${page === "maker" ? "bg-crimson-950 text-crimson-200" : "text-zinc-500"}`}>Mod Maker</button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-zinc-500">
              Card size
              <input
                type="range"
                min={CARD_MIN}
                max={CARD_MAX}
                step={20}
                value={cardMinWidth}
                onChange={(e) => setCardMinWidth(Number(e.target.value))}
                className="h-1.5 w-28 cursor-pointer accent-crimson-500"
              />
              <span className="w-8 font-mono text-zinc-400">{cardMinWidth}</span>
            </label>
            <button
              type="button"
              onClick={onChangeWorkspace}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Workspace…
            </button>
            <button
              type="button"
              onClick={onSyncOwned}
              disabled={busy}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              title="Read-only scan of Pearl Abyss save.save for owned donor PACs"
            >
              Sync owned
            </button>
            <button
              type="button"
              onClick={() => refresh(workspace)}
              disabled={busy}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
            >
              Rescan
            </button>
            <button
              type="button"
              onClick={() => refresh(workspace, true)}
              disabled={busy}
              className="rounded-lg border border-amber-800/60 px-3 py-1.5 text-xs text-amber-200/90 hover:bg-amber-950/40 disabled:opacity-50"
            >
              Update stale
            </button>
          </div>
        </div>
        <p className="mt-2 truncate font-mono text-[11px] text-zinc-600">{workspace}</p>
        <p className="mt-1 text-[10px] text-zinc-500">
          <span className="font-semibold text-zinc-400">Rescan</span> refreshes the mod catalog.{" "}
          <span className="font-semibold text-zinc-400">Update stale</span> rebuilds outdated{" "}
          <span className="font-mono">files/</span> and repacks zips. Export rebuilds selected mods automatically.
        </p>
        {registry?.owned_gear?.available ? (
          <p className="mt-1 text-[10px] text-zinc-500">
            Owned gear: {registry.owned_gear.gear_match_count ?? registry.owned_gear.owned_item_ids.length} items
            {registry.owned_gear.save_slot ? ` · ${registry.owned_gear.save_slot}` : ""}
            {registry.owned_mod_count !== undefined ? ` · ${registry.owned_mod_count} mods match` : ""}
          </p>
        ) : (
          <p className="mt-1 text-[10px] text-zinc-600">Owned gear: not synced — click Sync owned after loot changes.</p>
        )}
      </header>

      {page === "maker" && registry ? <ModMaker registry={registry} onBuilt={() => refresh(registry.workspace)} /> : <>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden px-6 py-4 lg:flex-row">
        <aside className="flex max-h-48 shrink-0 gap-2 overflow-x-auto lg:max-h-none lg:w-44 lg:flex-col lg:overflow-y-auto">
          <div className="min-w-[8rem] lg:min-w-0">
            <p className="mb-1 px-1 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">Folders</p>
            <FilterChip
              active={activeCategory === "all"}
              onClick={() => setActiveCategory("all")}
              label="All folders"
              count={registry?.mods.length}
            />
            {registry?.categories?.map((cat) => (
              <FilterChip
                key={cat.id}
                active={activeCategory === cat.id}
                onClick={() => setActiveCategory(cat.id)}
                label={cat.label}
                count={modsByCategory.get(cat.id)?.length}
              />
            ))}
          </div>
          <div className="min-w-[8rem] border-l border-zinc-800 pl-2 lg:min-w-0 lg:border-l-0 lg:border-t lg:pt-3 lg:pl-0">
            <p className="mb-1 px-1 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">Slot</p>
            <FilterChip active={activeSlot === "all"} onClick={() => setActiveSlot("all")} label="All slots" />
            {slotOrder.map((slot) => (
              <FilterChip
                key={slot}
                active={activeSlot === slot}
                onClick={() => setActiveSlot(slot)}
                label={slot}
                count={modsBySlot[slot]?.length ?? 0}
              />
            ))}
            <div className="mt-3 border-t border-zinc-800 pt-3">
              <label className="flex cursor-pointer items-center gap-2 px-1 text-xs text-zinc-400">
                <input
                  type="checkbox"
                  checked={ownedOnly}
                  onChange={(e) => setOwnedOnly(e.target.checked)}
                  disabled={!registry?.owned_gear?.available}
                  className="accent-crimson-500"
                />
                Owned
              </label>
              <p className="mt-1 px-1 text-[10px] leading-snug text-zinc-600">
                Show mods whose donor PAC matches your save inventory.
              </p>
            </div>
          </div>
        </aside>

        <main className="min-h-0 flex-1 overflow-y-auto pr-1">
          {visibleMods.length === 0 ? (
            <p className="py-12 text-center text-sm text-zinc-500">
              No mods here yet — drop a folder with <code className="text-zinc-400">mod_config.json</code> into a
              category folder (1H, Helms, Bows, Lanterns, Cannon Staffs).
            </p>
          ) : (
            groupedMods.map((group) => (
              <div key={group.label ?? "_flat"} className="mb-6">
                {group.label && activeCategory === "all" && (
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-zinc-500">{group.label}</h3>
                )}
                <div className="grid gap-3" style={gridStyle}>
                  {group.mods.map((mod) => (
                    <ModCard
                      key={mod.id}
                      mod={mod}
                      selected={selected[mod.slot] === mod.id}
                      disabled={!mod.built}
                      compact={cardMinWidth < 200}
                      onSelect={() => pickMod(mod)}
                      onOpenViewer={(m, glbUrl) => setViewer({ mod: m, glbUrl })}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </main>
      </div>

      <footer className="z-40 shrink-0 border-t border-zinc-800 bg-zinc-900/95 px-6 py-3 shadow-[0_-8px_32px_rgba(0,0,0,0.45)] backdrop-blur-md">
        <div className="mb-3">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-500">Selected loadout</p>
          <SelectedLoadoutStrip
            slotOrder={slotOrder}
            selectedBySlot={selectedBySlot}
            onClearSlot={clearSlot}
            onOpenViewer={(m, glbUrl) => setViewer({ mod: m, glbUrl })}
          />
        </div>
        <div className="flex flex-wrap items-end justify-between gap-4 border-t border-zinc-800/80 pt-3">
          <div className="min-w-0 flex-1">
            <label className="text-[10px] uppercase tracking-wide text-zinc-500">CDUMM name</label>
            <p className="truncate text-sm font-medium text-zinc-100">{loadoutTitle}</p>
            <p className="mt-1 text-xs text-zinc-500">{status}</p>
            {skippedDetail && (
              <p className="mt-0.5 text-[10px] text-amber-600/90" title={skippedDetail}>
                Skipped: {skippedDetail}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <label className="flex flex-col text-[10px] uppercase tracking-wide text-zinc-500">
              #
              <input
                type="number"
                min={1}
                max={99}
                value={loadoutNumber}
                onChange={(e) => setLoadoutNumber(Number(e.target.value) || 1)}
                className="mt-1 w-16 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm text-zinc-100"
              />
            </label>
            {lastZip && (
              <button
                type="button"
                onClick={() => revealInFinder(lastZip)}
                className="rounded-lg border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
              >
                Show zip
              </button>
            )}
            <button
              type="button"
              onClick={onExport}
              disabled={busy || selectedMods.length === 0}
              className="rounded-lg bg-crimson-600 px-5 py-2 text-sm font-semibold text-white hover:bg-crimson-500 disabled:opacity-40"
            >
              Export loadout
            </button>
          </div>
        </div>
      </footer>
      </>}

      {viewer && (
        <ModelLightbox mod={viewer.mod} glbUrl={viewer.glbUrl} onClose={() => setViewer(null)} />
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count?: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "mb-1 w-full rounded-lg border px-3 py-2 text-left text-xs transition",
        active ? "border-crimson-500 bg-crimson-950/50 text-crimson-200" : "border-zinc-800 text-zinc-400 hover:bg-zinc-900",
      ].join(" ")}
    >
      {label}
      {count !== undefined ? <span className="ml-1 text-zinc-600">({count})</span> : null}
    </button>
  );
}
