"""CLI entry point for Screenshot Wizard."""

import logging
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import click

from .analyzer import ScreenshotAnalyzer
from .config import SUPPORTED_EXTENSIONS, Config
from .file_manager import FileManager
from .pdf_converter import PDFPageConverter
from .pdf_generator import PDFGenerator
from .watcher import FolderWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingOptions:
    """Options for file processing."""

    content_type_override: Literal["text", "graphic"] | None = None
    thumbnail_size: Literal["small", "medium", "full"] = "medium"
    pdf_mode: Literal["per_page", "whole_document"] = "per_page"


class ScreenshotWizard:
    """Main application class that orchestrates all components."""

    def __init__(self, config: Config):
        """Initialize Screenshot Wizard.

        Args:
            config: Application configuration
        """
        self.config = config

        # Initialize components
        self.analyzer = ScreenshotAnalyzer(
            api_key=config.openai_api_key,
            model=config.openai_model,
            max_tokens=config.openai_max_tokens,
        )
        self.pdf_generator = PDFGenerator(config.pdf_settings)
        self.file_manager = FileManager(
            archive_folder=config.archive_folder,
            output_folder=config.output_folder,
        )
        self.pdf_converter = PDFPageConverter()

    def process_file(self, file_path: Path, options: ProcessingOptions | None = None) -> bool:
        """Process a single file.

        Args:
            file_path: Path to the file
            options: Processing options (None uses defaults)

        Returns:
            True if processing was successful
        """
        if options is None:
            options = ProcessingOptions()

        try:
            logger.info(f"Processing: {file_path.name}")

            if file_path.suffix.lower() == ".pdf":
                return self._process_pdf(file_path, options)
            else:
                return self._process_image(file_path, options)

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            return False

    def _process_image(self, file_path: Path, options: ProcessingOptions) -> bool:
        """Process an image file (PNG, JPG, JPEG).

        Args:
            file_path: Path to the image
            options: Processing options

        Returns:
            True if successful
        """
        result = self.analyzer.analyze(
            file_path,
            max_categories=self.config.max_categories,
            content_type_override=options.content_type_override,
        )

        pdf_path = self.file_manager.get_pdf_output_path(file_path.name)
        self.pdf_generator.generate(
            result,
            pdf_path,
            timestamp=datetime.now(),
            thumbnail_size=options.thumbnail_size,
        )

        self.file_manager.archive_file(file_path)

        logger.info(f"Successfully processed: {file_path.name} -> {pdf_path.name}")
        return True

    def _process_pdf(self, file_path: Path, options: ProcessingOptions) -> bool:
        """Process a PDF file by rendering pages to images first.

        Args:
            file_path: Path to the PDF
            options: Processing options

        Returns:
            True if successful
        """
        if options.pdf_mode == "whole_document":
            # Render first page only for a single analysis
            with tempfile.TemporaryDirectory() as tmpdir:
                rendered = Path(tmpdir) / f"{file_path.stem}_page_1.png"
                self.pdf_converter.render_page(file_path, 0, rendered)

                result = self.analyzer.analyze(
                    rendered,
                    max_categories=self.config.max_categories,
                    content_type_override=options.content_type_override,
                )
                result.source_file = file_path.name

                pdf_path = self.file_manager.get_pdf_output_path(file_path.name)
                self.pdf_generator.generate(
                    result,
                    pdf_path,
                    timestamp=datetime.now(),
                    thumbnail_size=options.thumbnail_size,
                )

        else:
            # Per-page mode: render and process each page individually
            page_count = self.pdf_converter.get_page_count(file_path)

            with tempfile.TemporaryDirectory() as tmpdir:
                for i in range(page_count):
                    rendered = Path(tmpdir) / f"{file_path.stem}_page_{i + 1}.png"
                    self.pdf_converter.render_page(file_path, i, rendered)

                    result = self.analyzer.analyze(
                        rendered,
                        max_categories=self.config.max_categories,
                        content_type_override=options.content_type_override,
                    )
                    result.source_file = f"{file_path.name} (page {i + 1})"

                    page_name = f"{file_path.stem}_page_{i + 1}.pdf"
                    pdf_path = self.file_manager.get_pdf_output_path(page_name)
                    self.pdf_generator.generate(
                        result,
                        pdf_path,
                        timestamp=datetime.now(),
                        thumbnail_size=options.thumbnail_size,
                    )

        self.file_manager.archive_file(file_path)
        logger.info(f"Successfully processed PDF: {file_path.name}")
        return True


def load_config() -> Config:
    """Load configuration, handling errors gracefully."""
    try:
        return Config()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)


@click.group()
@click.version_option(version="1.0.0", prog_name="Screenshot Wizard")
def cli():
    """Screenshot Wizard - AI-powered screenshot to PDF converter.

    Monitors a folder for PNG screenshots, extracts text using AI,
    categorizes content, and generates structured PDF documents.
    """
    pass


@cli.command()
@click.option(
    "--process-existing",
    is_flag=True,
    help="Process existing files in input folder before watching",
)
def watch(process_existing: bool):
    """Start monitoring the input folder for new files.

    This is the main operation mode. The wizard will continuously
    watch for new files and process them automatically.
    """
    config = load_config()
    config.ensure_folders_exist()

    wizard = ScreenshotWizard(config)

    click.echo("Screenshot Wizard - Folder Monitor")
    click.echo("=" * 40)
    click.echo(f"Input folder:   {config.input_folder}")
    click.echo(f"Output folder:  {config.output_folder}")
    click.echo(f"Archive folder: {config.archive_folder}")
    click.echo("=" * 40)

    watcher = FolderWatcher(
        input_folder=config.input_folder,
        callback=wizard.process_file,
        polling_interval=config.polling_interval,
    )

    if process_existing:
        click.echo("Processing existing files...")
        watcher.process_existing()

    click.echo("Watching for new files... (Press Ctrl+C to stop)")
    watcher.start()
    watcher.run_forever()


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--content-type",
    type=click.Choice(["auto", "text", "graphic"]),
    default="auto",
    help="Content type for analysis",
)
@click.option(
    "--thumbnail-size",
    type=click.Choice(["small", "medium", "full"]),
    default="medium",
    help="Thumbnail size for graphic content",
)
@click.option(
    "--pdf-mode",
    type=click.Choice(["per_page", "whole_document"]),
    default="per_page",
    help="PDF processing mode",
)
def process(
    file_path: Path,
    content_type: str,
    thumbnail_size: str,
    pdf_mode: str,
):
    """Process a single file manually.

    FILE_PATH: Path to the file to process (PNG, JPG, JPEG, or PDF)
    """
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        click.echo(
            f"Error: Unsupported file type '{file_path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            err=True,
        )
        sys.exit(1)

    config = load_config()
    config.ensure_folders_exist()

    wizard = ScreenshotWizard(config)

    options = ProcessingOptions(
        content_type_override=None if content_type == "auto" else content_type,
        thumbnail_size=thumbnail_size,
        pdf_mode=pdf_mode,
    )

    click.echo(f"Processing: {file_path}")
    success = wizard.process_file(file_path, options)

    if success:
        click.echo("Processing complete!")
    else:
        click.echo("Processing failed. Check logs for details.", err=True)
        sys.exit(1)


@cli.command()
def batch():
    """Process all pending files in the input folder."""
    config = load_config()
    config.ensure_folders_exist()

    wizard = ScreenshotWizard(config)

    pending_files = wizard.file_manager.list_pending_files(config.input_folder)

    if not pending_files:
        click.echo("No supported files found in input folder.")
        return

    click.echo(f"Found {len(pending_files)} file(s) to process.")

    success_count = 0
    for file_path in pending_files:
        if wizard.process_file(file_path):
            success_count += 1

    click.echo(f"Processed {success_count}/{len(pending_files)} files successfully.")


@cli.command("config")
def show_config():
    """Show the current configuration."""
    try:
        config = Config()
        click.echo(config.display())
    except ValueError as e:
        # Show config even if API key is missing
        click.echo("Configuration (API key not configured):")
        click.echo("-" * 40)
        click.echo("Please set OPENAI_API_KEY in .env file")
        click.echo(f"Error: {e}")


@cli.command()
def init():
    """Initialize default configuration and folder structure."""
    project_root = Path(__file__).parent.parent

    # Create folders
    folders = ["input", "output", "archive"]
    for folder in folders:
        folder_path = project_root / folder
        folder_path.mkdir(exist_ok=True)
        click.echo(f"Created folder: {folder_path}")

    # Check for .env file
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if not env_file.exists() and env_example.exists():
        click.echo("")
        click.echo("IMPORTANT: API Key Setup Required")
        click.echo("-" * 40)
        click.echo("1. Copy .env.example to .env")
        click.echo("2. Edit .env and add your OpenAI API key")
        click.echo("")
        click.echo("Your API key is stored locally only and never shared.")

    click.echo("")
    click.echo("Initialization complete!")
    click.echo("Run 'screenshot-wizard watch' to start monitoring.")


@cli.command()
def gui():
    """Launch the Screenshot Wizard GUI."""
    from .gui import ScreenshotWizardGUI

    try:
        config = load_config()
    except SystemExit:
        click.echo("Warning: Config load failed. GUI will start with defaults.", err=True)
        return

    app = ScreenshotWizardGUI(config)
    app.run()


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
