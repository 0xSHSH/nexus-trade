"""
IntelligenceService — wraps Google Gemini with retry logic, structured
prompt engineering, and score extraction.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Optional

from google import genai
from google.genai import types
from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import SectorScore

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are NexusTrade Intelligence Engine — an elite market analyst specialising in "
    "global trade flows, export opportunity identification, and sector-level risk assessment. "
    "You produce concise, data-driven reports for founders, investors, and trade professionals. "
    "Always respond in well-structured Markdown. Never fabricate statistics; if data is absent, "
    "say so explicitly. Avoid filler phrases like 'significant potential' without data to back it up."
)


def _build_prompt(sector: str, region: str, depth: str, market_data: str) -> str:
    depth_config = {
        "quick": {
            "sections": ["Executive Summary", "Top 3 Opportunities", "Key Risks"],
            "words": "300-500",
        },
        "standard": {
            "sections": [
                "Executive Summary",
                "Market Landscape",
                "Top Opportunities (5)",
                "Target Markets",
                "Competitive Dynamics",
                "Risk Factors",
                "Recommended Actions",
                "Data Sources",
            ],
            "words": "600-900",
        },
        "deep": {
            "sections": [
                "Executive Summary",
                "Market Landscape & Size Estimates",
                "Demand Signals",
                "Top Opportunities (5-7) with Entry Strategies",
                "Target Markets with Trade Flow Analysis",
                "Competitive Benchmarking",
                "Regulatory & Geopolitical Risks",
                "Supply Chain Considerations",
                "Recommended 90-Day Action Plan",
                "Opportunity Score Card (JSON block)",
                "Data Sources",
            ],
            "words": "1000-1400",
        },
    }
    cfg = depth_config.get(depth, depth_config["standard"])
    sections_list = "\n".join(f"  {i+1}. **{s}**" for i, s in enumerate(cfg["sections"]))

    score_instruction = ""
    if depth == "deep":
        score_instruction = """
At the end, include a JSON block (fenced with ```json) with this exact shape:
```json
{
  "score": {
    "overall": <0-100>,
    "market_size": <0-100>,
    "growth_velocity": <0-100>,
    "competitive_gap": <0-100>,
    "risk_adjusted": <0-100>
  }
}
```
Score criteria: overall = weighted average; market_size = TAM relevance (100=USD 50B+);
growth_velocity = YoY growth rate (100=30%+); competitive_gap = whitespace for new entrants;
risk_adjusted = opportunity net of geopolitical/regulatory risk.
"""

    return f"""## NexusTrade Analysis Request

**Sector:** {sector}
**Focus Region:** {region}
**Depth:** {depth}
**Target word count:** {cfg["words"]}

---

## Live Market Data (Web-sourced)

{market_data}

---

## Report Structure

Generate a trade intelligence report with EXACTLY these sections:

{sections_list}

**Style rules:**
- Lead each section with the most important insight (inverted pyramid).
- Use specific figures (USD values, growth %, country names) wherever the data supports it.
- Use ❌ for risks, ✅ for strengths, 🎯 for opportunities.
- End bullet points with the source title in parentheses if traceable.
- If data is insufficient, state it and recommend a primary research angle.
{score_instruction}"""


class IntelligenceService:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def analyse(
        self,
        sector: str,
        region: str,
        depth: str,
        market_data: str,
    ) -> str:
        prompt = _build_prompt(sector, region, depth, market_data)
        loop = asyncio.get_running_loop()
        start = time.monotonic()

        for attempt in range(3):
            try:
                response = await loop.run_in_executor(
                    None, lambda: self._client.models.generate_content(
                        model=settings.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=_SYSTEM_PROMPT,
                            temperature=settings.gemini_temperature,
                            max_output_tokens=settings.gemini_max_output_tokens,
                        ),
                    )
                )
                elapsed = time.monotonic() - start
                logger.info(
                    "gemini ok | sector=%s | region=%s | depth=%s | %.2fs",
                    sector, region, depth, elapsed,
                )
                return response.text

            except Exception as exc:
                err = str(exc).lower()
                retriable = any(x in err for x in ["429", "quota", "503", "unavailable", "busy"])

                if retriable and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(
                        "gemini retry | sector=%s | attempt=%d | wait=%ds | %s",
                        sector, attempt + 1, wait, exc,
                    )
                    await asyncio.sleep(wait)
                    continue

                if "invalid api key" in err or "api_key" in err:
                    logger.critical("gemini bad api key — check GEMINI_API_KEY env var")
                    raise HTTPException(500, "AI service configuration error. Contact support.")

                if retriable:
                    raise HTTPException(503, "AI service is temporarily busy. Retry in 30 seconds.")

                logger.error("gemini hard fail | sector=%s | %s", sector, exc)
                raise HTTPException(500, "Analysis failed. Please retry.")

        raise HTTPException(500, "Analysis failed after retries.")

    def extract_score(self, report: str) -> Optional[SectorScore]:
        """Extract the JSON score block embedded in a 'deep' report, if present."""
        pattern = r"```json\s*(\{.*?\"score\".*?\})\s*```"
        match = re.search(pattern, report, re.DOTALL)
        if not match:
            return None
        try:
            import json
            data = json.loads(match.group(1))
            return SectorScore(**data["score"])
        except Exception as e:
            logger.warning("score extraction failed: %s", e)
            return None