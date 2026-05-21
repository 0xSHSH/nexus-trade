"""
SessionService — in-memory store for query history and watchlists.

In production, swap the dict store for Redis or a database.
The interface is designed for a drop-in replacement.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models.schemas import HistoryRecord, WatchlistAddRequest, WatchlistEntry

_HISTORY_MAX = 50
_WATCHLIST_MAX = 20


class SessionService:
    def __init__(self):
        self._history: Dict[str, List[dict]] = defaultdict(list)
        self._watchlist: Dict[str, List[dict]] = defaultdict(list)
        self._lock = asyncio.Lock()

    # ── History ───────────────────────────────────────────────────────────────

    async def record_query(
        self,
        user_id: str,
        sector: str,
        region: str,
        depth: str,
        status: str,
        processing_ms: Optional[int] = None,
    ) -> None:
        async with self._lock:
            history = self._history[user_id]
            # Update existing in-progress record if present
            if status != "in_progress":
                for rec in reversed(history):
                    if (
                        rec["sector"] == sector
                        and rec["region"] == region
                        and rec["status"] == "in_progress"
                    ):
                        rec["status"] = status
                        rec["processing_ms"] = processing_ms
                        return

            history.append({
                "sector": sector,
                "region": region,
                "depth": depth,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_ms": processing_ms,
            })

            # Rolling window — keep most recent
            if len(history) > _HISTORY_MAX:
                self._history[user_id] = history[-_HISTORY_MAX:]

    async def get_history(self, user_id: str) -> List[HistoryRecord]:
        async with self._lock:
            return [
                HistoryRecord(**r)
                for r in reversed(self._history.get(user_id, []))
            ]

    async def clear_history(self, user_id: str) -> None:
        async with self._lock:
            self._history.pop(user_id, None)

    # ── Watchlist ─────────────────────────────────────────────────────────────

    async def get_watchlist(self, user_id: str) -> List[WatchlistEntry]:
        async with self._lock:
            return [WatchlistEntry(**e) for e in self._watchlist.get(user_id, [])]

    async def add_to_watchlist(
        self, user_id: str, req: WatchlistAddRequest
    ) -> WatchlistEntry:
        async with self._lock:
            wl = self._watchlist[user_id]
            # Deduplicate by sector+region
            existing = next(
                (e for e in wl if e["sector"].lower() == req.sector.lower()
                 and e["region"].lower() == req.region.lower()),
                None,
            )
            if existing:
                existing["alert_enabled"] = req.alert_enabled
                return WatchlistEntry(**existing)

            entry = {
                "sector": req.sector,
                "region": req.region,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "last_checked": None,
                "alert_enabled": req.alert_enabled,
            }
            wl.append(entry)
            return WatchlistEntry(**entry)

    async def remove_from_watchlist(self, user_id: str, sector: str) -> bool:
        async with self._lock:
            wl = self._watchlist.get(user_id, [])
            new_wl = [e for e in wl if e["sector"].lower() != sector.lower()]
            removed = len(new_wl) < len(wl)
            self._watchlist[user_id] = new_wl
            return removed
