import type { DonorEntry } from "./types";

const POLEARM_FAMILY = new Set(["cannon", "spear", "spear_mecha"]);
const MECHA_POLEARM_FAMILY = new Set(["sword_2h_mecha", ...POLEARM_FAMILY]);

export function compatibleDonorSlots(visualSlot: string | undefined): Set<string> {
  if (!visualSlot) return new Set();
  const slots = new Set<string>([visualSlot]);
  if (visualSlot === "spear_mecha") slots.add("spear");
  if (visualSlot === "sword_2h_mecha") slots.add("sword_2h");
  if ([...slots].some((slot) => POLEARM_FAMILY.has(slot))) {
    POLEARM_FAMILY.forEach((slot) => slots.add(slot));
  }
  if ([...slots].some((slot) => MECHA_POLEARM_FAMILY.has(slot))) {
    MECHA_POLEARM_FAMILY.forEach((slot) => slots.add(slot));
    POLEARM_FAMILY.forEach((slot) => slots.add(slot));
  }
  return slots;
}

function donorMatchPriority(visualSlot: string, donorSlot: string): number {
  if (donorSlot === visualSlot) return 0;
  if (visualSlot === "sword_2h_mecha" && donorSlot === "sword_2h") return 1;
  if (visualSlot === "spear_mecha" && donorSlot === "spear") return 1;
  return 2;
}

export function donorsForVisual(
  visualSlot: string,
  donors: DonorEntry[],
  options?: { ownedOnly?: boolean; ownedItemIds?: number[] },
): DonorEntry[] {
  const wanted = compatibleDonorSlots(visualSlot);
  const ownedSet = new Set(options?.ownedItemIds ?? []);
  const matches = donors.filter((donor) => {
    if (!wanted.has(donor.slot)) return false;
    if (options?.ownedOnly && ownedSet.size > 0 && !ownedSet.has(donor.item_id)) {
      return false;
    }
    return true;
  });

  return matches.sort((a, b) => {
    const aOwned = ownedSet.has(a.item_id) ? 0 : 1;
    const bOwned = ownedSet.has(b.item_id) ? 0 : 1;
    if (aOwned !== bOwned) return aOwned - bOwned;
    const aPriority = donorMatchPriority(visualSlot, a.slot);
    const bPriority = donorMatchPriority(visualSlot, b.slot);
    if (aPriority !== bPriority) return aPriority - bPriority;
    return a.name.localeCompare(b.name);
  });
}
