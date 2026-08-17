"""
dialogs.py
──────────
All popup / modal dialog windows.

  OptionsDialog   — processing settings (scrollable, screen-safe)
  WelcomeDialog   — first-run intro screen
  HistoryDialog   — scrollable table of every past conversion
"""

import tkinter as tk
from tkinter import ttk

from constants import APP_NAME, VERSION, C, F_NORMAL, F_BOLD, F_LARGE, F_SMALL
from utils     import Tooltip, load_conversion_log


# ════════════════════════════════════════════════════════════════════════════
#  OPTIONS DIALOG
# ════════════════════════════════════════════════════════════════════════════

class OptionsDialog(tk.Toplevel):
    """
    Modal dialog that collects all processing preferences.

    Scrollable so it never clips on small screens (capped at 82% height).
    Pre-loads saved settings from the config so returning users
    don't have to re-select everything each time.
    """

    def __init__(self, parent, types_present: list,
                 rerun_labels: list, units_in_file: set, cfg: dict):
        super().__init__(parent)
        self.title(f"{APP_NAME} — Processing Options")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()
        self.result = None

        SW, SH  = self.winfo_screenwidth(), self.winfo_screenheight()
        DLG_W   = 510
        MAX_H   = int(SH * 0.82)    # never taller than 82% of screen

        # ── Scrollable canvas ─────────────────────────────────────────────────
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill="both", expand=True)
        self._cv = tk.Canvas(outer, bg=C["bg"], highlightthickness=0,
                              width=DLG_W - 20)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self._cv.yview)
        self._sf = tk.Frame(self._cv, bg=C["bg"])
        self._sf.bind("<Configure>",
            lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.create_window((0, 0), window=self._sf, anchor="nw")
        self._cv.configure(yscrollcommand=sb.set)
        self._cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._cv.bind_all("<MouseWheel>",
            lambda e: self._cv.yview_scroll(int(-1*(e.delta/120)), "units"))

        f = self._sf

        # ── Header banner ─────────────────────────────────────────────────────
        hdr = tk.Frame(f, bg=C["accent"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"⚗  {APP_NAME}  v{VERSION}",
                 font=F_LARGE, bg=C["accent"], fg=C["white"]).pack(pady=(10, 2))
        tk.Label(hdr, text="Processing Options — settings remembered between sessions",
                 font=F_SMALL, bg=C["accent"], fg="#C8E0FF").pack(pady=(0, 8))

        # Status badges
        sbar = tk.Frame(f, bg=C["panel"], pady=5)
        sbar.pack(fill="x")

        def badge(parent, txt, bg):
            tk.Label(parent, text=txt, font=(*F_SMALL[:2], "bold"),
                     bg=bg, fg=C["white"], padx=6, pady=2).pack(
                side="left", padx=4)

        rr_bg  = C["badge_amber"] if rerun_labels else C["badge_green"]
        rr_txt = (f"⚠ {len(rerun_labels)} re-run(s)" if rerun_labels
                  else "✓ No re-runs")
        badge(sbar, f"Types: {', '.join(types_present)}", C["badge_blue"])
        badge(sbar, rr_txt, rr_bg)
        if units_in_file:
            badge(sbar, f"Units: {', '.join(sorted(units_in_file))}",
                  C["badge_blue"])

        # ── Section / widget helpers ──────────────────────────────────────────
        def section(title):
            wrap = tk.Frame(f, bg=C["bg"], padx=10, pady=3)
            wrap.pack(fill="x")
            tk.Frame(wrap, bg=C["accent"], height=2).pack(fill="x")
            tk.Label(wrap, text=title, font=F_BOLD,
                     bg=C["card"], fg=C["accent"],
                     anchor="w", padx=8, pady=3).pack(fill="x")
            body = tk.Frame(wrap, bg=C["card"], padx=12, pady=7)
            body.pack(fill="x")
            return body

        def radios(parent, var, items, note=None):
            if note:
                tk.Label(parent, text=note, font=F_SMALL,
                         bg=C["card"], fg=C["muted"],
                         wraplength=440, justify="left").pack(
                    anchor="w", pady=(0, 3))
            for label, val in items:
                tk.Radiobutton(
                    parent, text=label, variable=var, value=val,
                    font=F_NORMAL, bg=C["card"], fg=C["text"],
                    activebackground=C["card"], activeforeground=C["accent"],
                    selectcolor=C["panel"]).pack(anchor="w", pady=1)

        def chk(parent, text, var, tip=None):
            row = tk.Frame(parent, bg=C["card"])
            row.pack(fill="x", pady=1)
            cb = tk.Checkbutton(
                row, text=text, variable=var,
                font=F_NORMAL, bg=C["card"], fg=C["text"],
                activebackground=C["card"], activeforeground=C["accent"],
                selectcolor=C["panel"])
            cb.pack(side="left")
            if tip:
                Tooltip(cb, tip)

        # ── § 1  Re-run handling ──────────────────────────────────────────────
        s1 = section("① Sample Re-run Handling")
        self.dup_var = tk.StringVar(value=cfg.get("dup_handling", "average"))
        note1 = (f"Re-runs found: {', '.join(rerun_labels)}"
                 if rerun_labels else
                 "No re-runs detected. Setting applies if any occur.")
        radios(s1, self.dup_var, [
            ("Average runs — numeric mean, Uncal preserved  ← recommended", "average"),
            ("Separate rows — adds suffix (2), (3)…",                        "separate"),
            ("Keep first run only",                                            "first"),
            ("Keep last run only",                                             "last"),
        ], note=note1)

        # ── § 2  Uncal handling ───────────────────────────────────────────────
        s2 = section("② Uncal / Flagged Values")
        self.uncal_var = tk.StringVar(value=cfg.get("uncal_handling", "keep_text"))
        radios(s2, self.uncal_var, [
            ("Keep as text 'Uncal'  — red highlight in Excel  ← default",  "keep_text"),
            ("Replace with blank cell",                                       "blank"),
            ("Replace with 0",                                                "zero"),
        ])

        # ── § 3  Unit normalisation ───────────────────────────────────────────
        s3 = section("③ Unit Normalisation")
        tk.Label(s3,
                 text="Convert all concentrations to one unit.\n"
                      "Column headers will be labelled e.g.  Ca 393.366 (ppm)",
                 font=F_SMALL, bg=C["card"], fg=C["muted"],
                 justify="left").pack(anchor="w", pady=(0, 4))
        self.unit_var = tk.StringVar(value=cfg.get("target_unit", "ppm (mg/L)"))
        radios(s3, self.unit_var, [
            ("ppm  (mg/L)   ← standard for ICP-OES water analysis",  "ppm (mg/L)"),
            ("ppb  (ug/L)   — trace / ultra-trace work",              "ppb (ug/L)"),
            ("Keep as-is   — no conversion, original units",          "Keep as-is"),
        ])
        tk.Label(s3,
                 text="⚠  Ratio-type columns (Internal Standard) are never converted.",
                 font=(*F_SMALL[:2], "italic"),
                 bg=C["card"], fg=C["amber"],
                 wraplength=440).pack(anchor="w", pady=(4, 0))

        # ── § 4  Calibration QC sheet ─────────────────────────────────────────
        s4 = section("④ Calibration / QC Data")
        self.cal_sheet_var = tk.BooleanVar(value=cfg.get("cal_sheet", True))
        chk(s4, 'Export calibration rows to "Calibration QC" sheet  ← recommended',
            self.cal_sheet_var,
            tip="Blanks, standards and QC rows go to a separate sheet so they "
                "don't clutter your sample data.")
        self.cal_type_vars = {}
        cal_types = [t for t in types_present if t != "Sample"]
        if cal_types:
            sub = tk.Frame(s4, bg=C["card"])
            sub.pack(anchor="w", padx=14)
            lmap = {"BLK": "Blanks (BLK)",
                    "STD": "Standards (STD)",
                    "QC":  "QC / CCB (QC)"}
            for t in cal_types:
                v = tk.BooleanVar(value=True)
                self.cal_type_vars[t] = v
                tk.Checkbutton(sub, text=lmap.get(t, t), variable=v,
                               font=F_NORMAL, bg=C["card"], fg=C["text"],
                               activebackground=C["card"],
                               selectcolor=C["panel"]).pack(anchor="w")

        # ── § 5  Calibration curve PDF ────────────────────────────────────────
        s5 = section("⑤ Calibration Curve PDF")
        self.cal_pdf_var   = tk.BooleanVar(value=cfg.get("cal_pdf", True))
        self.cal_pdf_r2    = tk.BooleanVar(value=cfg.get("cal_pdf_r2", True))
        self.cal_pdf_table = tk.BooleanVar(value=cfg.get("cal_pdf_table", True))
        chk(s5, "Generate calibration curve PDF  (one page per element)",
            self.cal_pdf_var,
            tip="Saved alongside your Excel file with the same base name.")
        chk(s5, "Show R² and fit-type annotation on each chart",
            self.cal_pdf_r2)
        chk(s5, "Include data table below each chart",
            self.cal_pdf_table)

        # ── § 6  Display options ──────────────────────────────────────────────
        s6 = section("⑥ Column Style & Flags")
        self.col_style_var = tk.StringVar(
            value=cfg.get("col_style", "symbol_wavelength"))
        radios(s6, self.col_style_var, [
            ("Symbol + wavelength   Ca 393.366  ← unambiguous (default)",
             "symbol_wavelength"),
            ("Symbol only           Ca           — cleaner, may collide if same element "
             "measured at two wavelengths",
             "symbol_only"),
        ])
        tk.Frame(s6, bg=C["border"], height=1).pack(fill="x", pady=5)
        self.neg_flag_var = tk.BooleanVar(value=cfg.get("flag_negatives", True))
        chk(s6, "Highlight negative values in amber  (below detection / noise)",
            self.neg_flag_var,
            tip="Negative concentrations usually mean the signal is at or below "
                "the instrument's detection limit.")

        # ── Buttons ───────────────────────────────────────────────────────────
        brow = tk.Frame(f, bg=C["bg"], pady=12)
        brow.pack()
        ok_btn = tk.Button(brow, text="  ✅  Process  ", command=self._ok,
                           font=F_BOLD, bg=C["green"], fg=C["white"],
                           activebackground=C["green_dark"],
                           relief="flat", padx=14, pady=6, cursor="hand2")
        ok_btn.pack(side="left", padx=10)
        Tooltip(ok_btn, "Apply these settings and start processing.")

        cx_btn = tk.Button(brow, text="  ✖  Cancel  ", command=self._cancel,
                           font=F_NORMAL, bg=C["panel"], fg=C["muted"],
                           activebackground=C["card"],
                           relief="flat", padx=14, pady=6, cursor="hand2")
        cx_btn.pack(side="left", padx=4)

        # ── Fit to screen height ──────────────────────────────────────────────
        self.update_idletasks()
        content_h = self._sf.winfo_reqheight()
        final_h   = min(content_h + 4, MAX_H)
        self._cv.configure(height=final_h)
        self.geometry(f"{DLG_W}x{final_h}+"
                      f"{(SW - DLG_W)//2}+{(SH - final_h)//2}")

    def _ok(self):
        self.result = {
            "dup_handling":   self.dup_var.get(),
            "uncal_handling": self.uncal_var.get(),
            "target_unit":    self.unit_var.get(),
            "cal_sheet":      self.cal_sheet_var.get(),
            "cal_types":      [t for t, v in self.cal_type_vars.items()
                               if v.get()],
            "cal_pdf":        self.cal_pdf_var.get(),
            "cal_pdf_r2":     self.cal_pdf_r2.get(),
            "cal_pdf_table":  self.cal_pdf_table.get(),
            "col_style":      self.col_style_var.get(),
            "flag_negatives": self.neg_flag_var.get(),
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
#  WELCOME DIALOG  (shown once on first run)
# ════════════════════════════════════════════════════════════════════════════

class WelcomeDialog(tk.Toplevel):
    """
    First-run welcome screen.
    Plain-English explanation of what the tool does and how to use it.
    Not shown again after the first launch (config tracks this).
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"Welcome to {APP_NAME}")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        tk.Label(self, text=f"⚗  Welcome to {APP_NAME}",
                 font=F_LARGE, bg=C["accent"], fg=C["white"]).pack(
            fill="x", pady=12)

        body = tk.Frame(self, bg=C["bg"], padx=20, pady=10)
        body.pack(fill="both", expand=True)

        intro = (
            "This tool converts raw Agilent ICP-OES export files\n"
            "into clean, formatted Excel workbooks.\n\n"
            "Quick start:\n"
            "  1.  Pick your ICP file (CSV or Excel).\n"
            "  2.  The output filename is suggested automatically\n"
            "       — you can change it if you like.\n"
            "  3.  Click  ⚙ Options & Run  to choose settings.\n"
            "  4.  Your cleaned Excel and calibration PDF\n"
            "       are saved to the same folder.\n\n"
            "For multiple files at once, switch to\n"
            "  📁 Batch Folder  mode in the sidebar.\n\n"
            "Your settings are remembered between sessions.\n"
            "Check the  ℹ️ About  tab for a full colour legend\n"
            "and explanation of every output sheet."
        )
        tk.Label(body, text=intro, font=F_NORMAL,
                 bg=C["bg"], fg=C["text"], justify="left").pack(anchor="w")

        tk.Button(body, text="  Let's go!  ",
                  command=self.destroy,
                  font=F_BOLD, bg=C["green"], fg=C["white"],
                  activebackground=C["green_dark"],
                  relief="flat", padx=12, pady=6,
                  cursor="hand2").pack(pady=12)

        SW, SH = self.winfo_screenwidth(), self.winfo_screenheight()
        self.update_idletasks()
        W, H = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"{W}x{H}+{(SW-W)//2}+{(SH-H)//2}")


# ════════════════════════════════════════════════════════════════════════════
#  HISTORY DIALOG  (conversion log viewer)
# ════════════════════════════════════════════════════════════════════════════

class HistoryDialog(tk.Toplevel):
    """
    Scrollable table showing every file that has been converted.
    Reads from icp_cleaner_conversions.json (newest first).
    """

    COLS = [
        ("Timestamp",    160),
        ("Status",        60),
        ("Input file",   200),
        ("Output file",  200),
        ("Samples",       65),
        ("Elements",      65),
        ("Note",         180),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Conversion History")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.attributes("-topmost", True)

        SW, SH = self.winfo_screenwidth(), self.winfo_screenheight()
        W = min(1000, SW - 80)
        H = min(520,  SH - 80)
        self.geometry(f"{W}x{H}+{(SW-W)//2}+{(SH-H)//2}")

        # Title bar
        tk.Label(self, text="📋  Conversion History",
                 font=F_LARGE, bg=C["accent"], fg=C["white"]).pack(
            fill="x", pady=10)

        # Treeview with scrollbars
        tree_frame = tk.Frame(self, bg=C["bg"])
        tree_frame.pack(fill="both", expand=True, padx=8, pady=8)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[c for c, _ in self.COLS],
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.configure(command=self.tree.yview)
        hsb.configure(command=self.tree.xview)

        for col, width in self.COLS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, minwidth=40)

        # Tag colours for ok / failed rows
        self.tree.tag_configure("ok",     background="#1A3A2A", foreground="#58D68D")
        self.tree.tag_configure("failed", background="#3A1A1A", foreground="#E74C3C")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Load records
        records = load_conversion_log()
        if not records:
            self.tree.insert("", "end",
                             values=("No conversions recorded yet.", "", "",
                                     "", "", "", ""))
        else:
            for r in records:
                tag = "ok" if r.get("status") == "ok" else "failed"
                self.tree.insert("", "end", values=(
                    r.get("timestamp", ""),
                    r.get("status", ""),
                    r.get("input_file", ""),
                    r.get("output_file", ""),
                    r.get("samples", ""),
                    r.get("elements", ""),
                    r.get("note", ""),
                ), tags=(tag,))

        # Close button
        tk.Button(self, text="  Close  ", command=self.destroy,
                  font=F_NORMAL, bg=C["panel"], fg=C["muted"],
                  relief="flat", padx=10, pady=5,
                  cursor="hand2").pack(pady=8)
