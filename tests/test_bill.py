"""Bill parsing tests on synthetic text shaped like pypdf's extraction of real bills.

No real bill is committed: bills carry the account holder's name, address and
bank details. The values below are invented but keep the real layout.
"""

from __future__ import annotations

from datetime import date

from united_utilities import parse_bill_text

# Plain extraction keeps reading order; layout extraction keeps the fresh water
# (left) and wastewater (right) columns on one row.
SINGLE_TARIFF_TEXT = """
Billing period
9 October 2026 -
21 November 2026 B
Your meter number
is 00A000000
OUR READING
1000
YOUR READING
1012
12m³
(12,000 litres)
8 Oct 2026 21 Nov 2026
Your new charges £76.70
"""

SINGLE_TARIFF_LAYOUT = """
Fresh water
£40.00      /      Wastewater£30.00      \\
|  Usage      12 m³      @   £3.000  per m³    =      £36.00      |  Usage      12 m³      @  £2.000 per m³    =      £24.00
< Standing      44 days      @   £30.00 a year      =      £3.62      < Standing      44 days     @  £150.00 a year   =      £18.08
   charge      charge
Direct Debit discount      £5.00 (cr)
 Your new charges      £76.70
"""

SPLIT_TARIFF_TEXT = """
Billing period
9 January 2026 -
10 April 2026 B
YOUR READING
2000
ESTIMATED READING
2025
25m³
(25,000 litres)
8 Jan 2026 10 Apr 2026
Your new charges £152.65
"""

SPLIT_TARIFF_LAYOUT = """
      Charges for: 9 January 2026 - 31 March 2026
|  Usage      20.5 m³   @   £2.500  per m³    =      £51.25      |  Usage      20.5 m³   @  £1.800 per m³    =      £36.90
< Standing      82 days      @   £25.00 a year      =      £5.62      < Standing      82 days     @  £140.00 a year   =      £31.45
      Charges for: 1 April 2026 - 10 April 2026
|  Usage      4.5 m³      @   £3.000  per m³    =      £13.50      |  Usage      4.5 m³      @  £2.000 per m³    =      £9.00
< Standing      10 days      @   £30.00 a year      =      £0.82      < Standing      10 days      @  £150.00 a year   =      £4.11
"""

# A payment-plan update: balance and Direct Debit schedule only.
PAYMENT_PLAN_TEXT = """
Your balance
£23.03
We'll collect your next payment of £49.24 by Direct
25/01/26 £49.24 25/02/26 £49.07
Total for this bill £589.01
"""


def test_single_tariff_bill() -> None:
    bill = parse_bill_text(SINGLE_TARIFF_TEXT, SINGLE_TARIFF_LAYOUT)

    assert bill.itemised
    assert (bill.period_start, bill.period_end) == (date(2026, 10, 9), date(2026, 11, 21))
    assert bill.previous_reading is not None and bill.current_reading is not None
    assert (bill.previous_reading.value, bill.previous_reading.date, bill.previous_reading.read_by) == (
        1000,
        date(2026, 10, 8),
        "united_utilities",
    )
    assert (bill.current_reading.value, bill.current_reading.read_by) == (1012, "customer")
    assert bill.usage_m3 == 12
    assert bill.discount == 5.0
    assert bill.total == 76.70

    by_key = {(c.service, c.kind): c for c in bill.charges}
    assert len(bill.charges) == 4
    assert (by_key["water", "usage"].quantity, by_key["water", "usage"].rate) == (12, 3.0)
    assert (by_key["wastewater", "usage"].rate, by_key["wastewater", "usage"].amount) == (2.0, 24.0)
    assert (by_key["water", "standing"].quantity, by_key["water", "standing"].rate) == (44, 30.0)
    assert by_key["wastewater", "standing"].amount == 18.08
    assert all(c.period_start is None for c in bill.charges)

    # Line items minus the discount reconcile to the bill total.
    assert round(sum(c.amount for c in bill.charges) - (bill.discount or 0), 2) == bill.total
    assert bill.price_per_m3 == 5.0
    assert bill.standing_charge_per_year == 180.0


def test_split_tariff_bill_uses_latest_period_for_prices() -> None:
    bill = parse_bill_text(SPLIT_TARIFF_TEXT, SPLIT_TARIFF_LAYOUT)

    assert len(bill.charges) == 8
    assert {c.period_end for c in bill.charges} == {date(2026, 3, 31), date(2026, 4, 10)}
    old = [c for c in bill.charges if c.period_end == date(2026, 3, 31)]
    assert {c.period_start for c in old} == {date(2026, 1, 9)}
    # The new tariff from 1 April, not the old one or a blend.
    assert bill.price_per_m3 == 5.0
    assert bill.standing_charge_per_year == 180.0
    assert bill.current_reading is not None and bill.current_reading.read_by == "estimated"
    assert bill.discount is None


def test_payment_plan_update_is_not_itemised() -> None:
    bill = parse_bill_text(PAYMENT_PLAN_TEXT, PAYMENT_PLAN_TEXT)

    assert not bill.itemised
    assert bill.charges == []
    assert bill.previous_reading is None and bill.current_reading is None
    assert bill.period_start is None and bill.total is None
    assert bill.price_per_m3 is None and bill.standing_charge_per_year is None


def test_unrecognised_text_degrades_to_empty_bill() -> None:
    bill = parse_bill_text("completely different template", "")
    assert not bill.itemised
    assert bill.usage_m3 is None


def test_consistent_bills_have_no_problems() -> None:
    for text, layout in ((SINGLE_TARIFF_TEXT, SINGLE_TARIFF_LAYOUT), (SPLIT_TARIFF_TEXT, SPLIT_TARIFF_LAYOUT)):
        bill = parse_bill_text(text, layout)
        assert bill.problems == ()
        assert bill.trustworthy
    assert parse_bill_text(PAYMENT_PLAN_TEXT, PAYMENT_PLAN_TEXT).problems == ()


def test_total_mismatch_is_flagged_and_prices_withheld() -> None:
    bill = parse_bill_text(SINGLE_TARIFF_TEXT.replace("£76.70", "£99.99"), SINGLE_TARIFF_LAYOUT)

    assert any("add up to £76.70 but the bill total is £99.99" in p for p in bill.problems)
    assert not bill.trustworthy
    assert bill.price_per_m3 is None
    assert bill.standing_charge_per_year is None
    assert bill.charges  # raw lines are still there for inspection


def test_misread_line_amount_is_flagged() -> None:
    layout = SINGLE_TARIFF_LAYOUT.replace("=      £36.00", "=      £63.00")
    bill = parse_bill_text(SINGLE_TARIFF_TEXT, layout)

    assert any("water usage line £63.00 doesn't equal 12 × £3" in p for p in bill.problems)


def test_standing_charge_accepts_leap_year_pro_rating() -> None:
    # 44 days @ £150/yr is £18.08 over 365 days and £18.03 over 366; both are fine.
    layout = SINGLE_TARIFF_LAYOUT.replace("=      £18.08", "=      £18.03")
    text = SINGLE_TARIFF_TEXT.replace("£76.70", "£76.65")
    assert parse_bill_text(text, layout).problems == ()


def test_missing_column_is_flagged() -> None:
    # Only the fresh water half of each row was read.
    layout = """
|  Usage      12 m³      @   £3.000  per m³    =      £36.00
< Standing      44 days      @   £30.00 a year      =      £3.62
"""
    bill = parse_bill_text(SINGLE_TARIFF_TEXT, layout)

    assert any("expected one water and one wastewater" in p for p in bill.problems)
    assert not bill.trustworthy


def test_usage_disagreeing_with_readings_is_flagged() -> None:
    bill = parse_bill_text(SINGLE_TARIFF_TEXT.replace("YOUR READING\n1012", "YOUR READING\n1020"), SINGLE_TARIFF_LAYOUT)
    assert any("meter readings differ by 20 m³ but the bill says 12 m³" in p for p in bill.problems)


def test_changed_template_with_unreadable_charges_is_flagged() -> None:
    # The charges block is there but in a format the patterns don't recognise.
    layout = "Your charges\nUsage: 12 cubic metres at 300p each\n"
    bill = parse_bill_text(SINGLE_TARIFF_TEXT, layout)

    assert bill.problems == ("bill has a charges section but no charge lines could be read",)
    assert not bill.itemised and not bill.trustworthy


def test_unreadable_pdf_is_flagged_not_raised() -> None:
    from united_utilities import parse_bill

    bill = parse_bill(b"%PDF-1.4 truncated garbage")

    assert len(bill.problems) == 1
    assert bill.problems[0].startswith("PDF could not be read")
    assert not bill.trustworthy
