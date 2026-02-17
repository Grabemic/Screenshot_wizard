"""Tests for analyzer module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestScreenshotAnalyzer:
    """Test suite for ScreenshotAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with mocked OpenAI client."""
        with patch("src.analyzer.OpenAI"):
            from src.analyzer import ScreenshotAnalyzer

            return ScreenshotAnalyzer(api_key="test-key")

    @pytest.fixture
    def sample_png(self):
        """Create a minimal valid PNG file for testing."""
        # Minimal 1x1 transparent PNG
        png_data = bytes(
            [
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
                0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk
                0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
                0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
                0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
                0x42, 0x60, 0x82,
            ]
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_data)
            path = Path(f.name)

        yield path
        path.unlink(missing_ok=True)

    def test_parse_response_valid_json(self, analyzer):
        """Test parsing valid JSON response."""
        content = '{"text": "Hello World", "categories": ["Test", "Sample"]}'
        text, categories = analyzer._parse_response(content, max_categories=2)

        assert text == "Hello World"
        assert categories == ["Test", "Sample"]

    def test_parse_response_json_in_markdown(self, analyzer):
        """Test parsing JSON wrapped in markdown code block."""
        content = '```json\n{"text": "Hello World", "categories": ["Test"]}\n```'
        text, categories = analyzer._parse_response(content, max_categories=2)

        assert text == "Hello World"
        assert categories == ["Test"]

    def test_parse_response_limits_categories(self, analyzer):
        """Test that categories are limited to max_categories."""
        content = '{"text": "Hello", "categories": ["Cat1", "Cat2", "Cat3", "Cat4"]}'
        text, categories = analyzer._parse_response(content, max_categories=2)

        assert len(categories) == 2
        assert categories == ["Cat1", "Cat2"]

    def test_parse_response_invalid_json(self, analyzer):
        """Test fallback when JSON parsing fails."""
        content = "This is not JSON at all"
        text, categories = analyzer._parse_response(content, max_categories=2)

        assert text == content
        assert categories == ["Uncategorized"]

    def test_encode_image(self, analyzer, sample_png):
        """Test image encoding to base64."""
        encoded = analyzer._encode_image(sample_png)

        assert isinstance(encoded, str)
        assert len(encoded) > 0
        # Base64 should only contain valid characters
        import base64
        try:
            base64.b64decode(encoded)
        except Exception:
            pytest.fail("Invalid base64 encoding")

    def test_analyze_returns_result(self, sample_png):
        """Test full analysis flow with mocked API."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"text": "Test content", "categories": ["Screenshot", "Test"]}'
        )

        with patch("src.analyzer.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            from src.analyzer import ScreenshotAnalyzer

            analyzer = ScreenshotAnalyzer(api_key="test-key")
            result = analyzer.analyze(sample_png, max_categories=2)

            assert result.text == "Test content"
            assert result.categories == ["Screenshot", "Test"]
            assert result.source_file == sample_png.name

    def test_analyze_handles_empty_response(self, sample_png):
        """Test handling of empty API response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ""

        with patch("src.analyzer.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            from src.analyzer import ScreenshotAnalyzer

            analyzer = ScreenshotAnalyzer(api_key="test-key")
            result = analyzer.analyze(sample_png, max_categories=2)

            # Should return something reasonable even with empty response
            assert result.source_file == sample_png.name
