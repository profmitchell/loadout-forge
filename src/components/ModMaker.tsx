"use client";

import { useMemo, useState } from "react";
import type { DonorEntry, ModEntry, ModRegistry } from "@/lib/types";
import { donorsForVisual } from "@/lib/donors";
import { buildModMaker, revealInFinder } from "@/lib/tauri";

const FALLBACK_DONORS: DonorEntry[] = [
  { item_id: 13809, name: "Nazk Sword", slot: "sword", pacs: ["cd_phm_01_sword_0075.pac"], confidence: "Very high" },
  { item_id: 13811, name: "Aeserion Sword", slot: "sword", pacs: ["cd_phm_01_sword_0023.pac"], confidence: "Very high" },
  { item_id: 13810, name: "Chillfallen Sword", slot: "sword", pacs: ["cd_phm_01_sword_0102.pac"], confidence: "Very high" },
  { item_id: 1000747, name: "Lightningblade of Greed", slot: "sword", pacs: ["cd_phm_01_sword_0074.pac"], confidence: "High" },
  { item_id: 1000578, name: "Fated Shadow", slot: "sword", pacs: ["cd_phm_01_sword_0168.pac"], confidence: "High" },
  { item_id: 1163042, name: "Sword of the Wolf", slot: "sword", pacs: ["cd_phm_01_sword_0019.pac"], confidence: "Known safe" },
  { item_id: 14705, name: "Darkbringer", slot: "sword_2h", pacs: ["cd_phm_02_sword_0015.pac", "cd_phm_02_sword_0015_in.pac"], confidence: "Very high", experimental: true },
  { item_id: 15903, name: "Twisted Verdict", slot: "sword_2h", pacs: ["cd_phm_02_sword_0040.pac", "cd_phm_02_sword_0039_in.pac"], confidence: "Very high", experimental: true },
  { item_id: 1000545, name: "Bringer of Balance", slot: "sword_2h", pacs: ["cd_phm_02_sword_0114.pac"], confidence: "High" },
  { item_id: 15700, name: "Aeserion Spear", slot: "spear", pacs: ["cd_phm_02_spear_0120.pac"], confidence: "Very high" },
  { item_id: 15706, name: "Diverging Moon", slot: "spear", pacs: ["cd_phm_02_spear_0036.pac"], confidence: "Very high" },
  { item_id: 15702, name: "Grasping Moon", slot: "spear", pacs: ["cd_phm_02_spear_0027.pac"], confidence: "Very high" },
  { item_id: 330001, name: "Rhinard Cannon", slot: "cannon", pacs: ["cd_phm_02_cannon_0065.pac"], confidence: "Known safe" },
];

const MAKER_SLOTS = new Set(["sword", "sword_2h", "sword_2h_mecha", "spear", "spear_mecha", "cannon"]);

export function ModMaker({ registry, onBuilt }: { registry: ModRegistry; onBuilt: () => Promise<void> }) {
  const [sourceId, setSourceId] = useState("");
  const [donorId, setDonorId] = useState("");
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("Choose a built custom visual, then a compatible gameplay donor.");
  const [busy, setBusy] = useState(false);
  const [lastZip, setLastZip] = useState<string | null>(null);

  const ownedIds = useMemo(
    () => registry.owned_gear?.owned_item_ids ?? [],
    [registry.owned_gear?.owned_item_ids],
  );
  const sources = useMemo(
    () => registry.mods.filter((mod) => mod.built && MAKER_SLOTS.has(mod.slot)),
    [registry],
  );
  const source = sources.find((mod) => mod.id === sourceId);
  const donors = useMemo(() => {
    if (!source) return [];
    const catalog = registry.donors?.length ? registry.donors : FALLBACK_DONORS;
    return donorsForVisual(source.slot, catalog, {
      ownedOnly,
      ownedItemIds: ownedIds,
    });
  }, [source, registry.donors, ownedOnly, ownedIds]);
  const donor = donors.find((item) => String(item.item_id) === donorId);

  async function create() {
    if (!source || !donor) return;
    setBusy(true);
    setStatus("Building standalone CDUMM mod...");
    try {
      const out = await buildModMaker(
        {
          source_mod: source.source_mod,
          source_pac: source.donor_pac,
          visual_name: source.abbrev || source.display_name,
          donor: {
            item_id: donor.item_id,
            name: donor.name,
            slot: donor.slot,
            pacs: [...donor.pacs],
            confidence: donor.confidence,
            source: donor.source,
            experimental: donor.experimental,
          },
          donor_name: donor.name,
          item_id: donor.item_id,
          target_pacs: [...donor.pacs],
          title: title.trim() || undefined,
        },
        registry.workspace,
      );
      const zip = out.match(/Built: (.+\.zip)/)?.[1] ?? null;
      setLastZip(zip);
      setStatus(zip ? `Created and added to CDUMM staging: ${zip}` : out);
      await onBuilt();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
      <div className="mx-auto max-w-5xl">
        <h2 className="text-2xl font-bold">Mod Maker</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Turn one built custom visual into one standalone donor swap and place it in your CDUMM import staging list.
        </p>
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <Panel number="1" title="Custom visual">
            <select
              value={sourceId}
              onChange={(e) => {
                setSourceId(e.target.value);
                setDonorId("");
              }}
              className="maker-input"
            >
              <option value="">Choose a built mesh...</option>
              {sources.map((mod) => (
                <option key={mod.id} value={mod.id}>
                  {mod.category_label} - {mod.display_name}
                </option>
              ))}
            </select>
            {source && <Info mod={source} />}
          </Panel>
          <Panel number="2" title="Gameplay donor">
            <label className="mb-3 flex items-center gap-2 text-xs text-zinc-400">
              <input
                type="checkbox"
                checked={ownedOnly}
                onChange={(e) => {
                  setOwnedOnly(e.target.checked);
                  setDonorId("");
                }}
                disabled={!registry.owned_gear?.available}
                className="accent-crimson-500"
              />
              Owned only
              {registry.owned_gear?.available
                ? ` (${registry.owned_gear.gear_match_count ?? ownedIds.length} from save)`
                : " — sync owned gear on Loadout Forge tab first"}
            </label>
            <select
              value={donorId}
              disabled={!source}
              onChange={(e) => setDonorId(e.target.value)}
              className="maker-input"
            >
              <option value="">{source ? "Choose a compatible donor..." : "Choose a visual first..."}</option>
              {donors.map((item, index) => (
                <option key={item.item_id} value={item.item_id}>
                  {index === 0 ? "Recommended - " : ""}
                  {item.name} (ID {item.item_id})
                  {ownedIds.includes(item.item_id) ? " · owned" : ""}
                </option>
              ))}
            </select>
            {donor && <DonorInfo donor={donor} />}
            {source && donors.length === 0 && (
              <p className="mt-3 text-xs text-amber-500">
                No donors match the current filters. Try turning off Owned only or syncing owned gear from your save.
              </p>
            )}
          </Panel>
        </div>
        <Panel number="3" title="Export" wide>
          <label className="text-xs text-zinc-500">Optional CDUMM title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={source && donor ? `${donor.name} > ${source.abbrev}` : "Auto-generated from donor and visual"}
            className="maker-input mt-2"
          />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-2xl text-xs text-zinc-500">{status}</p>
            <div className="flex gap-2">
              {lastZip && (
                <button onClick={() => revealInFinder(lastZip)} className="maker-secondary">
                  Show zip
                </button>
              )}
              <button disabled={!source || !donor || busy} onClick={create} className="maker-primary">
                {busy ? "Building..." : "Create mod + add to CDUMM"}
              </button>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Panel({
  number,
  title,
  wide,
  children,
}: {
  number: string;
  title: string;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className={`${wide ? "mt-4" : ""} rounded-xl border border-zinc-800 bg-zinc-900/60 p-5`}>
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-crimson-950 text-xs font-bold text-crimson-400">
          {number}
        </span>
        <h3 className="font-semibold">{title}</h3>
      </div>
      {children}
    </section>
  );
}

function Info({ mod }: { mod: ModEntry }) {
  return (
    <div className="mt-4 text-xs text-zinc-500">
      <p className="font-medium text-zinc-300">{mod.display_name}</p>
      <p className="mt-1 font-mono">Built from {mod.donor_pac}</p>
      {mod.owned ? <p className="mt-1 text-crimson-400">Donor PAC is in your save inventory.</p> : null}
    </div>
  );
}

function DonorInfo({ donor }: { donor: DonorEntry }) {
  return (
    <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-400">
      <p className="font-semibold text-zinc-200">
        {donor.name}{" "}
        {donor.confidence ? <span className="text-crimson-400">{donor.confidence}</span> : null}
        {donor.source ? <span className="ml-2 text-zinc-600">({donor.source})</span> : null}
      </p>
      <p className="mt-2 font-mono">{donor.pacs.join(" + ")}</p>
      {donor.pacs.length > 1 && (
        <p className="mt-3 text-amber-400">
          Multi-part donor: test equipped and sheathed states. This direct remap is experimental until the original
          donor PACs are extracted.
        </p>
      )}
    </div>
  );
}
