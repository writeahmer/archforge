"""
Entry point for python -m archforge and ArchForge.exe.
"""

from __future__ import annotations

import sys


def run() -> None:
    # If no arguments provided (e.g. double-clicked in Explorer or dist/) or --gui explicitly requested:
    # Launch Desktop GUI by default.
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        try:
            from archforge.gui.app import launch_gui
            launch_gui()
            return
        except Exception as e:
            import os
            import traceback
            from pathlib import Path
            appdata = os.getenv("APPDATA")
            log_dir = Path(appdata) / "ArchForge" if appdata else Path.home() / ".archforge"
            log_dir.mkdir(parents=True, exist_ok=True)
            crash_file = log_dir / "crash.log"
            crash_file.write_text(f"GUI launch failed:\n{traceback.format_exc()}", encoding="utf-8")
            try:
                import tkinter.messagebox as mb
                mb.showerror("ArchForge Startup Error", f"Failed to start GUI:\n{e}\n\nDetails saved in:\n{crash_file}")
            except Exception:
                pass
            print(f"Notice: GUI unavailable ({e}), falling back to CLI.", file=sys.stderr)
            from archforge.cli import main
            sys.exit(main())

    # Otherwise run command line interface
    from archforge.cli import main
    sys.exit(main())


if __name__ == "__main__":
    run()
