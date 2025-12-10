from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover
    tk = None
    ttk = None
    messagebox = None
    Image = None
    ImageTk = None


def load_quality_config(site_dir: str | Path) -> Dict[str, Any]:
    config, _ = _load_quality_config(Path(site_dir))
    return config


def maybe_select_ideal_scenes(
    site_dir: str | Path,
    scene_metrics: Dict[str, Any],
    enable_prompt: bool = False,
    jpg_dir: Path | None = None,
) -> None:
    """
    If enabled and no imagery quality config exists yet, prompt the user to select
    an ideal scene per satellite and persist the selections to imagery_quality.json.
    """
    site_path = Path(site_dir)
    config, config_path = _load_quality_config(site_path)
    if config:
        return
    if not enable_prompt:
        return
    if not scene_metrics:
        print("[Imagery] No scene metrics available for quality selection.")
        return

    selections = _prompt_for_ideal_scenes(scene_metrics, jpg_dir or (site_path / "jpg_files" / "preprocessed"))
    if not selections:
        print("[Imagery] No ideal scenes were selected; skipping quality config creation.")
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {"satellites": selections}
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"[Imagery] Saved ideal scene selections to {config_path}.")


def _prompt_for_ideal_scenes(scene_metrics: Dict[str, Any], jpg_dir: Path) -> Dict[str, Dict[str, Any]]:
    by_sat: Dict[str, List[Dict[str, Any]]] = {}
    for entry in scene_metrics.values():
        sat = entry.get("satellite") or "unknown"
        by_sat.setdefault(sat, []).append(entry)
    for entries in by_sat.values():
        entries.sort(key=lambda e: e.get("date") or "")

    selections: Dict[str, Dict[str, Any]] = {}
    for sat in sorted(by_sat.keys()):
        entries = by_sat[sat]
        viewer = _SceneSelector(sat, entries, jpg_dir)
        selected = viewer.show()
        if selected is None:
            continue
        selections[sat] = selected
    return selections


def _load_quality_config(site_path: Path) -> tuple[Dict[str, Any], Path]:
    config_path = site_path / "imagery_quality.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return data, config_path
    except FileNotFoundError:
        return {}, config_path


class _SceneSelector:
    def __init__(self, satellite: str, entries: List[Dict[str, Any]], jpg_dir: Path):
        self.satellite = satellite
        self.entries = [
            entry for entry in entries if (jpg_dir / f"{entry.get('date')}_{satellite}.jpg").exists()
        ]
        self.jpg_dir = jpg_dir
        self.index = 0
        self.selected: Optional[Dict[str, Any]] = None
        self.root: Optional[tk.Tk] = None
        self.image_label = None
        self.meta_label = None
        self.tolerance_var = None
        self.current_image = None

    def show(self) -> Optional[Dict[str, Any]]:
        if not self.entries:
            print(f"[Imagery] No preprocessed JPG entries for {self.satellite}; skipping.")
            return _console_select(self.satellite, self.entries)
        if tk is None or Image is None or ttk is None:
            print(f"[Imagery] GUI unavailable for {self.satellite}; falling back to console selection.")
            return _console_select(self.satellite, self.entries)
        self.root = tk.Tk()
        self.root.title(f"Select ideal scene — {self.satellite}")
        self.root.geometry("900x700")
        self._build_widgets()
        self._load_current()
        self.root.mainloop()
        return self.selected

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        self.image_label = ttk.Label(frame)
        self.image_label.pack(pady=10)

        self.meta_label = ttk.Label(frame, justify="left")
        self.meta_label.pack(pady=5)

        control = ttk.Frame(frame)
        control.pack(pady=10)
        ttk.Button(control, text="<< Prev", command=self._prev_scene).grid(row=0, column=0, padx=5)
        ttk.Button(control, text="Next >>", command=self._next_scene).grid(row=0, column=1, padx=5)

        tol_frame = ttk.Frame(frame)
        tol_frame.pack(pady=5)
        ttk.Label(tol_frame, text="Tolerance:").pack(side="left", padx=4)
        self.tolerance_var = tk.StringVar(value="0.10")
        ttk.Entry(tol_frame, textvariable=self.tolerance_var, width=8).pack(side="left")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="Select", command=self._select_scene).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Skip", command=self._skip).grid(row=0, column=1, padx=5)

    def _load_current(self) -> None:
        scene = self.entries[self.index]
        path = self.jpg_dir / f"{scene.get('date')}_{self.satellite}.jpg"
        if Image is not None:
            img = Image.open(path)
            img.thumbnail((850, 500))
            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image)
        self.image_label.config(text=path.name if Image is None else "")
        info = (
            f"Scene: {scene.get('scene_id')}\n"
            f"Date: {scene.get('date')}\n"
            f"Cloud cover: {scene.get('cloud_cover')}\n"
            f"Valid pixels: {scene.get('valid_pixels')}\n"
        )
        self.meta_label.config(text=info)

    def _next_scene(self) -> None:
        self.index = (self.index + 1) % len(self.entries)
        self._load_current()

    def _prev_scene(self) -> None:
        self.index = (self.index - 1) % len(self.entries)
        self._load_current()

    def _select_scene(self) -> None:
        scene = self.entries[self.index]
        try:
            tolerance = float(self.tolerance_var.get())
        except (TypeError, ValueError):
            tolerance = 0.10
        self.selected = {
            "scene_id": scene.get("scene_id"),
            "date": scene.get("date"),
            "land_fraction": scene.get("land_fraction"),
            "water_fraction": scene.get("water_fraction"),
            "valid_pixels": scene.get("valid_pixels"),
            "cloud_cover": scene.get("cloud_cover"),
            "base_tolerance": tolerance,
        }
        if self.root:
            self.root.destroy()

    def _skip(self) -> None:
        self.selected = None
        if self.root:
            self.root.destroy()


def _console_select(sat: str, entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not entries:
        return None
    print(f"\n[Imagery] Select ideal scene for satellite {sat}:")
    max_rows = min(10, len(entries))
    for idx in range(max_rows):
        scene = entries[idx]
        date = scene.get("date", "unknown")
        scene_id = scene.get("scene_id", "unknown")
        cloud = scene.get("cloud_cover")
        valid = scene.get("valid_pixels")
        print(f"  [{idx}] {date} | {scene_id} | cloud={cloud}")
        if isinstance(valid, int):
            print(f"       valid pixels: {valid}")
    if len(entries) > max_rows:
        print(f"  ... and {len(entries) - max_rows} more scenes")
    choice = input("  Enter scene # to select (or press Enter to skip): ").strip()
    if not choice:
        return None
    try:
        idx = int(choice)
    except ValueError:
        print("  Invalid selection; skipping.")
        return None
    if idx < 0 or idx >= len(entries):
        print("  Selection out of range; skipping.")
        return None
    tol_input = input("  Enter base tolerance (default 0.10): ").strip()
    try:
        tolerance = float(tol_input) if tol_input else 0.10
    except ValueError:
        tolerance = 0.10
    scene = entries[idx]
    return {
        "scene_id": scene.get("scene_id"),
        "date": scene.get("date"),
        "land_fraction": scene.get("land_fraction"),
        "water_fraction": scene.get("water_fraction"),
        "valid_pixels": scene.get("valid_pixels"),
        "cloud_cover": scene.get("cloud_cover"),
        "base_tolerance": tolerance,
    }
