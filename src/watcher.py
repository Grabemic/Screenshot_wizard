"""Folder monitoring module for Screenshot Wizard."""

import logging
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class PNGHandler(FileSystemEventHandler):
    """Handles file system events for PNG files."""

    def __init__(self, callback: Callable[[Path], None], debounce_seconds: float = 1.0):
        """Initialize the handler.

        Args:
            callback: Function to call when a PNG file is detected
            debounce_seconds: Minimum time between processing the same file
        """
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last_processed: dict[str, float] = {}

    def _should_process(self, file_path: Path) -> bool:
        """Check if a file should be processed (debouncing)."""
        if not file_path.suffix.lower() == ".png":
            return False

        current_time = time.time()
        last_time = self._last_processed.get(str(file_path), 0)

        if current_time - last_time < self.debounce_seconds:
            return False

        self._last_processed[str(file_path)] = current_time
        return True

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if self._should_process(file_path):
            logger.info(f"New PNG detected: {file_path.name}")
            # Small delay to ensure file is fully written
            time.sleep(0.5)
            self.callback(file_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events (e.g., from temp location)."""
        if event.is_directory:
            return

        file_path = Path(event.dest_path)
        if self._should_process(file_path):
            logger.info(f"PNG moved to folder: {file_path.name}")
            time.sleep(0.5)
            self.callback(file_path)


class FolderWatcher:
    """Monitors a folder for new PNG files."""

    def __init__(
        self,
        input_folder: Path,
        callback: Callable[[Path], None],
        polling_interval: int = 5,
    ):
        """Initialize the folder watcher.

        Args:
            input_folder: Path to monitor for new files
            callback: Function to call when a new PNG is detected
            polling_interval: Seconds between checks (for fallback polling)
        """
        self.input_folder = input_folder
        self.callback = callback
        self.polling_interval = polling_interval
        self.observer: Observer | None = None
        self._running = False

    def start(self) -> None:
        """Start watching the folder."""
        # Ensure input folder exists
        self.input_folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting folder watcher on: {self.input_folder}")

        # Set up watchdog observer
        self.observer = Observer()
        handler = PNGHandler(self.callback)

        self.observer.schedule(handler, str(self.input_folder), recursive=False)
        self.observer.start()
        self._running = True

        logger.info("Folder watcher started. Press Ctrl+C to stop.")

    def run_forever(self) -> None:
        """Run the watcher until interrupted."""
        try:
            while self._running:
                time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the folder watcher."""
        self._running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Folder watcher stopped.")

    def process_existing(self) -> int:
        """Process any existing PNG files in the input folder.

        Returns:
            Number of files processed
        """
        png_files = list(self.input_folder.glob("*.png")) + list(
            self.input_folder.glob("*.PNG")
        )

        if not png_files:
            logger.info("No existing PNG files found in input folder.")
            return 0

        logger.info(f"Found {len(png_files)} existing PNG file(s) to process.")

        for file_path in png_files:
            self.callback(file_path)

        return len(png_files)
