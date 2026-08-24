"""
processing.py
─────────────
Core data pipeline — no GUI code here at all.

  build_working_df()  — extract and clean the columns we need
  pivot_samples()     — reshape: one row per sample, one col per element
  process_file()      — full pipeline: load → clean → pivot → PDF → Excel
"""

import os
import datetime

import pandas as pd

from constants   import REQUIRED_COLS
from utils       import (clean_value, safe_avg, load_agilent_file,
                          log_error, log_conversion)
from excel_utils import format_sheet, fmt_info_sheet
from pdf_export  import build_cal_pdf


# ════════════════════════════════════════════════════════════════════════════
#  UNIT SUFFIX HELPER
# ════════════════════════════════════════════════════════════════════════════

def _unit_suffix(target_unit: str) -> str:
    return {
        "ppm (mg/L)": " (ppm)",
        "ppb (ug/L)": " (ppb)",
        "Keep as-is": "",
    }.get(target_unit, "")


# ════════════════════════════════════════════════════════════════════════════
#  BUILD WORKING DATAFRAME
# ════════════════════════════════════════════════════════════════════════════

def build_working_df(df_in: pd.DataFrame, opts: dict) -> pd.DataFrame:
    """
    Extract the columns we care about from a raw Agilent DataFrame,
    apply unit conversion, and build the ColKey (the column header
    that will appear in the final pivoted table).

    Parameters
    ----------
    df_in : raw rows from one type group (e.g. only Sample rows)
    opts  : the user's options dict from the dialog

    Returns
    -------
    DataFrame with columns: Sample, Element, ElemLabel, Value, Type,
                            Unit (if present), ColKey
    """
    has_unit = "Unit" in df_in.columns
    suffix   = _unit_suffix(opts["target_unit"])

    # Only grab columns that actually exist in this file
    want = [c for c in
            ["Label", "Element", "Element Label", "Concentration", "Type", "Unit"]
            if c in df_in.columns]
    df = df_in[want].copy().rename(columns={
        "Label":         "Sample",
        "Element":       "Element",
        "Element Label": "ElemLabel",
        "Concentration": "Value",
        "Type":          "Type",
        "Unit":          "Unit",
    })

    # Column header key: full "Ca 393.366" or just "Ca"
    col_src      = "ElemLabel" if opts["col_style"] == "symbol_only" else "Element"
    df["ColKey"] = df[col_src].str.strip()

    # Clean / convert each value
    def _clean(row):
        unit = row.get("Unit") if has_unit else None
        # Internal standards are ratio-type — never convert them
        if unit and unit.strip().lower() == "ratio":
            return clean_value(row["Value"], opts["uncal_handling"])
        return clean_value(row["Value"], opts["uncal_handling"],
                           from_unit=unit, target_unit=opts["target_unit"])

    df["Value"] = df.apply(_clean, axis=1)

    # Add unit suffix to column keys (skip ratio columns)
    if suffix and has_unit:
        df["ColKey"] = df.apply(
            lambda r: r["ColKey"]
            if str(r.get("Unit", "")).strip().lower() == "ratio"
            else r["ColKey"] + suffix,
            axis=1,
        )
    return df


# ════════════════════════════════════════════════════════════════════════════
#  PIVOT SAMPLES
# ════════════════════════════════════════════════════════════════════════════

def pivot_samples(df_s: pd.DataFrame, opts: dict):
    """
    Reshape sample data so there is one row per sample and
    one column per element — the format scientists actually want to use.

    Handles duplicate/re-run samples according to opts["dup_handling"]:
      "average"  — numeric mean of all runs
      "separate" — suffix with (2), (3)…
      "first"    — keep first occurrence
      "last"     — keep last occurrence

    Returns
    -------
    (pivoted_df, list_of_rerun_sample_names, working_df_with_run_numbers)
    """
    original_order = df_s["Sample"].drop_duplicates().tolist()
    dup_mode       = opts["dup_handling"]
    counts = df_s.groupby(["Sample", "ColKey"]).size().reset_index(name="n")
    dupes  = counts[counts["n"] > 1]["Sample"].unique().tolist()

    if dup_mode == "separate" and dupes:
        df_s = df_s.copy()
        df_s["_run_n"] = df_s.groupby(["Sample", "ColKey"]).cumcount()
        df_s["UniqSample"] = df_s.apply(
            lambda r: r["Sample"] if r["_run_n"] == 0
            else f"{r['Sample']} ({r['_run_n'] + 1})", axis=1)
        piv = df_s.pivot_table(
            index="UniqSample", columns="ColKey",
            values="Value", aggfunc="first")
        piv.index.name = "Sample"
        new_ord = []
        for s in original_order:
            new_ord.append(s)
            if s in dupes:
                max_n = int(df_s[df_s["Sample"] == s]["_run_n"].max())
                for i in range(2, max_n + 2):
                    new_ord.append(f"{s} ({i})")
        piv = piv.reindex([x for x in new_ord if x in piv.index])

    elif dup_mode == "average" and dupes:
        piv = df_s.pivot_table(
            index="Sample", columns="ColKey",
            values="Value", aggfunc=safe_avg)
        piv.index.name = "Sample"

    elif dup_mode == "first":
        piv = df_s.pivot_table(
            index="Sample", columns="ColKey",
            values="Value", aggfunc="first")
        piv.index.name = "Sample"

    elif dup_mode == "last":
        piv = df_s.pivot_table(
            index="Sample", columns="ColKey",
            values="Value", aggfunc="last")
        piv.index.name = "Sample"

    else:
        piv = df_s.pivot_table(
            index="Sample", columns="ColKey",
            values="Value", aggfunc="first")
        piv.index.name = "Sample"

    # Restore original run order; anything extra goes at the bottom
    valid  = [s for s in original_order if s in piv.index]
    extras = [s for s in piv.index      if s not in valid]
    return piv.reindex(valid + extras), dupes, df_s


# ════════════════════════════════════════════════════════════════════════════
#  FULL FILE PIPELINE
# ════════════════════════════════════════════════════════════════════════════

def process_file(input_path: str, output_path: str, opts: dict,
                 log_fn, run_date_tag: str = None,
                 progress_fn=None):
    """
    Full pipeline for one ICP file.

    Steps:
      1. Load the file
      2. Validate columns
      3. Split into Sample / Calibration / STD rows
      4. Pivot samples
      5. Pivot calibration QC  (optional)
      6. Build calibration curve PDF  (optional)
      7. Write Excel workbook
      8. Write conversion log entry

    Parameters
    ----------
    input_path   : path to the raw Agilent file
    output_path  : path to write the cleaned Excel file
    opts         : user options dict from OptionsDialog
    log_fn       : callable(str) — sends messages to the GUI log panel
    run_date_tag : date string for the Run Info sheet (used in batch mode)
    progress_fn  : callable(float 0→1) — optional progress bar update

    Returns
    -------
    (pivoted_DataFrame or None,  success: bool)
    """
    def _p(v):
        if progress_fn:
            progress_fn(v)

    # ── Step 1: Load ──────────────────────────────────────────────────────────
    try:
        log_fn(f"  Loading: {os.path.basename(input_path)}")
        df_raw = load_agilent_file(input_path)
        _p(0.1)
    except Exception as e:
        log_fn(f"  ❌ {log_error('Load failed', e)}")
        log_conversion(input_path, output_path, 0, 0, success=False,
                       note="Load failed")
        return None, False

    # ── Step 2: Validate ──────────────────────────────────────────────────────
    if not REQUIRED_COLS.issubset(df_raw.columns):
        msg = (f"Required columns not found.\n"
               f"Found: {list(df_raw.columns[:6])}…\n\n"
               "Make sure this is a standard Agilent ICP export "
               "with 6 metadata rows at the top.")
        log_fn(f"  ❌ {msg}")
        log_conversion(input_path, output_path, 0, 0, success=False,
                       note="Missing columns")
        return None, False

    types_present = sorted(df_raw["Type"].dropna().unique().tolist())
    units_present = (set(df_raw["Unit"].dropna().str.strip().str.lower().unique())
                     if "Unit" in df_raw.columns else set())
    log_fn(f"  ✅ {len(df_raw)} rows  |  Types: {types_present}"
           f"  |  Units: {sorted(units_present)}")

    # ── Step 3: Split by type ─────────────────────────────────────────────────
    df_samples_raw = df_raw[df_raw["Type"] == "Sample"].copy()
    cal_types      = opts.get("cal_types",
                              [t for t in types_present if t != "Sample"])
    df_cal_raw     = df_raw[df_raw["Type"].isin(cal_types)].copy()
    df_std_raw     = df_raw[df_raw["Type"] == "STD"].copy()

    if df_samples_raw.empty:
        log_fn("  ⚠️  No rows with Type='Sample' found — skipping.")
        log_conversion(input_path, output_path, 0, 0, success=False,
                       note="No Sample rows")
        return None, False

    _p(0.2)

    # ── Step 4: Pivot samples ─────────────────────────────────────────────────
    try:
        df_s                     = build_working_df(df_samples_raw, opts)
        pivoted, dupes, df_s_out = pivot_samples(df_s, opts)
        log_fn(f"  ✅ {len(pivoted)} samples × {len(pivoted.columns)} elements")
    except Exception as e:
        log_fn(f"  ❌ {log_error('Sample processing failed', e)}")
        log_conversion(input_path, output_path, 0, 0, success=False,
                       note=f"Pivot failed: {e}")
        return None, False

    _p(0.4)

    # ── Step 5: Calibration QC pivot ─────────────────────────────────────────
    pivoted_cal = None
    if opts.get("cal_sheet") and not df_cal_raw.empty:
        try:
            df_c        = build_working_df(df_cal_raw, opts)
            cal_ord     = df_c["Sample"].drop_duplicates().tolist()
            pivoted_cal = df_c.pivot_table(
                index="Sample", columns="ColKey",
                values="Value", aggfunc="first")
            pivoted_cal.index.name = "Sample"
            pivoted_cal = pivoted_cal.reindex(
                [s for s in cal_ord if s in pivoted_cal.index])
        except Exception as e:
            log_fn(f"  ⚠️  Cal QC sheet skipped: {e}")

    _p(0.55)

    # ── Step 6: Calibration curve PDF ────────────────────────────────────────
    pdf_path = os.path.splitext(output_path)[0] + "_calibration_curves.pdf"
    pdf_ok   = False
    if opts.get("cal_pdf") and not df_std_raw.empty:
        log_fn("  📈 Building calibration curve PDF…")
        try:
            pdf_ok = build_cal_pdf(df_std_raw, pdf_path, opts, input_path)
            if pdf_ok:
                log_fn(f"  ✅ PDF: {os.path.basename(pdf_path)}")
        except Exception as e:
            log_fn(f"  ⚠️  PDF skipped: {log_error('PDF build', e)}")

    _p(0.75)

    # ── Step 7: Write Excel ───────────────────────────────────────────────────
    log_fn("  💾 Writing Excel…")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

            # Sheet 1 — Cleaned sample data
            pivoted.to_excel(writer, sheet_name="Cleaned Data", index=True)
            format_sheet(writer.sheets["Cleaned Data"],
                         flag_neg=opts["flag_negatives"])

            # Sheet 2 — Calibration QC  (optional)
            if pivoted_cal is not None and not pivoted_cal.empty:
                pivoted_cal.to_excel(writer, sheet_name="Calibration QC",
                                     index=True)
                format_sheet(writer.sheets["Calibration QC"],
                             flag_neg=opts["flag_negatives"],
                             hdr_key="cal_fill")

            # Sheet 3 — Re-run notes  (if duplicates found)
            if dupes:
                pd.DataFrame(
                    [{"Sample": s,
                      "Re-runs detected": "yes",
                      "Handling": opts["dup_handling"]}
                     for s in dupes]
                ).to_excel(writer, sheet_name="Re-run Notes", index=False)

            # Sheet 4 — Run Info (audit trail)
            ri_df = pd.DataFrame([
                {"Field": "Source file",     "Value": os.path.basename(input_path)},
                {"Field": "Full path",       "Value": input_path},
                {"Field": "Processed at",    "Value": now},
                {"Field": "Run date tag",    "Value": run_date_tag or now[:10]},
                {"Field": "Samples",         "Value": len(pivoted)},
                {"Field": "Elements",        "Value": len(pivoted.columns)},
                {"Field": "Unit target",     "Value": opts["target_unit"]},
                {"Field": "Re-run handling", "Value": opts["dup_handling"]},
                {"Field": "Cal PDF",         "Value": str(pdf_ok)},
                {"Field": "Script version",  "Value": "1.0.0"},
                {"Field": "Generated by",    "Value": "Agilent ICP Cleaner"},
            ])
            ri_df.to_excel(writer, sheet_name="Run Info", index=False)
            fmt_info_sheet(writer.sheets["Run Info"])

    except Exception as e:
        log_fn(f"  ❌ {log_error('Excel write failed', e)}")
        log_conversion(input_path, output_path,
                       len(pivoted), len(pivoted.columns),
                       pdf_path if pdf_ok else "",
                       success=False, note=f"Excel write failed: {e}")
        return None, False

    _p(1.0)
    log_fn(f"  ✅ Excel: {os.path.basename(output_path)}")

    # ── Step 8: Write conversion log entry ───────────────────────────────────
    log_conversion(
        input_path, output_path,
        n_samples=len(pivoted),
        n_elements=len(pivoted.columns),
        pdf_path=pdf_path if pdf_ok else "",
        success=True,
        note=f"dup={opts['dup_handling']}, unit={opts['target_unit']}",
    )

    return pivoted, True
