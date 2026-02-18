# Screenshot Wizard

AI-powered CLI tool that monitors a folder for screenshots and documents (PNG, JPG, JPEG, PDF), analyzes content using OpenAI GPT-4 Vision (auto-detecting text vs graphic), generates categorized PDFs with optional thumbnail embedding, and archives processed files. Includes a Tkinter GUI.

## Tech Stack
- Python 3.14, Click (CLI), OpenAI API, Watchdog (file monitoring), ReportLab (PDF generation)
- PyMuPDF (PDF-to-image conversion), Pillow (image processing, GUI preview)
- Config: YAML (`config/settings.yaml`) + `.env` (API key)

## Project Structure
- `src/main.py` - CLI entry point (click commands: init, watch, process, batch, config, gui) + `ProcessingOptions` dataclass + `ScreenshotWizard` orchestrator
- `src/gui.py` - Tkinter GUI (file list, preview, processing options, watcher integration, threaded processing)
- `src/analyzer.py` - OpenAI GPT-4 Vision integration with auto-detect (text/graphic), `AnalysisResult` dataclass
- `src/pdf_generator.py` - PDF creation with ReportLab, thumbnail embedding for graphic content
- `src/pdf_converter.py` - PyMuPDF wrapper for rendering PDF pages to PNG images
- `src/file_manager.py` - File operations (archive, listing, unique paths)
- `src/watcher.py` - Folder monitoring with watchdog (`FileHandler`, `PNGHandler` alias for backward compat)
- `src/config.py` - Configuration from YAML + environment variables, `SUPPORTED_EXTENSIONS` constant
- `tests/` - Unit tests for all modules (pytest, 74 tests)

## Commands
```bash
venv\Scripts\activate
python -m src.main init                    # Create folders
python -m src.main watch                   # Monitor input/ for new files
python -m src.main process <file>          # Process single file (PNG/JPG/JPEG/PDF)
python -m src.main process <file> --content-type graphic --thumbnail-size medium
python -m src.main process <file> --pdf-mode whole_document
python -m src.main batch                   # Process all pending files
python -m src.main config                  # Show configuration
python -m src.main gui                     # Launch Tkinter GUI
```

## Testing
```bash
venv\Scripts\python -m pytest tests/ -v
```

## Key Notes
- Supported formats: PNG, JPG, JPEG, PDF (defined in `config.SUPPORTED_EXTENSIONS`)
- Content type detection: auto-detect (default), text, or graphic — controlled via CLI flags or GUI radio buttons
- Graphic content: embeds a thumbnail (small/medium/full) + AI description in output PDF
- PDF input: rendered to PNG pages via PyMuPDF, then analyzed per-page or as whole document
- Thumbnail sizing: uses Pillow to read actual pixel dimensions, constrains height to fit page (avoids ReportLab overflow)
- Windows: use `iterdir()` + suffix check instead of separate glob patterns to avoid case-insensitive duplicates
- Windows: use `tempfile.mkstemp()` + `os.close(fd)` for PyMuPDF temp files (NamedTemporaryFile holds lock)
- ReportLab: avoid naming custom styles `BodyText` (conflicts with built-in); current custom style is `CustomBody`
- GUI threading: Tkinter mainloop on main thread, watchdog on its own thread, processing in `threading.Thread`, queues polled every 250ms via `root.after()`
- API key must be set in `.env` file (not committed to git)
