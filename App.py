"""
app.py
──────
The main GUI launcher window — ICPLauncherApp.

Three sidebar tabs:
  📄 Single File  — process one ICP file
  📁 Batch Folder — process every file in a folder
  ℹ️  About        — colour legend, output explanations, help

No data processing logic lives here.
This file only handles the GUI — it calls out to processing.py for the work.
"""

import os
import datetime
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

from constants  import APP_NAME, VERSION, VERSION_DATE, REQUIRED_COLS, C
from constants  import F_NORMAL, F_BOLD, F_LARGE, F_SMALL, F_MONO
from utils      import (load_config, save_config, suggest_filename,
                         load_agilent_file, open_path, log_error,
                         load_conversion_log)
from dialogs    import OptionsDialog, WelcomeDialog, HistoryDialog
from processing import process_file

import pandas as pd


class ICPLauncherApp:
    """
    Main application window.

    Responsibilities:
      • Build and manage the GUI layout
      • Handle file picking and filename suggestion
      • Dispatch processing to background threads (so the GUI never freezes)
      • Stream log messages to the log panel
      • Update the progress bar
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME}  v{VERSION}")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)
        self.cfg = load_config()

        # ── Tk variables ──────────────────────────────────────────────────────
        self.input_file   = tk.StringVar()
        self.output_file  = tk.StringVar()
        self._name_auto   = True     # True while output name is the suggestion
        self.batch_folder = tk.StringVar()
        self.batch_out    = tk.StringVar()
        self.batch_master = tk.StringVar()
        self.batch_csv    = tk.BooleanVar(value=True)
        self.batch_xlsx   = tk.BooleanVar(value=True)

        # ── Window geometry ───────────────────────────────────────────────────
        SW, SH = root.winfo_screenwidth(), root.winfo_screenheight()
        W = min(880, SW - 60)
        H = min(680, SH - 80)
        root.minsize(720, 540)
        root.geometry(f"{W}x{H}+{(SW-W)//2}+{(SH-H)//2}")

        self._build_ui()

        # First-run welcome
        if self.cfg.get("first_run", True):
            self.cfg["first_run"] = False
            save_config(self.cfg)
            WelcomeDialog(self.root)

    # ════════════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Title bar
        tbar = tk.Frame(self.root, bg=C["accent"], height=50)
        tbar.pack(fill="x")
        tbar.pack_propagate(False)
        tk.Label(tbar, text=f"⚗  {APP_NAME}",
                 font=F_LARGE, bg=C["accent"], fg=C["white"]).pack(
            side="left", padx=18, pady=10)
        tk.Label(tbar, text=f"v{VERSION}  ·  {VERSION_DATE}",
                 font=F_SMALL, bg=C["accent"], fg="#C8E0FF").pack(
            side="left", pady=16)

        # History button in title bar
        tk.Button(tbar, text="📋 History", command=self._show_history,
                  font=F_SMALL, bg=C["accent_dark"], fg=C["white"],
                  relief="flat", padx=8, pady=4,
                  cursor="hand2").pack(side="right", padx=12, pady=10)

        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = tk.Frame(body, bg=C["sidebar"], width=168)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="MODE", font=(*F_SMALL[:2], "bold"),
                 bg=C["sidebar"], fg=C["muted"]).pack(pady=(18, 4))

        self.mode     = tk.StringVar(value="single")
        self._sb_btns = {}
        self._sb_btn("📄  Single File",  "single")
        self._sb_btn("📁  Batch Folder", "batch")
        self._sb_btn("ℹ️   About",         "about")

        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(
            fill="x", padx=12, pady=10)
        tk.Label(self.sidebar,
                 text="Accepts:\nCSV · XLSX\nXLS · XLSM",
                 font=F_SMALL, bg=C["sidebar"], fg=C["muted"],
                 justify="center").pack()

        # ── Content area ──────────────────────────────────────────────────────
        self.content = tk.Frame(body, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self._frames = {
            "single": self._build_single_frame(),
            "batch":  self._build_batch_frame(),
            "about":  self._build_about_frame(),
        }

        # ── Progress bar ──────────────────────────────────────────────────────
        self._progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(self.root, variable=self._progress_var,
                        maximum=1.0, mode="determinate").pack(
            fill="x", side="bottom")

        # ── Log panel ─────────────────────────────────────────────────────────
        log_wrap = tk.Frame(self.root, bg=C["panel"], height=320)
        log_wrap.pack(fill="x", side="bottom")
        log_wrap.pack_propagate(False)

        log_hdr = tk.Frame(log_wrap, bg=C["sidebar"])
        log_hdr.pack(fill="x")
        tk.Label(log_hdr, text="  📋  Run Log",
                 font=F_BOLD, bg=C["sidebar"], fg=C["accent"]).pack(
            side="left", pady=4)
        tk.Button(log_hdr, text="Clear", font=F_SMALL,
                  bg=C["sidebar"], fg=C["muted"], relief="flat",
                  cursor="hand2",
                  command=self._clear_log).pack(side="right", padx=8)

        self.log_box = scrolledtext.ScrolledText(
            log_wrap, bg=C["log_bg"], fg=C["log_fg"],
            font=F_MONO, relief="flat", wrap="word", state="disabled")
        self.log_box.pack(fill="both", expand=True)

        self._show_mode()

    def _sb_btn(self, label, mode_val):
        btn = tk.Button(
            self.sidebar, text=label, font=F_NORMAL,
            bg=C["sidebar"], fg=C["text"],
            activebackground=C["sidebar_sel"],
            relief="flat", anchor="w", padx=14, pady=8,
            cursor="hand2", width=15,
            command=lambda m=mode_val: self._switch(m))
        btn.pack(fill="x")
        self._sb_btns[mode_val] = btn

    def _switch(self, mode_val):
        self.mode.set(mode_val)
        self._show_mode()

    def _show_mode(self):
        m = self.mode.get()
        for key, frame in self._frames.items():
            if key == m:
                frame.pack(fill="both", expand=True)
                self._sb_btns[key].configure(
                    bg=C["sidebar_sel"], fg=C["accent"])
            else:
                frame.pack_forget()
                self._sb_btns[key].configure(
                    bg=C["sidebar"], fg=C["text"])

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Reusable labelled file-picker row ─────────────────────────────────────
    def _file_row(self, parent, label, var, btn_text, btn_cmd,
                  tooltip="", width=16):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", padx=18, pady=4)
        tk.Label(row, text=label, font=F_BOLD,
                 bg=C["bg"], fg=C["text"],
                 width=width, anchor="w").pack(side="left")
        ent = tk.Entry(row, textvariable=var, font=F_NORMAL,
                       bg=C["card"], fg=C["text"],
                       insertbackground=C["text"],
                       relief="flat", bd=4)
        ent.pack(side="left", fill="x", expand=True, padx=(0, 6))
        btn = tk.Button(row, text=btn_text, command=btn_cmd,
                        font=F_SMALL, bg=C["accent"], fg=C["white"],
                        activebackground=C["accent_dark"],
                        relief="flat", padx=8, pady=3, cursor="hand2")
        btn.pack(side="left")
        if tooltip:
            from utils import Tooltip
            Tooltip(btn, tooltip)
        return ent

    # ════════════════════════════════════════════════════════════════════════
    #  SINGLE FILE FRAME
    # ════════════════════════════════════════════════════════════════════════

    def _build_single_frame(self):
        f = tk.Frame(self.content, bg=C["bg"])

        tk.Label(f, text="Single File Mode", font=F_LARGE,
                 bg=C["bg"], fg=C["text"]).pack(
            anchor="w", padx=18, pady=(16, 2))
        tk.Label(f, text="Process one ICP export file at a time.",
                 font=F_SMALL, bg=C["bg"], fg=C["muted"]).pack(
            anchor="w", padx=18, pady=(0, 10))

        self._file_row(f, "Input file:", self.input_file,
                       "Browse…", self._browse_input,
                       tooltip="Select your Agilent ICP export (CSV or Excel).")

        # Output row — has the Auto/Custom badge
        out_row = tk.Frame(f, bg=C["bg"])
        out_row.pack(fill="x", padx=18, pady=4)
        tk.Label(out_row, text="Output file:", font=F_BOLD,
                 bg=C["bg"], fg=C["text"], width=16, anchor="w").pack(
            side="left")
        self._out_entry = tk.Entry(
            out_row, textvariable=self.output_file, font=F_NORMAL,
            bg=C["card"], fg=C["text"],
            insertbackground=C["text"], relief="flat", bd=4)
        self._out_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._out_entry.bind("<Key>", self._on_output_edit)
        tk.Button(out_row, text="Browse…", command=self._browse_output,
                  font=F_SMALL, bg=C["accent"], fg=C["white"],
                  activebackground=C["accent_dark"],
                  relief="flat", padx=8, pady=3,
                  cursor="hand2").pack(side="left")
        self._auto_badge = tk.Label(
            out_row, text="✨ Auto",
            font=F_SMALL, bg=C["badge_blue"], fg=C["white"],
            padx=5, pady=2)
        self._auto_badge.pack(side="left", padx=6)

        # Run + open buttons
        btn_row = tk.Frame(f, bg=C["bg"])
        btn_row.pack(pady=18)
        run_btn = tk.Button(
            btn_row, text="  ⚙  Options & Run  ",
            command=self._single_run,
            font=F_LARGE, bg=C["green"], fg=C["white"],
            activebackground=C["green_dark"],
            relief="flat", padx=18, pady=8, cursor="hand2")
        run_btn.pack(side="left", padx=8)

        self._open_btn_single = tk.Button(
            btn_row, text="📂 Open output folder",
            font=F_NORMAL, bg=C["panel"], fg=C["accent"],
            relief="flat", padx=10, pady=8, cursor="hand2",
            command=lambda: open_path(
                os.path.dirname(self.output_file.get())))
        self._open_btn_single_shown = False

        return f

    # ════════════════════════════════════════════════════════════════════════
    #  BATCH FRAME
    # ════════════════════════════════════════════════════════════════════════

    def _build_batch_frame(self):
        f = tk.Frame(self.content, bg=C["bg"])

        tk.Label(f, text="Batch Folder Mode", font=F_LARGE,
                 bg=C["bg"], fg=C["text"]).pack(
            anchor="w", padx=18, pady=(16, 2))
        tk.Label(f,
                 text="Process every ICP file in a folder.\n"
                      "Each file gets its own Excel + PDF.\n"
                      "All runs are also appended to a master workbook "
                      "for your historical log.",
                 font=F_SMALL, bg=C["bg"], fg=C["muted"],
                 justify="left").pack(anchor="w", padx=18, pady=(0, 10))

        self._file_row(f, "Input folder:",    self.batch_folder,
                       "Browse…", self._browse_batch_folder,
                       tooltip="Folder containing your ICP export files.")
        self._file_row(f, "Output folder:",   self.batch_out,
                       "Browse…", self._browse_batch_out,
                       tooltip="Where individual cleaned files will be saved.")
        self._file_row(f, "Master workbook:", self.batch_master,
                       "Browse…", self._browse_batch_master,
                       tooltip="All runs appended here with Run Date column.\n"
                               "Perfect for building your historical log.")

        ft_row = tk.Frame(f, bg=C["bg"])
        ft_row.pack(fill="x", padx=18, pady=4)
        tk.Label(ft_row, text="Include:", font=F_BOLD,
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        for label, var in [("CSV", self.batch_csv),
                            ("XLSX / XLS", self.batch_xlsx)]:
            tk.Checkbutton(ft_row, text=label, variable=var,
                           font=F_NORMAL, bg=C["bg"], fg=C["text"],
                           activebackground=C["bg"],
                           selectcolor=C["panel"]).pack(side="left", padx=8)

        btn_row = tk.Frame(f, bg=C["bg"])
        btn_row.pack(pady=16)
        tk.Button(btn_row, text="  ⚙  Options & Run Batch  ",
                  command=self._batch_run,
                  font=F_LARGE, bg=C["green"], fg=C["white"],
                  activebackground=C["green_dark"],
                  relief="flat", padx=18, pady=8,
                  cursor="hand2").pack(side="left", padx=8)

        self._open_btn_batch = tk.Button(
            btn_row, text="📂 Open output folder",
            font=F_NORMAL, bg=C["panel"], fg=C["accent"],
            relief="flat", padx=10, pady=8, cursor="hand2",
            command=lambda: open_path(self.batch_out.get()))

        return f

    # ════════════════════════════════════════════════════════════════════════
    #  ABOUT FRAME
    # ════════════════════════════════════════════════════════════════════════

    def _build_about_frame(self):
        f = tk.Frame(self.content, bg=C["bg"])

        tk.Label(f, text=f"⚗  {APP_NAME}  v{VERSION}",
                 font=F_LARGE, bg=C["bg"], fg=C["accent"]).pack(
            anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text=f"Built for Agilent ICP-OES data  ·  {VERSION_DATE}",
                 font=F_SMALL, bg=C["bg"], fg=C["muted"]).pack(
            anchor="w", padx=24, pady=(0, 14))

        sections = [
            ("What this program does",
             "Converts raw Agilent ICP export files (CSV or Excel) into clean, "
             "formatted Excel workbooks and calibration curve PDFs. Handles unit "
             "conversion, duplicate sample runs, and multi-file batch processing."),

            ("Output files explained",
             "📊  Cleaned Data sheet    — one row per sample, one column per element.\n"
             "📋  Calibration QC sheet  — blanks, standards and QC in a separate tab.\n"
             "📄  Calibration PDF       — scatter plots with regression lines per element.\n"
             "ℹ️   Run Info sheet        — full audit trail: source file, date, settings.\n"
             "📓  Re-run Notes sheet    — logged if duplicate sample runs were detected.\n"
             "📋  Conversion log        — icp_cleaner_conversions.json next to the script."),

            ("Colour legend in Excel",
             "🔴 Red cell    — value is Uncal (outside calibration range).\n"
             "🟡 Amber cell  — negative concentration (at or below detection limit).\n"
             "⬛ Navy header — element column headers.\n"
             "⬜ Grey row    — sample name column."),

            ("File structure",
             "main.py        — double-click this to launch the app.\n"
             "app.py         — main window and GUI layout.\n"
             "dialogs.py     — options dialog, welcome screen, history viewer.\n"
             "processing.py  — all data processing logic.\n"
             "pdf_export.py  — calibration curve PDF builder.\n"
             "excel_utils.py — Excel formatting helpers.\n"
             "utils.py       — config, logging, filename suggestion, file loading.\n"
             "constants.py   — colours, fonts, version, shared paths."),

            ("Dependencies",
             "pandas · openpyxl · matplotlib · reportlab · numpy\n"
             "Install with:  pip install pandas openpyxl matplotlib reportlab numpy"),
        ]

        cv = tk.Canvas(f, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=C["bg"])
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True, padx=12, pady=4)
        sb.pack(side="right", fill="y")
        cv.bind_all("<MouseWheel>",
                    lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))

        for title, body_text in sections:
            card = tk.Frame(inner, bg=C["card"], padx=14, pady=10)
            card.pack(fill="x", padx=8, pady=4)
            tk.Label(card, text=title, font=F_BOLD,
                     bg=C["card"], fg=C["accent"], anchor="w").pack(anchor="w")
            tk.Frame(card, bg=C["border"], height=1).pack(fill="x", pady=4)
            tk.Label(card, text=body_text, font=F_NORMAL,
                     bg=C["card"], fg=C["text"],
                     justify="left", wraplength=580).pack(anchor="w")

        return f

    # ════════════════════════════════════════════════════════════════════════
    #  FILE PICKERS
    # ════════════════════════════════════════════════════════════════════════

    def _browse_input(self):
        init = self.cfg.get("last_dir", "") or os.path.expanduser("~")
        path = filedialog.askopenfilename(
            title="Select your Agilent ICP file", initialdir=init,
            filetypes=[("All supported", "*.csv *.xlsx *.xls *.xlsm"),
                       ("CSV", "*.csv"), ("Excel", "*.xlsx *.xls *.xlsm"),
                       ("All", "*.*")])
        if not path:
            return
        self.input_file.set(path)
        self.cfg["last_dir"] = os.path.dirname(path)
        save_config(self.cfg)

        # Auto-suggest output filename from the data
        try:
            df_raw = load_agilent_file(path)
            if REQUIRED_COLS.issubset(df_raw.columns):
                name    = suggest_filename(df_raw)
                out_dir = os.path.dirname(path)
                self.output_file.set(os.path.join(out_dir, name))
                self._name_auto = True
                self._auto_badge.configure(bg=C["badge_blue"],
                                           fg=C["white"], text="✨ Auto")
                self.log(f"💡 Suggested: {name}")
        except Exception:
            pass

    def _on_output_edit(self, _=None):
        """Called when user types in the output entry — clears the Auto badge."""
        if self._name_auto:
            self._name_auto = False
            self._auto_badge.configure(bg=C["panel"], fg=C["muted"],
                                       text="✏ Custom")

    def _browse_output(self):
        init_dir  = (os.path.dirname(self.output_file.get())
                     or self.cfg.get("last_dir", "")
                     or os.path.expanduser("~"))
        init_file = os.path.basename(self.output_file.get()) or \
                    "Cleaned_Usable_Data.xlsx"
        path = filedialog.asksaveasfilename(
            title="Save cleaned Excel as…",
            initialdir=init_dir, initialfile=init_file,
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")])
        if path:
            self.output_file.set(path)
            self._name_auto = False
            self._auto_badge.configure(bg=C["panel"], fg=C["muted"],
                                       text="✏ Custom")

    def _browse_batch_folder(self):
        init = self.cfg.get("last_dir", "") or os.path.expanduser("~")
        path = filedialog.askdirectory(
            title="Select folder of ICP files", initialdir=init)
        if not path:
            return
        self.batch_folder.set(path)
        self.cfg["last_dir"] = path
        save_config(self.cfg)
        if not self.batch_out.get():
            self.batch_out.set(path)
        if not self.batch_master.get():
            self.batch_master.set(
                os.path.join(path, "MASTER_All_Runs.xlsx"))

    def _browse_batch_out(self):
        init = self.batch_folder.get() or os.path.expanduser("~")
        path = filedialog.askdirectory(
            title="Output folder for cleaned files", initialdir=init)
        if path:
            self.batch_out.set(path)

    def _browse_batch_master(self):
        init_dir = self.batch_out.get() or os.path.expanduser("~")
        path = filedialog.asksaveasfilename(
            title="Save master workbook as…",
            initialdir=init_dir, initialfile="MASTER_All_Runs.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")])
        if path:
            self.batch_master.set(path)

    # ════════════════════════════════════════════════════════════════════════
    #  LOGGING + PROGRESS
    # ════════════════════════════════════════════════════════════════════════

    def log(self, msg: str):
        """Append a timestamped message to the log panel (thread-safe)."""
        def _go():
            self.log_box.configure(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}]  {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, _go)

    def _set_progress(self, v: float):
        self.root.after(0, lambda: self._progress_var.set(v))

    def _show_history(self):
        HistoryDialog(self.root)

    # ════════════════════════════════════════════════════════════════════════
    #  SINGLE RUN
    # ════════════════════════════════════════════════════════════════════════

    def _single_run(self):
        inp = self.input_file.get().strip()
        out = self.output_file.get().strip()

        if not inp or not os.path.isfile(inp):
            messagebox.showwarning("No input file",
                "Please select an ICP input file first.")
            return
        if not out:
            messagebox.showwarning("No output path",
                "Please choose where to save the output file.")
            return

        try:
            df_raw = load_agilent_file(inp)
        except Exception as e:
            messagebox.showerror("Could not read file",
                f"Failed to open:\n{inp}\n\nError: {e}")
            return

        if not REQUIRED_COLS.issubset(df_raw.columns):
            messagebox.showerror("Unrecognised format",
                "This doesn't look like a standard Agilent ICP export.\n\n"
                f"Expected columns: {', '.join(REQUIRED_COLS)}\n"
                f"Found: {list(df_raw.columns[:6])}…")
            return

        types_present = sorted(df_raw["Type"].dropna().unique().tolist())
        units_in_file = (set(df_raw["Unit"].dropna().str.strip().str.lower().unique())
                         if "Unit" in df_raw.columns else set())
        dupes = (df_raw[df_raw["Type"] == "Sample"]
                 .groupby(["Label", "Element"]).size()
                 .reset_index(name="n")
                 .query("n > 1")["Label"].unique().tolist())

        dlg = OptionsDialog(self.root, types_present, dupes,
                            units_in_file, self.cfg)
        self.root.wait_window(dlg)
        if dlg.result is None:
            self.log("❌ Cancelled.")
            return

        opts = dlg.result
        self.cfg.update({k: v for k, v in opts.items() if k != "cal_types"})
        save_config(self.cfg)

        self.log(f"\n{'═'*50}")
        self.log(f"🚀 Single run: {os.path.basename(inp)}")
        self._set_progress(0)

        def _run():
            _, ok = process_file(inp, out, opts, self.log,
                                 progress_fn=self._set_progress)
            if ok:
                self.log(f"🎉 Complete! → {os.path.basename(out)}")
                self.log("See You Space Cowboy 🤠")
                self.root.after(0, self._show_open_single)
            else:
                self.log("❌ Run failed — see log above.")
                messagebox.showerror("Processing failed",
                    "Something went wrong.\n\n"
                    "Check the Run Log panel for details.\n"
                    "Full error saved to icp_cleaner_error.log")

        threading.Thread(target=_run, daemon=True).start()

    def _show_open_single(self):
        if not self._open_btn_single_shown:
            self._open_btn_single.pack(side="left", padx=8)
            self._open_btn_single_shown = True

    # ════════════════════════════════════════════════════════════════════════
    #  BATCH RUN
    # ════════════════════════════════════════════════════════════════════════

    def _batch_run(self):
        folder  = self.batch_folder.get().strip()
        out_dir = self.batch_out.get().strip()
        master  = self.batch_master.get().strip()

        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder",
                "Select an input folder first.")
            return
        if not out_dir:
            messagebox.showwarning("No output folder",
                "Choose where to save the individual output files.")
            return
        if not master:
            messagebox.showwarning("No master workbook",
                "Choose a path for the master workbook.")
            return

        os.makedirs(out_dir, exist_ok=True)
        exts = []
        if self.batch_csv.get():  exts += [".csv"]
        if self.batch_xlsx.get(): exts += [".xlsx", ".xls", ".xlsm"]

        files = sorted([
            os.path.join(folder, fn) for fn in os.listdir(folder)
            if os.path.splitext(fn)[1].lower() in exts
        ])
        if not files:
            messagebox.showwarning("No files found",
                f"No matching ICP files found in:\n{folder}\n\n"
                "Check the file type checkboxes.")
            return

        self.log(f"\n{'═'*50}")
        self.log(f"📁 Batch: {len(files)} file(s) in "
                 f"{os.path.basename(folder)}")

        try:
            df_first = load_agilent_file(files[0])
        except Exception as e:
            messagebox.showerror("Could not read first file", str(e))
            return

        types_present = (sorted(df_first["Type"].dropna().unique().tolist())
                         if "Type" in df_first.columns else ["Sample"])
        units_in_file = (set(df_first["Unit"].dropna().str.strip()
                                             .str.lower().unique())
                         if "Unit" in df_first.columns else set())

        dlg = OptionsDialog(self.root, types_present, [], units_in_file,
                            self.cfg)
        self.root.wait_window(dlg)
        if dlg.result is None:
            self.log("❌ Batch cancelled.")
            return

        opts = dlg.result
        self.cfg.update({k: v for k, v in opts.items() if k != "cal_types"})
        save_config(self.cfg)

        self.log(f"🚀 Batch starting — {len(files)} file(s)…")
        self._set_progress(0)

        def _run_batch():
            master_frames = []
            ok_n = fail_n = 0

            for i, fpath in enumerate(files):
                fname = os.path.basename(fpath)
                self.log(f"\n── [{i+1}/{len(files)}]  {fname} ──")

                # Scale progress across each file's share of 0→1
                s = i / len(files)
                e = (i + 1) / len(files)
                def _prog(v, _s=s, _e=e):
                    self._set_progress(_s + v * (_e - _s))

                try:
                    df_raw    = load_agilent_file(fpath)
                    suggested = (suggest_filename(df_raw)
                                 if REQUIRED_COLS.issubset(df_raw.columns)
                                 else os.path.splitext(fname)[0]
                                 + "_cleaned.xlsx")
                except Exception:
                    suggested = os.path.splitext(fname)[0] + "_cleaned.xlsx"

                out_path = os.path.join(out_dir, suggested)
                base, e2 = os.path.splitext(out_path)
                c = 1
                while os.path.exists(out_path):
                    out_path = f"{base}_{c}{e2}"; c += 1

                try:
                    mtime    = os.path.getmtime(fpath)
                    run_date = datetime.datetime.fromtimestamp(mtime)\
                                               .strftime("%Y-%m-%d")
                except Exception:
                    run_date = datetime.datetime.now().strftime("%Y-%m-%d")

                pivoted, ok = process_file(
                    fpath, out_path, opts, self.log,
                    run_date_tag=run_date, progress_fn=_prog)

                if ok and pivoted is not None:
                    ok_n += 1
                    p = pivoted.copy()
                    p.insert(0, "Run Date",    run_date)
                    p.insert(1, "Source File", fname)
                    master_frames.append(p)
                else:
                    fail_n += 1

            # Write master workbook
            if master_frames:
                self.log(f"\n📚 Writing master workbook "
                         f"({len(master_frames)} runs)…")
                try:
                    from excel_utils import format_sheet
                    master_df = pd.concat(master_frames, ignore_index=False)
                    master_df.index.name = "Sample"
                    with pd.ExcelWriter(master, engine="openpyxl") as writer:
                        master_df.to_excel(
                            writer, sheet_name="All Runs", index=True)
                        format_sheet(writer.sheets["All Runs"])

                        summary = (master_df.reset_index()
                                            .groupby("Source File")
                                            .agg(Run_Date =("Run Date",  "first"),
                                                 Samples   =("Sample",   "count"))
                                            .reset_index())
                        summary.columns = ["Source File", "Run Date", "Samples"]
                        summary.to_excel(
                            writer, sheet_name="Batch Summary", index=False)
                        format_sheet(writer.sheets["Batch Summary"])
                    self.log(f"✅ Master: {os.path.basename(master)}")
                except Exception as e:
                    self.log(f"❌ Master write failed: "
                             f"{log_error('Master workbook', e)}")

            self._set_progress(1.0)
            self.log(f"\n{'═'*50}")
            self.log(f"🎉 Batch complete: {ok_n} succeeded, {fail_n} failed.")
            if fail_n:
                self.log("   Details in icp_cleaner_error.log")
            self.log("See You Space Cowboy 🤠")
            self.root.after(0, lambda: self._open_btn_batch.pack(
                side="left", padx=8))

        threading.Thread(target=_run_batch, daemon=True).start()
