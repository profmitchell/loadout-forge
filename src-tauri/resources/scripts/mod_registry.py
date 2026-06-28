#!/usr/bin/env python3
"""Scan workspace mods and emit a JSON registry for LoadoutForge."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from weapon_donor_families import is_shotgun_pac, shotgun_slot_info  # noqa: E402

PAC_SLOTS: dict[str, dict[str, str]] = {
    "cd_phm_00_hel_0013_05.pac": {
        "slot": "helm",
        "equip": "Canta Plate Helm",
        "label": "Helm",
    },
    "cd_phm_00_hel_00_0369.pac": {
        "slot": "helm",
        "equip": "Ashad Plate Helm",
        "label": "Helm",
    },
    "cd_phm_00_hand_belt_0013.pac": {
        "slot": "gloves",
        "equip": "Keredig Plate Armor Gloves",
        "label": "Gloves",
    },
    "cd_phm_00_vest_belt_0013.pac": {
        "slot": "belt_pendant",
        "equip": "Canta Vest Belt",
        "label": "Belt Pendant",
    },
    "cd_phm_00_sho_0013.pac": {
        "slot": "boots",
        "equip": "Grace Plate Boots",
        "label": "Boots",
    },
    "cd_t0000_lantern_0001.pac": {
        "slot": "lantern",
        "equip": "Default Lantern",
        "label": "Lantern",
    },
    "cd_phm_04_bow_0008.pac": {
        "slot": "bow",
        "equip": "White Wood Bow",
        "label": "Bow",
    },
    "cd_phm_04_arw_0001.pac": {
        "slot": "arrow",
        "equip": "Default Arrow",
        "label": "Arrow",
    },
    "cd_phm_04_quiver_0008.pac": {
        "slot": "quiver",
        "equip": "Warspike Quiver",
        "label": "Quiver",
    },
    "cd_phm_01_sword_0019.pac": {
        "slot": "sword",
        "equip": "Sword of the Wolf",
        "label": "Sword",
    },
    "cd_phm_02_sword_0020.pac": {
        "slot": "sword_2h",
        "equip": "Rhett's Sword",
        "label": "2H Sword",
    },
    "cd_phm_02_sword_0015.pac": {
        "slot": "weapon_tassel",
        "equip": "Darkbringer",
        "label": "Weapon tassel",
    },
    "cd_phm_00_cloak_00_0340.pac": {
        "slot": "cloak",
        "equip": "Scarecrow Camouflage Cloak",
        "label": "Cloak",
    },
    "cd_phm_02_cannon_0065.pac": {
        "slot": "cannon",
        "equip": "Finest Rhinard Cannon",
        "label": "Cannon",
    },
    "cd_phm_02_spear_0001.pac": {
        "slot": "spear",
        "equip": "Default Spear",
        "label": "Spear",
    },
    "cd_phm_02_spear_0048.pac": {
        "slot": "spear_mecha",
        "equip": "Electro-Mecha Spear",
        "label": "Mecha Spear",
    },
    "cd_phm_02_warhammer_0016.pac": {
        "slot": "sword_2h_mecha",
        "equip": "Electro-Mecha Longsword",
        "label": "Mecha 2H",
    },
    "cd_phm_07_shotgun_0003.pac": {
        "slot": "shotgun",
        "equip": "Bleed Shotgun",
        "label": "Shotgun",
    },
    "cd_phm_08_musket_0011.pac": {
        "slot": "musket",
        "equip": "Demenissian Hero's Musket",
        "label": "Musket",
    },
    "cd_phm_08_musket_0012.pac": {
        "slot": "musket",
        "equip": "Default Musket",
        "label": "Musket",
    },
}

# Friendly labels for top-level category folders (auto-discovered; these are display overrides)
CATEGORY_LABELS: dict[str, str] = {
    "1H": "1H Swords",
    "2H": "2H Swords",
    "Cloaks": "Cloaks",
    "Helms": "Helms",
    "Bows": "Bows",
    "Arrows": "Arrows",
    "Quivers": "Quivers",
    "Weapon Tassels": "Weapon Tassels",
    "Lanterns": "Lanterns",
    "Cannon Staffs": "Cannon Staffs",
    "Muskets": "Muskets",
    "Shotguns": "Shotguns",
    "Spears": "Spears",
    "Rhinard": "Rhinard",
    "Armor": "Armor",
}

# Abbreviations keyed by mod folder name (works regardless of category path)
ABBR_BY_FOLDER: dict[str, str] = {
    "CRESCENTMOD": "CrescentSentinel",
    "PRISMBLADE": "PrismBlade",
    "SPLITTERMOD": "Ionblade",
    "GEOMOD": "RoseKatana",
    "ObsidianCrescentBow": "CrescentBow",
    "CelestialCrescentBow": "CelestialCrescent",
    "ObsidianBow": "CrescentBow",
    "ConcreteCrystalLantern": "Concrete",
    "AzureLatticeLantern": "Azure",
    "RhinardCannon": "Lance-Void",
    "RhinardCannon>LanceOfTheVoid": "Lance-Void",
    "LumenLance": "Lumen",
    "CelestialAegisSceptre": "AegisScept",
    "WhiteObsidianStag": "WhiteStag",
    "BlackObsidianStag": "BlackStag",
    "SentinelHelm": "Sentinel",
    "GraniteSentinelHelm": "Granite",
    "CarapaceLantern": "Carapace",
    "IvoryBeaconLantern": "IvoryBeacon",
    "IvoryArcRifle": "IvoryArc",
    "ObsidianMusketMod": "IvoryArc",
    "MassiveColossusBlade": "Colossus2H",
    "TattooPropHelm": "StagHexProp",
    "TattooHoodCloak": "StagHexCloak",
    "PrismaticLance": "Prismatic",
}

SKIP_PARTS = {
    ".bak",
    "BowReplacer",
    "WolfSwordReplacer",
    "Lumen_Cannonmodel",
    "_TasselTemplate",
}
SKIP_TOP_LEVEL = {
    "shared_tools",
    "CohenConcepts_Loadouts",
    "CohenConcepts_MeshPack",
    "docs",
    "loadout-forge",
    "GEOMOD",
    "GameplayMods",
    "MODSTOMAKE",
    "Lumen_Cannonmodel",
    "AzureMonolithBladeModel",
}


def _should_skip_mod(rel: str) -> bool:
    if ".bak" in rel:
        return True
    if any(skip in rel for skip in SKIP_PARTS):
        return True
    top = rel.split("/", 1)[0]
    return top in SKIP_TOP_LEVEL


def find_built_pac_files(mod_root: Path) -> list[Path]:
    """Return built PAC files under mod_root/files, excluding backups."""
    files_dir = mod_root / "files"
    if not files_dir.is_dir():
        return []
    return sorted(
        path
        for path in files_dir.rglob("*.pac")
        if path.is_file()
        and ".bak" not in path.name
        and "backup" not in {part.lower() for part in path.parts}
    )


def resolve_built_pac(mod_root: Path, config_pac: str | None = None) -> str | None:
    """Pick the PAC name that is actually present in a built mod's files/ tree."""
    files_dir = mod_root / "files"
    if not files_dir.is_dir():
        return None
    build_report = mod_root / "build_report.json"
    if build_report.is_file():
        try:
            report = json.loads(build_report.read_text(encoding="utf-8"))
            report_pac = str(report.get("donor_pac") or "").strip()
            if report_pac and next(files_dir.rglob(report_pac), None):
                return report_pac
        except json.JSONDecodeError:
            pass
    candidates = find_built_pac_files(mod_root)
    if not candidates:
        return None
    preferred = (config_pac or "").strip()
    if preferred and any(path.name == preferred for path in candidates):
        return preferred
    if len(candidates) == 1:
        return candidates[0].name
    character_candidates = [path for path in candidates if "character" in path.parts]
    pool = character_candidates or candidates
    pool.sort(key=lambda path: path.name)
    return pool[0].name


def resolve_built_source_pac(
    mod_root: Path,
    preferred_pac: str | None = None,
) -> tuple[Path, str] | None:
    """Return (pac_path, pac_name) for a built mod, if resolvable."""
    pac_name = resolve_built_pac(mod_root, preferred_pac)
    if not pac_name:
        return None
    pac_path = next((mod_root / "files").rglob(pac_name), None)
    if pac_path is None or not pac_path.is_file():
        return None
    return pac_path, pac_name


def slot_for_pac(pac_name: str) -> str | None:
    info = pac_slot_info(pac_name)
    return str(info["slot"]) if info else None


def load_shotgun_equip_by_pac(workspace: Path) -> dict[str, str]:
    """Map shotgun PAC filenames to a human equip label from the item catalog."""
    import csv

    csv_path = workspace / "CustomItems/research/item_catalog_enriched.csv"
    if not csv_path.is_file():
        return {}
    mapping: dict[str, str] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_pacs = (row.get("pac_files") or "").strip()
            if not raw_pacs:
                continue
            label = (row.get("display_name") or row.get("internal_name") or "").strip()
            if not label:
                continue
            for pac in raw_pacs.split(";"):
                pac = pac.strip()
                if pac and is_shotgun_pac(pac) and pac not in mapping:
                    mapping[pac] = label
    return mapping


def pac_slot_info(pac_name: str, *, shotgun_equip: dict[str, str] | None = None) -> dict[str, str] | None:
    pac_name = Path(pac_name).name
    if pac_name in PAC_SLOTS:
        return PAC_SLOTS[pac_name]
    if is_shotgun_pac(pac_name):
        equip = (shotgun_equip or {}).get(pac_name)
        return shotgun_slot_info(pac_name, equip=equip)
    return None


def infer_pac(config: dict, mod_root: Path) -> str | None:
    pac = config.get("donor_pac")
    if pac:
        return pac
    runtime_assets = config.get("runtime_assets")
    if isinstance(runtime_assets, list):
        for asset in runtime_assets:
            if isinstance(asset, dict) and asset.get("pac"):
                return str(asset["pac"])
    br = mod_root / "build_report.json"
    if br.is_file():
        report = json.loads(br.read_text(encoding="utf-8"))
        if "sword" in str(report.get("custom_submesh", "")).lower():
            return "cd_phm_01_sword_0019.pac"
    return None


def mod_folder_name(rel_path: str) -> str:
    return rel_path.split("/")[-1]


def mod_category(rel_path: str) -> str | None:
    parts = rel_path.split("/")
    return parts[0] if len(parts) >= 2 else None


def category_label(folder: str) -> str:
    return CATEGORY_LABELS.get(folder, folder)


def abbreviate(rel_path: str, display_name: str) -> str:
    folder = mod_folder_name(rel_path)
    if folder in ABBR_BY_FOLDER:
        return ABBR_BY_FOLDER[folder]
    if folder.startswith("DarkMarksmanCloak_"):
        tail = folder.split("_", 1)[1]
        words = re.findall(r"[A-Z][a-z]*|[a-z]+", tail)
        if words and words[-2:] == ["Hood", "Helm"]:
            words = words[:-2]
        if len(words) >= 2:
            return "".join(words[:2])
        return "".join(words) if words else tail[:12]
    name = display_name.split(">")[-1].strip() if ">" in display_name else display_name
    name = re.sub(r"\s+Visual Swap$", "", name, flags=re.I)
    for sep in ("\u2014", "—", " - "):
        if sep in name:
            name = name.split(sep, 1)[-1].strip()
            break
    parts = re.findall(r"[A-Za-z0-9]+", name)
    if len(parts) >= 2 and parts[0].lower() in {"obsidian", "myh", "canta", "rhinard"}:
        return parts[1] if len(parts[1]) > 2 else "".join(parts[:2])
    if len(parts) >= 2 and parts[0].lower() == "dark" and len(parts[1]) > 2:
        return parts[1] if len(parts) >= 2 else parts[0]
    return parts[0] if parts else folder[:12]


def glb_path(mod_root: Path, config: dict, workspace: Path | None = None) -> Path | None:
    candidates: list[str] = []
    base = config.get("clean_basename")
    if base:
        candidates.append(f"{base}.glb")
    src = config.get("source_glb")
    if src:
        candidates.append(src)
    for key in ("sources", "cloak_variants"):
        for entry in config.get(key) or []:
            entry_base = entry.get("clean_basename")
            if entry_base:
                candidates.append(f"{entry_base}.glb")
    for rel in candidates:
        p = mod_root / rel
        if p.is_file():
            return p
    if workspace is not None:
        variant = config.get("source_variant")
        if variant:
            parent = workspace / variant
            if parent.is_dir() and (parent / "mod_config.json").is_file():
                parent_config = json.loads((parent / "mod_config.json").read_text(encoding="utf-8"))
                inherited = glb_path(parent, parent_config, workspace)
                if inherited is not None:
                    return inherited
    return None


def discover_mod_roots(workspace: Path) -> list[Path]:
    roots: list[Path] = []
    for cfg in sorted(workspace.rglob("mod_config.json")):
        rel = cfg.parent.relative_to(workspace).as_posix()
        if _should_skip_mod(rel):
            continue
        roots.append(cfg.parent)
    return roots


def discover_category_folders(workspace: Path, mod_roots: list[Path]) -> list[dict]:
    seen: set[str] = set()
    categories: list[dict] = []
    for mod_root in mod_roots:
        rel = mod_root.relative_to(workspace).as_posix()
        config = json.loads((mod_root / "mod_config.json").read_text(encoding="utf-8"))
        cat = config.get("category_override") or mod_category(rel)
        if not cat or cat in seen:
            continue
        seen.add(cat)
        categories.append({"id": cat, "label": category_label(cat)})
    return sorted(categories, key=lambda c: c["label"].lower())


LEGACY_SOURCE_MOD: dict[str, str] = {
    "Bows/ObsidianBow": "Bows/ObsidianCrescentBow",
    "ObsidianBow": "Bows/ObsidianCrescentBow",
    "Muskets/ObsidianMusketMod": "Muskets/IvoryArcRifle",
    "ObsidianMusketMod": "Muskets/IvoryArcRifle",
    "2H/MassiveColossusBlade": "2H/ElectroMecha_MassiveColossusBlade",
    "2H/ToweringObeliskBlade": "2H/ElectroMecha_ToweringObeliskBlade",
    "MassiveColossusBlade": "2H/ElectroMecha_MassiveColossusBlade",
    "ToweringObeliskBlade": "2H/ElectroMecha_ToweringObeliskBlade",
}


def resolve_source_mod(workspace: Path, source_mod: str, mods: list[dict] | None = None) -> str:
    """Map legacy flat paths to current category tree (e.g. CRESCENTMOD -> 1H/CRESCENTMOD)."""
    source_mod = LEGACY_SOURCE_MOD.get(source_mod, source_mod)
    direct = workspace / source_mod
    if (direct / "mod_config.json").is_file():
        return source_mod
    if mods is None:
        mods = build_registry(workspace)["mods"]
    name = mod_folder_name(source_mod)
    matches = [
        m["source_mod"]
        for m in mods
        if mod_folder_name(m["source_mod"]) == name or m["source_mod"] == source_mod
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous source_mod '{source_mod}' — matches: {matches}")
    raise FileNotFoundError(f"No mod found for source_mod '{source_mod}' under {workspace}")


DONOR_SWAP_TARGETS: tuple[dict, ...] = (
    {"item_id": 13809, "name": "Nazk Sword", "slot": "sword", "pacs": ["cd_phm_01_sword_0075.pac"], "confidence": "Very high", "source": "rhett"},
    {"item_id": 13811, "name": "Aeserion Sword", "slot": "sword", "pacs": ["cd_phm_01_sword_0023.pac"], "confidence": "Very high", "source": "rhett"},
    {"item_id": 13810, "name": "Chillfallen Sword", "slot": "sword", "pacs": ["cd_phm_01_sword_0102.pac"], "confidence": "Very high", "source": "rhett"},
    {"item_id": 1000747, "name": "Lightningblade of Greed", "slot": "sword", "pacs": ["cd_phm_01_sword_0074.pac"], "confidence": "High", "source": "rhett"},
    {"item_id": 1000578, "name": "Fated Shadow", "slot": "sword", "pacs": ["cd_phm_01_sword_0168.pac"], "confidence": "High", "source": "rhett"},
    {"item_id": 1163042, "name": "Sword of the Wolf", "slot": "sword", "pacs": ["cd_phm_01_sword_0019.pac"], "confidence": "Known safe", "source": "rhett"},
    {"item_id": 14705, "name": "Darkbringer", "slot": "sword_2h", "pacs": ["cd_phm_02_sword_0015.pac", "cd_phm_02_sword_0015_in.pac"], "confidence": "Very high", "source": "rhett", "experimental": True},
    {"item_id": 15903, "name": "Twisted Verdict", "slot": "sword_2h", "pacs": ["cd_phm_02_sword_0040.pac", "cd_phm_02_sword_0039_in.pac"], "confidence": "Very high", "source": "rhett", "experimental": True},
    {"item_id": 1000545, "name": "Bringer of Balance", "slot": "sword_2h", "pacs": ["cd_phm_02_sword_0114.pac"], "confidence": "High", "source": "rhett"},
    {"item_id": 15700, "name": "Aeserion Spear", "slot": "spear", "pacs": ["cd_phm_02_spear_0120.pac"], "confidence": "Very high", "source": "rhett"},
    {"item_id": 15706, "name": "Diverging Moon", "slot": "spear", "pacs": ["cd_phm_02_spear_0036.pac"], "confidence": "Very high", "source": "rhett"},
    {"item_id": 15702, "name": "Grasping Moon", "slot": "spear", "pacs": ["cd_phm_02_spear_0027.pac"], "confidence": "Very high", "source": "rhett"},
    {"item_id": 330001, "name": "Rhinard Cannon", "slot": "cannon", "pacs": ["cd_phm_02_cannon_0065.pac"], "confidence": "Known safe", "source": "rhett"},
)


def load_donor_catalog(workspace: Path) -> list[dict]:
    catalog_path = workspace / "CohenConcepts_Loadouts/donor_catalog.json"
    if catalog_path.is_file():
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        donors = payload.get("donors")
        if isinstance(donors, list) and donors:
            return [dict(row) for row in donors]
    return [dict(row) for row in DONOR_SWAP_TARGETS]


def load_owned_gear_meta(workspace: Path) -> dict:
    owned_path = workspace / "CohenConcepts_Loadouts/owned_gear.json"
    if not owned_path.is_file():
        return {
            "available": False,
            "owned_item_ids": [],
            "owned_pacs": [],
        }
    try:
        payload = json.loads(owned_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "available": False,
            "owned_item_ids": [],
            "owned_pacs": [],
        }

    owned_item_ids: list[int] = []
    owned_pacs: set[str] = set()
    for rows in (payload.get("items_by_slot") or {}).values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            owned_item_ids.append(int(row["item_id"]))
            for pac in row.get("pacs") or []:
                owned_pacs.add(str(pac))

    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "save_path": payload.get("save_path"),
        "save_profile": payload.get("save_profile"),
        "save_slot": payload.get("save_slot"),
        "gear_match_count": payload.get("gear_match_count", len(owned_item_ids)),
        "owned_item_id_count": payload.get("owned_item_id_count", len(owned_item_ids)),
        "owned_item_ids": sorted(set(owned_item_ids)),
        "owned_pacs": sorted(owned_pacs),
    }


def build_registry(workspace: Path) -> dict:
    owned_meta = load_owned_gear_meta(workspace)
    owned_pacs = set(owned_meta.get("owned_pacs") or [])
    donors = load_donor_catalog(workspace)
    mod_roots = discover_mod_roots(workspace)
    shotgun_equip = load_shotgun_equip_by_pac(workspace)
    mods: list[dict] = []
    skipped: list[dict] = []
    seen_roots: set[str] = set()

    for cfg in sorted(workspace.rglob("mod_config.json")):
        rel = cfg.parent.relative_to(workspace).as_posix()
        if _should_skip_mod(rel):
            skipped.append({"path": rel, "reason": "excluded (backup, template, or mesh-only folder)"})
            continue
        if rel in seen_roots:
            continue
        seen_roots.add(rel)
        config = json.loads(cfg.read_text(encoding="utf-8"))
        pac = infer_pac(config, cfg.parent)
        if not pac:
            skipped.append({"path": rel, "reason": "missing donor_pac in mod_config.json"})
            continue
        if pac_slot_info(pac, shotgun_equip=shotgun_equip) is None:
            skipped.append({"path": rel, "reason": f"unsupported donor_pac: {pac}"})
            continue

    for mod_root in mod_roots:
        rel = mod_root.relative_to(workspace).as_posix()
        config = json.loads((mod_root / "mod_config.json").read_text(encoding="utf-8"))
        pac = infer_pac(config, mod_root)
        slot_info = pac_slot_info(pac or "", shotgun_equip=shotgun_equip) if pac else None
        if not pac or slot_info is None:
            continue
        if pac == "cd_phm_02_sword_0020.pac":
            skipped.append({"path": rel, "reason": "deprecated Rhett 2H donor — use ElectroMecha_* mod"})
            continue
        config_pac = pac
        built_pacs = find_built_pac_files(mod_root)
        built = bool(built_pacs)
        if built:
            resolved = resolve_built_pac(mod_root, config_pac)
            if resolved and pac_slot_info(resolved, shotgun_equip=shotgun_equip):
                pac = resolved
        if pac_slot_info(pac, shotgun_equip=shotgun_equip) is None:
            skipped.append({"path": rel, "reason": f"unsupported built donor_pac: {pac}"})
            continue
        slot_info = pac_slot_info(pac, shotgun_equip=shotgun_equip)
        assert slot_info is not None
        preview_dir = mod_root / "nexus_previews"
        previews = {
            angle: str((preview_dir / f"{angle}.png").resolve())
            for angle in ("front", "side", "three_quarter", "top")
            if (preview_dir / f"{angle}.png").is_file()
        }
        display = config.get("display_name") or config.get("mod_name") or rel
        cat = config.get("category_override") or mod_category(rel)
        mods.append(
            {
                "id": rel.replace("/", "__"),
                "source_mod": rel,
                "folder_name": mod_folder_name(rel),
                "category": cat,
                "category_label": category_label(cat) if cat else None,
                "display_name": display,
                "abbrev": abbreviate(rel, display),
                "mod_name": config.get("mod_name", ""),
                "slot": slot_info["slot"],
                "slot_label": config.get("slot_label_override", slot_info["label"]),
                "equip": config.get("equip_override", slot_info["equip"]),
                "donor_pac": pac,
                "built": built,
                "version": config.get("version", "1.0.0"),
                "description": config.get("description", ""),
                "preview_dir": str(preview_dir.resolve()) if preview_dir.is_dir() else None,
                "preview_front": previews.get("front"),
                "previews": previews,
                "glb": str(gpb) if (gpb := glb_path(mod_root, config, workspace)) else None,
                "owned": bool(owned_pacs and pac in owned_pacs),
            }
        )
    mods.sort(key=lambda m: (m.get("category") or "", m["slot"], m["display_name"].lower()))
    categories = discover_category_folders(workspace, mod_roots)
    existing = sorted(
        p.name
        for p in (workspace / "CohenConcepts_Loadouts").glob("Loadout*")
        if p.is_dir() and re.fullmatch(r"Loadout\d+", p.name)
    )
    next_num = 1
    if existing:
        nums = [int(re.search(r"\d+", n).group()) for n in existing if re.search(r"\d+", n)]
        next_num = max(nums, default=0) + 1
    slot_entries: dict[str, dict[str, str]] = dict(PAC_SLOTS)
    for pac_name, equip in sorted(shotgun_equip.items()):
        slot_entries.setdefault(
            pac_name,
            shotgun_slot_info(pac_name, equip=equip),
        )
    for pac_name in sorted(slot_entries):
        if is_shotgun_pac(pac_name) and pac_name not in shotgun_equip:
            slot_entries.setdefault(pac_name, shotgun_slot_info(pac_name))

    unbuilt = sum(1 for m in mods if not m["built"])
    owned_mod_count = sum(1 for m in mods if m.get("owned"))
    return {
        "workspace": str(workspace.resolve()),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "owned_gear": owned_meta,
        "owned_mod_count": owned_mod_count,
        "donors": donors,
        "categories": categories,
        "slots": [
            {"id": info["slot"], "label": info["label"], "equip": info["equip"], "pac": pac}
            for pac, info in sorted(slot_entries.items())
        ],
        "mods": mods,
        "skipped": skipped,
        "unbuilt_count": unbuilt,
        "next_loadout_number": next_num,
        "naming_pattern": "Cohen Concepts > Loadout {NN} - {Gear-Gear-Gear}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--out", type=Path, default=WORKSPACE / "CohenConcepts_Loadouts/mod_registry.json")
    args = parser.parse_args()
    reg = build_registry(args.workspace.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mods": len(reg["mods"]), "categories": reg["categories"], "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
