"""Auto-detect ComfyUI and Forge Neo installations, then link their model
folders so both apps share the same files without duplication."""

from __future__ import annotations

import argparse
import concurrent.futures
import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FOLDER_MAP: dict[str, str] = {
    # comfyui models/ subfolder  ->  forge neo models/ subfolder
    "checkpoints":    "Stable-diffusion",
    "vae":            "VAE",
    "loras":          "Lora",
    "controlnet":     "ControlNet",
    "upscale_models": "ESRGAN",
    "embeddings":     "embeddings",
    "clip":           "text_encoder",
    "unet":           "unet",
    "hypernetworks":  "hypernetworks",
}

COMFYUI_DIR_NAMES = {"comfyui", "ComfyUI"}
FORGE_DIR_NAMES = {
    "sd-webui-forge-neo", "sd-webui-forge-classic",
    "stable-diffusion-webui-forge", "forge-neo",
}

SKIP_DIRS = frozenset({
    "Windows", "Program Files", "Program Files (x86)", "$Recycle.Bin",
    "System Volume Information", "System32", "node_modules", ".git",
    "Recovery", "PerfLogs", "ProgramData",
})

MAX_DEPTH = 4

ENV_VARS_COMFYUI = ("COMFYUI_PATH",)
ENV_VARS_FORGE = ("FORGE_PATH", "SD_WEBUI_PATH")
ENV_VARS_LAUNCHERS = ("PINOKIO_HOME", "STABILITY_MATRIX_PATH")

# ---------------------------------------------------------------------------
# Markers — how we confirm a directory is actually the right app
# ---------------------------------------------------------------------------

def is_comfyui(path: Path) -> bool:
    return (path / "models").is_dir() and (
        (path / "main.py").is_file()
        or (path / "comfy").is_dir()
        or (path / "models" / "checkpoints").is_dir()
    )


def is_forge_neo(path: Path) -> bool:
    return (path / "webui.bat").is_file() or (path / "webui.sh").is_file()

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _log(tag: str, msg: str) -> None:
    print(f"  {tag:4s} {msg}")


def _header(title: str) -> None:
    print(f"\n{title}")

# ---------------------------------------------------------------------------
# Layer 1 — Registry & environment variables
# ---------------------------------------------------------------------------

def _scan_registry() -> tuple[list[Path], list[Path]]:
    """Return (comfyui_candidates, forge_candidates) from the Windows registry."""
    comfy: list[Path] = []
    forge: list[Path] = []
    if os.name != "nt":
        return comfy, forge
    try:
        import winreg
    except ImportError:
        return comfy, forge

    def _search_uninstall(hive: int) -> None:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        try:
            with winreg.OpenKey(hive, key_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        i += 1
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(key, subkey_name) as sk:
                            name, _ = winreg.QueryValueEx(sk, "DisplayName")
                            loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                            name_lower = str(name).lower()
                            p = Path(str(loc))
                            if "comfyui" in name_lower and is_comfyui(p):
                                comfy.append(p.resolve())
                            if "forge" in name_lower and is_forge_neo(p):
                                forge.append(p.resolve())
                    except OSError:
                        continue
        except OSError:
            pass

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            _search_uninstall(hive)
        except OSError:
            pass

    return comfy, forge


def _scan_env_vars() -> tuple[list[Path], list[Path]]:
    comfy: list[Path] = []
    forge: list[Path] = []

    for var in ENV_VARS_COMFYUI:
        val = os.environ.get(var)
        if val:
            p = Path(val)
            if is_comfyui(p):
                comfy.append(p.resolve())

    for var in ENV_VARS_FORGE:
        val = os.environ.get(var)
        if val:
            p = Path(val)
            if is_forge_neo(p):
                forge.append(p.resolve())

    for var in ENV_VARS_LAUNCHERS:
        val = os.environ.get(var)
        if val:
            p = Path(val)
            if p.is_dir():
                for child in _safe_scandir(p):
                    if child.is_dir(follow_symlinks=False):
                        cp = Path(child.path)
                        if is_comfyui(cp):
                            comfy.append(cp.resolve())
                        if is_forge_neo(cp):
                            forge.append(cp.resolve())

    return comfy, forge

# ---------------------------------------------------------------------------
# Layer 2 — Launcher config files
# ---------------------------------------------------------------------------

def _safe_scandir(path: Path) -> list[os.DirEntry[str]]:
    try:
        return list(os.scandir(path))
    except (PermissionError, OSError):
        return []


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _check_children(base: Path, comfy: list[Path], forge: list[Path]) -> None:
    """Scan immediate children of *base* for ComfyUI / Forge markers."""
    for entry in _safe_scandir(base):
        if not entry.is_dir(follow_symlinks=False):
            continue
        p = Path(entry.path)
        # Some launchers nest the actual app one level deeper in app/
        for candidate in (p, p / "app"):
            if candidate.is_dir():
                if is_comfyui(candidate):
                    comfy.append(candidate.resolve())
                if is_forge_neo(candidate):
                    forge.append(candidate.resolve())


def _scan_pinokio() -> tuple[list[Path], list[Path]]:
    comfy: list[Path] = []
    forge: list[Path] = []
    home = Path.home()

    # Pinokio stores its base dir in config.json
    config_path = home / "pinokio" / "config.json"
    cfg = _read_json(config_path)
    if cfg and isinstance(cfg.get("base"), str):
        api_dir = Path(cfg["base"]) / "api"
    else:
        api_dir = home / "pinokio" / "api"

    if api_dir.is_dir():
        _check_children(api_dir, comfy, forge)

    return comfy, forge


def _scan_stability_matrix() -> tuple[list[Path], list[Path]]:
    comfy: list[Path] = []
    forge: list[Path] = []

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")

    settings = Path(appdata) / "StabilityMatrix" / "settings.json"
    cfg = _read_json(settings)

    data_dir: Path | None = None
    if cfg:
        for key in ("LibraryDir", "DataDirectory", "library_dir"):
            val = cfg.get(key)
            if val and isinstance(val, str):
                data_dir = Path(val)
                break

    if data_dir is None:
        data_dir = Path(appdata) / "StabilityMatrix"

    packages = data_dir / "Packages"
    if packages.is_dir():
        _check_children(packages, comfy, forge)

    return comfy, forge


def _scan_invokeai() -> tuple[list[Path], list[Path]]:
    """InvokeAI is not ComfyUI or Forge, but its config may point to shared
    model directories we could use.  For now just note its presence."""
    # Not directly useful — included for completeness per spec.
    return [], []


def _scan_launcher_configs() -> tuple[list[Path], list[Path]]:
    c1, f1 = _scan_pinokio()
    c2, f2 = _scan_stability_matrix()
    c3, f3 = _scan_invokeai()
    return c1 + c2 + c3, f1 + f2 + f3

# ---------------------------------------------------------------------------
# Layer 3 — Fast filesystem scan
# ---------------------------------------------------------------------------

def _scan_dir_recursive(
    root: Path,
    comfy_results: list[Path],
    forge_results: list[Path],
    depth: int = 0,
) -> None:
    if depth > MAX_DEPTH:
        return
    for entry in _safe_scandir(root):
        if not entry.is_dir(follow_symlinks=False):
            continue
        name = entry.name
        if name in SKIP_DIRS or name.startswith("."):
            continue
        p = Path(entry.path)
        matched = False
        if name in COMFYUI_DIR_NAMES or name.lower() == "comfyui":
            # Also check app/ subfolder (Pinokio layout)
            for candidate in (p, p / "app"):
                if is_comfyui(candidate):
                    comfy_results.append(candidate.resolve())
                    matched = True
                    break
        if name in FORGE_DIR_NAMES or name.lower() in {n.lower() for n in FORGE_DIR_NAMES}:
            for candidate in (p, p / "app"):
                if is_forge_neo(candidate):
                    forge_results.append(candidate.resolve())
                    matched = True
                    break
        if not matched:
            _scan_dir_recursive(p, comfy_results, forge_results, depth + 1)


def _scan_drive(drive: Path) -> tuple[list[Path], list[Path]]:
    comfy: list[Path] = []
    forge: list[Path] = []
    _scan_dir_recursive(drive, comfy, forge)
    return comfy, forge


def _scan_filesystem() -> tuple[list[Path], list[Path]]:
    drives: list[Path] = []
    if os.name == "nt":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            d = Path(f"{letter}:\\")
            if d.exists():
                drives.append(d)
    else:
        for p in (Path("/home"), Path("/opt"), Path("/mnt")):
            if p.is_dir():
                drives.append(p)

    if not drives:
        return [], []

    comfy_all: list[Path] = []
    forge_all: list[Path] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(drives), 8)
    ) as pool:
        futures = {pool.submit(_scan_drive, d): d for d in drives}
        for future in concurrent.futures.as_completed(futures):
            try:
                c, f = future.result()
                comfy_all.extend(c)
                forge_all.extend(f)
            except Exception:
                pass

    return comfy_all, forge_all

# ---------------------------------------------------------------------------
# Layer 4 — Manual input fallback
# ---------------------------------------------------------------------------

def _ask_path(app_name: str, validator) -> Path | None:
    for _ in range(3):
        raw = input(f"  Enter path to {app_name} (or press Enter to skip): ").strip()
        if not raw:
            return None
        p = Path(raw)
        # Also try app/ subfolder
        for candidate in (p, p / "app"):
            if candidate.is_dir() and validator(candidate):
                return candidate.resolve()
        print(f"  FAIL Could not verify {app_name} at that path.")
    return None

# ---------------------------------------------------------------------------
# Layer 5 — Multi-pick
# ---------------------------------------------------------------------------

def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        r = p.resolve()
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _pick(candidates: list[Path], app_name: str) -> Path | None:
    candidates = _dedupe(candidates)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    print(f"\n  Multiple {app_name} installations found:")
    for i, c in enumerate(candidates, 1):
        print(f"    [{i}] {c}")
    choice = input(f"  Select [1-{len(candidates)}]: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]
    return candidates[0]

# ---------------------------------------------------------------------------
# Detection orchestrator
# ---------------------------------------------------------------------------

def detect_forge_neo() -> Path | None:
    """Try to find Forge Neo relative to this script's location."""
    script_dir = Path(__file__).resolve().parent
    for candidate in (script_dir / "app", script_dir):
        if is_forge_neo(candidate):
            return candidate
    cwd = Path.cwd()
    for candidate in (cwd / "app", cwd):
        if is_forge_neo(candidate):
            return candidate
    return None


def detect_installations(
    skip_scan: bool = False,
) -> tuple[Path | None, Path | None]:
    """Run detection layers and return (comfyui_path, forge_path)."""
    comfy_all: list[Path] = []
    forge_all: list[Path] = []

    # Forge Neo: try local detection first
    local_forge = detect_forge_neo()
    if local_forge:
        forge_all.append(local_forge)

    # Layer 1
    c, f = _scan_registry()
    comfy_all.extend(c)
    forge_all.extend(f)

    c, f = _scan_env_vars()
    comfy_all.extend(c)
    forge_all.extend(f)

    # Layer 2
    c, f = _scan_launcher_configs()
    comfy_all.extend(c)
    forge_all.extend(f)

    # Layer 3 — only if we still need something
    if (not comfy_all or not forge_all) and not skip_scan:
        print("  Scanning drives...")
        c, f = _scan_filesystem()
        comfy_all.extend(c)
        forge_all.extend(f)

    # Layer 5 — pick if multiple
    comfyui = _pick(comfy_all, "ComfyUI")
    forge = _pick(forge_all, "Forge Neo")

    # Layer 4 — manual fallback
    if comfyui is None:
        print("\n  Could not auto-detect ComfyUI.")
        comfyui = _ask_path("ComfyUI", is_comfyui)
    if forge is None:
        print("\n  Could not auto-detect Forge Neo.")
        forge = _ask_path("Forge Neo", is_forge_neo)

    return comfyui, forge

# ---------------------------------------------------------------------------
# YAML writer
# ---------------------------------------------------------------------------

def build_yaml(comfyui_root: Path) -> tuple[str, list[tuple[str, str, bool]]]:
    """Build extra_model_paths.yaml content. Returns (yaml_text, mapping_log)
    where mapping_log is [(comfy_name, forge_name, exists)]."""
    base = PurePosixPath(comfyui_root.as_posix())
    lines = [
        "# Auto-generated by forge_neo_link_comfyui.py",
        "",
        "comfyui:",
        f"  base_path: {base}/",
    ]
    mapping_log: list[tuple[str, str, bool]] = []

    for comfy_folder, forge_name in FOLDER_MAP.items():
        rel = f"models/{comfy_folder}"
        exists = (comfyui_root / rel).is_dir()
        mapping_log.append((comfy_folder, forge_name, exists))
        if exists:
            lines.append(f"  {forge_name}: {rel}")

    lines.append("")
    return "\n".join(lines), mapping_log


def write_yaml(
    forge_root: Path,
    comfyui_root: Path,
    dry_run: bool,
) -> Path:
    yaml_text, mapping_log = build_yaml(comfyui_root)

    _header("Linking model folders:")
    for comfy_name, forge_name, exists in mapping_log:
        if exists:
            _log("OK", f"{comfy_name:<16s} -> {forge_name}")
        else:
            _log("SKIP", f"{comfy_name:<16s} -- not found")

    dest = forge_root / "extra_model_paths.yaml"

    if dry_run:
        print(f"\n  (dry run) Would write {dest}")
        print(f"\n{yaml_text}")
    else:
        dest.write_text(yaml_text, encoding="utf-8")
        print(f"\nWrote {dest}")

    return dest

# ---------------------------------------------------------------------------
# Junction symlinks (--symlinks)
# ---------------------------------------------------------------------------

def _is_admin() -> bool:
    if os.name != "nt":
        return os.getuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def create_junctions(
    forge_root: Path,
    comfyui_root: Path,
    dry_run: bool,
) -> None:
    if not _is_admin():
        print("\n  WARN Not running as Administrator — junctions may fail.")
        print("       Right-click your terminal and choose 'Run as administrator'.\n")

    models = forge_root / "models"
    if not models.is_dir():
        models.mkdir(parents=True, exist_ok=True)

    _header("Creating junction links:")
    for comfy_folder, forge_name in FOLDER_MAP.items():
        source = comfyui_root / "models" / comfy_folder
        dest = models / forge_name

        if not source.is_dir():
            _log("SKIP", f"{forge_name:<16s} -- source not found")
            continue
        if dest.exists():
            _log("SKIP", f"{forge_name:<16s} -- already exists")
            continue

        if dry_run:
            _log("OK", f"{forge_name:<16s} -> {source}  (dry run)")
            continue

        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(dest), str(source)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                _log("OK", f"{forge_name:<16s} -> {source}")
            else:
                _log("FAIL", f"{forge_name:<16s} -- {result.stderr.strip()}")
        else:
            try:
                os.symlink(source, dest)
                _log("OK", f"{forge_name:<16s} -> {source}")
            except OSError as exc:
                _log("FAIL", f"{forge_name:<16s} -- {exc}")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Link ComfyUI model folders into Forge Neo.",
    )
    parser.add_argument(
        "--symlinks", action="store_true",
        help="Create junction links (mklink /J) instead of YAML-only linking",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be done without writing anything",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run even if extra_model_paths.yaml already exists",
    )
    args = parser.parse_args()

    # First-run guard: if already configured, exit silently
    forge_quick = detect_forge_neo()
    if forge_quick and not args.force and not args.dry_run:
        yaml_path = forge_quick / "extra_model_paths.yaml"
        if yaml_path.is_file():
            try:
                content = yaml_path.read_text(encoding="utf-8")
                if "comfyui:" in content:
                    return  # already set up — silent exit
            except OSError:
                pass

    try:
        print("Detecting installations...")
        comfyui, forge = detect_installations()

        if comfyui is None:
            print("\n  Could not find ComfyUI. Exiting.")
            sys.exit(1)
        if forge is None:
            print("\n  Could not find Forge Neo. Exiting.")
            sys.exit(1)

        _log("", f"ComfyUI:   {comfyui}")
        _log("", f"Forge Neo: {forge}")

        write_yaml(forge, comfyui, args.dry_run)

        if args.symlinks:
            create_junctions(forge, comfyui, args.dry_run)

        if not args.dry_run:
            print("\nRestart Forge Neo to load ComfyUI models.")
            print("\nTo auto-run on every launch, add this line to webui-user.bat")
            print("(before \"call webui.bat\"):\n")
            print("  python forge_neo_link_comfyui.py")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(130)


if __name__ == "__main__":
    main()
