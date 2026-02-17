"""OpenAI GPT-4 Vision integration for screenshot analysis."""

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path

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


@dataclass
class AnalysisResult:
    """Result of screenshot analysis."""

    text: str
    categories: list[str]
    source_file: str


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
            # Try to extract JSON from the response
            # Sometimes the model wraps JSON in markdown code blocks
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.index("```") + 3
                end = content.index("```", start)
                content = content[start:end].strip()

            data = json.loads(content)
            text = data.get("text", "[No text detected]")
            categories = data.get("categories", ["Uncategorized"])

            # Limit categories
            if len(categories) > max_categories:
                categories = categories[:max_categories]

            return text, categories

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Return the raw content as text if parsing fails
            return content, ["Uncategorized"]

    def analyze(self, image_path: Path, max_categories: int = 2) -> AnalysisResult:
        """Analyze a screenshot image.

        Args:
            image_path: Path to the PNG image
            max_categories: Maximum number of categories to extract

        Returns:
            AnalysisResult with extracted text and categories
        """
        logger.info(f"Analyzing image: {image_path.name}")

        # Encode image to base64
        base64_image = self._encode_image(image_path)

        # Send to OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
        )

        # Extract content from response
        content = response.choices[0].message.content or ""
        text, categories = self._parse_response(content, max_categories)

        logger.info(f"Analysis complete. Categories: {categories}")

        return AnalysisResult(
            text=text,
            categories=categories,
            source_file=image_path.name,
        )
