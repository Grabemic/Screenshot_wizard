# Screenshot Wizard

AI-powered CLI tool that monitors a folder for PNG screenshots, extracts text content using OpenAI GPT-4 Vision, categorizes the content, and generates structured PDF documents.

## Features

- **Folder Monitoring**: Continuously watches input folder for new PNG files
- **AI-Powered Analysis**: Uses OpenAI GPT-4 Vision to extract and understand screenshot content
- **Dynamic Categorization**: AI suggests up to 2 relevant categories based on content
- **PDF Generation**: Creates formatted PDFs with categories header and extracted text
- **File Management**: Moves processed PNGs to archive folder

## Installation

### Prerequisites

- Python 3.10 or higher
- OpenAI API key

### Setup

1. Clone or download this project

2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your API key:
   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env    # Linux/macOS
   ```

   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

5. Initialize the project folders:
   ```bash
   python -m src.main init
   ```

## Usage

### Start Folder Watcher (Main Mode)

Monitor the input folder for new screenshots:

```bash
python -m src.main watch
```

With processing of existing files:

```bash
python -m src.main watch --process-existing
```

### Process a Single File

```bash
python -m src.main process path/to/screenshot.png
```

### Batch Process All Pending Files

```bash
python -m src.main batch
```

### View Configuration

```bash
python -m src.main config
```

## Configuration

Settings are stored in `config/settings.yaml`:

| Setting | Description | Default |
|---------|-------------|---------|
| `folders.input` | Path to monitor for PNG files | `./input` |
| `folders.output` | Path for generated PDFs | `./output` |
| `folders.archive` | Path for processed PNGs | `./archive` |
| `processing.polling_interval` | Seconds between folder checks | `5` |
| `processing.max_categories` | Maximum categories per document | `2` |

## PDF Output Format

Generated PDFs include:

```
┌─────────────────────────────────────────────┐
│ CATEGORIES: [Category 1] | [Category 2]     │
│─────────────────────────────────────────────│
│                                             │
│ [Extracted text content from screenshot]    │
│                                             │
│─────────────────────────────────────────────│
│ Source: original_filename.png               │
│ Processed: 2024-01-15 14:30:00              │
└─────────────────────────────────────────────┘
```

## Project Structure

```
screenshot_wizard/
├── src/
│   ├── __init__.py          # Package init
│   ├── main.py              # CLI entry point
│   ├── watcher.py           # Folder monitoring
│   ├── analyzer.py          # OpenAI GPT-4 Vision integration
│   ├── pdf_generator.py     # PDF creation
│   ├── file_manager.py      # File operations
│   └── config.py            # Configuration management
├── config/
│   └── settings.yaml        # Default configuration
├── tests/
│   └── test_*.py            # Unit tests
├── input/                   # Drop PNG files here
├── output/                  # Generated PDFs appear here
├── archive/                 # Processed PNGs are moved here
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .env                     # Your API key (local only)
└── README.md
```

## Security

**Your API key is stored ONLY locally:**

- `.env` file is in `.gitignore` and never committed
- API key is read at runtime only, never logged
- No cloud storage or remote transmission of the key

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Troubleshooting

### "API key not configured" error

1. Ensure `.env` file exists in the project root
2. Check that `OPENAI_API_KEY` is set correctly
3. Make sure there are no extra spaces or quotes around the key

### PDF generation fails

- Check that the PNG file is valid and not corrupted
- Ensure the output folder has write permissions

### Watcher not detecting files

- Files must have `.png` or `.PNG` extension
- Ensure the input folder path is correct
- Check file permissions

## License

MIT License
