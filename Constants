"""
constants.py
────────────
All shared constants: version info, file paths, colour palette,
and cross-platform font selection.

Nothing in here has side-effects — safe to import anywhere.
"""

import os
import platform

# ── Version ───────────────────────────────────────────────────────────────────
VERSION      = "1.0.0"
VERSION_DATE = "2026-04-24"
APP_NAME     = "Agilent ICP Cleaner"

# ── File paths  (all live next to the script) ─────────────────────────────────
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH   = os.path.join(_SCRIPT_DIR, "icp_cleaner_config.json")
ERROR_LOG     = os.path.join(_SCRIPT_DIR, "icp_cleaner_error.log")
CONV_LOG      = os.path.join(_SCRIPT_DIR, "icp_cleaner_conversions.json")

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":           "#1E2535",
    "panel":        "#252D40",
    "card":         "#2D3650",
    "accent":       "#4A9EFF",
    "accent_dark":  "#2A6ECC",
    "green":        "#2ECC71",
    "green_dark":   "#27AE60",
    "danger":       "#E74C3C",
    "amber":        "#F39C12",
    "text":         "#E8ECF0",
    "muted":        "#8892A0",
    "border":       "#3D4860",
    "white":        "#FFFFFF",
    "badge_green":  "#1A5C3A",
    "badge_blue":   "#1A3A5C",
    "badge_amber":  "#5C3D1A",
    "sidebar":      "#161D2E",
    "sidebar_sel":  "#2A3550",
    "log_bg":       "#0D1117",
    "log_fg":       "#58D68D",
    "success_bg":   "#1A3A2A",
}

# ── Cross-platform font selection ─────────────────────────────────────────────
# Windows → Segoe UI  |  Mac → SF Pro Display  |  Linux → DejaVu Sans
_OS = platform.system()   # "Windows" | "Darwin" | "Linux"

def _pick_font(size=10, bold=False):
    weight = "bold" if bold else "normal"
    if _OS == "Windows":
        family = "Segoe UI"
    elif _OS == "Darwin":
        family = "SF Pro Display"
    else:
        family = "DejaVu Sans"
    return (family, size, weight)

F_NORMAL = _pick_font(10)
F_BOLD   = _pick_font(10, bold=True)
F_LARGE  = _pick_font(13, bold=True)
F_SMALL  = _pick_font(8)
F_MONO   = ("Courier New" if _OS == "Windows" else "Courier", 9, "normal")

# ── Required data columns ─────────────────────────────────────────────────────
REQUIRED_COLS = {"Label", "Element", "Concentration", "Type"}

# ── Default config values ─────────────────────────────────────────────────────
CFG_DEFAULTS = {
    "dup_handling":   "average",
    "uncal_handling": "keep_text",
    "target_unit":    "ppm (mg/L)",
    "col_style":      "symbol_wavelength",
    "flag_negatives": True,
    "cal_sheet":      True,
    "cal_pdf":        True,
    "cal_pdf_r2":     True,
    "cal_pdf_table":  True,
    "last_dir":       "",
    "first_run":      True,
}
