"""Multimodal vision: extract clinical findings from X-ray or chart images via Claude Vision."""

from __future__ import annotations

import base64
from pathlib import Path

import anthropic
from PIL import Image

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_VISION_SYSTEM = """You are a dental radiograph analysis assistant.
Given a dental X-ray or clinical image, extract structured clinical findings.
Return ONLY valid JSON with this schema:
{
  "teeth": {
    "<tooth_number>": {
      "observations": ["<observation>"],
      "suspected_conditions": ["<condition>"]
    }
  },
  "periodontal": "<summary or null>",
  "bone_level": "<summary or null>",
  "other_findings": ["<finding>"],
  "confidence": "high|medium|low",
  "notes": "<any caveats>"
}
Do not diagnose — only describe radiographic observations."""


def _encode_image(image_path: Path) -> tuple[str, str]:
    """Return base64-encoded image and its media type."""
    img = Image.open(image_path)
    fmt = img.format or "PNG"
    media_type = f"image/{fmt.lower()}"
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def analyze_xray(image_path: Path | str, clinical_context: str = "") -> dict:
    """Send an X-ray image to Claude Vision and return structured findings."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data, media_type = _encode_image(image_path)

    user_content: list[dict] = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": image_data},
        },
    ]
    if clinical_context:
        user_content.append({"type": "text", "text": f"Clinical context: {clinical_context}"})
    user_content.append({"type": "text", "text": "Analyze this dental image and return findings as JSON."})

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_VISION_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    import json

    raw = response.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
