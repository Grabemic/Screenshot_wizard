"""Tkinter GUI for Screenshot Wizard."""

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Literal

from PIL import Image, ImageTk

from .config import SUPPORTED_EXTENSIONS, Config
from .main import ProcessingOptions, ScreenshotWizard
from .pdf_converter import PDFPageConverter
from .watcher import FolderWatcher

logger = logging.getLogger(__name__)


class ScreenshotWizardGUI:
    """Tkinter GUI for Screenshot Wizard."""

    def __init__(self, config: Config):
        self.config = config
        self.wizard = ScreenshotWizard(config)

        # Queues for thread communication
        self.watcher_queue: queue.Queue[Path] = queue.Queue()
        self.result_queue: queue.Queue[tuple[str, bool]] = queue.Queue()

        # State
        self._watcher: FolderWatcher | None = None
        self._watcher_running = False
        self._new_files: set[str] = set()
        self._processing = False
        self._preview_photo: ImageTk.PhotoImage | None = None

        # Build UI
        self.root = tk.Tk()
        self.root.title("Screenshot Wizard")
        self.root.geometry("1000x650")
        self.root.minsize(800, 500)

        self._build_toolbar()
        self._build_main_panels()
        self._build_status_bar()

        # Start polling queues
        self._poll_queues()
        # Start auto-refreshing file list
        self._auto_refresh_file_list()

    # ── Toolbar ──────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        # Watcher toggle
        self.watcher_btn = ttk.Button(
            toolbar, text="Start Watcher", command=self._toggle_watcher
        )
        self.watcher_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Input folder
        ttk.Label(toolbar, text="Input:").pack(side=tk.LEFT)
        self.input_var = tk.StringVar(value=str(self.config.input_folder))
        self.input_entry = ttk.Entry(toolbar, textvariable=self.input_var, width=25)
        self.input_entry.pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(toolbar, text="Browse", command=self._browse_input).pack(
            side=tk.LEFT, padx=(0, 10)
        )

        # Output folder
        ttk.Label(toolbar, text="Output:").pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value=str(self.config.output_folder))
        self.output_entry = ttk.Entry(toolbar, textvariable=self.output_var, width=25)
        self.output_entry.pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(toolbar, text="Browse", command=self._browse_output).pack(
            side=tk.LEFT
        )

    # ── Main Panels ─────────────────────────────────────────────────

    def _build_main_panels(self) -> None:
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: file list
        left = ttk.LabelFrame(main, text="Files", padding=5)
        main.add(left, weight=1)

        self.file_listbox = tk.Listbox(left, selectmode=tk.SINGLE)
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)

        scrollbar = ttk.Scrollbar(
            left, orient=tk.VERTICAL, command=self.file_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # Center panel: preview
        center = ttk.LabelFrame(main, text="Preview", padding=5)
        main.add(center, weight=2)

        self.preview_label = ttk.Label(center, text="Select a file to preview")
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # Right panel: options
        right = ttk.LabelFrame(main, text="Processing Options", padding=10)
        main.add(right, weight=1)

        # Content type
        ttk.Label(right, text="Content Type:").pack(anchor=tk.W, pady=(0, 5))
        self.content_type_var = tk.StringVar(value="auto")
        for val, label in [
            ("auto", "Auto-detect"),
            ("text", "Text Document"),
            ("graphic", "Graphic / Picture"),
        ]:
            ttk.Radiobutton(
                right,
                text=label,
                variable=self.content_type_var,
                value=val,
                command=self._on_options_changed,
            ).pack(anchor=tk.W)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Thumbnail size
        self.thumb_frame = ttk.Frame(right)
        self.thumb_frame.pack(fill=tk.X)
        ttk.Label(self.thumb_frame, text="Thumbnail Size:").pack(
            anchor=tk.W, pady=(0, 5)
        )
        self.thumbnail_var = tk.StringVar(value="medium")
        for val, label in [
            ("small", "Small"),
            ("medium", "Medium"),
            ("full", "Full Width"),
        ]:
            ttk.Radiobutton(
                self.thumb_frame,
                text=label,
                variable=self.thumbnail_var,
                value=val,
            ).pack(anchor=tk.W)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # PDF mode
        self.pdf_mode_frame = ttk.Frame(right)
        self.pdf_mode_frame.pack(fill=tk.X)
        ttk.Label(self.pdf_mode_frame, text="PDF Mode:").pack(
            anchor=tk.W, pady=(0, 5)
        )
        self.pdf_mode_var = tk.StringVar(value="per_page")
        for val, label in [
            ("per_page", "Per Page"),
            ("whole_document", "Whole Document"),
        ]:
            ttk.Radiobutton(
                self.pdf_mode_frame,
                text=label,
                variable=self.pdf_mode_var,
                value=val,
            ).pack(anchor=tk.W)

        # Process button
        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        self.process_btn = ttk.Button(
            right, text="Process File", command=self._process_selected
        )
        self.process_btn.pack(fill=tk.X, pady=(5, 0))

        # Initial visibility
        self._on_options_changed()

    # ── Status Bar ───────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ── Watcher Control ─────────────────────────────────────────────

    def _toggle_watcher(self) -> None:
        if self._watcher_running:
            self._stop_watcher()
        else:
            self._start_watcher()

    def _start_watcher(self) -> None:
        input_folder = Path(self.input_var.get())
        input_folder.mkdir(parents=True, exist_ok=True)

        self._watcher = FolderWatcher(
            input_folder=input_folder,
            callback=self._on_watcher_detected,
            polling_interval=self.config.polling_interval,
        )
        self._watcher.start()
        self._watcher_running = True

        self.watcher_btn.config(text="Stop Watcher")
        self._set_status("Watching")

    def _stop_watcher(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self._watcher_running = False

        self.watcher_btn.config(text="Start Watcher")
        self._set_status("Ready")

    def _on_watcher_detected(self, file_path: Path) -> None:
        """Called from watchdog thread — puts file into queue."""
        self.watcher_queue.put(file_path)

    # ── Folder Browsing ──────────────────────────────────────────────

    def _browse_input(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Input Folder",
            initialdir=self.input_var.get(),
        )
        if folder:
            self.input_var.set(folder)
            self._save_folder_settings()
            # Restart watcher on new folder if running
            if self._watcher_running:
                self._stop_watcher()
                self._start_watcher()
            self._refresh_file_list()

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.output_var.get(),
        )
        if folder:
            self.output_var.set(folder)
            self._save_folder_settings()

    def _save_folder_settings(self) -> None:
        self.config.save_folder_settings(
            self.input_var.get(), self.output_var.get()
        )

    # ── File List ────────────────────────────────────────────────────

    def _refresh_file_list(self) -> None:
        input_folder = Path(self.input_var.get())
        if not input_folder.exists():
            return

        # Remember current selection
        current_sel = self._get_selected_filename()

        self.file_listbox.delete(0, tk.END)

        try:
            files = sorted(
                (
                    f
                    for f in input_folder.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
                ),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return

        for f in files:
            prefix = "[NEW] " if f.name in self._new_files else ""
            self.file_listbox.insert(tk.END, f"{prefix}{f.name}")

        # Restore selection if still present
        if current_sel:
            for i in range(self.file_listbox.size()):
                item = self.file_listbox.get(i)
                if item.replace("[NEW] ", "") == current_sel:
                    self.file_listbox.selection_set(i)
                    break

    def _auto_refresh_file_list(self) -> None:
        self._refresh_file_list()
        self.root.after(2000, self._auto_refresh_file_list)

    def _get_selected_filename(self) -> str | None:
        sel = self.file_listbox.curselection()
        if not sel:
            return None
        item = self.file_listbox.get(sel[0])
        return item.replace("[NEW] ", "")

    def _get_selected_filepath(self) -> Path | None:
        name = self._get_selected_filename()
        if name is None:
            return None
        return Path(self.input_var.get()) / name

    # ── Preview ──────────────────────────────────────────────────────

    def _on_file_select(self, _event: tk.Event | None = None) -> None:
        file_path = self._get_selected_filepath()
        if file_path is None or not file_path.exists():
            return

        self._update_options_visibility(file_path)
        self._show_preview(file_path)

    def _show_preview(self, file_path: Path) -> None:
        try:
            if file_path.suffix.lower() == ".pdf":
                self._show_pdf_preview(file_path)
            else:
                self._show_image_preview(file_path)
        except Exception as e:
            self.preview_label.config(image="", text=f"Preview error: {e}")
            self._preview_photo = None

    def _show_image_preview(self, file_path: Path) -> None:
        img = Image.open(file_path)
        # Fit to preview area
        max_w, max_h = 400, 400
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self._preview_photo, text="")

    def _show_pdf_preview(self, file_path: Path) -> None:
        """Render first page of PDF for preview."""
        import tempfile

        converter = PDFPageConverter(dpi=150)
        with tempfile.TemporaryDirectory() as tmpdir:
            rendered = Path(tmpdir) / "preview.png"
            converter.render_page(file_path, 0, rendered)
            self._show_image_preview(rendered)

    # ── Options Visibility ───────────────────────────────────────────

    def _on_options_changed(self) -> None:
        content_type = self.content_type_var.get()

        # Show thumbnail options when graphic is selected
        if content_type == "graphic":
            self.thumb_frame.pack(fill=tk.X)
        else:
            self.thumb_frame.pack_forget()

        # PDF mode visibility handled by file selection
        file_path = self._get_selected_filepath()
        if file_path:
            self._update_options_visibility(file_path)

    def _update_options_visibility(self, file_path: Path) -> None:
        """Show/hide PDF mode options based on selected file type."""
        if file_path.suffix.lower() == ".pdf":
            self.pdf_mode_frame.pack(fill=tk.X)
        else:
            self.pdf_mode_frame.pack_forget()

        # Thumbnail frame visibility based on content type
        content_type = self.content_type_var.get()
        if content_type == "graphic":
            self.thumb_frame.pack(fill=tk.X)
        else:
            self.thumb_frame.pack_forget()

    # ── Processing ───────────────────────────────────────────────────

    def _process_selected(self) -> None:
        file_path = self._get_selected_filepath()
        if file_path is None or not file_path.exists():
            messagebox.showwarning("No File", "Please select a file to process.")
            return

        if self._processing:
            messagebox.showinfo("Busy", "Processing is already in progress.")
            return

        self._processing = True
        self.process_btn.config(state=tk.DISABLED)
        self._set_status("Processing")

        content_type = self.content_type_var.get()
        options = ProcessingOptions(
            content_type_override=None if content_type == "auto" else content_type,
            thumbnail_size=self.thumbnail_var.get(),
            pdf_mode=self.pdf_mode_var.get(),
        )

        thread = threading.Thread(
            target=self._process_in_thread,
            args=(file_path, options),
            daemon=True,
        )
        thread.start()

    def _process_in_thread(self, file_path: Path, options: ProcessingOptions) -> None:
        """Run processing in a background thread."""
        try:
            success = self.wizard.process_file(file_path, options)
            self.result_queue.put((file_path.name, success))
        except Exception as e:
            logger.error(f"Processing thread error: {e}")
            self.result_queue.put((file_path.name, False))

    # ── Queue Polling ────────────────────────────────────────────────

    def _poll_queues(self) -> None:
        # Check watcher queue
        try:
            while True:
                file_path = self.watcher_queue.get_nowait()
                self._new_files.add(file_path.name)
                self._refresh_file_list()
        except queue.Empty:
            pass

        # Check result queue
        try:
            while True:
                filename, success = self.result_queue.get_nowait()
                self._processing = False
                self.process_btn.config(state=tk.NORMAL)
                self._new_files.discard(filename)

                if success:
                    self._set_status("Ready")
                    messagebox.showinfo(
                        "Success", f"Successfully processed: {filename}"
                    )
                else:
                    self._set_status("Ready")
                    messagebox.showerror(
                        "Error", f"Failed to process: {filename}"
                    )

                self._refresh_file_list()
        except queue.Empty:
            pass

        self.root.after(250, self._poll_queues)

    # ── Helpers ──────────────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        self.status_var.set(status)

    def run(self) -> None:
        """Start the GUI main loop."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self) -> None:
        if self._watcher_running:
            self._stop_watcher()
        self.root.destroy()
