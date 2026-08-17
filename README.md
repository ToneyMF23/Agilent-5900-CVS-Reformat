# Agilent-5900-CVS-Reformat

The Why: This code was written to convert Agilent 5900 generic CVS files into a more user friendly as well as creating Calibration PDF's. Generic Agilent CVS files output data vertically with each ion tested per sample stacked one upon another. This means ICP-OES runs with as few as 10 samples with 10 selected ions can be hundreds of rows of data that is not user friendly for data compilation. This code orientates this data into a more user friendly CVS and generates calibrations PDF's for data validation.

Prerequisite: See `Requirements.txt` for required Python packages.

Vscode Use Method:
1. Create a parent folder
2. Copy all code files into that folder
3. Open the folder in VS Code (ensure Python is installed)
4. Select `main.py` and click Run
5. For **Single File Conversion**: Click Browse, select file, specify parameters. Output CSV and PDF save to your chosen location (or input folder if none selected)
6. For **Batch File Conversion**: Click Browse, select folder, specify parameters. All outputs save to your chosen location. A master workbook is generated for all batch results.
  
Standalone-Application Method:
1. Create a parent folder
2. Copy all code files into that folder
3. Open the folder in VS Code
4. Ensure all `.py` files are visible
5. In the terminal, run: python build_exe.py
6. Find `Agilent 5900 CSV Reformator.exe` in the `dist/` folder
7. Double-click `Agilent 5900 CSV Reformator.exe` to launch the application
   **Note:** Launching may take up to 1 minute while the app loads, I am sorry for its slow nature
8. For **Single File Conversion**: Click Browse, select file, specify parameters. Output CSV and PDF save to your chosen location (or input folder if none selected)
9. For **Batch File Conversion**: Click Browse, select folder, specify parameters. All outputs save to your chosen location. A master workbook is generated for all batch results.
