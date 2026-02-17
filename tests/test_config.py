"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestConfig:
    """Test suite for Config class."""

    def test_default_settings_structure(self):
        """Test that default settings have required keys."""
        # Import here to avoid loading .env during module import
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from src.config import Config

            config = Config()
            defaults = config._default_settings()

            assert "folders" in defaults
            assert "processing" in defaults
            assert "pdf" in defaults
            assert "openai" in defaults

            assert "input" in defaults["folders"]
            assert "output" in defaults["folders"]
            assert "archive" in defaults["folders"]

    def test_api_key_validation_fails_without_key(self):
        """Test that missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY from environment
            os.environ.pop("OPENAI_API_KEY", None)

            from src.config import Config

            with pytest.raises(ValueError, match="API key not configured"):
                Config()

    def test_api_key_validation_fails_with_placeholder(self):
        """Test that placeholder API key raises ValueError."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "your-api-key-here"}):
            from src.config import Config

            with pytest.raises(ValueError, match="API key not configured"):
                Config()

    def test_path_resolution_relative(self):
        """Test relative path resolution."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from src.config import Config

            config = Config()
            resolved = config._resolve_path("./input")

            assert resolved.is_absolute()
            assert resolved.name == "input"

    def test_path_resolution_absolute(self):
        """Test absolute path stays unchanged."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from src.config import Config

            config = Config()
            abs_path = "/some/absolute/path"
            resolved = config._resolve_path(abs_path)

            assert str(resolved) == abs_path

    def test_custom_yaml_loading(self):
        """Test loading custom YAML configuration."""
        custom_settings = {
            "folders": {
                "input": "./custom_input",
                "output": "./custom_output",
                "archive": "./custom_archive",
            },
            "processing": {
                "polling_interval": 10,
                "max_categories": 3,
            },
            "pdf": {
                "page_size": "letter",
                "font_family": "Helvetica",
                "font_size": 12,
                "margin": 50,
            },
            "openai": {
                "model": "gpt-4o-mini",
                "max_tokens": 2048,
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(custom_settings, f)
            temp_path = Path(f.name)

        try:
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                from src.config import Config

                config = Config(config_path=temp_path)

                assert config.polling_interval == 10
                assert config.max_categories == 3
                assert config.openai_model == "gpt-4o-mini"
        finally:
            temp_path.unlink()

    def test_ensure_folders_exist(self):
        """Test that ensure_folders_exist creates directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_settings = {
                "folders": {
                    "input": f"{tmpdir}/test_input",
                    "output": f"{tmpdir}/test_output",
                    "archive": f"{tmpdir}/test_archive",
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

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(custom_settings, f)
                temp_path = Path(f.name)

            try:
                with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                    from src.config import Config

                    config = Config(config_path=temp_path)
                    config.ensure_folders_exist()

                    assert config.input_folder.exists()
                    assert config.output_folder.exists()
                    assert config.archive_folder.exists()
            finally:
                temp_path.unlink()

    def test_display_output(self):
        """Test configuration display string."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from src.config import Config

            config = Config()
            display = config.display()

            assert "Input Folder:" in display
            assert "Output Folder:" in display
            assert "Archive Folder:" in display
            assert "API Key:" in display
            assert "test-key" not in display  # Key should be masked
