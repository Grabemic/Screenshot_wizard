"""Configuration management for Screenshot Wizard."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

SUPPORTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".pdf"})


class Config:
    """Configuration manager that loads settings from YAML and environment variables."""

    def __init__(self, config_path: Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to settings.yaml file. If None, uses default location.
        """
        # Load environment variables from .env file
        load_dotenv()

        # Determine project root (parent of src directory)
        self.project_root = Path(__file__).parent.parent

        # Load YAML configuration
        if config_path is None:
            config_path = self.project_root / "config" / "settings.yaml"

        self._config_path = config_path
        self._settings = self._load_yaml(config_path)

        # Validate API key exists
        self._validate_api_key()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load settings from YAML file."""
        if not path.exists():
            return self._default_settings()

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or self._default_settings()

    def _default_settings(self) -> dict[str, Any]:
        """Return default settings if YAML file is missing."""
        return {
            "folders": {
                "input": "./input",
                "output": "./output",
                "archive": "./archive",
            },
            "processing": {
                "polling_interval": 5,
                "max_categories": 2,
            },
            "pdf": {
                "page_size": "A4",
                "font_family": "Helvetica",
                "font_size": 11,
                "margin": 72,
            },
            "openai": {
                "model": "gpt-4o",
                "max_tokens": 4096,
            },
        }

    def _validate_api_key(self) -> None:
        """Validate that OpenAI API key is configured."""
        api_key = self.openai_api_key
        if not api_key or api_key == "your-api-key-here":
            raise ValueError(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in your .env file or environment variables."
            )

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path relative to project root."""
        path = Path(path_str)
        if path.is_absolute():
            return path
        return self.project_root / path

    @property
    def openai_api_key(self) -> str | None:
        """Get OpenAI API key from environment."""
        return os.getenv("OPENAI_API_KEY")

    @property
    def input_folder(self) -> Path:
        """Get input folder path."""
        return self._resolve_path(self._settings["folders"]["input"])

    @property
    def output_folder(self) -> Path:
        """Get output folder path."""
        return self._resolve_path(self._settings["folders"]["output"])

    @property
    def archive_folder(self) -> Path:
        """Get archive folder path."""
        return self._resolve_path(self._settings["folders"]["archive"])

    @property
    def polling_interval(self) -> int:
        """Get polling interval in seconds."""
        return self._settings["processing"]["polling_interval"]

    @property
    def max_categories(self) -> int:
        """Get maximum number of categories."""
        return self._settings["processing"]["max_categories"]

    @property
    def openai_model(self) -> str:
        """Get OpenAI model name."""
        return self._settings["openai"]["model"]

    @property
    def openai_max_tokens(self) -> int:
        """Get OpenAI max tokens."""
        return self._settings["openai"]["max_tokens"]

    @property
    def pdf_settings(self) -> dict[str, Any]:
        """Get PDF generation settings."""
        return self._settings["pdf"]

    def ensure_folders_exist(self) -> None:
        """Create all required folders if they don't exist."""
        for folder in [self.input_folder, self.output_folder, self.archive_folder]:
            folder.mkdir(parents=True, exist_ok=True)

    def save_folder_settings(self, input_folder: str, output_folder: str) -> None:
        """Write updated folder paths back to settings.yaml.

        Args:
            input_folder: New input folder path
            output_folder: New output folder path
        """
        self._settings["folders"]["input"] = input_folder
        self._settings["folders"]["output"] = output_folder

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._settings, f, default_flow_style=False)

    def display(self) -> str:
        """Return a formatted string of current configuration (without sensitive data)."""
        return f"""Screenshot Wizard Configuration
==============================
Input Folder:     {self.input_folder}
Output Folder:    {self.output_folder}
Archive Folder:   {self.archive_folder}
Polling Interval: {self.polling_interval}s
Max Categories:   {self.max_categories}
OpenAI Model:     {self.openai_model}
API Key:          {"*" * 8}...{"*" * 4} (configured)
"""
