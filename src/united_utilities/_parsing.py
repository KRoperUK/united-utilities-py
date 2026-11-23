"""Helpers for the quirky shapes the UU API returns.

Dates arrive as ``DDMMYYYY`` strings (e.g. ``"21112026"``), sometimes null or
empty. Numeric meter readings arrive as strings.
"""

from __future__ import annotations

from datetime import date


def parse_date(value: str | None) -> date | None:
    """Parse a ``DDMMYYYY`` string. Returns None for empty/invalid input."""
    if not value or len(value) != 8 or not value.isdigit():
        return None
    day, month, year = int(value[0:2]), int(value[2:4]), int(value[4:8])
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_int(value: str | int | None) -> int | None:
    """Parse an int that may arrive as a string or be absent."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
