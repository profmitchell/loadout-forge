export type SlotId = "helm" | "lantern" | "bow" | "sword" | "cannon" | "musket";

export interface SlotInfo {
  id: SlotId;
  label: string;
  equip: string;
  pac: string;
}

export interface CategoryInfo {
  id: string;
  label: string;
}

export interface ModEntry {
  id: string;
  source_mod: string;
  folder_name: string;
  category: string | null;
  category_label: string | null;
  display_name: string;
  abbrev: string;
  mod_name: string;
  slot: SlotId;
  slot_label: string;
  equip: string;
  donor_pac: string;
  built: boolean;
  version: string;
  description: string;
  preview_dir: string | null;
  preview_front: string | null;
  previews: Record<string, string>;
  glb: string | null;
}

export interface SkippedMod {
  path: string;
  reason: string;
}

export interface ModRegistry {
  workspace: string;
  scanned_at?: string;
  categories: CategoryInfo[];
  slots: SlotInfo[];
  mods: ModEntry[];
  skipped?: SkippedMod[];
  unbuilt_count?: number;
  next_loadout_number: number;
  naming_pattern: string;
}

export interface Settings {
  workspace: string;
}
