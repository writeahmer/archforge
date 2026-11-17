# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
project_root = Path.cwd() / "generated_project"

datas = [
    (str(project_root / "sql" / "game_ddl.sql"), "sql"),
]

a = Analysis(
    [str(project_root / "src" / "gui_game.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "src.common",
        "src.game.engine",
        "src.game.game_session",
        "src.game.state_machine",
        "src.game.help",
        "src.question.generator",
        "src.question.validator",
        "src.score.leaderboard",
        "sqlite3",
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SpaceFractions",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed GUI application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
