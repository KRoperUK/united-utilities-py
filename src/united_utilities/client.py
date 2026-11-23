"""Async client for the United Utilities mobile API.

Reverse-engineered from the "United Utilities: Your Water" app (build 102).
Auth is a static app ``apiKey`` header plus a ``customerId`` + numeric ``pin``
login that returns a short ``sessionToken``; every other call carries that
token in a ``token`` header.

WARNING: the login has a 3-strike lockout. A wrong PIN decrements
``attemptsRemaining`` and the account locks at zero, so this client never
retries ``login()``. Do not loop on :class:`AuthError`.
"""

from __future__ import annotations

import contextlib
import json as _json
import logging
from types import TracebackType
from typing import Any

from aiohttp import ClientError as AiohttpClientError
from aiohttp import ClientSession

from .const import API_KEY, BASE_URL, USER_AGENT
from .exceptions import AuthError, ClientError, NotLoggedInError
from .models import (
    AccountDetails,
    MeterReadings,
    PaymentInfo,
    Preferences,
    StatementItem,
)

_LOGGER = logging.getLogger(__name__)


class UnitedUtilitiesClient:
    """Talks to the UU mobile API for a single account.

    Pass a shared ``aiohttp.ClientSession`` (HA integrations should use the one
    from ``async_get_clientsession(hass)``). If omitted, the client creates and
    owns its own session, closed by :meth:`close` or the context manager.

    Usage::

        async with UnitedUtilitiesClient(customer_id, pin, account_number) as uu:
            await uu.login()
            details = await uu.account_details()
    """

    def __init__(
        self,
        customer_id: str,
        pin: str,
        account_number: str | None = None,
        *,
        session: ClientSession | None = None,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
    ) -> None:
        self._customer_id = customer_id
        self._pin = pin
        self._account_number = account_number
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._token: str | None = None
        self._session = session
        self._owns_session = session is None

    @property
    def logged_in(self) -> bool:
        return self._token is not None

    async def login(self) -> None:
        """Exchange customerId + PIN for a session token.

        Raises :class:`AuthError` on bad credentials (check
        ``.attempts_remaining`` — do NOT retry).
        """
        data = await self._request(
            "POST",
            "/api/account/login",
            data={"customerId": self._customer_id, "pin": self._pin, "platform": "android"},
            authed=False,
        )
        token = data.get("sessionToken")
        if not token:
            raise AuthError("Login response contained no sessionToken.")
        self._token = token

    async def logout(self) -> None:
        if self._token is None:
            return
        try:
            # The gateway WAF 403s a body-less POST; an empty JSON object is accepted.
            await self._request("POST", "/api/account/logout", json={})
        finally:
            self._token = None

    async def account_details(self, account_number: str | None = None) -> AccountDetails:
        return AccountDetails.from_json(await self._post_account("/api/account/details", account_number))

    async def meter_readings(self, account_number: str | None = None) -> MeterReadings:
        return MeterReadings.from_json(await self._post_account("/api/reading/meterreading", account_number))

    async def payment_info(self, account_number: str | None = None) -> PaymentInfo:
        return PaymentInfo.from_json(await self._post_account("/api/payment", account_number))

    async def statement(self, account_number: str | None = None) -> list[StatementItem]:
        data = await self._post_account("/api/statement", account_number)
        return [StatementItem.from_json(x) for x in data.get("history") or []]

    async def preferences(self) -> Preferences:
        return Preferences.from_json(await self._request("GET", "/api/account/preferences"))

    async def notifications(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/account/GetCustomerNotifications")
        return list(data.get("notifications") or [])

    # -- internals -----------------------------------------------------------

    def _ensure_session(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession()
        return self._session

    def _require_account(self, account_number: str | None) -> str:
        account = account_number or self._account_number
        if not account:
            raise ValueError("account_number was not provided to the call or the client.")
        return account

    async def _post_account(self, path: str, account_number: str | None) -> dict[str, Any]:
        return await self._request("POST", path, json={"accountNumber": self._require_account(account_number)})

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, str] | None = None,
        authed: bool = True,
    ) -> dict[str, Any]:
        headers = {"apiKey": self._api_key, "User-Agent": USER_AGENT}
        if authed:
            if self._token is None:
                raise NotLoggedInError("Call login() before making data requests.")
            headers["token"] = self._token

        session = self._ensure_session()
        try:
            async with session.request(
                method, f"{self._base_url}{path}", headers=headers, json=json, data=data
            ) as resp:
                if resp.status == 401:
                    return self._handle_401(path, await resp.text())
                if resp.status >= 400:
                    raise ClientError(f"HTTP {resp.status} from {path}", code=str(resp.status))
                body: dict[str, Any] = await resp.json(content_type=None)
                return body
        except (ClientError, NotLoggedInError):
            raise
        except AiohttpClientError as err:
            raise ClientError(f"Request to {path} failed: {err}") from err

    def _handle_401(self, path: str, text: str) -> dict[str, Any]:
        if path.endswith("/login"):
            attempts = None
            with contextlib.suppress(ValueError, AttributeError):
                attempts = _json.loads(text).get("attemptsRemaining")
            raise AuthError(
                "Login rejected by United Utilities (check customerId/PIN).",
                code="401",
                attempts_remaining=attempts,
            )
        # Token expired/invalid on a data call. Clear it; caller re-logs in ONCE.
        self._token = None
        raise NotLoggedInError("Session token rejected (401); log in again.")

    async def close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> UnitedUtilitiesClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
