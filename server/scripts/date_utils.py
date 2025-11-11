#!/usr/bin/env python3
"""date_utils.py

Utility helpers that let scripts respect an optional date override.
If the environment variable SWAS_CURRENT_DATE is set, it should hold a date
in ISO (YYYY-MM-DD), US (MM/DD/YYYY), or ISO datetime format
(YYYY-MM-DDTHH:MM[:SS]). When provided, all helpers return that moment;
otherwise they defer to the real current clock.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

ENV_KEY = "SWAS_CURRENT_DATE"
_SUPPORTED_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
)


def _parse_override(value: str) -> Optional[datetime]:
    raw = value.strip()
    if not raw:
        return None

    for fmt in _SUPPORTED_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if "H" not in fmt:
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt

    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


_OVERRIDE_NOW: Optional[datetime] = None
_raw = os.environ.get(ENV_KEY)
if _raw:
    _OVERRIDE_NOW = _parse_override(_raw)


def get_current_datetime() -> datetime:
    """Return the override datetime if provided, else the live clock."""
    return _OVERRIDE_NOW or datetime.now()


def get_current_date():
    """Return the current date, respecting the override if set."""
    return get_current_datetime().date()


def get_current_year() -> int:
    """Return the effective current year."""
    return get_current_datetime().year


def override_active() -> bool:
    """True if the override is active and parsed successfully."""
    return _OVERRIDE_NOW is not None


def describe_override() -> Optional[str]:
    """Return the ISO string for the active override, if any."""
    if _OVERRIDE_NOW is None:
        return None
    return _OVERRIDE_NOW.isoformat()
