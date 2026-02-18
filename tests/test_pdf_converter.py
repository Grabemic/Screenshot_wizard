"""Tests for PDF converter module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPDFPageConverter:
    """Test suite for PDFPageConverter class."""

    @pytest.fixture
    def converter(self):
        """Create a PDFPageConverter instance."""
        from src.pdf_converter import PDFPageConverter

        return PDFPageConverter(dpi=72)

    @pytest.fixture
    def sample_pdf(self):
        """Create a minimal PDF file for testing using pymupdf."""
        import pymupdf

        # Create temp file path, close it first so pymupdf can write to it
        fd, tmp_name = tempfile.mkstemp(suffix=".pdf")
        import os
        os.close(fd)
        path = Path(tmp_name)

        doc = pymupdf.open()
        page = doc.new_page(width=200, height=200)
        page.insert_text((50, 100), "Test page 1")
        page2 = doc.new_page(width=200, height=200)
        page2.insert_text((50, 100), "Test page 2")
        doc.save(str(path))
        doc.close()

        yield path
        path.unlink(missing_ok=True)

    def test_get_page_count(self, converter, sample_pdf):
        """Test getting page count from a PDF."""
        count = converter.get_page_count(sample_pdf)
        assert count == 2

    def test_render_page(self, converter, sample_pdf):
        """Test rendering a single page to PNG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "page.png"
            result = converter.render_page(sample_pdf, 0, output)

            assert result == output
            assert output.exists()
            assert output.stat().st_size > 0

    def test_render_page_invalid_index(self, converter, sample_pdf):
        """Test that invalid page index raises IndexError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "page.png"
            with pytest.raises(IndexError):
                converter.render_page(sample_pdf, 5, output)

    def test_render_all_pages(self, converter, sample_pdf):
        """Test rendering all pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "pages"
            results = converter.render_all_pages(sample_pdf, output_dir)

            assert len(results) == 2
            assert all(p.exists() for p in results)
            assert all(p.suffix == ".png" for p in results)

    def test_zoom_calculation(self):
        """Test that DPI affects zoom factor."""
        from src.pdf_converter import PDFPageConverter

        converter_low = PDFPageConverter(dpi=72)
        converter_high = PDFPageConverter(dpi=200)

        assert converter_low._zoom == 1.0
        assert converter_high._zoom == pytest.approx(200 / 72)
