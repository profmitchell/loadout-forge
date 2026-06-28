#!/usr/bin/env python3
"""Create a standalone CDUMM mod by remapping a built visual to a donor PAC."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

STAGING = Path.home() / "Library/Application Support/cdumm/CDMods/_import_staging"


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value) or "CustomMod"


def _lantern_swap_helpers(workspace: Path):
    sys.path.insert(0, str(workspace))
    from shared_tools.lantern_companion_hide import (
        hide_lantern_companions,
        is_lantern_companion_pac,
        is_lantern_main_pac,
    )

    return hide_lantern_companions, is_lantern_companion_pac, is_lantern_main_pac


def _lantern_main_pac(target_pacs: list[str], is_lantern_main_pac) -> str | None:
    for pac in target_pacs:
        if is_lantern_main_pac(pac):
            return pac
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--stdin-config", action="store_true")
    parser.add_argument("--no-stage", action="store_true")
    args = parser.parse_args()
    if not args.stdin_config:
        raise ValueError("Mod Maker requires --stdin-config")

    payload = json.loads(sys.stdin.read())
    donor_payload = payload.get("donor") if isinstance(payload.get("donor"), dict) else {}
    donor_name = str(donor_payload.get("name") or payload.get("donor_name") or "Donor")
    item_id = donor_payload.get("item_id") or payload.get("item_id")
    target_pacs = list(donor_payload.get("pacs") or payload.get("target_pacs") or [])
    if not target_pacs:
        raise ValueError("Mod Maker requires at least one target PAC")
    normalized_payload = {
        **payload,
        "donor_name": donor_name,
        "item_id": item_id,
        "target_pacs": target_pacs,
        "donor": {
            **donor_payload,
            "name": donor_name,
            "item_id": item_id,
            "pacs": target_pacs,
        },
    }
    workspace = args.workspace.resolve()
    source = workspace / payload["source_mod"]
    source_files = source / "files"
    if not source_files.is_dir():
        raise FileNotFoundError(f"Source mod is not built: {source}")

    source_pac = payload["source_pac"]
    source_main = next(source_files.rglob(source_pac), None)
    if not source_main:
        raise FileNotFoundError(f"Source PAC not found in built files: {source_pac}")

    title = payload.get("title") or f"{donor_name} > {payload['visual_name']}"
    mod_name = f"CohenConcepts_{slug(donor_name)}_{slug(payload['visual_name'])}"
    out_dir = workspace / "CustomItems" / "GeneratedMods" / mod_name
    files_dir = out_dir / "files"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    files_dir.mkdir(parents=True)

    source_character = source_main.parent
    hide_lantern_companions = is_lantern_companion_pac = is_lantern_main_pac = None
    lantern_main: str | None = None
    if source_pac.startswith("cd_t0000_lantern_"):
        hide_lantern_companions, is_lantern_companion_pac, is_lantern_main_pac = _lantern_swap_helpers(
            workspace
        )
        lantern_main = _lantern_main_pac(target_pacs, is_lantern_main_pac)

    for path in sorted(source_files.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store" or ".bak" in path.name:
            continue
        rel = path.relative_to(source_files)
        if lantern_main and is_lantern_companion_pac(path.name):
            continue
        if path.parent == source_character and (path.name == source_pac or path.name == source_pac + "_xml"):
            continue
        dest = files_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    for target in target_pacs:
        if lantern_main and is_lantern_companion_pac(target):
            continue
        dest = files_dir / source_main.relative_to(source_files).with_name(target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_main, dest)
        source_xml = source_main.with_name(source_main.name + "_xml")
        if source_xml.is_file():
            shutil.copy2(source_xml, dest.with_name(dest.name + "_xml"))

    if lantern_main and hide_lantern_companions is not None:
        dest_char = files_dir / "character"
        source_char = source / "files" / "character"
        forge_src = workspace / ".crimsonforge"
        forge_arg = str(forge_src) if forge_src.is_dir() else None
        from shared_tools.lantern_companion_hide import (
            lantern_companion_names,
            lantern_companions_are_hidden,
        )

        copied_from_source = False
        if source_pac == lantern_main and lantern_companions_are_hidden(source_char, lantern_main):
            for companion in lantern_companion_names(lantern_main):
                for rel in (companion, f"{companion}_xml"):
                    src = source_char / rel
                    if src.is_file():
                        shutil.copy2(src, dest_char / rel)
            copied_from_source = True
        if not copied_from_source:
            vanilla_dir = source / "backups" / "vanilla"
            hide_lantern_companions(
                dest_char,
                lantern_main,
                vanilla_dir=vanilla_dir if vanilla_dir.is_dir() else None,
                crimsonforge_src=forge_arg,
            )

    entries = []
    for path in sorted(files_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(files_dir).as_posix()
        fmt = "pac_xml" if rel.endswith(".pac_xml") else Path(rel).suffix.lstrip(".") or "file"
        entries.append({"path": rel, "format": fmt})

    description = payload.get("description") or f"Replaces {donor_name} with the {payload['visual_name']} visual."
    game_patch = payload.get("game_patch", "1.12.01")
    win_desc = (
        f"{description.rstrip('.')}. Built for Crimson Desert {game_patch} "
        f"- Windows and macOS (CDUMM mesh_loose_mod)."
    )
    metadata = {
        "title": title, "name": mod_name, "mod_name": mod_name, "author": "Mitchell",
        "version": payload.get("version", "1.0.1"), "game": "Crimson Desert", "format": "v1",
        "files_dir": "files", "description": win_desc, "game_patch": game_patch,
    }
    manifest = {**metadata, "kind": "mesh_loose_mod", "files": entries}
    modinfo = {**metadata, "type": "mesh_loose_mod", "generator": "Cohen Concepts Mod Maker"}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_dir / "modinfo.json").write_text(json.dumps(modinfo, indent=2) + "\n", encoding="utf-8")
    (out_dir / "mod_maker_config.json").write_text(json.dumps(normalized_payload, indent=2) + "\n", encoding="utf-8")
    warning = ""
    if lantern_main:
        warning = (
            "Lantern donor: only the main PAC gets the custom mesh. "
            "Belt sub01 and ring companions are hidden (no static duplicate).\n\n"
        )
    elif len(target_pacs) > 1:
        warning = "EXPERIMENTAL multi-part donor remap; verify both equipped and sheathed states.\n"
    (out_dir / "README.txt").write_text(
        f"{title}\n\n{warning}CDUMM install (Windows or macOS):\n"
        f"1. Disable other {donor_name} replacers.\n"
        f"2. Import {mod_name}_CDUMM.zip into CDUMM.\n"
        f"3. Enable the mod, apply, then restart the game.\n\n"
        f"Donor item ID: {item_id}\n"
        f"Game patch: {game_patch}\n",
        encoding="utf-8",
    )

    zip_path = out_dir / f"{mod_name}_CDUMM.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("README.txt", "manifest.json", "modinfo.json", "mod_maker_config.json"):
            archive.write(out_dir / name, name)
        for path in sorted(files_dir.rglob("*")):
            if path.is_file() and ".bak" not in path.name:
                archive.write(path, path.relative_to(out_dir).as_posix())
    if not args.no_stage:
        STAGING.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, STAGING / zip_path.name)
    print(f"Built: {zip_path}")

    try:
        export_script = workspace / "shared_tools/export_nexus_bundle.py"
        if export_script.is_file():
            subprocess.run(
                [sys.executable, str(export_script), "--mod", str(out_dir.relative_to(workspace)), "--workspace", str(workspace)],
                check=False,
                cwd=workspace,
            )
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
