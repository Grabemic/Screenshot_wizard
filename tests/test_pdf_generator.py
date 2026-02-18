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

    @pytest.fixture
    def sample_png(self):
        """Create a minimal valid PNG file for testing."""
        png_data = bytes(
            [
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
                0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
                0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
                0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
                0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
                0x42, 0x60, 0x82,
            ]
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_data)
            path = Path(f.name)

        yield path
        path.unlink(missing_ok=True)

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

    def test_generate_graphic_content(self, generator, sample_png):
        """Test generating PDF with graphic content type."""
        from src.analyzer import AnalysisResult

        result = AnalysisResult(
            text="",
            categories=["Photo", "Nature"],
            source_file="sunset.png",
            content_type="graphic",
            description="A beautiful sunset over the ocean.",
            source_image_path=sample_png,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "graphic_output.pdf"
            result_path = generator.generate(
                result, output_path, thumbnail_size="medium"
            )

            assert result_path.exists()
            assert output_path.stat().st_size > 0

    def test_generate_graphic_small_thumbnail(self, generator, sample_png):
        """Test generating PDF with small thumbnail size."""
        from src.analyzer import AnalysisResult

        result = AnalysisResult(
            text="",
            categories=["Diagram"],
            source_file="diagram.png",
            content_type="graphic",
            description="A system architecture diagram.",
            source_image_path=sample_png,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "small_thumb.pdf"
            result_path = generator.generate(
                result, output_path, thumbnail_size="small"
            )

            assert result_path.exists()

    def test_generate_graphic_full_thumbnail(self, generator, sample_png):
        """Test generating PDF with full-width thumbnail."""
        from src.analyzer import AnalysisResult

        result = AnalysisResult(
            text="",
            categories=["Screenshot"],
            source_file="fullscreen.png",
            content_type="graphic",
            description="Full screen capture.",
            source_image_path=sample_png,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "full_thumb.pdf"
            result_path = generator.generate(
                result, output_path, thumbnail_size="full"
            )

            assert result_path.exists()

    def test_generate_graphic_no_source_image(self, generator):
        """Test graphic content without source image path."""
        from src.analyzer import AnalysisResult

        result = AnalysisResult(
            text="",
            categories=["Photo"],
            source_file="missing.png",
            content_type="graphic",
            description="A description without an image.",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "no_image.pdf"
            result_path = generator.generate(result, output_path)

            assert result_path.exists()
