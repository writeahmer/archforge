"""
ArchForge Desktop GUI Application built with Tkinter / ttk.
Double-click executable interface with live plan tracking and log streaming.
"""

from __future__ import annotations

import os
import platform
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Dict, List, Optional

from archforge.agent.events import EventBus, EventType
from archforge.agent.generator import ProjectGenerator
from archforge.config import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
    AgentConfig,
)
from archforge.llm.deepseek_client import DeepSeekClient


def find_resource(rel_path: str) -> str:
    """Finds resource file checking PyInstaller bundle, cwd, parent, or package root."""
    # 1. PyInstaller bundled temporary dir (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / rel_path
        if p.exists():
            return str(p.resolve())
    # 2. Local current working directory
    p_cwd = Path(rel_path)
    if p_cwd.exists():
        return str(p_cwd.resolve())
    # 3. Parent directory (e.g. when exe is run directly inside dist/)
    p_parent = Path("..") / rel_path
    if p_parent.exists():
        return str(p_parent.resolve())
    # 4. Source package directory
    try:
        p_pkg = Path(__file__).resolve().parent.parent.parent / rel_path
        if p_pkg.exists():
            return str(p_pkg.resolve())
    except Exception:
        pass
    return ""


def get_default_output_dir() -> str:
    """Returns sensible default output directory."""
    if Path.cwd().name.lower() == "dist":
        return str((Path.cwd().parent / "generated_project").resolve())
    return str((Path.cwd() / "generated_project").resolve())


class ArchForgeGUI:
    """Tkinter Desktop UI for ArchForge Code Agent."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ArchForge - Architectural Code Agent")
        self.root.geometry("900x720")
        self.root.minsize(800, 600)

        # Apply clean theme
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.config = AgentConfig.load()
        self.event_bus = EventBus()
        self.event_queue = self.event_bus.get_queue()

        self.cancel_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.output_directory: Optional[Path] = None

        self._build_ui()
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. API Configuration Section
        cfg_frame = ttk.LabelFrame(main_frame, text=" DeepSeek LLM Configuration ", padding="8")
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        # Row 1: API Key & Toggle
        ttk.Label(cfg_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=3)
        self.api_key_var = tk.StringVar(value=self.config.api_key)
        self.api_key_entry = ttk.Entry(cfg_frame, textvariable=self.api_key_var, show="*", width=42)
        self.api_key_entry.grid(row=0, column=1, sticky=tk.EW, padx=4, pady=3)

        self.show_key_var = tk.BooleanVar(value=False)
        self.show_key_btn = ttk.Checkbutton(
            cfg_frame, text="Show", variable=self.show_key_var, command=self._toggle_key_visibility
        )
        self.show_key_btn.grid(row=0, column=2, padx=4, pady=3)

        self.test_conn_btn = ttk.Button(cfg_frame, text="Test Connection", command=self._test_connection)
        self.test_conn_btn.grid(row=0, column=3, padx=4, pady=3)

        self.save_key_var = tk.BooleanVar(value=bool(self.config.api_key))
        ttk.Checkbutton(cfg_frame, text="Save in Profile (%APPDATA%)", variable=self.save_key_var).grid(
            row=0, column=4, padx=4, pady=3
        )

        # Row 2: Model Name and Base URL
        ttk.Label(cfg_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=3)
        self.model_var = tk.StringVar(value=self.config.model or DEFAULT_MODEL)
        self.model_combo = ttk.Combobox(cfg_frame, textvariable=self.model_var, values=SUPPORTED_MODELS, width=20)
        self.model_combo.grid(row=1, column=1, sticky=tk.W, padx=4, pady=3)

        ttk.Label(cfg_frame, text="Base URL:").grid(row=1, column=2, sticky=tk.E, padx=4, pady=3)
        self.base_url_var = tk.StringVar(value=self.config.base_url or DEFAULT_BASE_URL)
        ttk.Entry(cfg_frame, textvariable=self.base_url_var, width=32).grid(
            row=1, column=3, columnspan=2, sticky=tk.EW, padx=4, pady=3
        )

        cfg_frame.columnconfigure(1, weight=1)

        # 2. File and Output Directory Inputs
        io_frame = ttk.LabelFrame(main_frame, text=" Input Architecture & Output Target ", padding="8")
        io_frame.pack(fill=tk.X, pady=(0, 8))

        # Doc Picker
        ttk.Label(io_frame, text="Documentation (.md):").grid(row=0, column=0, sticky=tk.W, padx=4, pady=3)
        default_doc = find_resource("samples/Architecture_Documentation.md")
        self.doc_path_var = tk.StringVar(value=default_doc)
        ttk.Entry(io_frame, textvariable=self.doc_path_var).grid(row=0, column=1, sticky=tk.EW, padx=4, pady=3)
        ttk.Button(io_frame, text="Browse...", command=self._pick_doc).grid(row=0, column=2, padx=4, pady=3)

        # Views Picker
        ttk.Label(io_frame, text="Views (.md):").grid(row=1, column=0, sticky=tk.W, padx=4, pady=3)
        default_views = find_resource("samples/Architecture_View.md")
        self.views_path_var = tk.StringVar(value=default_views)
        ttk.Entry(io_frame, textvariable=self.views_path_var).grid(row=1, column=1, sticky=tk.EW, padx=4, pady=3)
        ttk.Button(io_frame, text="Browse...", command=self._pick_views).grid(row=1, column=2, padx=4, pady=3)

        # Output Dir Picker
        ttk.Label(io_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=3)
        default_out = get_default_output_dir()
        self.out_path_var = tk.StringVar(value=default_out)
        ttk.Entry(io_frame, textvariable=self.out_path_var).grid(row=2, column=1, sticky=tk.EW, padx=4, pady=3)
        ttk.Button(io_frame, text="Browse...", command=self._pick_output_dir).grid(row=2, column=2, padx=4, pady=3)

        io_frame.columnconfigure(1, weight=1)

        # 3. Execution Control Buttons & Progress Bar
        ctrl_frame = ttk.Frame(main_frame, padding="4")
        ctrl_frame.pack(fill=tk.X, pady=(0, 8))

        self.generate_btn = ttk.Button(ctrl_frame, text="🚀 Generate Project", command=self._start_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=4)

        self.cancel_btn = ttk.Button(ctrl_frame, text="Cancel", state=tk.DISABLED, command=self._cancel_generation)
        self.cancel_btn.pack(side=tk.LEFT, padx=4)

        self.open_folder_btn = ttk.Button(ctrl_frame, text="📂 Open Output Folder", state=tk.DISABLED, command=self._open_output_folder)
        self.open_folder_btn.pack(side=tk.RIGHT, padx=4)

        self.progress_bar = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        # 4. Plan Checklist & Live Execution Logs (Paned)
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Top pane: Plan / Todo Checklist
        plan_frame = ttk.LabelFrame(paned, text=" Agent Plan & Todo Tracking ", padding="6")
        self.todo_listbox = tk.Listbox(plan_frame, height=5, font=("Consolas", 10))
        todo_scroll = ttk.Scrollbar(plan_frame, orient=tk.VERTICAL, command=self.todo_listbox.yview)
        self.todo_listbox.config(yscrollcommand=todo_scroll.set)
        self.todo_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        todo_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        paned.add(plan_frame, weight=1)

        # Bottom pane: Live Logs & Tool Call Stream
        log_frame = ttk.LabelFrame(paned, text=" Live Execution Logs & Tool Calls ", padding="6")
        self.log_text = ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9), height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        paned.add(log_frame, weight=2)

    def _toggle_key_visibility(self) -> None:
        self.api_key_entry.config(show="" if self.show_key_var.get() else "*")

    def _test_connection(self) -> None:
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model = self.model_var.get().strip()

        if not api_key:
            messagebox.showwarning("API Key Required", "Please enter a DeepSeek API key to test.")
            return

        self.log_text.insert(tk.END, f"[Connecting] Testing credentials with {base_url} ({model})...\n")
        self.log_text.see(tk.END)

        def run_test():
            client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)
            try:
                ok, msg = client.test_connection()
                if ok:
                    self.root.after(0, lambda: messagebox.showinfo("Connection Successful", f"DeepSeek API Connected!\n\n{msg}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Connection Failed", f"DeepSeek API Error:\n\n{msg}"))
            finally:
                client.close()

        threading.Thread(target=run_test, daemon=True).start()

    def _pick_doc(self) -> None:
        p = filedialog.askopenfilename(
            title="Select Architecture_Documentation.md",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if p:
            self.doc_path_var.set(p)

    def _pick_views(self) -> None:
        p = filedialog.askopenfilename(
            title="Select Architecture_View.md",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if p:
            self.views_path_var.set(p)

    def _pick_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Select Output Directory for Generated Project")
        if d:
            self.out_path_var.set(d)

    def _start_generation(self) -> None:
        doc_str = self.doc_path_var.get().strip()
        views_str = self.views_path_var.get().strip()
        out_str = self.out_path_var.get().strip()

        if not doc_str:
            messagebox.showerror("File Error", "Please select Architecture_Documentation.md file.")
            return
        if not views_str:
            messagebox.showerror("File Error", "Please select Architecture_View.md file.")
            return
        if not out_str:
            messagebox.showerror("Configuration Error", "Please specify an Output Directory.")
            return

        doc_p = Path(doc_str).resolve()
        views_p = Path(views_str).resolve()
        out_p = Path(out_str).resolve()

        if not doc_p.is_file():
            messagebox.showerror("File Error", f"Documentation file not found or is not a file:\n{doc_p}")
            return
        if not views_p.is_file():
            messagebox.showerror("File Error", f"Views file not found or is not a file:\n{views_p}")
            return

        self.config.api_key = self.api_key_var.get().strip()
        self.config.model = self.model_var.get().strip()
        self.config.base_url = self.base_url_var.get().strip()
        self.config.save_api_key_locally = self.save_key_var.get()
        self.config.save()

        self.output_directory = out_p
        self.cancel_event.clear()
        self.generate_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.open_folder_btn.config(state=tk.DISABLED)
        self.progress_bar.start(10)

        self.todo_listbox.delete(0, tk.END)
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, "=== STARTING ARCHFORGE GENERATION ===\n")

        def worker():
            try:
                generator = ProjectGenerator(
                    doc_path=doc_p,
                    views_path=views_p,
                    output_dir=out_p,
                    config=self.config,
                    event_bus=self.event_bus,
                    cancel_event=self.cancel_event,
                )
                result = generator.run()
                self.root.after(0, lambda: self._on_generation_finished(result))
            except Exception as e:
                err_dict = {"success": False, "error": str(e)}
                self.root.after(0, lambda: self._on_generation_finished(err_dict))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _cancel_generation(self) -> None:
        self.cancel_event.set()
        self.cancel_btn.config(state=tk.DISABLED)
        self.log_text.insert(tk.END, "\n[CANCEL] Cancellation signal dispatched to agent...\n")

    def _on_generation_finished(self, result: Dict[str, Any]) -> None:
        self.progress_bar.stop()
        self.generate_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.open_folder_btn.config(state=tk.NORMAL)

        if result.get("success"):
            messagebox.showinfo(
                "Generation Complete",
                f"Project successfully generated and verified!\nOutput location:\n{self.output_directory}",
            )
        elif result.get("reason") == "cancelled":
            messagebox.showwarning("Cancelled", "Project generation was cancelled.")
        else:
            messagebox.showerror("Generation Error", f"Generation finished with errors:\n{result.get('error', 'Unknown error')}")

    def _open_output_folder(self) -> None:
        if self.output_directory and self.output_directory.exists():
            if platform.system() == "Windows":
                os.startfile(str(self.output_directory))
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(self.output_directory)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_directory)])

    def _poll_events(self) -> None:
        """Polls events emitted by background agent loop to update GUI widgets."""
        try:
            while True:
                event = self.event_queue.get_nowait()
                if event.event_type == EventType.STATUS:
                    self.log_text.insert(tk.END, f"[STATUS] {event.message}\n")
                elif event.event_type == EventType.PLAN:
                    self.todo_listbox.delete(0, tk.END)
                    for item in event.data.get("todos", []):
                        st = item.get("status", "pending")
                        icon = "[✓]" if st == "completed" else "[►]" if st == "in_progress" else "[ ]"
                        self.todo_listbox.insert(tk.END, f" {icon} {item.get('task')}")
                elif event.event_type == EventType.TOOL_CALL:
                    self.log_text.insert(tk.END, f"  -> [TOOL CALL] {event.message}\n")
                elif event.event_type == EventType.TOOL_RESULT:
                    self.log_text.insert(tk.END, f"     {event.message}\n")
                elif event.event_type == EventType.THOUGHT:
                    self.log_text.insert(tk.END, f"  💭 {event.message}\n")
                elif event.event_type == EventType.WARNING:
                    self.log_text.insert(tk.END, f"[WARN] {event.message}\n")
                elif event.event_type == EventType.ERROR:
                    self.log_text.insert(tk.END, f"[ERROR] {event.message}\n")
                elif event.event_type == EventType.DONE:
                    self.log_text.insert(tk.END, f"\n=== FINISHED ===\n{event.message}\n")

                self.log_text.see(tk.END)
        except queue.Empty:
            pass

        self.root.after(100, self._poll_events)


def launch_gui() -> None:
    root = tk.Tk()
    app = ArchForgeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
