"""
excel_utils.py
──────────────
Everything that touches openpyxl formatting.

format_sheet()  — applies colours, borders, frozen panes, auto-width
                  to any worksheet.  Used for every sheet we write.
"""

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils  import get_column_letter

# ── Style definitions ─────────────────────────────────────────────────────────
# Defined once here so every sheet uses exactly the same look.
XL = {
    "hdr_fill":  PatternFill("solid", fgColor="2C3E50"),   # dark navy header
    "hdr_font":  Font(bold=True, color="FFFFFF", name="Calibri", size=10),
    "idx_fill":  PatternFill("solid", fgColor="D5D8DC"),   # grey sample column
    "idx_font":  Font(bold=True, name="Calibri", size=10),
    "dat_font":  Font(name="Calibri", size=10),
    "center":    Alignment(horizontal="center", vertical="center"),
    "left":      Alignment(horizontal="left",   vertical="center"),
    "border":    Border(
                     bottom=Side(style="thin", color="BDC3C7"),
                     right =Side(style="thin", color="BDC3C7"),
                 ),
    "uncal_fill":PatternFill("solid", fgColor="FDECEA"),   # red  — Uncal
    "neg_fill":  PatternFill("solid", fgColor="FEF9E7"),   # amber — negative
    "cal_fill":  PatternFill("solid", fgColor="1A5276"),   # deep blue — cal sheet
    "info_fill": PatternFill("solid", fgColor="EBF5FB"),   # pale blue — Run Info
}


def format_sheet(ws, flag_neg: bool = True, hdr_key: str = "hdr_fill"):
    """
    Apply consistent formatting to any openpyxl worksheet.

    What this does:
      • Row 1 gets the navy header style
      • Column 1 gets the grey index style
      • All other cells get the standard data font + border
      • "Uncal" cells get a red background
      • Negative numbers get an amber background  (if flag_neg=True)
      • Column widths are auto-fitted (capped between 8 and 32 characters)
      • Row 1 and Column A are frozen so you can scroll without losing headers

    Parameters
    ----------
    ws       : openpyxl Worksheet object
    flag_neg : True to highlight negative concentrations in amber
    hdr_key  : key in XL dict to use for the header fill colour
               ("hdr_fill" = navy,  "cal_fill" = deep blue for cal sheet)
    """
    for ri, row in enumerate(
            ws.iter_rows(min_row=1, max_row=ws.max_row,
                         max_col=ws.max_column), start=1):
        for cell in row:
            cell.border    = XL["border"]
            cell.alignment = XL["center"]

            if ri == 1:
                # Header row
                cell.fill = XL[hdr_key]
                cell.font = XL["hdr_font"]
            elif cell.column == 1:
                # Sample name column
                cell.fill      = XL["idx_fill"]
                cell.font      = XL["idx_font"]
                cell.alignment = XL["left"]
            else:
                # Data cell
                cell.font = XL["dat_font"]
                v = cell.value
                if isinstance(v, str) and v.lower() == "uncal":
                    cell.fill = XL["uncal_fill"]
                elif flag_neg and isinstance(v, (int, float)) and v < 0:
                    cell.fill = XL["neg_fill"]

    # Auto-fit column widths
    for ci in range(1, ws.max_column + 1):
        col_letter = get_column_letter(ci)
        max_len = max(
            (len(str(c.value or "")) for c in ws[col_letter]),
            default=8,
        )
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 8), 32)

    # Freeze header row and sample column
    ws.freeze_panes = "B2"


def fmt_info_sheet(ws):
    """
    Special formatting for the Run Info sheet.
    Column A is bold labels; Column B is plain values.
    No frozen panes needed here.
    """
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row,
                             max_col=ws.max_column):
        for cell in row:
            cell.font      = XL["dat_font"]
            cell.alignment = XL["left"]
            if cell.row == 1:
                cell.font = XL["hdr_font"]
                cell.fill = XL["hdr_fill"]
            elif cell.column == 1:
                cell.font = Font(bold=True, name="Calibri", size=10)
                cell.fill = XL["info_fill"]
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 64
