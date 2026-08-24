"""
main.py
───────
Entry point for the Agilent ICP Cleaner application.
Double-click this file to launch.
"""
import sys
import os
import tkinter as tk
from app import ICPLauncherApp


def show_splash(root):
    splash = tk.Toplevel()
    splash.overrideredirect(True)
    SW, SH = splash.winfo_screenwidth(), splash.winfo_screenheight()
    W, H = 400, 300
    splash.geometry(f"{W}x{H}+{(SW-W)//2}+{(SH-H)//2}")
    splash.configure(bg="#1E2535")

    _here = os.path.dirname(os.path.abspath(__file__))
    _logo = os.path.join(_here, "ICP_CVS_Cleaner_Logo.png")
    if os.path.isfile(_logo):
        try:
            img = tk.PhotoImage(file=_logo).subsample(2, 2)
            lbl = tk.Label(splash, image=img, bg="#1E2535")
            lbl.image = img
            lbl.pack(pady=(40, 10))
        except Exception:
            pass

    tk.Label(splash, text="Agilent ICP Cleaner  v1.0.0",
             font=("Segoe UI", 13, "bold"),
             bg="#1E2535", fg="#4A9EFF").pack()
    tk.Label(splash, text="Loading…",
             font=("Segoe UI", 9),
             bg="#1E2535", fg="#8892A0").pack(pady=6)

    splash.update()
    root.after(5000, splash.destroy)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    root.withdraw()

    _here = os.path.dirname(os.path.abspath(__file__))
    _logo = os.path.join(_here, "ICP_CVS_Cleaner_Logo.png")
    if os.path.isfile(_logo):
        try:
            icon = tk.PhotoImage(file=_logo)
            root.iconphoto(True, icon)
        except Exception:
            pass

    show_splash(root)
    root.after(2500, root.deiconify)

    ICPLauncherApp(root)

    if sys.platform == "darwin":
        root.attributes("-zoomed", True)
    else:
        root.state("zoomed")

    root.mainloop()


if __name__ == "__main__":
    main()
