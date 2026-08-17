import os
import sys
import subprocess

print("\n" + "="*60)
print("  Building ICP-Cleaner.exe...")
print("="*60 + "\n")

if not os.path.exists("main.py"):
    print("ERROR: main.py not found in current folder")
    sys.exit(1)

print("✅ Found main.py")
print("Installing PyInstaller if needed...")
subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

print("Building executable...")
subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "Agilent 5900 CSV Reformator",
    "--icon=ICP_CVS_Cleaner_Logo.png",
    "main.py"
])

print("\n" + "="*60)
print("✅ Done! Find ICP-Cleaner.exe in the 'dist' folder")
print("="*60 + "\n")
