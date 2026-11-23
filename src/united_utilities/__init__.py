"""Async client for the reverse-engineered United Utilities mobile API."""

from __future__ import annotations

from .bill import Bill, BillReading, ChargeLine, parse_bill, parse_bill_text
from .client import UnitedUtilitiesClient, lookup_customer_id
from .const import API_KEY, BASE_URL
from .exceptions import AccountLockedError, AuthError, ClientError, NotLoggedInError
from .models import (
    AccountDetails,
    AccountHistoryItem,
    BillingPeriod,
    MeterDetails,
    MeterReading,
    MeterReadings,
    PaymentInfo,
    Preferences,
    StatementItem,
)

__all__ = [
    "API_KEY",
    "BASE_URL",
    "AccountDetails",
    "AccountHistoryItem",
    "AccountLockedError",
    "AuthError",
    "Bill",
    "BillReading",
    "BillingPeriod",
    "ChargeLine",
    "ClientError",
    "MeterDetails",
    "MeterReading",
    "MeterReadings",
    "NotLoggedInError",
    "PaymentInfo",
    "Preferences",
    "StatementItem",
    "UnitedUtilitiesClient",
    "lookup_customer_id",
    "parse_bill",
    "parse_bill_text",
]
