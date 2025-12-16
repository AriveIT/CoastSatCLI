# Gooey Icon Overrides

Place custom icons in this folder to brand the GUI. Gooey will use any of these files when present; missing files fall back to defaults.

Recommended filenames and roles:
- `program_icon.png` (or `.ico` on Windows): App/window icon shown in the title bar and task switcher.
- `config_icon.png`: Icon for the settings/config button in the toolbar.
- `start.png`: Start/run button.
- `stop.png`: Stop/cancel button.
- `success.png`: Success state indicator.
- `error.png`: Error/failure indicator.
- `refresh.png`: Refresh/reload button.
- `spinner.png`: Busy/progress indicator.

Tips:
- Use 256x256 (or larger) transparent PNGs; Gooey downscales as needed. On Windows, you can supply `program_icon.ico`.
- Keep filenames exact (lowercase) so Gooey picks them up automatically.
- You can reuse the same artwork for multiple roles (e.g., copy `program_icon.png` to `config_icon.png`) if you don’t have separate assets yet.
