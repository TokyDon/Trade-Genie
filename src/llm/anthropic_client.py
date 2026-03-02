"""
Trade Genie - Anthropic Claude LLM Client
"""

import json
import logging
import re
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def analyze_with_anthropic(events_digest: str, top_picks: int = 10) -> Optional[dict]:
    """Run analysis using Anthropic Claude."""
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY.startswith("your_"):
        logger.info("Anthropic key not configured, skipping.")
        return None

    try:
        import anthropic
        from src.llm.prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            events_digest=events_digest, top_picks=top_picks
        )

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text

        # Extract JSON from response (Claude may wrap it in markdown)
        json_match = re.search(r"```json\s*([\s\S]+?)\s*```", raw_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_str = raw_text.strip()
            if json_str.startswith("{"):
                pass  # Already JSON
            else:
                # Find first { to last }
                start = json_str.find("{")
                end = json_str.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

        result = json.loads(json_str)
        result["_model"] = "anthropic/claude-opus-4-5"
        result["_raw"] = raw_text
        logger.info("Anthropic analysis complete.")
        return result

    except Exception as e:
        logger.error(f"Anthropic analysis failed: {e}")
        return None
