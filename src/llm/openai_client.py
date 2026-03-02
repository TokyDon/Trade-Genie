"""
Trade Genie - OpenAI LLM Client
"""

import json
import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def analyze_with_openai(events_digest: str, top_picks: int = 10) -> Optional[dict]:
    """Run analysis using OpenAI GPT-4o."""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_"):
        logger.info("OpenAI key not configured, skipping.")
        return None

    try:
        from openai import OpenAI
        from src.llm.prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            events_digest=events_digest, top_picks=top_picks
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content
        result = json.loads(raw_text)
        result["_model"] = "openai/gpt-4o"
        result["_raw"] = raw_text
        logger.info("OpenAI analysis complete.")
        return result

    except Exception as e:
        logger.error(f"OpenAI analysis failed: {e}")
        return None
