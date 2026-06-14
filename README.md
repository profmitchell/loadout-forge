# LoadoutForge

Mac desktop app (Tauri + Next.js) for mixing Cohen Concepts Crimson Desert mesh mods into **CDUMM loadout zips**.

## Why loadouts?

CDUMM `mesh_loose_mod` replacers conflict if multiple are applied for different items at once. A **loadout zip** bundles bow + lantern + sword + cannon (and helm) into **one** mod so a single Apply enables everything.

## Run (dev)

```bash
cd loadout-forge
npm run tauri:dev
```

## Build standalone `.app`

```bash
cd loadout-forge
npm run tauri:build
```

Output: `src-tauri/target/release/bundle/macos/LoadoutForge.app`

The `.app` **bundles** `mod_registry.py` and `build_loadout.py` — you do **not** need `shared_tools/` on disk for scan/export. You still point the app at your **mods workspace** (category folders + `CohenConcepts_Loadouts/`).

**First launch:** if auto-detect fails, click **Workspace…** and pick your `Crimson Desert Mods` folder (native folder picker).

**System Python** (`/opt/homebrew/bin/python3`) is enough; `GEOMOD/.venv` is optional.

## Naming

Exported loadouts use:

- **CDUMM title:** `Cohen Concepts > Loadout 04 - Crescent-Obsidian-Lance-Void-Concrete`
- **Zip:** `CohenConcepts_Loadout04_Crescent-Obsidian-Lance-Void-Concrete_CDUMM.zip`

Abbreviations are defined in `shared_tools/mod_registry.py` (`ABBR_OVERRIDES`).

## Workspace

Default workspace: `/Users/Shared/CohenConcepts/Crimson Desert Mods`

Use **Workspace…** in the app to point at another clone. Settings persist in app config.

## Category folders (auto-discovered)

Drop any mod with `mod_config.json` under a category folder — **Rescan** picks it up:

| Folder | Slot |
|--------|------|
| `1H/` | swords |
| `Helms/` | helms |
| `Bows/` | bows |
| `Lanterns/` | lanterns |
| `Cannon Staffs/` | cannons |

New top-level folders appear automatically in the **Folders** sidebar.

## 3D viewer

- Cards **auto-load a spinning 3D preview** when scrolled into view (from each mod's `.glb`)
- **Double-click** a card preview → fullscreen lightbox with orbit + zoom
- **Esc** or click outside to close

## Requirements

**To run the built `.app`:** macOS + system `python3` + your mods workspace.

**To develop/rebuild:** Node 20+, Rust/Cargo, `npm install`.

Individual mods must be **built** (`tools/build_all.py`) before export.

## CLI (same backend)

```bash
echo '{"loadout_number":5,"mods":["Helms__WhiteObsidianStag","ObsidianBow","PRISMBLADE","Rhinard/LumenLance"]}' \
  | GEOMOD/.venv/bin/python3.14 CohenConcepts_Loadouts/tools/build_loadout.py --stdin-config
```

Mod IDs match `CohenConcepts_Loadouts/mod_registry.json` (`source_mod` with `/` → `__` for nested paths).
