"""Parse United Utilities bill PDFs into readings and itemised charges.

The API gives bill totals and meter readings but not tariffs; only the PDF has
the per-m³ rates, standing charges and the fresh-water / wastewater split.

Bills come in two templates. Itemised bills show both meter readings and a
"Your charges" block with fresh water on the left and wastewater on the right,
one block per tariff period when a bill spans 1 April. Shorter bills (payment
plan updates) have neither; they parse to a :class:`Bill` with no readings or
charges rather than raising.

Text matching is inherently tied to the bill template, so every parse is
cross-checked: line items must add up to the total, each line must equal
quantity × rate, both services must bill the same volume, and the volume must
match the meter readings. Any failure is recorded in :attr:`Bill.problems`, and
the price properties then return ``None`` rather than a possibly wrong figure.
Needs the ``pdf`` extra (``pip install united-utilities[pdf]``).
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime

_DATE_LONG = "%d %B %Y"
_DATE_SHORT = "%d %b %Y"

_PERIOD = re.compile(r"Billing period\s+(\d{1,2} \w+ \d{4})\s*-\s*(\d{1,2} \w+ \d{4})")
_READING = re.compile(r"\b(OUR|YOUR|ESTIMATED|AN ESTIMATED)\s+READING\s+(\d+)")
_READING_DATES = re.compile(r"(\d{1,2} \w{3} \d{4})\s+(\d{1,2} \w{3} \d{4})")
_USAGE_TOTAL = re.compile(r"(\d[\d,]*)\s?m³\s*\(\s*[\d,]+ litres\)")
_TOTAL = re.compile(r"Your new charges\s+£([\d,]+\.\d{2})")
_DISCOUNT = re.compile(r"discount\s+£([\d,]+\.\d{2})\s*\(cr\)", re.IGNORECASE)
_TARIFF_PERIOD = re.compile(r"Charges for:\s*(\d{1,2} \w+ \d{4})\s*-\s*(\d{1,2} \w+ \d{4})")
_USAGE_LINE = re.compile(r"Usage\s+([\d.]+)\s*m³\s*@\s*£([\d.]+)\s*per m³\s*=\s*£([\d,]+\.\d{2})")
_STANDING_LINE = re.compile(r"Standing\s+(\d+)\s*days\s*@\s*£([\d,.]+)\s*a year\s*=\s*£([\d,]+\.\d{2})")

_READ_BY = {"OUR": "united_utilities", "YOUR": "customer", "ESTIMATED": "estimated", "AN ESTIMATED": "estimated"}
_SERVICES = ("water", "wastewater")  # left column, right column
# Text that only appears on bills with a charges breakdown. If it's present but no charge
# lines parsed, the template has probably changed.
_ITEMISED_MARKERS = re.compile(r"per m³|a year\s*=|Your charges")
_PENNY = 0.015  # rounding tolerance for amounts, in £
_M3 = 0.01  # tolerance for usage volumes, in m³


@dataclass(frozen=True)
class BillReading:
    value: int
    date: date | None
    read_by: str  # "customer", "united_utilities" or "estimated"


@dataclass(frozen=True)
class ChargeLine:
    service: str  # "water" (fresh water) or "wastewater"
    kind: str  # "usage" or "standing"
    quantity: float  # m³ for usage, days for standing
    rate: float  # £ per m³ for usage, £ per year for standing
    amount: float
    period_start: date | None = None  # tariff period, when the bill splits charges
    period_end: date | None = None


@dataclass(frozen=True)
class Bill:
    period_start: date | None = None
    period_end: date | None = None
    previous_reading: BillReading | None = None
    current_reading: BillReading | None = None
    usage_m3: int | None = None
    charges: list[ChargeLine] = field(default_factory=list)
    discount: float | None = None
    total: float | None = None
    #: Reasons the parse may be wrong (template change, misread column). Empty when every
    #: cross-check passed. Don't trust the charges or prices of a bill that has problems.
    problems: tuple[str, ...] = ()

    @property
    def itemised(self) -> bool:
        """True when the bill carried a charges breakdown."""
        return bool(self.charges)

    @property
    def trustworthy(self) -> bool:
        """Itemised, and every cross-check between the parsed figures passed."""
        return self.itemised and not self.problems

    def _latest(self, kind: str) -> list[ChargeLine]:
        lines = [c for c in self.charges if c.kind == kind]
        if not lines:
            return []
        latest_end = max((c.period_end for c in lines if c.period_end), default=None)
        return [c for c in lines if c.period_end == latest_end]

    @property
    def price_per_m3(self) -> float | None:
        """Combined fresh water + wastewater usage rate (£/m³) for the bill's latest tariff.

        ``None`` unless the bill is :attr:`trustworthy`, so a misread bill never yields a price.
        """
        lines = self._latest("usage") if self.trustworthy else []
        return round(sum(c.rate for c in lines), 3) if lines else None

    @property
    def standing_charge_per_year(self) -> float | None:
        """Combined standing charges (£/year) for the bill's latest tariff. ``None`` unless trustworthy."""
        lines = self._latest("standing") if self.trustworthy else []
        return round(sum(c.rate for c in lines), 2) if lines else None


def _date(value: str, fmt: str) -> date | None:
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def _money(value: str) -> float:
    return float(value.replace(",", ""))


def _charges(layout_text: str) -> list[ChargeLine]:
    """Charge lines from layout-mode text, where each row holds both columns."""
    charges: list[ChargeLine] = []
    period: tuple[date | None, date | None] = (None, None)
    for line in layout_text.splitlines():
        if m := _TARIFF_PERIOD.search(line):
            period = (_date(m.group(1), _DATE_LONG), _date(m.group(2), _DATE_LONG))
            continue
        for kind, pattern in (("usage", _USAGE_LINE), ("standing", _STANDING_LINE)):
            for service, m in zip(_SERVICES, pattern.finditer(line), strict=False):
                charges.append(
                    ChargeLine(
                        service=service,
                        kind=kind,
                        quantity=float(m.group(1)),
                        rate=_money(m.group(2)),
                        amount=_money(m.group(3)),
                        period_start=period[0],
                        period_end=period[1],
                    )
                )
    return charges


def _problems(bill: Bill, text: str, layout_text: str) -> tuple[str, ...]:
    """Cross-check the parsed figures against each other and the bill's own arithmetic."""
    if not bill.charges:
        if _ITEMISED_MARKERS.search(text) or _ITEMISED_MARKERS.search(layout_text):
            return ("bill has a charges section but no charge lines could be read",)
        return ()

    problems: list[str] = []
    if bill.total is None:
        problems.append("charges were read but the bill total was not")
    else:
        lines_total = sum(c.amount for c in bill.charges) - (bill.discount or 0)
        if abs(lines_total - bill.total) > _PENNY:
            problems.append(f"charge lines add up to £{lines_total:.2f} but the bill total is £{bill.total:.2f}")

    for c in bill.charges:
        if c.kind == "usage":
            expected = [c.quantity * c.rate]
        else:  # standing charge pro-rated by day; accept either year length
            expected = [c.quantity * c.rate / 365, c.quantity * c.rate / 366]
        if all(abs(e - c.amount) > _PENNY for e in expected):
            problems.append(f"{c.service} {c.kind} line £{c.amount:.2f} doesn't equal {c.quantity:g} × £{c.rate:g}")

    periods = {(c.period_start, c.period_end) for c in bill.charges}
    for period in periods:
        lines = [c for c in bill.charges if (c.period_start, c.period_end) == period]
        for kind in ("usage", "standing"):
            services = sorted(c.service for c in lines if c.kind == kind)
            if services != ["wastewater", "water"]:
                problems.append(
                    f"expected one water and one wastewater {kind} line per period, got {services or 'none'}"
                )
        usage = {c.service: c.quantity for c in lines if c.kind == "usage"}
        if len(usage) == 2 and abs(usage["water"] - usage["wastewater"]) > _M3:
            problems.append("water and wastewater usage volumes differ")

    water_usage = sum(c.quantity for c in bill.charges if c.kind == "usage" and c.service == "water")
    if bill.usage_m3 is not None and abs(water_usage - bill.usage_m3) > _M3:
        problems.append(f"charged usage {water_usage:g} m³ doesn't match the bill's {bill.usage_m3} m³")
    if bill.previous_reading and bill.current_reading and bill.usage_m3 is not None:
        read_usage = bill.current_reading.value - bill.previous_reading.value
        if read_usage != bill.usage_m3:
            problems.append(f"meter readings differ by {read_usage} m³ but the bill says {bill.usage_m3} m³")
    if bill.period_start is None or bill.period_end is None:
        problems.append("charges were read but the billing period was not")
    return tuple(problems)


def parse_bill_text(text: str, layout_text: str) -> Bill:
    """Parse a bill from its extracted text.

    ``text`` is plain extraction (reading order); ``layout_text`` is layout-mode
    extraction, which keeps the fresh water and wastewater columns on one row.
    """
    period = _PERIOD.search(text)
    readings = _READING.findall(text)
    reading_dates = _READING_DATES.search(text)
    dates = (
        (_date(reading_dates.group(1), _DATE_SHORT), _date(reading_dates.group(2), _DATE_SHORT))
        if reading_dates
        else (None, None)
    )
    previous = current = None
    if len(readings) >= 2:
        (prev_by, prev_value), (cur_by, cur_value) = readings[0], readings[1]
        previous = BillReading(int(prev_value), dates[0], _READ_BY[prev_by])
        current = BillReading(int(cur_value), dates[1], _READ_BY[cur_by])
    usage = _USAGE_TOTAL.search(text)
    total = _TOTAL.search(text)
    discount = _DISCOUNT.search(layout_text)
    bill = Bill(
        period_start=_date(period.group(1), _DATE_LONG) if period else None,
        period_end=_date(period.group(2), _DATE_LONG) if period else None,
        previous_reading=previous,
        current_reading=current,
        usage_m3=int(usage.group(1).replace(",", "")) if usage else None,
        charges=_charges(layout_text),
        discount=_money(discount.group(1)) if discount else None,
        total=_money(total.group(1)) if total else None,
    )
    return replace(bill, problems=_problems(bill, text, layout_text))


def parse_bill(pdf: bytes) -> Bill:
    """Parse a bill PDF (as returned by :meth:`UnitedUtilitiesClient.bill_pdf`)."""
    try:
        from pypdf import PdfReader
    except ImportError as err:  # pragma: no cover - exercised only without the extra
        raise ImportError("parse_bill needs pypdf: pip install 'united-utilities[pdf]'") from err

    # pypdf warns about the bill's rotated sidebar text in layout mode; it doesn't affect the charges.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        pages = PdfReader(io.BytesIO(pdf)).pages
        text = "\n".join(page.extract_text() or "" for page in pages)
        layout_text = "\n".join(page.extract_text(extraction_mode="layout") or "" for page in pages)
    except Exception as err:  # noqa: BLE001 - pypdf raises many types on malformed input
        return Bill(problems=(f"PDF could not be read ({type(err).__name__})",))
    return parse_bill_text(text, layout_text)
