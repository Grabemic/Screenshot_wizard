"""Tests for PDF generator module."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest


class TestPDFGenerator:
    """Test suite for PDFGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create PDF generator with default settings."""
        from src.pdf_generator import PDFGenerator

        settings = {
            "page_size": "A4",
            "font_family": "Helvetica",
            "font_size": 11,
            "margin": 72,
        }
        return PDFGenerator(settings)

    @pytest.fixture
    def sample_result(self):
        """Create a sample analysis result."""
        from src.analyzer import AnalysisResult

        return AnalysisResult(
            text="This is sample extracted text.\nWith multiple lines.",
            categories=["Test", "Sample"],
            source_file="test_screenshot.png",
        )

    def test_escape_text_ampersand(self, generator):
        """Test escaping ampersand characters."""
        text = "Tom & Jerry"
        escaped = generator._escape_text(text)
        assert escaped == "Tom &amp; Jerry"

    def test_escape_text_angle_brackets(self, generator):
        """Test escaping angle brackets."""
        text = "<script>alert('xss')</script>"
        escaped = generator._escape_text(text)
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "<script>" not in escaped

    def test_escape_text_combined(self, generator):
        """Test escaping multiple special characters."""
        text = "A < B & B > C"
        escaped = generator._escape_text(text)
        assert escaped == "A &lt; B &amp; B &gt; C"

    def test_generate_creates_file(self, generator, sample_result):
        """Test that generate creates a PDF file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.pdf"
            result_path = generator.generate(sample_result, output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_generate_with_custom_timestamp(self, generator, sample_result):
        """Test generating PDF with custom timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.pdf"
            custom_time = datetime(2024, 6, 15, 10, 30, 0)

            result_path = generator.generate(
                sample_result, output_path, timestamp=custom_time
            )

            assert result_path.exists()

    def test_generate_with_unicode_text(self, generator):
        """Test generating PDF with unicode characters."""
        from src.analyzer import AnalysisResult

        result = AnalysisResult(
            text="Hello 世界! Привет мир! مرحبا",
            categories=["Unicode", "International"],
            source_file="unicode_test.png",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "unicode_output.pdf"
            result_path = generator.generate(result, output_path)

            assert result_path.exists()
            assert output_path.stat().st_size > 0

    def test_generate_with_long_text(self, generator):
        """Test generating PDF with very long text content."""
        from src.analyzer import AnalysisResult

        long_text = "This is a line of text.\n" * 100

        result = AnalysisResult(
            text=long_text,
            categories=["Long", "Document"],
            source_file="long_text.png",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "long_output.pdf"
            result_path = generator.generate(result, output_path)

            assert result_path.exists()

    def test_generate_with_single_category(self, generator):
        """Test generating PDF with single category."""
        from src.analyzer import AnalysisResult

        result = AnalysisResult(
            text="Simple text",
            categories=["SingleCategory"],
            source_file="single_cat.png",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "single_cat_output.pdf"
            result_path = generator.generate(result, output_path)

            assert result_path.exists()

    def test_letter_page_size(self):
        """Test creating generator with letter page size."""
        from src.pdf_generator import PDFGenerator

        settings = {
            "page_size": "letter",
            "font_family": "Helvetica",
            "font_size": 11,
            "margin": 72,
        }
        generator = PDFGenerator(settings)

        # Letter size is 612x792 points
        assert generator.page_size[0] == 612
        assert generator.page_size[1] == 792
