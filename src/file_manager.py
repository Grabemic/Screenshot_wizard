"""File management operations for Screenshot Wizard."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FileManager:
    """Handles file operations for screenshot processing."""

    def __init__(self, archive_folder: Path, output_folder: Path):
        """Initialize file manager.

        Args:
            archive_folder: Path to archive processed PNGs
            output_folder: Path for generated PDFs
        """
        self.archive_folder = archive_folder
        self.output_folder = output_folder

        # Ensure folders exist
        self.archive_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def _get_unique_path(self, target_folder: Path, filename: str) -> Path:
        """Get a unique file path, appending timestamp if file exists.

        Args:
            target_folder: Target directory
            filename: Original filename

        Returns:
            Unique path that doesn't conflict with existing files
        """
        target_path = target_folder / filename

        if not target_path.exists():
            return target_path

        # File exists, append timestamp
        stem = target_path.stem
        suffix = target_path.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{stem}_{timestamp}{suffix}"

        return target_folder / new_filename

    def get_pdf_output_path(self, source_filename: str) -> Path:
        """Get the output path for a generated PDF.

        Args:
            source_filename: Original PNG filename

        Returns:
            Path for the output PDF
        """
        # Replace .png extension with .pdf
        pdf_filename = Path(source_filename).stem + ".pdf"
        return self._get_unique_path(self.output_folder, pdf_filename)

    def archive_file(self, source_path: Path) -> Path:
        """Move a processed file to the archive folder.

        Args:
            source_path: Path to the file to archive

        Returns:
            Path to the archived file
        """
        archive_path = self._get_unique_path(self.archive_folder, source_path.name)

        logger.info(f"Archiving {source_path.name} to {archive_path}")
        shutil.move(str(source_path), str(archive_path))

        return archive_path

    def list_pending_files(self, input_folder: Path) -> list[Path]:
        """List all PNG files in the input folder.

        Args:
            input_folder: Path to scan for PNG files

        Returns:
            List of PNG file paths
        """
        png_files = list(input_folder.glob("*.png")) + list(input_folder.glob("*.PNG"))
        return sorted(png_files, key=lambda p: p.stat().st_mtime)

    def cleanup_empty_input(self, input_folder: Path) -> None:
        """Remove empty subdirectories from input folder.

        Args:
            input_folder: Path to clean up
        """
        for subfolder in input_folder.iterdir():
            if subfolder.is_dir() and not any(subfolder.iterdir()):
                logger.debug(f"Removing empty directory: {subfolder}")
                subfolder.rmdir()
