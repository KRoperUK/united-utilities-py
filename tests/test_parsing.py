from __future__ import annotations

from datetime import date

import pytest

from united_utilities._parsing import parse_date, parse_int


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("21112026", date(2026, 11, 21)),
        ("09042027", date(2027, 4, 9)),
        ("", None),
        (None, None),
        ("2111202", None),  # too short
        ("32112026", None),  # invalid day
        ("abcdefgh", None),
    ],
)
def test_parse_date(raw: str | None, expected: date | None) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1975", 1975), (1965, 1965), ("", None), (None, None), ("x", None)],
)
def test_parse_int(raw: str | int | None, expected: int | None) -> None:
    assert parse_int(raw) == expected
