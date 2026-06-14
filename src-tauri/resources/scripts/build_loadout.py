#!/usr/bin/env python3
"""Assemble a Cohen Concepts loadout zip from built individual mod files/."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
LOADOUTS_ROOT = Path(__file__).resolve().parents[1]
STAGING = Path.home() / "Library/Application Support/cdumm/CDMods/_import_staging"
REGISTRY = LOADOUTS_ROOT / "mod_registry.json"


def scripts_path(workspace: Path) -> Path:
    override = os.environ.get("LOADOUTFORGE_SCRIPTS")
    if override:
        return Path(override)
    bundled = Path(__file__).resolve().parent
    if (bundled / "mod_registry.py").is_file():
        return bundled
    return workspace / "shared_tools"


def loadouts_root(workspace: Path) -> Path:
    return workspace / "CohenConcepts_Loadouts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("loadout_id", nargs="?", default=None, help="e.g. Loadout01 or auto from --stdin-config")
    parser.add_argument("--config", type=Path, help="Path to loadout_config.json")
    parser.add_argument("--stdin-config", action="store_true", help="Read full loadout JSON from stdin")
    parser.add_argument("--no-stage", action="store_true")
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    return parser.parse_args()


def load_registry(workspace: Path) -> dict:
    sys.path.insert(0, str(scripts_path(workspace)))
    from mod_registry import build_registry  # noqa: E402

    reg = build_registry(workspace)
    reg_path = loadouts_root(workspace) / "mod_registry.json"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    return reg


def names_from_abbrevs(
    number: int,
    abbrevs: list[str],
    *,
    individual: bool = False,
) -> dict[str, str]:
    gear = "-".join(abbrevs)
    if individual:
        if len(abbrevs) != 1:
            raise ValueError("Individual export requires exactly one mod")
        slug = re.sub(r"[^A-Za-z0-9]+", "", abbrevs[0]) or "Gear"
        return {
            "id": f"Individual_{slug}",
            "display_name": f"Cohen Concepts > {abbrevs[0]}",
            "mod_name": f"CohenConcepts_{slug}",
            "zip_name": f"CohenConcepts_{slug}_CDUMM.zip",
            "gear_slug": slug,
        }
    num = f"{number:02d}"
    lid = f"Loadout{num}"
    return {
        "id": lid,
        "display_name": f"Cohen Concepts > Loadout {num} - {gear}",
        "mod_name": f"CohenConcepts_Loadout{num}_{gear.replace('-', '_')}",
        "zip_name": f"CohenConcepts_Loadout{num}_{gear}_CDUMM.zip",
        "gear_slug": gear,
    }


def config_from_stdin(workspace: Path) -> dict:
    payload = json.loads(sys.stdin.read())
    registry = load_registry(workspace)
    mod_by_id = {m["id"]: m for m in registry["mods"]}
    mod_by_source = {m["source_mod"]: m for m in registry["mods"]}

    number = int(payload.get("loadout_number") or registry.get("next_loadout_number") or 1)
    selected: list[dict] = []
    abbrevs: list[str] = []
    for entry in payload["mods"]:
        key = entry if isinstance(entry, str) else entry.get("source_mod") or entry.get("id")
        mod = mod_by_id.get(key) or mod_by_source.get(key)
        if not mod:
            raise ValueError(f"Unknown mod: {key}")
        if not mod["built"]:
            raise FileNotFoundError(f"Mod not built: {mod['source_mod']} — run build_all.py first")
        abbrevs.append(entry.get("abbrev", mod["abbrev"]) if isinstance(entry, dict) else mod["abbrev"])
        selected.append(
            {
                "source_mod": mod["source_mod"],
                "label": mod["display_name"],
                "equip": f"{mod['equip']} / {mod['donor_pac']}",
                "slot": mod["slot"],
                "abbrev": mod["abbrev"],
            }
        )

    slots = {item["slot"] for item in selected}
    if len(slots) != len(selected):
        raise ValueError("Loadout cannot include two mods for the same equipment slot")

    individual = bool(payload.get("individual"))
    names = names_from_abbrevs(number, abbrevs, individual=individual)
    if individual:
        names["display_name"] = f"Cohen Concepts > {selected[0]['label']}"
    desc_parts = ", ".join(item["label"] for item in selected)
    return {
        **names,
        "individual": individual,
        "version": payload.get("version", "1.0.0"),
        "author": payload.get("author", "Mitchell"),
        "description": payload.get("description")
        or (f"Individual gear export: {desc_parts}." if individual else f"Custom loadout: {desc_parts}."),
        "items": selected,
    }


def resolve_item_source(workspace: Path, source_mod: str) -> str:
    sys.path.insert(0, str(scripts_path(workspace)))
    from mod_registry import build_registry, resolve_source_mod  # noqa: E402

    reg = build_registry(workspace)
    return resolve_source_mod(workspace, source_mod, reg["mods"])


def copy_mod_files(source_mod: Path, dest_root: Path) -> list[str]:
    src = source_mod / "files"
    if not src.is_dir():
        raise FileNotFoundError(f"Missing built files/: {src} — run that mod's build_all.py first")
    copied: list[str] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".DS_Store" or ".bak" in path.name:
            continue
        rel = path.relative_to(src)
        out = dest_root / "files" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            bak = out.with_suffix(out.suffix + ".before_loadout_copy.bak")
            if not bak.exists():
                shutil.copy2(out, bak)
        shutil.copy2(path, out)
        copied.append(rel.as_posix())
    return copied


def build_from_config(config: dict, workspace: Path, loadout_dir: Path, stage: bool) -> Path:
    staging_files = loadout_dir / "files"
    if staging_files.exists():
        shutil.rmtree(staging_files)
    staging_files.mkdir(parents=True, exist_ok=True)

    manifest_paths: list[str] = []
    individual = bool(config.get("individual"))
    readme_lines = [
        config["display_name"],
        "",
        "CDUMM:",
        "1. Disable other mesh_loose_mod replacers for these same items.",
        (
            "2. Import this zip, enable it, Apply, and restart the game."
            if individual
            else "2. Disable separate individual zips for items in this loadout."
        ),
        *([] if individual else ["3. Import this zip, enable ONLY this loadout mod, Apply, restart."]),
        "",
        "Includes:",
    ]

    for item in config["items"]:
        resolved = resolve_item_source(workspace, item["source_mod"])
        mod_path = workspace / resolved
        copied = copy_mod_files(mod_path, loadout_dir)
        source_config = json.loads((mod_path / "mod_config.json").read_text(encoding="utf-8"))
        for patch_name in source_config.get("root_patch_files", []):
            patch_source = mod_path / patch_name
            if not patch_source.is_file():
                raise FileNotFoundError(f"Missing root patch file: {patch_source}")
            shutil.copy2(patch_source, loadout_dir / patch_name)
        readme_lines.append(f"  - {item['label']} ({item['equip']})")
        manifest_paths.extend(copied)

    normalized: list[dict] = []
    seen: set[str] = set()
    for path in sorted(manifest_paths):
        if path in seen:
            continue
        seen.add(path)
        suffix = Path(path).suffix.lower()
        if path.endswith(".pac_xml"):
            fmt = "pac_xml"
        elif suffix == ".pac":
            fmt = "pac"
        elif suffix == ".dds":
            fmt = "dds"
        else:
            fmt = "file"
        normalized.append({"path": path, "format": fmt})

    manifest = {
        "format": "v1",
        "kind": "mesh_loose_mod",
        "game": "Crimson Desert",
        "title": config["display_name"],
        "name": config["mod_name"],
        "mod_name": config["mod_name"],
        "author": config["author"],
        "version": config["version"],
        "files_dir": "files",
        "description": config["description"],
        "files": sorted(normalized, key=lambda x: x["path"]),
    }
    modinfo = {
        "title": config["display_name"],
        "name": config["mod_name"],
        "author": config["author"],
        "version": config["version"],
        "game": "Crimson Desert",
        "format": "v1",
        "type": "mesh_loose_mod",
        "files_dir": "files",
        "description": config["description"],
        "generator": "Cohen Concepts LoadoutForge",
    }
    (loadout_dir / "loadout_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (loadout_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (loadout_dir / "modinfo.json").write_text(json.dumps(modinfo, indent=2) + "\n", encoding="utf-8")
    (loadout_dir / "README.txt").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    zip_path = loadout_dir / config["zip_name"]
    if zip_path.exists():
        bak = zip_path.with_suffix(".zip.before_rebuild.bak")
        if not bak.exists():
            shutil.copy2(zip_path, bak)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("README.txt", "manifest.json", "modinfo.json", "loadout_config.json"):
            p = loadout_dir / name
            if p.is_file():
                zf.write(p, name)
        root_patch_names: set[str] = set()
        for item in config["items"]:
            resolved = resolve_item_source(workspace, item["source_mod"])
            source_config = json.loads((workspace / resolved / "mod_config.json").read_text(encoding="utf-8"))
            root_patch_names.update(source_config.get("root_patch_files", []))
        for name in sorted(root_patch_names):
            p = loadout_dir / name
            if p.is_file():
                zf.write(p, name)
        for path in sorted((loadout_dir / "files").rglob("*")):
            if path.is_file() and ".bak" not in path.name:
                zf.write(path, path.relative_to(loadout_dir).as_posix())

    if stage:
        STAGING.mkdir(parents=True, exist_ok=True)
        staged = STAGING / zip_path.name
        if staged.exists():
            bak = staged.with_suffix(".zip.before_loadout_stage.bak")
            if not bak.exists():
                shutil.copy2(staged, bak)
        shutil.copy2(zip_path, staged)
        print(f"Staged: {staged}")

    print(f"Built: {zip_path} ({zip_path.stat().st_size} bytes)")
    return zip_path


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()

    out_root = loadouts_root(workspace)
    if args.stdin_config:
        config = config_from_stdin(workspace)
        loadout_dir = out_root / config["id"]
    elif args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        loadout_dir = out_root / config.get("id", args.loadout_id or "Loadout01")
    else:
        loadout_id = args.loadout_id or "Loadout01"
        loadout_dir = out_root / loadout_id
        config = json.loads((loadout_dir / "loadout_config.json").read_text(encoding="utf-8"))

    loadout_dir.mkdir(parents=True, exist_ok=True)
    zip_path = build_from_config(config, workspace, loadout_dir, stage=not args.no_stage)
    print(json.dumps({"zip": str(zip_path), "display_name": config["display_name"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
