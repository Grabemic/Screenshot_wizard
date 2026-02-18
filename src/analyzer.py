"""OpenAI GPT-4 Vision integration for screenshot analysis."""

import base64
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from openai import OpenAI

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """
Analyze this screenshot image and provide:

1. EXTRACTED TEXT: Extract all readable text from the image exactly as it appears.

2. CATEGORIES: Suggest up to 2 categories that best describe this content.
   Categories should be concise (1-3 words each).
   Examples: "Email", "Invoice", "Code Snippet", "Chat Message",
   "Error Log", "Documentation", "Social Media", "Receipt", etc.

Respond in this exact JSON format:
{
  "text": "The extracted text content...",
  "categories": ["Category1", "Category2"]
}

Important:
- Extract ALL visible text, preserving line breaks where appropriate
- If no text is visible, set text to "[No text detected]"
- Always provide at least one category
- Categories should be relevant and specific
"""

AUTO_DETECT_PROMPT = """
Analyze this image and determine if it is primarily a TEXT document or a GRAPHIC/picture.

- TEXT: screenshots of documents, emails, code, chat messages, web pages with text, etc.
- GRAPHIC: photos, diagrams, charts, illustrations, UI mockups, maps, etc.

If TEXT: extract all readable text exactly as it appears.
If GRAPHIC: provide a detailed written description of the visual content.

In both cases, suggest up to 2 categories.

Respond in this exact JSON format:
{
  "content_type": "text" or "graphic",
  "text": "The extracted text (if text document) or empty string (if graphic)",
  "description": "Detailed description (if graphic) or empty string (if text)",
  "categories": ["Category1", "Category2"]
}
"""

GRAPHIC_ANALYSIS_PROMPT = """
Provide a detailed written description of this image. Describe:
- What the image shows (subject matter, scene, objects)
- Layout and composition
- Colors and visual style
- Any text visible in the image
- Purpose or context if apparent

Also suggest up to 2 categories.

Respond in this exact JSON format:
{
  "description": "Detailed description of the image...",
  "categories": ["Category1", "Category2"]
}
"""


@dataclass
class AnalysisResult:
    """Result of screenshot analysis."""

    text: str
    categories: list[str]
    source_file: str
    content_type: Literal["text", "graphic"] = "text"
    description: str = ""
    source_image_path: Path | None = None


# Map file extensions to MIME types for the API
_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class ScreenshotAnalyzer:
    """Analyzes screenshots using OpenAI GPT-4 Vision."""

    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 4096):
        """Initialize the analyzer.

        Args:
            api_key: OpenAI API key
            model: Model to use for analysis
            max_tokens: Maximum tokens for response
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 string."""
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    def _parse_response(self, content: str, max_categories: int) -> tuple[str, list[str]]:
        """Parse the JSON response from the API.

        Args:
            content: Raw response content
            max_categories: Maximum number of categories to return

        Returns:
            Tuple of (extracted_text, categories)
        """
        try:
            data = self._extract_json(content)
            text = data.get("text", "[No text detected]")
            categories = data.get("categories", ["Uncategorized"])

            if len(categories) > max_categories:
                categories = categories[:max_categories]

            return text, categories

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return content, ["Uncategorized"]

    def _extract_json(self, content: str) -> dict:
        """Extract JSON from raw API response content, handling markdown wrapping."""
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        return json.loads(content)

    def _parse_auto_response(
        self, content: str, max_categories: int
    ) -> tuple[str, str, str, list[str]]:
        """Parse auto-detect JSON response.

        Returns:
            Tuple of (content_type, text, description, categories)
        """
        try:
            data = self._extract_json(content)
            content_type = data.get("content_type", "text")
            text = data.get("text", "")
            description = data.get("description", "")
            categories = data.get("categories", ["Uncategorized"])

            if len(categories) > max_categories:
                categories = categories[:max_categories]

            if not text and content_type == "text":
                text = "[No text detected]"

            return content_type, text, description, categories

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse auto-detect response: {e}")
            return "text", content, "", ["Uncategorized"]

    def _parse_graphic_response(
        self, content: str, max_categories: int
    ) -> tuple[str, list[str]]:
        """Parse graphic analysis JSON response.

        Returns:
            Tuple of (description, categories)
        """
        try:
            data = self._extract_json(content)
            description = data.get("description", "")
            categories = data.get("categories", ["Uncategorized"])

            if len(categories) > max_categories:
                categories = categories[:max_categories]

            return description, categories

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse graphic response: {e}")
            return content, ["Uncategorized"]

    def analyze(
        self,
        image_path: Path,
        max_categories: int = 2,
        content_type_override: Literal["text", "graphic"] | None = None,
        image_mime_type: str | None = None,
    ) -> AnalysisResult:
        """Analyze a screenshot image.

        Args:
            image_path: Path to the image file
            max_categories: Maximum number of categories to extract
            content_type_override: Force "text" or "graphic" mode, or None for auto-detect
            image_mime_type: MIME type override (defaults based on file extension)

        Returns:
            AnalysisResult with extracted text/description and categories
        """
        logger.info(f"Analyzing image: {image_path.name}")

        # Determine MIME type
        if image_mime_type is None:
            image_mime_type = _MIME_TYPES.get(image_path.suffix.lower(), "image/png")

        base64_image = self._encode_image(image_path)

        # Choose prompt based on content type
        if content_type_override == "graphic":
            prompt = GRAPHIC_ANALYSIS_PROMPT
        elif content_type_override == "text":
            prompt = ANALYSIS_PROMPT
        else:
            prompt = AUTO_DETECT_PROMPT

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime_type};base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
        )

        raw_content = response.choices[0].message.content or ""

        if content_type_override == "graphic":
            description, categories = self._parse_graphic_response(
                raw_content, max_categories
            )
            logger.info(f"Graphic analysis complete. Categories: {categories}")
            return AnalysisResult(
                text="",
                categories=categories,
                source_file=image_path.name,
                content_type="graphic",
                description=description,
                source_image_path=image_path,
            )

        elif content_type_override == "text":
            text, categories = self._parse_response(raw_content, max_categories)
            logger.info(f"Text analysis complete. Categories: {categories}")
            return AnalysisResult(
                text=text,
                categories=categories,
                source_file=image_path.name,
                content_type="text",
            )

        else:
            # Auto-detect
            content_type, text, description, categories = self._parse_auto_response(
                raw_content, max_categories
            )
            logger.info(
                f"Auto-detect: {content_type}. Categories: {categories}"
            )
            return AnalysisResult(
                text=text,
                categories=categories,
                source_file=image_path.name,
                content_type=content_type,
                description=description,
                source_image_path=image_path if content_type == "graphic" else None,
            )
