"""Tests for watcher module."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPNGHandler:
    """Test suite for PNGHandler class."""

    def test_should_process_png_file(self):
        """Test that PNG files are accepted."""
        from src.watcher import PNGHandler

        handler = PNGHandler(callback=MagicMock())

        assert handler._should_process(Path("test.png"))
        assert handler._should_process(Path("test.PNG"))

    def test_should_not_process_non_png(self):
        """Test that non-PNG files are rejected."""
        from src.watcher import PNGHandler

        handler = PNGHandler(callback=MagicMock())

        assert not handler._should_process(Path("test.jpg"))
        assert not handler._should_process(Path("test.pdf"))
        assert not handler._should_process(Path("test.txt"))

    def test_debounce_same_file(self):
        """Test that same file is debounced."""
        from src.watcher import PNGHandler

        handler = PNGHandler(callback=MagicMock(), debounce_seconds=1.0)

        # First call should be processed
        assert handler._should_process(Path("test.png"))

        # Immediate second call should be debounced
        assert not handler._should_process(Path("test.png"))

    def test_debounce_different_files(self):
        """Test that different files are not debounced."""
        from src.watcher import PNGHandler

        handler = PNGHandler(callback=MagicMock(), debounce_seconds=1.0)

        assert handler._should_process(Path("test1.png"))
        assert handler._should_process(Path("test2.png"))

    def test_on_created_triggers_callback(self):
        """Test that on_created triggers callback for PNG files."""
        from src.watcher import PNGHandler

        callback = MagicMock()
        handler = PNGHandler(callback=callback, debounce_seconds=0)

        # Create mock event
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/path/test.png"

        with patch("src.watcher.time.sleep"):  # Skip the 0.5s delay
            handler.on_created(event)

        callback.assert_called_once()

    def test_on_created_ignores_directories(self):
        """Test that directories are ignored."""
        from src.watcher import PNGHandler

        callback = MagicMock()
        handler = PNGHandler(callback=callback)

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/some/path/folder"

        handler.on_created(event)

        callback.assert_not_called()

    def test_on_moved_triggers_callback(self):
        """Test that on_moved triggers callback for PNG files."""
        from src.watcher import PNGHandler

        callback = MagicMock()
        handler = PNGHandler(callback=callback, debounce_seconds=0)

        event = MagicMock()
        event.is_directory = False
        event.dest_path = "/some/path/moved.png"

        with patch("src.watcher.time.sleep"):
            handler.on_moved(event)

        callback.assert_called_once()


class TestFolderWatcher:
    """Test suite for FolderWatcher class."""

    @pytest.fixture
    def temp_input_dir(self):
        """Create temporary input directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_creates_input_folder(self):
        """Test that start creates input folder if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_folder = Path(tmpdir) / "new_input"

            from src.watcher import FolderWatcher

            watcher = FolderWatcher(
                input_folder=input_folder,
                callback=MagicMock(),
            )

            watcher.start()
            watcher.stop()

            assert input_folder.exists()

    def test_process_existing_empty(self, temp_input_dir):
        """Test process_existing with empty folder."""
        from src.watcher import FolderWatcher

        callback = MagicMock()
        watcher = FolderWatcher(
            input_folder=temp_input_dir,
            callback=callback,
        )

        count = watcher.process_existing()

        assert count == 0
        callback.assert_not_called()

    def test_process_existing_with_files(self, temp_input_dir):
        """Test process_existing with PNG files."""
        # Create test files
        (temp_input_dir / "test1.png").touch()
        (temp_input_dir / "test2.png").touch()

        from src.watcher import FolderWatcher

        callback = MagicMock()
        watcher = FolderWatcher(
            input_folder=temp_input_dir,
            callback=callback,
        )

        count = watcher.process_existing()

        assert count == 2
        assert callback.call_count == 2

    def test_start_and_stop(self, temp_input_dir):
        """Test starting and stopping the watcher."""
        from src.watcher import FolderWatcher

        watcher = FolderWatcher(
            input_folder=temp_input_dir,
            callback=MagicMock(),
        )

        watcher.start()
        assert watcher._running

        watcher.stop()
        assert not watcher._running
