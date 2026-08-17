"""
pdf_export.py
─────────────
Builds the calibration curve PDF report.

One page per element:
  • Scatter plot of Concentration vs Intensity
  • Regression line overlay (linear or quadratic)
  • R² annotation + instrument correlation coefficient
  • Data table below the chart  (optional)

Cover page with run metadata.
"""

import os
import io
import re
import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")    # render without a display — no tkinter conflict
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from reportlab.lib.pagesizes import letter
from reportlab.lib           import colors
from reportlab.lib.units     import inch
from reportlab.platypus      import (SimpleDocTemplate, Paragraph, Spacer,
                                      Table, TableStyle, Image as RLImage,
                                      HRFlowable, PageBreak)
from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums     import TA_CENTER

from constants import APP_NAME, VERSION


def build_cal_pdf(df_std, out_path: str, opts: dict,
                  input_path: str) -> bool:
    """
    Generate the calibration curve PDF.

    Parameters
    ----------
    df_std      : DataFrame of STD-type rows from the ICP file
    out_path    : full path where the PDF should be saved
    opts        : user options dict (cal_pdf_r2, cal_pdf_table, target_unit)
    input_path  : path to the original source file (for the cover page)

    Returns
    -------
    True if the PDF was written successfully, False otherwise.
    """
    import pandas as pd

    # Make Concentration and Intensity numeric
    for col in ["Concentration", "Intensity"]:
        if col in df_std.columns:
            df_std[col] = pd.to_numeric(df_std[col], errors="coerce")

    if not {"Concentration", "Intensity"}.issubset(df_std.columns):
        return False

    elements = df_std["Element"].dropna().unique().tolist()
    if not elements:
        return False

    # ── ReportLab styles ──────────────────────────────────────────────────────
    base     = getSampleStyleSheet()
    title_s  = ParagraphStyle("title",  parent=base["Title"],
                               fontSize=18,
                               textColor=colors.HexColor("#1A2744"),
                               spaceAfter=4)
    sub_s    = ParagraphStyle("sub",    parent=base["Normal"],
                               fontSize=10,
                               textColor=colors.HexColor("#555"),
                               spaceAfter=2)
    elem_s   = ParagraphStyle("elem",   parent=base["Heading1"],
                               fontSize=13,
                               textColor=colors.HexColor("#2C3E50"),
                               spaceBefore=6, spaceAfter=4)
    note_s   = ParagraphStyle("note",   parent=base["Normal"],
                               fontSize=8,
                               textColor=colors.HexColor("#777"),
                               spaceAfter=2)
    hdr_cs   = ParagraphStyle("hdr_c",  parent=base["Normal"],
                               fontSize=8, textColor=colors.white,
                               alignment=TA_CENTER)
    dat_cs   = ParagraphStyle("dat_c",  parent=base["Normal"],
                               fontSize=8,
                               textColor=colors.HexColor("#1A1A1A"),
                               alignment=TA_CENTER)

    doc   = SimpleDocTemplate(out_path, pagesize=letter,
                               leftMargin=0.6*inch, rightMargin=0.6*inch,
                               topMargin=0.5*inch,  bottomMargin=0.5*inch)
    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.0*inch))
    story.append(Paragraph("Calibration Curves", title_s))
    story.append(Paragraph("Agilent ICP-OES Analysis Report", sub_s))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor("#4A9EFF"),
                             spaceAfter=12))
    story.append(Spacer(1, 0.2*inch))

    # Detect feed name from STD labels (generic — not hardcoded)
    feed_name = "Unknown"
    if "Label" in df_std.columns:
        for lbl in df_std["Label"].dropna().unique():
            m = re.match(r'^(.+?)\s+\d+%', str(lbl))
            if m:
                feed_name = m.group(1).strip()
                break

    fit_types = (", ".join(sorted(set(df_std["Calibration fit"]
                                       .dropna().unique())))
                 if "Calibration fit" in df_std.columns else "N/A")

    meta = Table([
        ["Generated",     datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")],
        ["Source file",   os.path.basename(input_path)],
        ["Feed / matrix", feed_name],
        ["Elements",      str(len(elements))],
        ["Unit",          opts["target_unit"]],
        ["Fit types",     fit_types],
        ["Created by",    f"{APP_NAME} v{VERSION}"],
    ], colWidths=[1.5*inch, 4.4*inch])
    meta.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("FONTNAME",       (0, 0), (0, -1),  "Helvetica-Bold"),
        ("TEXTCOLOR",      (0, 0), (0, -1),  colors.HexColor("#2C3E50")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#F4F7FB"), colors.HexColor("#FFFFFF")]),
        ("BOX",  (0, 0), (-1, -1), 0.5,  colors.HexColor("#CCC")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDD")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(meta)
    story.append(PageBreak())

    # ── One page per element ──────────────────────────────────────────────────
    for elem in elements:
        edf = (df_std[df_std["Element"] == elem]
               .dropna(subset=["Concentration", "Intensity"])
               .copy())
        if len(edf) < 2:
            continue

        x        = edf["Concentration"].values.astype(float)
        y        = edf["Intensity"].values.astype(float)
        lbls     = edf["Label"].tolist()
        fit_type = (edf["Calibration fit"].iloc[0]
                    if "Calibration fit" in edf.columns else "Linear")
        corr     = (edf["Correlation coefficient"].iloc[0]
                    if "Correlation coefficient" in edf.columns else "-")
        unit_col = edf["Unit"].iloc[0] if "Unit" in edf.columns else ""
        elem_lbl = (edf["Element Label"].iloc[0]
                    if "Element Label" in edf.columns else elem)

        # Matplotlib figure
        fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=130)
        fig.patch.set_facecolor("#F8FAFD")
        ax.set_facecolor("#FFFFFF")

        ax.scatter(x, y, color="#4A9EFF", s=60, zorder=5,
                   edgecolors="#1A6ECC", linewidths=0.8, label="Standards")

        # Regression overlay
        r2 = float("nan")
        try:
            deg    = 2 if str(fit_type).lower() in ("quadratic", "rational") else 1
            coeffs = np.polyfit(x, y, deg)
            x_line = np.linspace(min(x) * 0.95, max(x) * 1.05, 300)
            ax.plot(x_line, np.polyval(coeffs, x_line),
                    color="#E74C3C", linewidth=1.8, linestyle="--",
                    label=f"{fit_type} fit", zorder=4)
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2     = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        except Exception:
            pass

        # Annotation box
        if opts.get("cal_pdf_r2", True):
            ann = []
            if not np.isnan(r2):
                ann.append(f"R\u00b2 = {r2:.5f}")
            if str(corr).strip() not in ("", "-", "nan"):
                ann.append(f"r (instrument) = {corr}")
            ann.append(f"Fit: {fit_type}")
            ax.text(0.03, 0.97, "\n".join(ann),
                    transform=ax.transAxes, fontsize=8, va="top",
                    bbox=dict(boxstyle="round,pad=0.4",
                              facecolor="#EBF5FB", alpha=0.9,
                              edgecolor="#4A9EFF", lw=0.8))

        # Point labels
        for xi, yi, lb in zip(x, y, lbls):
            ax.annotate(str(lb), (xi, yi),
                        textcoords="offset points", xytext=(4, 5),
                        fontsize=6.5, color="#444", clip_on=True)

        unit_disp = (opts["target_unit"].split(" ")[0]
                     if opts["target_unit"] != "Keep as-is" else unit_col)
        ax.set_xlabel(f"Concentration ({unit_disp})", fontsize=9, labelpad=6)
        ax.set_ylabel("Intensity (CPS)", fontsize=9, labelpad=6)
        ax.set_title(f"{elem}  \u00b7  {elem_lbl}", fontsize=11,
                     fontweight="bold", color="#1A2744", pad=8)
        ax.tick_params(labelsize=8)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.grid(True, linestyle="--", linewidth=0.4, color="#DDE", alpha=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=8, framealpha=0.8)
        plt.tight_layout(pad=1.2)

        # Save figure to an in-memory buffer (avoids temp files)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)

        # ReportLab page content
        story.append(Paragraph(f"{elem}  \u00b7  {elem_lbl}", elem_s))
        story.append(HRFlowable(width="100%", thickness=1,
                                 color=colors.HexColor("#4A9EFF"),
                                 spaceAfter=6))
        story.append(RLImage(buf, width=6.5*inch, height=3.65*inch))
        story.append(Spacer(1, 0.1*inch))

        # Optional data table
        if opts.get("cal_pdf_table", True):
            td = [[Paragraph("Standard",            hdr_cs),
                   Paragraph(f"Conc. ({unit_disp})", hdr_cs),
                   Paragraph("Intensity (CPS)",     hdr_cs)]]
            for xi, yi, lb in zip(x, y, lbls):
                td.append([Paragraph(str(lb),      dat_cs),
                           Paragraph(f"{xi:,.4g}", dat_cs),
                           Paragraph(f"{yi:,.0f}", dat_cs)])
            ct = Table(td, colWidths=[2.5*inch, 2.0*inch, 2.0*inch])
            ct.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#2C3E50")),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1),
                 [colors.HexColor("#F4F7FB"), colors.HexColor("#FFFFFF")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCC")),
                ("BOX",  (0, 0), (-1, -1), 0.6, colors.HexColor("#999")),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(ct)

        story.append(Paragraph(
            f"Regression: {fit_type.lower()} degree overlay. "
            "Instrument r stored in source file.", note_s))
        story.append(PageBreak())

    doc.build(story)
    return True
