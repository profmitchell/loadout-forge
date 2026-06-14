#!/usr/bin/env python3
"""Scan workspace mods and emit a JSON registry for LoadoutForge."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]

PAC_SLOTS: dict[str, dict[str, str]] = {
    "cd_phm_00_hel_0013_05.pac": {
        "slot": "helm",
        "equip": "Canta Plate Helm",
        "label": "Helm",
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
    "cd_phm_01_sword_0019.pac": {
        "slot": "sword",
        "equip": "Sword of the Wolf",
        "label": "Sword",
    },
    "cd_phm_02_cannon_0065.pac": {
        "slot": "cannon",
        "equip": "Finest Rhinard Cannon",
        "label": "Cannon",
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
    "Helms": "Helms",
    "Bows": "Bows",
    "Lanterns": "Lanterns",
    "Cannon Staffs": "Cannon Staffs",
    "Muskets": "Muskets",
    "Rhinard": "Rhinard",
}

# Abbreviations keyed by mod folder name (works regardless of category path)
ABBR_BY_FOLDER: dict[str, str] = {
    "CRESCENTMOD": "Crescent",
    "PRISMBLADE": "Prism",
    "SPLITTERMOD": "Splitter",
    "GEOMOD": "Geo",
    "ObsidianCrescentBow": "CrescentBow",
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
}

SKIP_PARTS = {".bak", "Template", "BowReplacer", "WolfSwordReplacer", "Lumen_Cannonmodel", "AzureMonolithBladeModel"}
SKIP_TOP_LEVEL = {
    "shared_tools",
    "CohenConcepts_Loadouts",
    "CohenConcepts_MeshPack",
    "docs",
    "loadout-forge",
    "GEOMOD",
    "Lumen_Cannonmodel",
    "AzureMonolithBladeModel",
}


def infer_pac(config: dict, mod_root: Path) -> str | None:
    pac = config.get("donor_pac")
    if pac:
        return pac
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
    name = display_name.split(">")[-1].strip() if ">" in display_name else display_name
    name = re.sub(r"\s+Visual Swap$", "", name, flags=re.I)
    parts = re.findall(r"[A-Za-z0-9]+", name)
    if len(parts) >= 2 and parts[0].lower() in {"obsidian", "myh", "canta", "rhinard"}:
        return parts[1] if len(parts[1]) > 2 else "".join(parts[:2])
    return parts[0] if parts else folder[:12]


def glb_path(mod_root: Path, config: dict) -> Path | None:
    for key in ("clean_basename",):
        base = config.get(key)
        if base:
            p = mod_root / f"{base}.glb"
            if p.is_file():
                return p
    src = config.get("source_glb")
    if src:
        p = mod_root / src
        if p.is_file():
            return p
    return None


def discover_mod_roots(workspace: Path) -> list[Path]:
    roots: list[Path] = []
    for cfg in sorted(workspace.rglob("mod_config.json")):
        rel = cfg.parent.relative_to(workspace).as_posix()
        if any(skip in rel for skip in SKIP_PARTS):
            continue
        if ".bak" in rel:
            continue
        roots.append(cfg.parent)
    return roots


def discover_category_folders(workspace: Path, mod_roots: list[Path]) -> list[dict]:
    seen: set[str] = set()
    categories: list[dict] = []
    for mod_root in mod_roots:
        rel = mod_root.relative_to(workspace).as_posix()
        cat = mod_category(rel)
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


def build_registry(workspace: Path) -> dict:
    mod_roots = discover_mod_roots(workspace)
    mods: list[dict] = []
    for mod_root in mod_roots:
        rel = mod_root.relative_to(workspace).as_posix()
        config = json.loads((mod_root / "mod_config.json").read_text(encoding="utf-8"))
        pac = infer_pac(config, mod_root)
        if not pac or pac not in PAC_SLOTS:
            continue
        slot_info = PAC_SLOTS[pac]
        built = (mod_root / "files").is_dir() and any((mod_root / "files").rglob("*.pac"))
        preview_dir = mod_root / "nexus_previews"
        previews = {
            angle: str((preview_dir / f"{angle}.png").resolve())
            for angle in ("front", "side", "three_quarter", "top")
            if (preview_dir / f"{angle}.png").is_file()
        }
        display = config.get("display_name") or config.get("mod_name") or rel
        cat = mod_category(rel)
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
                "slot_label": slot_info["label"],
                "equip": slot_info["equip"],
                "donor_pac": pac,
                "built": built,
                "version": config.get("version", "1.0.0"),
                "description": config.get("description", ""),
                "preview_dir": str(preview_dir.resolve()) if preview_dir.is_dir() else None,
                "preview_front": previews.get("front"),
                "previews": previews,
                "glb": str(gpb) if (gpb := glb_path(mod_root, config)) else None,
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
    return {
        "workspace": str(workspace.resolve()),
        "categories": categories,
        "slots": [
            {"id": info["slot"], "label": info["label"], "equip": info["equip"], "pac": pac}
            for pac, info in PAC_SLOTS.items()
        ],
        "mods": mods,
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
