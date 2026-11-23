# united-utilities-py

Async Python client for the **United Utilities** "Your Water" mobile API,
reverse-engineered from the app (build 102). Pairs with a Home Assistant
integration (`united-utilities-hass`).

> Unofficial. Uses a private app API that United Utilities can change or
> withdraw at any time. For personal use with your own account.

## Why the mobile API (not the website)

The `myaccount.unitedutilities.com` website is gated behind Google reCAPTCHA
Enterprise and Jscrambler, so a scripted login needs a real browser. The mobile
app talks to a separate gateway (`prd-mobile-apigateway.unitedutilities.com`)
with a far simpler scheme: a static app `apiKey` header plus a `customerId` +
numeric `PIN` login that returns a session token. No captcha.

## Credentials

The mobile API does **not** use your website email/password. It needs:

- **`customerId`** — a numeric id assigned when you register in the app.
- **`pin`** — the numeric PIN you set in the app.
- **`accountNumber`** — your water account number (for account-scoped calls).

The easiest way to find `customerId` is to capture the app's `api/account/login`
request once; the body is `customerId=…&pin=…&platform=…` (form-encoded). The
app pins its TLS certificate, so an intercepting proxy breaks the app's *data*
calls even though the login call goes through — that's expected.

> ⚠️ **Login has a 3-strike lockout.** A wrong PIN decrements
> `attemptsRemaining`; at zero the account locks. This client never retries
> `login()`. Do not loop on `AuthError`.

## Install

```sh
pip install united-utilities
```

## Usage

```python
import asyncio
from united_utilities import UnitedUtilitiesClient


async def main() -> None:
    async with UnitedUtilitiesClient("24000000", "000000", "4000000000") as uu:
        await uu.login()
        details = await uu.account_details()
        meter = await uu.meter_readings()
        print("balance:", details.account_balance)
        if meter.latest:
            print("last read:", meter.latest.value, "on", meter.latest.date)


asyncio.run(main())
```

In Home Assistant, pass the shared session:

```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession

client = UnitedUtilitiesClient(customer_id, pin, account_number,
                               session=async_get_clientsession(hass))
```

## Endpoints covered

| Method | Returns |
| --- | --- |
| `login()` / `logout()` | session token lifecycle |
| `account_details()` | balance, next payment, meter flag, payment plan, bill count |
| `meter_readings()` | meter details + reading history (`.latest`) |
| `statement()` | itemised bills & payments |
| `payment_info()` | current balance, minimum payment |
| `preferences()` | notification preferences |
| `notifications()` | customer notifications |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Response shapes were confirmed against
live production responses; tests run on synthetic fixtures (no real account
data) with `aresponses`.

## License

MIT
