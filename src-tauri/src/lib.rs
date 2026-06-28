use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tauri::{AppHandle, Manager};

const FALLBACK_WORKSPACE: &str = "/Users/Shared/CohenConcepts/Crimson Desert Mods";

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Settings {
    workspace: String,
}

fn settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().app_config_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join("settings.json"))
}

fn is_workspace(path: &Path) -> bool {
    if !path.is_dir() {
        return false;
    }
    let has_mod_folders = path.join("Helms").is_dir()
        || path.join("1H").is_dir()
        || path.join("Lanterns").is_dir();
    has_mod_folders && path.join("CohenConcepts_Loadouts").is_dir()
}

fn walk_parents(start: &Path, max_depth: usize) -> Option<PathBuf> {
    let mut current = Some(start);
    for _ in 0..max_depth {
        let path = current?;
        if is_workspace(path) {
            return Some(path.to_path_buf());
        }
        current = path.parent();
    }
    None
}

fn discover_workspace(app: &AppHandle) -> Option<PathBuf> {
    if let Ok(exe) = std::env::current_exe() {
        if let Some(found) = walk_parents(exe.parent().unwrap_or(&exe), 12) {
            return Some(found);
        }
    }
    if let Ok(resource) = app.path().resource_dir() {
        if let Some(found) = walk_parents(&resource, 12) {
            return Some(found);
        }
    }
    let fallback = PathBuf::from(FALLBACK_WORKSPACE);
    if is_workspace(&fallback) {
        return Some(fallback);
    }
    None
}

fn load_settings(app: &AppHandle) -> Settings {
    if let Ok(path) = settings_path(app) {
        if let Ok(text) = fs::read_to_string(&path) {
            if let Ok(settings) = serde_json::from_str::<Settings>(&text) {
                if is_workspace(Path::new(&settings.workspace)) {
                    return settings;
                }
            }
        }
    }
    if let Some(found) = discover_workspace(app) {
        return Settings {
            workspace: found.to_string_lossy().into_owned(),
        };
    }
    Settings {
        workspace: FALLBACK_WORKSPACE.to_string(),
    }
}

fn save_settings(app: &AppHandle, settings: &Settings) -> Result<(), String> {
    let path = settings_path(app)?;
    let text = serde_json::to_string_pretty(settings).map_err(|e| e.to_string())?;
    fs::write(path, text + "\n").map_err(|e| e.to_string())
}

fn bundled_scripts_dir(app: &AppHandle) -> Option<PathBuf> {
    let resource = app.path().resource_dir().ok()?;
    for scripts in [resource.join("scripts"), resource.join("resources/scripts")] {
        if scripts.join("mod_registry.py").is_file() {
            return Some(scripts);
        }
    }
    None
}

fn sync_owned_gear_script(app: &AppHandle, workspace: &Path) -> Result<PathBuf, String> {
    let workspace_script = workspace.join("shared_tools/sync_owned_gear.py");
    if workspace_script.is_file() {
        return Ok(workspace_script);
    }
    if let Some(bundled) = bundled_scripts_dir(app) {
        let script = bundled.join("sync_owned_gear.py");
        if script.is_file() {
            return Ok(script);
        }
    }
    Err("Missing sync_owned_gear.py (workspace shared_tools/ or bundled scripts)".to_string())
}

fn sync_workspace_script(app: &AppHandle, workspace: &Path) -> Result<PathBuf, String> {
    let workspace_script = workspace.join("shared_tools/sync_workspace.py");
    if workspace_script.is_file() {
        return Ok(workspace_script);
    }
    if let Some(bundled) = bundled_scripts_dir(app) {
        let script = bundled.join("sync_workspace.py");
        if script.is_file() {
            return Ok(script);
        }
    }
    let fallback = workspace.join("shared_tools/mod_registry.py");
    if fallback.is_file() {
        return Ok(fallback);
    }
    if let Some(bundled) = bundled_scripts_dir(app) {
        let script = bundled.join("mod_registry.py");
        if script.is_file() {
            return Ok(script);
        }
    }
    Err("Missing sync_workspace.py (workspace shared_tools/ or bundled scripts)".to_string())
}

fn mod_registry_script(app: &AppHandle, workspace: &Path) -> Result<PathBuf, String> {
    let workspace_script = workspace.join("shared_tools/mod_registry.py");
    if workspace_script.is_file() {
        return Ok(workspace_script);
    }
    if let Some(bundled) = bundled_scripts_dir(app) {
        let script = bundled.join("mod_registry.py");
        if script.is_file() {
            return Ok(script);
        }
    }
    Err("Missing mod_registry.py (workspace shared_tools/ or bundled scripts)".to_string())
}

fn build_loadout_script(app: &AppHandle, workspace: &Path) -> Result<PathBuf, String> {
    let workspace_script = workspace.join("CohenConcepts_Loadouts/tools/build_loadout.py");
    if workspace_script.is_file() {
        return Ok(workspace_script);
    }
    if let Some(bundled) = bundled_scripts_dir(app) {
        let script = bundled.join("build_loadout.py");
        if script.is_file() {
            return Ok(script);
        }
    }
    Err("Missing build_loadout.py (workspace CohenConcepts_Loadouts/tools/ or bundled scripts)".to_string())
}

fn build_mod_maker_script(app: &AppHandle, workspace: &Path) -> Result<PathBuf, String> {
    let workspace_script = workspace.join("shared_tools/build_mod_maker.py");
    if workspace_script.is_file() { return Ok(workspace_script); }
    if let Some(bundled) = bundled_scripts_dir(app) {
        let script = bundled.join("build_mod_maker.py");
        if script.is_file() { return Ok(script); }
    }
    Err("Missing build_mod_maker.py".to_string())
}

fn scripts_env(_app: &AppHandle, workspace: &Path) -> Option<String> {
    let shared = workspace.join("shared_tools");
    if shared.join("mod_registry.py").is_file() {
        return Some(shared.to_string_lossy().into_owned());
    }
    None
}

fn python_bin(workspace: &Path) -> PathBuf {
    for name in ["python3.14", "python3.13", "python3.12", "python3"] {
        let venv = workspace.join("GEOMOD/.venv/bin").join(name);
        if venv.is_file() {
            return venv;
        }
    }
    for fallback in ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"] {
        let p = PathBuf::from(fallback);
        if p.is_file() {
            return p;
        }
    }
    PathBuf::from("python3")
}

fn python_command(
    app: &AppHandle,
    workspace: &Path,
    script: &Path,
) -> Result<Command, String> {
    let mut cmd = Command::new(python_bin(workspace));
    cmd.arg(script);
    if let Some(scripts) = scripts_env(app, workspace) {
        cmd.env("LOADOUTFORGE_SCRIPTS", scripts);
    }
    Ok(cmd)
}

#[tauri::command]
fn get_settings(app: AppHandle) -> Result<Settings, String> {
    Ok(load_settings(&app))
}

#[tauri::command]
fn set_workspace(app: AppHandle, workspace: String) -> Result<Settings, String> {
    if !is_workspace(Path::new(&workspace)) {
        return Err(format!(
            "Not a valid mods workspace (need category folders + CohenConcepts_Loadouts): {workspace}"
        ));
    }
    let settings = Settings { workspace };
    save_settings(&app, &settings)?;
    Ok(settings)
}

#[tauri::command]
async fn pick_workspace(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let settings = load_settings(&app);
    let picked = app
        .dialog()
        .file()
        .set_title("Choose Crimson Desert Mods workspace")
        .set_directory(settings.workspace)
        .blocking_pick_folder();
    Ok(picked.map(|p| p.to_string()))
}

#[tauri::command]
fn scan_mods(app: AppHandle, workspace: Option<String>, full: Option<bool>) -> Result<String, String> {
    let settings = workspace
        .map(|w| Settings { workspace: w })
        .unwrap_or_else(|| load_settings(&app));
    let root = Path::new(&settings.workspace);
    if !is_workspace(root) {
        return Err(format!(
            "Workspace not found or invalid: {}\nUse Workspace… to pick your Crimson Desert Mods folder.",
            settings.workspace
        ));
    }

    let script = sync_workspace_script(&app, root)?;
    let registry_path = root.join("CohenConcepts_Loadouts/mod_registry.json");
    fs::create_dir_all(registry_path.parent().unwrap()).map_err(|e| e.to_string())?;

    let mut cmd = python_command(&app, root, &script)?;
    cmd.arg("--workspace")
        .arg(root)
        .arg("--out")
        .arg(&registry_path);
    if full.unwrap_or(false) {
        cmd.arg("--update-stale").arg("--skip-previews");
    }
    let output = cmd
        .output()
        .map_err(|e| format!("Failed to run Python (is python3 installed?): {e}"))?;

    if !output.status.success() {
        return Err(format!(
            "scan_mods failed:\n{}\n{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        ));
    }

    fs::read_to_string(registry_path).map_err(|e| e.to_string())
}

#[tauri::command]
fn build_loadout(
    app: AppHandle,
    workspace: Option<String>,
    payload: String,
    stage_to_cdumm: Option<bool>,
) -> Result<String, String> {
    let settings = workspace
        .map(|w| Settings { workspace: w })
        .unwrap_or_else(|| load_settings(&app));
    let root = Path::new(&settings.workspace);
    if !is_workspace(root) {
        return Err(format!("Workspace not found or invalid: {}", settings.workspace));
    }

    let script = build_loadout_script(&app, root)?;
    let mut cmd = python_command(&app, root, &script)?;
    cmd.arg("--stdin-config")
        .arg("--workspace")
        .arg(root);
    if !stage_to_cdumm.unwrap_or(true) {
        cmd.arg("--no-stage");
    }

    let mut child = cmd
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to run Python: {e}"))?;

    child
        .stdin
        .take()
        .ok_or_else(|| "Failed to open stdin".to_string())?
        .write_all(payload.as_bytes())
        .map_err(|e| e.to_string())?;

    let output = child.wait_with_output().map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        return Err(format!("build_loadout failed:\n{stdout}\n{stderr}"));
    }

    Ok(stdout)
}

#[tauri::command]
fn sync_owned_gear(app: AppHandle, workspace: Option<String>) -> Result<String, String> {
    let settings = workspace
        .map(|w| Settings { workspace: w })
        .unwrap_or_else(|| load_settings(&app));
    let root = Path::new(&settings.workspace);
    if !is_workspace(root) {
        return Err(format!("Workspace not found or invalid: {}", settings.workspace));
    }

    let script = sync_owned_gear_script(&app, root)?;
    let output = python_command(&app, root, &script)?
        .output()
        .map_err(|e| format!("Failed to run Python: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    if !output.status.success() {
        return Err(format!("sync_owned_gear failed:\n{stdout}\n{stderr}"));
    }

    let mut lines = stdout.trim().to_string();
    if !stderr.trim().is_empty() {
        if !lines.is_empty() {
            lines.push('\n');
        }
        lines.push_str(stderr.trim());
    }
    Ok(lines)
}

#[tauri::command]
fn build_mod_maker(app: AppHandle, workspace: Option<String>, payload: String) -> Result<String, String> {
    let settings = workspace.map(|w| Settings { workspace: w }).unwrap_or_else(|| load_settings(&app));
    let root = Path::new(&settings.workspace);
    let script = build_mod_maker_script(&app, root)?;
    let mut child = python_command(&app, root, &script)?.arg("--stdin-config").arg("--workspace").arg(root)
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().map_err(|e| e.to_string())?;
    child.stdin.take().ok_or_else(|| "Failed to open stdin".to_string())?.write_all(payload.as_bytes()).map_err(|e| e.to_string())?;
    let output = child.wait_with_output().map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    if !output.status.success() { return Err(format!("build_mod_maker failed:\n{stdout}\n{}", String::from_utf8_lossy(&output.stderr))); }
    Ok(stdout)
}

#[tauri::command]
fn read_glb_bytes(path: String) -> Result<Vec<u8>, String> {
    let file = Path::new(&path);
    if !file.is_file() {
        return Err(format!("GLB not found: {path}"));
    }
    let meta = fs::metadata(file).map_err(|e| e.to_string())?;
    if meta.len() > 80 * 1024 * 1024 {
        return Err(format!("GLB too large for viewer (>80MB): {path}"));
    }
    fs::read(file).map_err(|e| e.to_string())
}

#[tauri::command]
fn read_preview_image(path: String) -> Result<String, String> {
    let data = fs::read(&path).map_err(|e| e.to_string())?;
    let encoded = base64::Engine::encode(&base64::engine::general_purpose::STANDARD, data);
    Ok(format!("data:image/png;base64,{encoded}"))
}

#[tauri::command]
fn reveal_in_finder(path: String) -> Result<(), String> {
    Command::new("open")
        .arg("-R")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_settings,
            set_workspace,
            pick_workspace,
            scan_mods,
            sync_owned_gear,
            build_loadout,
            build_mod_maker,
            read_preview_image,
            read_glb_bytes,
            reveal_in_finder
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
