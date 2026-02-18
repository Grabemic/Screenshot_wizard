# Screenshot Wizard

AI-powered CLI tool that monitors a folder for PNG screenshots, extracts text using OpenAI GPT-4 Vision, generates categorized PDFs, and archives processed files.

## Tech Stack
- Python 3.14, Click (CLI), OpenAI API, Watchdog (file monitoring), ReportLab (PDF generation)
- Config: YAML (`config/settings.yaml`) + `.env` (API key)

## Project Structure
- `src/main.py` - CLI entry point (click commands: init, watch, process, batch, config)
- `src/analyzer.py` - OpenAI GPT-4 Vision integration
- `src/pdf_generator.py` - PDF creation with ReportLab
- `src/file_manager.py` - File operations (archive, listing, unique paths)
- `src/watcher.py` - Folder monitoring with watchdog
- `src/config.py` - Configuration from YAML + environment variables
- `tests/` - Unit tests for all modules (pytest)

## Commands
```bash
venv\Scripts\activate
python -m src.main init          # Create folders
python -m src.main watch         # Monitor input/ for new PNGs
python -m src.main process <file>  # Process single PNG
python -m src.main batch         # Process all pending PNGs
python -m src.main config        # Show configuration
```

## Testing
```bash
venv\Scripts\python -m pytest tests/ -v
```

## Key Notes
- Windows: file glob patterns are case-insensitive, use `iterdir()` + suffix check instead of separate `*.png` + `*.PNG` globs to avoid duplicates
- ReportLab: avoid naming custom styles `BodyText` (conflicts with built-in); current custom style is `CustomBody`
- API key must be set in `.env` file (not committed to git)
