"""PDF to image conversion using PyMuPDF."""

import logging
from pathlib import Path

import pymupdf

logger = logging.getLogger(__name__)


class PDFPageConverter:
    """Converts PDF pages to PNG images using PyMuPDF."""

    def __init__(self, dpi: int = 200):
        """Initialize converter.

        Args:
            dpi: Resolution for rendered pages
        """
        self.dpi = dpi
        self._zoom = dpi / 72.0

    def get_page_count(self, pdf_path: Path) -> int:
        """Return the number of pages in a PDF file."""
        with pymupdf.open(str(pdf_path)) as doc:
            return len(doc)

    def render_page(self, pdf_path: Path, page_index: int, output_path: Path) -> Path:
        """Render a single PDF page to a PNG image.

        Args:
            pdf_path: Path to the PDF file
            page_index: Zero-based page index
            output_path: Path for the output PNG file

        Returns:
            Path to the rendered PNG file
        """
        with pymupdf.open(str(pdf_path)) as doc:
            if page_index < 0 or page_index >= len(doc):
                raise IndexError(
                    f"Page index {page_index} out of range (0-{len(doc) - 1})"
                )

            page = doc[page_index]
            mat = pymupdf.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=mat)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(output_path))
            logger.info(f"Rendered page {page_index} to {output_path}")

        return output_path

    def render_all_pages(self, pdf_path: Path, output_dir: Path) -> list[Path]:
        """Render all pages of a PDF to PNG images.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory for output PNG files

        Returns:
            List of paths to rendered PNG files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered = []

        with pymupdf.open(str(pdf_path)) as doc:
            for i in range(len(doc)):
                output_path = output_dir / f"{pdf_path.stem}_page_{i + 1}.png"
                page = doc[i]
                mat = pymupdf.Matrix(self._zoom, self._zoom)
                pix = page.get_pixmap(matrix=mat)
                pix.save(str(output_path))
                rendered.append(output_path)
                logger.info(f"Rendered page {i + 1}/{len(doc)} to {output_path}")

        return rendered
