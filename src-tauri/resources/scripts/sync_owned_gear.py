#!/usr/bin/env python3
"""Refresh CohenConcepts_Loadouts/owned_gear.json from the newest Pearl Abyss save."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
OUT_PATH = WORKSPACE / "CohenConcepts_Loadouts/owned_gear.json"
CATALOG_PATH = WORKSPACE / "CohenConcepts_Loadouts/donor_catalog.json"

GEAR_SLOTS = {
    "arrow",
    "boots",
    "bow",
    "cannon",
    "chest",
    "cloak",
    "gloves",
    "helm",
    "lantern",
    "musket",
    "quiver",
    "shotgun",
    "spear",
    "spear_mecha",
    "sword",
    "sword_2h",
    "sword_2h_mecha",
}

SLOT_TO_KIND = {
    "sword": "sword_1h",
    "sword_2h": "sword_2h",
    "sword_2h_mecha": "sword_2h",
    "spear": "spear",
    "spear_mecha": "spear",
    "arrow": "arrow",
    "quiver": "quiver",
    "bow": "bow",
    "cannon": "cannon",
    "musket": "musket",
    "shotgun": "shotgun",
    "helm": "helm",
    "cloak": "cloak",
    "lantern": "lantern",
}

SLOT_LABELS = {
    "sword": "One-handed swords",
    "sword_2h": "Two-handed swords",
    "cannon": "Cannons / staff weapons",
    "bow": "Bows",
    "arrow": "Arrows",
    "quiver": "Quivers",
    "musket": "Muskets",
    "shotgun": "Shotguns",
    "spear": "Spears",
    "helm": "Helms / hats",
    "chest": "Chest armor",
    "gloves": "Gloves",
    "boots": "Boots",
    "cloak": "Cloaks",
    "lantern": "Lanterns",
}


def _slug(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return text[:48] or "item"


def _equip_label(name: str) -> str:
    return name.split(" —", 1)[0].split(" >", 1)[0].strip()


def _pearl_abyss_saves() -> list[Path]:
    roots = [
        Path.home() / "Library/Application Support/Pearl Abyss/CD/save",
        Path.home() / "CrimsonDesert/save",
    ]
    found: list[Path] = []
    for root in roots:
        if root.is_dir():
            found.extend(root.rglob("save.save"))
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def _load_owned_ids(save_path: Path) -> list[int]:
    cdumm_src = WORKSPACE.parent / "CDUMM-PathcMerge/src"
    if str(cdumm_src) not in sys.path:
        sys.path.insert(0, str(cdumm_src))
    from cdumm.save_inventory_parser import extract_owned_item_ids_from_save

    return extract_owned_item_ids_from_save(save_path) or []


def donor_to_install_target(donor: dict[str, object]) -> dict[str, object]:
    name = str(donor["name"])
    pacs = donor.get("pacs") or []
    pac = str(pacs[0]) if pacs else ""
    item_id = int(donor["item_id"])
    return {
        "id": _slug(name),
        "label": name,
        "equip": _equip_label(name),
        "donor_pac": pac,
        "donor_item_id": item_id,
        "owned": True,
    }


def build_owned_gear(save_path: Path) -> dict[str, object]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    by_id = {int(row["item_id"]): row for row in catalog["donors"]}
    owned_ids = set(_load_owned_ids(save_path))

    matched: list[dict[str, object]] = []
    for item_id in sorted(owned_ids):
        donor = by_id.get(item_id)
        if donor and donor.get("slot") in GEAR_SLOTS:
            matched.append(dict(donor))

    by_slot: dict[str, list[dict[str, object]]] = defaultdict(list)
    for donor in matched:
        by_slot[str(donor["slot"])].append(donor)

    install_targets: dict[str, list[dict[str, object]]] = defaultdict(list)
    for slot, donors in by_slot.items():
        kind = SLOT_TO_KIND.get(slot)
        if not kind:
            continue
        for donor in sorted(donors, key=lambda row: str(row["name"]).lower()):
            install_targets[kind].append(donor_to_install_target(donor))

    slot100 = save_path.parent.name if save_path.parent.name.startswith("slot") else save_path.parent.name
    auto_dir = save_path.parents[1].name if len(save_path.parents) > 1 else ""

    return {
        "workspace": str(WORKSPACE),
        "generated_at": datetime.now(UTC).isoformat(),
        "save_path": str(save_path),
        "save_profile": auto_dir,
        "save_slot": slot100,
        "owned_item_id_count": len(owned_ids),
        "gear_match_count": len(matched),
        "slot_labels": SLOT_LABELS,
        "items_by_slot": {
            slot: [
                {
                    "item_id": int(row["item_id"]),
                    "name": row["name"],
                    "slot": row["slot"],
                    "pacs": list(row.get("pacs") or []),
                    "source": row.get("source"),
                    "confidence": row.get("confidence"),
                }
                for row in sorted(rows, key=lambda row: str(row["name"]).lower())
            ]
            for slot, rows in sorted(by_slot.items())
        },
        "install_targets": dict(sorted(install_targets.items())),
    }


def main() -> int:
    saves = _pearl_abyss_saves()
    if not saves:
        print("No Pearl Abyss save.save files found.", file=sys.stderr)
        return 1
    save_path = saves[0]
    payload = build_owned_gear(save_path)
    if OUT_PATH.is_file():
        backup = OUT_PATH.with_suffix(f".json.before_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_bytes(OUT_PATH.read_bytes())
        print(f"Backed up existing file to {backup.name}")
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({payload['gear_match_count']} gear items from {save_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
