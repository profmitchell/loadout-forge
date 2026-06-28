export type SlotId =
  | "helm"
  | "gloves"
  | "boots"
  | "lantern"
  | "bow"
  | "sword"
  | "sword_2h"
  | "cloak"
  | "cannon"
  | "spear"
  | "spear_mecha"
  | "sword_2h_mecha"
  | "shotgun"
  | "musket";

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
  build_stale?: boolean;
  zip_stale?: boolean;
  preview_stale?: boolean;
  owned?: boolean;
  version: string;
  description: string;
  preview_dir: string | null;
  preview_front: string | null;
  previews: Record<string, string>;
  glb: string | null;
}

export interface DonorEntry {
  item_id: number;
  name: string;
  slot: string;
  pacs: string[];
  confidence?: string;
  source?: string;
  experimental?: boolean;
  owned?: boolean;
}

export interface OwnedGearMeta {
  available: boolean;
  generated_at?: string;
  save_path?: string;
  save_profile?: string;
  save_slot?: string;
  gear_match_count?: number;
  owned_item_id_count?: number;
  owned_item_ids: number[];
  owned_pacs: string[];
}

export interface SkippedMod {
  path: string;
  reason: string;
}

export interface LastSyncMeta {
  at?: string;
  names_synced?: boolean;
  rebuilt_count?: number;
  rebuilt?: string[];
  rebuild_failed?: string[];
  repacked_count?: number;
  repacked?: string[];
}

export interface ModRegistry {
  workspace: string;
  scanned_at?: string;
  owned_gear?: OwnedGearMeta;
  owned_mod_count?: number;
  donors?: DonorEntry[];
  categories: CategoryInfo[];
  slots: SlotInfo[];
  mods: ModEntry[];
  skipped?: SkippedMod[];
  unbuilt_count?: number;
  build_stale_count?: number;
  zip_stale_count?: number;
  preview_stale_count?: number;
  next_loadout_number: number;
  naming_pattern: string;
  _last_sync?: LastSyncMeta;
}

export interface Settings {
  workspace: string;
}
