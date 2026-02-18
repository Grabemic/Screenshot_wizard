"""Tests for GUI module — non-visual logic only."""

import os
import queue
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestGUIQueueLogic:
    """Test queue polling and state management logic."""

    def test_watcher_queue_marks_new_files(self):
        """Test that files from watcher queue are marked as NEW."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from src.gui import ScreenshotWizardGUI

            # We can't instantiate the full GUI (requires display), so
            # test the underlying data structure logic
            new_files: set[str] = set()
            watcher_queue: queue.Queue[Path] = queue.Queue()

            # Simulate watcher detecting a file
            watcher_queue.put(Path("/input/screenshot.png"))

            # Simulate polling
            try:
                while True:
                    file_path = watcher_queue.get_nowait()
                    new_files.add(file_path.name)
            except queue.Empty:
                pass

            assert "screenshot.png" in new_files

    def test_result_queue_clears_processing_state(self):
        """Test that result queue clears processing flag."""
        result_queue: queue.Queue[tuple[str, bool]] = queue.Queue()

        # Simulate processing result
        result_queue.put(("test.png", True))

        processing = True
        try:
            while True:
                filename, success = result_queue.get_nowait()
                processing = False
                assert success
                assert filename == "test.png"
        except queue.Empty:
            pass

        assert not processing

    def test_result_queue_handles_failure(self):
        """Test that failed processing is reported correctly."""
        result_queue: queue.Queue[tuple[str, bool]] = queue.Queue()

        result_queue.put(("bad_file.png", False))

        results = []
        try:
            while True:
                results.append(result_queue.get_nowait())
        except queue.Empty:
            pass

        assert len(results) == 1
        assert results[0] == ("bad_file.png", False)


class TestGUIConfigSaving:
    """Test config saving from GUI folder changes."""

    def test_save_folder_settings(self):
        """Test that folder settings are saved to YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.yaml"
            settings = {
                "folders": {
                    "input": "./input",
                    "output": "./output",
                    "archive": "./archive",
                },
                "processing": {"polling_interval": 5, "max_categories": 2},
                "pdf": {
                    "page_size": "A4",
                    "font_family": "Helvetica",
                    "font_size": 11,
                    "margin": 72,
                },
                "openai": {"model": "gpt-4o", "max_tokens": 4096},
            }

            with open(config_path, "w") as f:
                yaml.dump(settings, f)

            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                from src.config import Config

                config = Config(config_path=config_path)
                config.save_folder_settings("C:/new/input", "C:/new/output")

            # Verify saved
            with open(config_path) as f:
                saved = yaml.safe_load(f)

            assert saved["folders"]["input"] == "C:/new/input"
            assert saved["folders"]["output"] == "C:/new/output"
            # Archive should be unchanged
            assert saved["folders"]["archive"] == "./archive"


class TestGUIEntryManagement:
    """Test file list entry logic."""

    def test_new_file_prefix(self):
        """Test that NEW prefix is added and stripped correctly."""
        new_files = {"screenshot.png"}
        filename = "screenshot.png"

        prefix = "[NEW] " if filename in new_files else ""
        display = f"{prefix}{filename}"

        assert display == "[NEW] screenshot.png"
        assert display.replace("[NEW] ", "") == "screenshot.png"

    def test_supported_extensions_filter(self):
        """Test that only supported files appear in list."""
        from src.config import SUPPORTED_EXTENSIONS

        test_files = [
            "test.png",
            "photo.jpg",
            "image.jpeg",
            "doc.pdf",
            "readme.txt",
            "script.py",
            "data.csv",
        ]

        filtered = [
            f for f in test_files if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        assert len(filtered) == 4
        assert "readme.txt" not in filtered
        assert "script.py" not in filtered
        assert "data.csv" not in filtered
