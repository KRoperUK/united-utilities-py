"""Typed models for United Utilities API responses.

Field coverage is deliberately partial: only what a Home Assistant integration
needs. Shapes were confirmed against live production responses (app build 102).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from ._parsing import parse_date, parse_int


@dataclass(frozen=True)
class AccountHistoryItem:
    amount: float | None
    date: date | None
    type: str | None  # "BI" = bill, "PA" = payment
    bill_cancelled: bool | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> AccountHistoryItem:
        return cls(
            amount=d.get("amount"),
            date=parse_date(d.get("date")),
            type=d.get("type"),
            bill_cancelled=d.get("billCancelled"),
        )


@dataclass(frozen=True)
class AccountDetails:
    account_balance: float | None
    next_payment_date: date | None
    next_payment_due: float | None
    is_on_meter: bool | None
    can_submit_meter_reading: bool | None
    payment_plan: str | None
    payment_plan_status: str | None
    is_active: bool | None
    has_missed_payment: bool | None
    unread_bill_count: int | None
    billing_preference: str | None
    account_history: list[AccountHistoryItem]

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> AccountDetails:
        return cls(
            account_balance=d.get("accountBalance"),
            next_payment_date=parse_date(d.get("nextPaymentDate")),
            next_payment_due=d.get("nextPaymentDue"),
            is_on_meter=d.get("isOnMeter"),
            can_submit_meter_reading=d.get("canSubmitMeterReading"),
            payment_plan=d.get("paymentPlan"),
            payment_plan_status=d.get("paymentPlanStatus"),
            is_active=d.get("isActive"),
            has_missed_payment=d.get("hasMissedPayment"),
            unread_bill_count=d.get("getUnreadBillCount"),
            billing_preference=d.get("billingPreference"),
            account_history=[AccountHistoryItem.from_json(x) for x in d.get("accountHistory") or []],
        )


@dataclass(frozen=True)
class MeterReading:
    date: date | None
    value: int | None
    reading_type: str | None  # "C" = customer, "R" = company read

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> MeterReading:
        return cls(
            date=parse_date(d.get("date")),
            value=parse_int(d.get("value")),
            reading_type=d.get("readingType"),
        )


@dataclass(frozen=True)
class MeterDetails:
    meter_location: str | None
    serial_number: str | None
    number_of_dials: int | None
    window_start_date: date | None
    window_end_date: date | None
    last_routine_read: int | None
    last_reading_type: str | None
    error_code: str | None
    error_text: str | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> MeterDetails:
        return cls(
            meter_location=d.get("meterLocation"),
            serial_number=d.get("serialNumber"),
            number_of_dials=d.get("numberOfDials"),
            window_start_date=parse_date(d.get("windowStartDate")),
            window_end_date=parse_date(d.get("windowEndDate")),
            last_routine_read=parse_int(d.get("lastRoutineRead")),
            last_reading_type=d.get("lastReadingType"),
            error_code=d.get("errorCode"),
            error_text=d.get("errorText"),
        )


@dataclass(frozen=True)
class MeterReadings:
    details: MeterDetails | None
    readings: list[MeterReading]
    next_reading_date: date | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> MeterReadings:
        details = d.get("details")
        return cls(
            details=MeterDetails.from_json(details) if details else None,
            readings=[MeterReading.from_json(x) for x in d.get("readings") or []],
            next_reading_date=parse_date(d.get("nextReadingDate")),
        )

    @property
    def latest(self) -> MeterReading | None:
        """Most recent reading, or None if there are no readings."""
        return self.readings[0] if self.readings else None


@dataclass(frozen=True)
class BillingPeriod:
    start: date | None
    end: date | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> BillingPeriod:
        return cls(
            start=parse_date(d.get("billPeriodStartDate")),
            end=parse_date(d.get("billPeriodEndDate")),
        )


@dataclass(frozen=True)
class StatementItem:
    item_type: str | None  # "BI" = bill, "PA" = payment
    date: date | None
    amount: float | None
    new_balance: float | None
    previous_balance: float | None
    billing_period: BillingPeriod | None
    bill_cancelled: bool | None
    document_id: str | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> StatementItem:
        period = d.get("billingPeriod")
        return cls(
            item_type=d.get("itemType"),
            date=parse_date(d.get("date")),
            amount=d.get("amount"),
            new_balance=d.get("newBalance"),
            previous_balance=d.get("previousBalance"),
            billing_period=BillingPeriod.from_json(period) if period else None,
            bill_cancelled=d.get("billCancelled"),
            document_id=d.get("documentId"),
        )


@dataclass(frozen=True)
class PaymentInfo:
    current_balance: float | None
    minimum_payment: float | None
    court_debt: bool | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> PaymentInfo:
        return cls(
            current_balance=d.get("currentBalance"),
            minimum_payment=d.get("minimumPayment"),
            court_debt=d.get("courtDebt"),
        )


@dataclass(frozen=True)
class Preferences:
    notifications_system_enabled: bool | None
    notify_other: bool | None
    notify_payment: bool | None

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> Preferences:
        return cls(
            notifications_system_enabled=d.get("notificationsSystemEnabled"),
            notify_other=d.get("notifyOther"),
            notify_payment=d.get("notifyPayment"),
        )
