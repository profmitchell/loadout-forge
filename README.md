# Loadout Forge

Mac desktop app (Tauri + Next.js) for mixing Cohen Concepts Crimson Desert mesh mods into **CDUMM loadout zips**.

Loadout Forge is an independent Cohen Concepts project. It exports packages compatible with [Crimson Desert Ultimate Mods Manager (CDUMM)](https://github.com/faisalkindi/CrimsonDesert-UltimateModsManager), created and maintained by Faisal Al Kindi (`faisalkindi`). It is not an official CDUMM build or replacement.

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

On Mitchell's development machine the app can auto-detect the Cohen Concepts workspace. Other users should click **Workspace...** and select a compatible mods workspace.

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

## Relationship to CDUMM

Loadout Forge does not include or modify CDUMM source code. It creates `mesh_loose_mod` archives that users can import into CDUMM. CDUMM remains a separate project with its own maintainers, releases, support channels, and license terms.

## Contributing

Issues and pull requests are welcome. Keep changes focused, do not commit generated `.app` bundles or private mod assets, and run these checks before opening a pull request:

```bash
npm run lint
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

## Credits

- Loadout Forge: Mitchell Cohen / Cohen Concepts
- CDUMM compatibility target: Faisal Al Kindi and the CDUMM contributors
- Built with Tauri, Next.js, React Three Fiber, and Three.js

## License

Loadout Forge is released under the [MIT License](LICENSE).
