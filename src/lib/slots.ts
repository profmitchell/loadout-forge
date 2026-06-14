import type { ModEntry, ModRegistry, SlotId } from "./types";

/** Default slot order for loadout UI (registry may add more, e.g. musket). */
export const SLOT_ORDER: SlotId[] = ["helm", "lantern", "bow", "sword", "cannon", "musket"];

export function slotOrderFromRegistry(registry: ModRegistry | null): SlotId[] {
  if (registry?.slots?.length) {
    const ids = registry.slots.map((s) => s.id as SlotId);
    const seen = new Set(ids);
    for (const slot of SLOT_ORDER) {
      if (!seen.has(slot)) ids.push(slot);
    }
    return ids;
  }
  return SLOT_ORDER;
}

export function buildModsBySlot(registry: ModRegistry | null): Record<string, ModEntry[]> {
  const map: Record<string, ModEntry[]> = {};
  for (const slot of slotOrderFromRegistry(registry)) {
    map[slot] = [];
  }
  registry?.mods.forEach((m) => {
    if (!map[m.slot]) map[m.slot] = [];
    map[m.slot].push(m);
  });
  return map;
}
