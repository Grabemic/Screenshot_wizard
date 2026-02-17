"""Tests for file manager module."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


class TestFileManager:
    """Test suite for FileManager class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive = base / "archive"
            output = base / "output"
            input_dir = base / "input"

            # Create directories
            archive.mkdir()
            output.mkdir()
            input_dir.mkdir()

            yield {"base": base, "archive": archive, "output": output, "input": input_dir}

    @pytest.fixture
    def file_manager(self, temp_dirs):
        """Create FileManager instance with temp directories."""
        from src.file_manager import FileManager

        return FileManager(
            archive_folder=temp_dirs["archive"],
            output_folder=temp_dirs["output"],
        )

    def test_creates_folders_if_missing(self):
        """Test that FileManager creates folders if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive = base / "new_archive"
            output = base / "new_output"

            from src.file_manager import FileManager

            fm = FileManager(archive_folder=archive, output_folder=output)

            assert archive.exists()
            assert output.exists()

    def test_get_pdf_output_path(self, file_manager, temp_dirs):
        """Test PDF output path generation."""
        pdf_path = file_manager.get_pdf_output_path("screenshot.png")

        assert pdf_path.suffix == ".pdf"
        assert pdf_path.stem == "screenshot"
        assert pdf_path.parent == temp_dirs["output"]

    def test_get_pdf_output_path_unique(self, file_manager, temp_dirs):
        """Test unique path generation when file exists."""
        # Create existing file
        existing = temp_dirs["output"] / "screenshot.pdf"
        existing.touch()

        pdf_path = file_manager.get_pdf_output_path("screenshot.png")

        assert pdf_path != existing
        assert "screenshot_" in pdf_path.name
        assert pdf_path.suffix == ".pdf"

    def test_archive_file(self, file_manager, temp_dirs):
        """Test archiving a file."""
        # Create source file
        source = temp_dirs["input"] / "test.png"
        source.write_bytes(b"test content")

        archived = file_manager.archive_file(source)

        assert archived.exists()
        assert archived.parent == temp_dirs["archive"]
        assert not source.exists()

    def test_archive_file_unique(self, file_manager, temp_dirs):
        """Test archiving with existing file in archive."""
        # Create existing file in archive
        existing = temp_dirs["archive"] / "test.png"
        existing.write_bytes(b"existing")

        # Create source file
        source = temp_dirs["input"] / "test.png"
        source.write_bytes(b"new content")

        archived = file_manager.archive_file(source)

        assert archived.exists()
        assert archived != existing
        assert existing.exists()  # Original still exists

    def test_list_pending_files_empty(self, file_manager, temp_dirs):
        """Test listing empty input folder."""
        pending = file_manager.list_pending_files(temp_dirs["input"])
        assert pending == []

    def test_list_pending_files(self, file_manager, temp_dirs):
        """Test listing PNG files."""
        # Create some test files
        (temp_dirs["input"] / "test1.png").touch()
        (temp_dirs["input"] / "test2.PNG").touch()
        (temp_dirs["input"] / "test3.txt").touch()  # Should be ignored

        pending = file_manager.list_pending_files(temp_dirs["input"])

        assert len(pending) == 2
        assert all(p.suffix.lower() == ".png" for p in pending)

    def test_list_pending_files_sorted_by_mtime(self, file_manager, temp_dirs):
        """Test that files are sorted by modification time."""
        import time

        # Create files with different mtimes
        file1 = temp_dirs["input"] / "first.png"
        file1.touch()
        time.sleep(0.1)

        file2 = temp_dirs["input"] / "second.png"
        file2.touch()

        pending = file_manager.list_pending_files(temp_dirs["input"])

        assert pending[0].name == "first.png"
        assert pending[1].name == "second.png"

    def test_cleanup_empty_input(self, file_manager, temp_dirs):
        """Test cleanup of empty subdirectories."""
        # Create empty subdirectory
        empty_dir = temp_dirs["input"] / "empty_subdir"
        empty_dir.mkdir()

        # Create non-empty subdirectory
        non_empty = temp_dirs["input"] / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").touch()

        file_manager.cleanup_empty_input(temp_dirs["input"])

        assert not empty_dir.exists()
        assert non_empty.exists()
