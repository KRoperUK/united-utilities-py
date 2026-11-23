"""Async client for the reverse-engineered United Utilities mobile API."""

from __future__ import annotations

from .client import UnitedUtilitiesClient
from .const import API_KEY, BASE_URL
from .exceptions import AuthError, ClientError, NotLoggedInError
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
    "AuthError",
    "BillingPeriod",
    "ClientError",
    "MeterDetails",
    "MeterReading",
    "MeterReadings",
    "NotLoggedInError",
    "PaymentInfo",
    "Preferences",
    "StatementItem",
    "UnitedUtilitiesClient",
]
