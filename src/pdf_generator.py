"""PDF generation module for Screenshot Wizard."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .analyzer import AnalysisResult

logger = logging.getLogger(__name__)

PAGE_SIZES = {
    "A4": A4,
    "letter": letter,
}

THUMBNAIL_WIDTHS = {
    "small": 1.5 * inch,
    "medium": 3.0 * inch,
    "full": None,  # Will be calculated based on page width
}


class PDFGenerator:
    """Generates PDF documents from analysis results."""

    def __init__(self, settings: dict[str, Any]):
        """Initialize PDF generator.

        Args:
            settings: PDF settings from configuration
        """
        self.page_size = PAGE_SIZES.get(settings.get("page_size", "A4"), A4)
        self.font_family = settings.get("font_family", "Helvetica")
        self.font_size = settings.get("font_size", 11)
        self.margin = settings.get("margin", 72)

        # Create styles
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self) -> None:
        """Create custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                "CategoryHeader",
                parent=self.styles["Heading1"],
                fontName=f"{self.font_family}-Bold",
                fontSize=14,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=12,
                spaceBefore=0,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "CustomBody",
                parent=self.styles["Normal"],
                fontName=self.font_family,
                fontSize=self.font_size,
                leading=self.font_size * 1.4,
                spaceAfter=6,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "Footer",
                parent=self.styles["Normal"],
                fontName=self.font_family,
                fontSize=9,
                textColor=colors.HexColor("#7f8c8d"),
                spaceBefore=12,
            )
        )

        self.styles.add(
            ParagraphStyle(
                "DescriptionLabel",
                parent=self.styles["Normal"],
                fontName=f"{self.font_family}-Bold",
                fontSize=12,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=6,
                spaceBefore=12,
            )
        )

    def _escape_text(self, text: str) -> str:
        """Escape special characters for ReportLab XML."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _create_category_header(self, categories: list[str]) -> Table:
        """Create a formatted category header table."""
        category_text = " | ".join(categories)

        data = [[f"CATEGORIES: {category_text}"]]

        table = Table(data, colWidths=[self.page_size[0] - 2 * self.margin])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecf0f1")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
                    ("FONTNAME", (0, 0), (-1, -1), f"{self.font_family}-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("PADDING", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                ]
            )
        )

        return table

    def _create_footer(self, source_file: str, timestamp: datetime) -> Paragraph:
        """Create footer with source file and timestamp."""
        footer_text = (
            f"<b>Source:</b> {self._escape_text(source_file)}<br/>"
            f"<b>Processed:</b> {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return Paragraph(footer_text, self.styles["Footer"])

    def _create_separator(self) -> Table:
        """Create a horizontal line separator."""
        line_table = Table([[""]], colWidths=[self.page_size[0] - 2 * self.margin])
        line_table.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#bdc3c7")),
                ]
            )
        )
        return line_table

    def _build_text_section(self, result: AnalysisResult) -> list:
        """Build elements for text content."""
        elements = []

        text_content = self._escape_text(result.text)
        text_content = text_content.replace("\n", "<br/>")

        body_para = Paragraph(text_content, self.styles["CustomBody"])
        elements.append(body_para)

        return elements

    def _build_graphic_section(
        self,
        result: AnalysisResult,
        thumbnail_size: Literal["small", "medium", "full"] = "medium",
    ) -> list:
        """Build elements for graphic content with thumbnail and description."""
        elements = []

        # Embed thumbnail if source image is available
        if result.source_image_path and result.source_image_path.exists():
            width = THUMBNAIL_WIDTHS.get(thumbnail_size)
            if width is None:
                # "full" — use available page width
                width = self.page_size[0] - 2 * self.margin

            try:
                img = RLImage(str(result.source_image_path), width=width)
                # Constrain height to fit within page
                max_height = self.page_size[1] - 2 * self.margin - 2 * inch
                if img.imageHeight and img.imageWidth:
                    scaled_height = width * img.imageHeight / img.imageWidth
                    if scaled_height > max_height:
                        img = RLImage(
                            str(result.source_image_path),
                            width=max_height * img.imageWidth / img.imageHeight,
                            height=max_height,
                        )
                img.hAlign = "CENTER"
                elements.append(img)
                elements.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                logger.warning(f"Failed to embed thumbnail: {e}")

        # Description
        if result.description:
            elements.append(
                Paragraph("Description:", self.styles["DescriptionLabel"])
            )
            desc_text = self._escape_text(result.description)
            desc_text = desc_text.replace("\n", "<br/>")
            elements.append(Paragraph(desc_text, self.styles["CustomBody"]))

        # Also include any extracted text
        if result.text and result.text != "[No text detected]":
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(
                Paragraph("Extracted Text:", self.styles["DescriptionLabel"])
            )
            text_content = self._escape_text(result.text)
            text_content = text_content.replace("\n", "<br/>")
            elements.append(Paragraph(text_content, self.styles["CustomBody"]))

        return elements

    def generate(
        self,
        result: AnalysisResult,
        output_path: Path,
        timestamp: datetime | None = None,
        thumbnail_size: Literal["small", "medium", "full"] = "medium",
    ) -> Path:
        """Generate a PDF from analysis result.

        Args:
            result: Analysis result with text and categories
            output_path: Path for the output PDF file
            timestamp: Processing timestamp (defaults to now)
            thumbnail_size: Size for embedded thumbnails (graphic content)

        Returns:
            Path to the generated PDF file
        """
        if timestamp is None:
            timestamp = datetime.now()

        logger.info(f"Generating PDF: {output_path.name}")

        # Create the PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        # Build content
        elements = []

        # Category header
        elements.append(self._create_category_header(result.categories))
        elements.append(Spacer(1, 0.3 * inch))

        # Separator
        elements.append(self._create_separator())
        elements.append(Spacer(1, 0.2 * inch))

        # Content section based on type
        if result.content_type == "graphic":
            elements.extend(self._build_graphic_section(result, thumbnail_size))
        else:
            elements.extend(self._build_text_section(result))

        # Spacer before footer
        elements.append(Spacer(1, 0.5 * inch))

        # Footer line
        elements.append(self._create_separator())
        elements.append(Spacer(1, 0.1 * inch))

        # Footer
        elements.append(self._create_footer(result.source_file, timestamp))

        # Build the PDF
        doc.build(elements)

        logger.info(f"PDF generated successfully: {output_path}")
        return output_path
