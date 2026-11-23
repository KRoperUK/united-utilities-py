from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from aiohttp import web
from aresponses import ResponsesMockServer

from united_utilities import (
    API_KEY,
    AuthError,
    NotLoggedInError,
    UnitedUtilitiesClient,
)

FIXTURES = Path(__file__).parent / "fixtures"
TEST_HOST = "uu.test"
TEST_BASE_URL = f"https://{TEST_HOST}"

Handler = Callable[[web.Request], Awaitable[web.Response]]


def _fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / name).read_text())
    return data


def _json(payload: Any, status: int = 200) -> web.Response:
    return web.json_response(payload, status=status)


def _capture(captured: dict[str, Any], payload: Any, status: int = 200) -> Handler:
    """Handler that records headers + body, then returns ``payload``."""

    async def handler(request: web.Request) -> web.Response:
        captured["headers"] = dict(request.headers)
        captured["content_type"] = request.content_type
        captured["body"] = await request.text()
        return _json(payload, status)

    return handler


@pytest.fixture
async def session() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession() as client_session:
        yield client_session


@pytest.fixture
def client(session: aiohttp.ClientSession) -> UnitedUtilitiesClient:
    return UnitedUtilitiesClient(
        "24000000",
        "000000",
        account_number="4000000000",
        session=session,
        base_url=TEST_BASE_URL,
    )


def _add_login(aresponses: ResponsesMockServer, token: str = "t") -> None:
    aresponses.add(TEST_HOST, "/api/account/login", "POST", _json({"sessionToken": token}))


async def test_login_success_sets_token(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    captured: dict[str, Any] = {}
    aresponses.add(
        TEST_HOST,
        "/api/account/login",
        "POST",
        _capture(captured, {"sessionToken": "abc123", "isWeakPIN": None}),
    )
    await client.login()

    assert client.logged_in
    assert captured["headers"]["apiKey"] == API_KEY
    # Login must be form-encoded, not JSON.
    assert captured["content_type"] == "application/x-www-form-urlencoded"
    assert "customerId=24000000" in captured["body"]
    assert "pin=000000" in captured["body"]


async def test_login_rejected_raises_with_attempts(
    client: UnitedUtilitiesClient, aresponses: ResponsesMockServer
) -> None:
    aresponses.add(TEST_HOST, "/api/account/login", "POST", _json({"attemptsRemaining": 2}, 401))
    with pytest.raises(AuthError) as excinfo:
        await client.login()

    assert excinfo.value.attempts_remaining == 2
    assert not client.logged_in
    # Only one login route was registered; a retry would hit an unmatched route.
    aresponses.assert_plan_strictly_followed()


async def test_data_call_before_login_raises(client: UnitedUtilitiesClient) -> None:
    with pytest.raises(NotLoggedInError):
        await client.account_details()


async def test_account_details_parsed(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    captured: dict[str, Any] = {}
    _add_login(aresponses)
    aresponses.add(
        TEST_HOST,
        "/api/account/details",
        "POST",
        _capture(captured, _fixture("account_details.json")),
    )
    await client.login()
    details = await client.account_details()

    assert details.account_balance == 80.58
    assert details.next_payment_due == 51.78
    assert details.next_payment_date == date(2026, 11, 23)
    assert details.is_on_meter is True
    assert details.unread_bill_count == 2
    assert len(details.account_history) == 2
    assert details.account_history[0].type == "BI"

    assert captured["headers"]["token"] == "t"
    assert captured["headers"]["apiKey"] == API_KEY
    assert json.loads(captured["body"]) == {"accountNumber": "4000000000"}


async def test_meter_readings_parsed(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    _add_login(aresponses)
    aresponses.add(TEST_HOST, "/api/reading/meterreading", "POST", _json(_fixture("meterreading.json")))
    await client.login()
    meter = await client.meter_readings()

    assert meter.details is not None
    assert meter.details.serial_number == "00A000000"
    assert meter.details.last_routine_read == 1975
    assert len(meter.readings) == 2
    assert meter.latest is not None
    assert meter.latest.value == 1975
    assert meter.latest.date == date(2026, 11, 21)
    assert meter.next_reading_date == date(2027, 4, 9)


async def test_statement_parsed(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    _add_login(aresponses)
    aresponses.add(TEST_HOST, "/api/statement", "POST", _json(_fixture("statement.json")))
    await client.login()
    items = await client.statement()

    assert len(items) == 2
    bill = items[0]
    assert bill.item_type == "BI"
    assert bill.amount == 76.51
    assert bill.billing_period is not None
    assert bill.billing_period.start == date(2026, 10, 9)
    assert items[1].billing_period is None


async def test_payment_info_parsed(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    _add_login(aresponses)
    aresponses.add(
        TEST_HOST,
        "/api/payment",
        "POST",
        _json({"currentBalance": 80.58, "minimumPayment": 0.0, "courtDebt": False}),
    )
    await client.login()
    info = await client.payment_info()

    assert info.current_balance == 80.58
    assert info.minimum_payment == 0.0
    assert info.court_debt is False


async def test_preferences_and_notifications(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    _add_login(aresponses)
    aresponses.add(
        TEST_HOST,
        "/api/account/preferences",
        "GET",
        _json({"notificationsSystemEnabled": False, "notifyOther": False, "notifyPayment": True}),
    )
    aresponses.add(TEST_HOST, "/api/account/GetCustomerNotifications", "GET", _json({"notifications": []}))
    await client.login()

    prefs = await client.preferences()
    assert prefs.notify_payment is True
    assert await client.notifications() == []


async def test_expired_token_surfaces_not_logged_in(
    client: UnitedUtilitiesClient, aresponses: ResponsesMockServer
) -> None:
    _add_login(aresponses)
    aresponses.add(TEST_HOST, "/api/payment", "POST", aresponses.Response(status=401))
    await client.login()

    with pytest.raises(NotLoggedInError):
        await client.payment_info()
    assert not client.logged_in  # token cleared so caller re-logs in deliberately


async def test_logout_clears_token(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    captured: dict[str, Any] = {}
    _add_login(aresponses)
    aresponses.add(TEST_HOST, "/api/account/logout", "POST", _capture(captured, {"sessionToken": ""}))
    await client.login()
    await client.logout()
    assert not client.logged_in
    # Body-less POSTs are 403'd by the gateway WAF, so logout must send a JSON body.
    assert captured["content_type"] == "application/json"
    assert json.loads(captured["body"]) == {}


async def test_server_error_raises_client_error(client: UnitedUtilitiesClient, aresponses: ResponsesMockServer) -> None:
    from united_utilities import ClientError

    _add_login(aresponses)
    aresponses.add(TEST_HOST, "/api/account/details", "POST", aresponses.Response(status=500))
    await client.login()

    with pytest.raises(ClientError) as excinfo:
        await client.account_details()
    assert excinfo.value.code == "500"


async def test_login_locked_raises_account_locked(
    client: UnitedUtilitiesClient, aresponses: ResponsesMockServer
) -> None:
    from united_utilities import AccountLockedError

    aresponses.add(TEST_HOST, "/api/account/login", "POST", aresponses.Response(status=423))
    with pytest.raises(AccountLockedError) as excinfo:
        await client.login()
    assert isinstance(excinfo.value, AuthError)  # callers that only know AuthError still stop
    assert excinfo.value.code == "423"


async def test_lookup_customer_id(session: aiohttp.ClientSession, aresponses: ResponsesMockServer) -> None:
    from united_utilities import lookup_customer_id

    find: dict[str, Any] = {}
    check: dict[str, Any] = {}
    aresponses.add(
        TEST_HOST,
        "/api/registration/find",
        "POST",
        _capture(find, {"registrationToken": "reg-token", "address": {"addressLine1": "1 Example Street"}}),
    )
    aresponses.add(
        TEST_HOST,
        "/api/registration/check",
        "GET",
        _capture(check, {"customerId": "24000000", "validationToken": "v"}),
    )

    customer_id = await lookup_customer_id(" 4000000000 ", "m1 1aa", session=session, base_url=TEST_BASE_URL)

    assert customer_id == "24000000"
    assert find["content_type"] == "application/x-www-form-urlencoded"
    assert "accountNumber=4000000000" in find["body"]
    assert "postcode=M11AA" in find["body"]  # spaces removed, upper-cased like the app
    assert find["headers"]["apiKey"] == API_KEY
    assert check["headers"]["token"] == "reg-token"
    assert not session.closed  # caller-owned session left open


async def test_lookup_no_match_raises_auth_error(
    session: aiohttp.ClientSession, aresponses: ResponsesMockServer
) -> None:
    from united_utilities import lookup_customer_id

    aresponses.add(TEST_HOST, "/api/registration/find", "POST", aresponses.Response(status=401))
    with pytest.raises(AuthError):
        await lookup_customer_id("4000000000", "M11AA", session=session, base_url=TEST_BASE_URL)
    aresponses.assert_plan_strictly_followed()


async def test_lookup_locked_raises(session: aiohttp.ClientSession, aresponses: ResponsesMockServer) -> None:
    from united_utilities import AccountLockedError, lookup_customer_id

    aresponses.add(TEST_HOST, "/api/registration/find", "POST", aresponses.Response(status=423))
    with pytest.raises(AccountLockedError):
        await lookup_customer_id("4000000000", "M11AA", session=session, base_url=TEST_BASE_URL)


async def test_lookup_unregistered_account(session: aiohttp.ClientSession, aresponses: ResponsesMockServer) -> None:
    from united_utilities import ClientError, lookup_customer_id

    aresponses.add(TEST_HOST, "/api/registration/find", "POST", _json({"registrationToken": "reg-token"}))
    aresponses.add(TEST_HOST, "/api/registration/check", "GET", _json({"customerId": None, "validationToken": None}))
    with pytest.raises(ClientError, match="register in the app") as excinfo:
        await lookup_customer_id("4000000000", "M11AA", session=session, base_url=TEST_BASE_URL)
    assert excinfo.value.code == "not_registered"
