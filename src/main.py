"""CLI entry point for Screenshot Wizard."""

import logging
import sys
from datetime import datetime
from pathlib import Path

import click

from .analyzer import ScreenshotAnalyzer
from .config import Config
from .file_manager import FileManager
from .pdf_generator import PDFGenerator
from .watcher import FolderWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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

    def process_file(self, file_path: Path) -> bool:
        """Process a single PNG file.

        Args:
            file_path: Path to the PNG file

        Returns:
            True if processing was successful
        """
        try:
            logger.info(f"Processing: {file_path.name}")

            # Analyze the screenshot
            result = self.analyzer.analyze(
                file_path,
                max_categories=self.config.max_categories,
            )

            # Generate PDF
            pdf_path = self.file_manager.get_pdf_output_path(file_path.name)
            self.pdf_generator.generate(
                result,
                pdf_path,
                timestamp=datetime.now(),
            )

            # Archive the original PNG
            self.file_manager.archive_file(file_path)

            logger.info(f"Successfully processed: {file_path.name} -> {pdf_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            return False


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
    """Start monitoring the input folder for new PNG files.

    This is the main operation mode. The wizard will continuously
    watch for new PNG files and process them automatically.
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

    click.echo("Watching for new PNG files... (Press Ctrl+C to stop)")
    watcher.start()
    watcher.run_forever()


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def process(file_path: Path):
    """Process a single PNG file manually.

    FILE_PATH: Path to the PNG file to process
    """
    if not file_path.suffix.lower() == ".png":
        click.echo("Error: File must be a PNG image.", err=True)
        sys.exit(1)

    config = load_config()
    config.ensure_folders_exist()

    wizard = ScreenshotWizard(config)

    click.echo(f"Processing: {file_path}")
    success = wizard.process_file(file_path)

    if success:
        click.echo("Processing complete!")
    else:
        click.echo("Processing failed. Check logs for details.", err=True)
        sys.exit(1)


@cli.command()
def batch():
    """Process all pending PNG files in the input folder."""
    config = load_config()
    config.ensure_folders_exist()

    wizard = ScreenshotWizard(config)

    pending_files = wizard.file_manager.list_pending_files(config.input_folder)

    if not pending_files:
        click.echo("No PNG files found in input folder.")
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


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
