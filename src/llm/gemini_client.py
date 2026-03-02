"""
Trade Genie - Google Gemini LLM Client
"""

import json
import logging
import re
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def analyze_with_gemini(events_digest: str, top_picks: int = 10) -> Optional[dict]:
    """Run analysis using Google Gemini."""
    if (
        not settings.GOOGLE_GEMINI_API_KEY
        or settings.GOOGLE_GEMINI_API_KEY.startswith("your_")
    ):
        logger.info("Gemini key not configured, skipping.")
        return None

    try:
        import google.generativeai as genai
        from src.llm.prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT

        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4000,
                response_mime_type="application/json",
            ),
        )

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            events_digest=events_digest, top_picks=top_picks
        )

        response = model.generate_content(prompt)
        raw_text = response.text

        # Strip markdown if present
        json_match = re.search(r"```json\s*([\s\S]+?)\s*```", raw_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = raw_text.strip()
            if not json_str.startswith("{"):
                start = json_str.find("{")
                end = json_str.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

        result = json.loads(json_str)
        result["_model"] = "google/gemini-1.5-pro"
        result["_raw"] = raw_text
        logger.info("Gemini analysis complete.")
        return result

    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return None
