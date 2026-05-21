"""
MarketSearchService — live web data aggregation for sector analysis.
Runs multiple targeted queries in parallel and trims to context budget.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

from ddgs import DDGS

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_queries(sector: str, region: str) -> List[str]:
    """
    Generate a diverse query set to maximise data coverage.
    Mixes trade/export, growth, news, and competitor angles.
    """
    base = f"{sector}"
    region_tag = f"{region}" if region and region.lower() != "global" else "global"

    return [
        f"{base} export opportunities {region_tag} 2024 2025",
        f"{base} market size growth trends {region_tag}",
        f"{base} industry news recent developments",
        f"{base} trade challenges risks {region_tag}",
        f"{base} key players market share {region_tag}",
    ]


class MarketSearchService:
    async def fetch(self, sector: str, region: str) -> str:
        queries = _build_queries(sector, region)
        loop = asyncio.get_running_loop()
        tasks = [
            self._run_query(loop, q, settings.search_max_results)
            for q in queries
        ]
        results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

        snippets: List[str] = []
        for q, result in zip(queries, results_per_query):
            if isinstance(result, Exception):
                logger.warning("search failed | query=%r | err=%s", q, result)
                continue
            snippets.extend(result)

        if not snippets:
            return (
                f"⚠️ No live market data could be retrieved for **{sector}** in **{region}**. "
                "The AI will provide a general analysis based on training knowledge, "
                "which may not reflect current conditions."
            )

        body = "\n\n---\n\n".join(snippets)
        return self._trim(body, settings.search_context_chars)

    @staticmethod
    async def _run_query(loop, query: str, max_results: int) -> List[str]:
        """Run a single DuckDuckGo query in a thread executor."""
        # Small stagger to respect DDG rate limits
        await asyncio.sleep(0.5)
        results = await loop.run_in_executor(
            None,
            lambda: list(DDGS().text(query, max_results=max_results, region="wt-wt")),
        )
        return [
            f"### {r['title']}\n{r['body']}\n_Source: [{r['href']}]({r['href']})_"
            for r in results
            if r.get("body")
        ]

    @staticmethod
    def _trim(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        # Trim to last complete sentence / paragraph boundary
        cut = truncated.rfind("\n\n")
        if cut > max_chars * 0.7:
            truncated = truncated[:cut]
        return truncated + "\n\n_[Search results trimmed to fit context window]_"
