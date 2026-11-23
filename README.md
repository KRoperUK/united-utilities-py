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

The app doesn't show `customerId`, but you can look it up from your account
number and postcode, the same way the app's "register again" screen does. The
account must already be registered in the app:

```python
from united_utilities import lookup_customer_id

customer_id = await lookup_customer_id("4000000000", "M1 1AA")
```

> ⚠️ **Login and lookup both lock out.** A wrong PIN decrements
> `attemptsRemaining`; at zero the account locks (HTTP 423, raised as
> `AccountLockedError`, which the app says lasts 60 minutes). This client never
> retries `login()` or `lookup_customer_id()`. Do not loop on `AuthError`.

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

client = UnitedUtilitiesClient(customer_id, pin, account_number, session=async_get_clientsession(hass))
```

## Endpoints covered

| Method | Returns |
| --- | --- |
| `lookup_customer_id(account_number, postcode)` | the app `customerId` (module function, no login needed) |
| `login()` / `logout()` | session token lifecycle |
| `account_details()` | balance, next payment, meter flag, payment plan, bill count |
| `meter_readings()` | meter details + reading history (`.latest`) |
| `statement()` | itemised bills & payments |
| `bill_pdf(document_id)` | a bill as PDF bytes (`document_id` from `statement()`) |
| `payment_info()` | current balance, minimum payment |
| `preferences()` | notification preferences |
| `notifications()` | customer notifications |

## Bill PDFs: tariffs and charges

The API has bill totals and meter readings but not tariffs. The bill PDF does,
and `parse_bill()` reads it (install the extra: `pip install
"united-utilities[pdf]"`):

```python
from united_utilities import parse_bill

latest = next(i for i in await uu.statement() if i.item_type == "BI" and i.document_id)
bill = parse_bill(await uu.bill_pdf(latest.document_id))
if bill.trustworthy:
    print(bill.price_per_m3, bill.standing_charge_per_year)  # e.g. 5.51, 177.59
else:
    print(bill.problems)
```

A `Bill` has the billing period, both meter readings and who read them, every
charge line (fresh water / wastewater × usage / standing charge, per tariff
period when a bill spans 1 April), any discount and the total. Some bills are
payment-plan updates with no charges; those have `itemised == False`.

Parsing matches the bill's wording, so every parse is cross-checked. Line items
must add up to the total, each line must equal quantity × rate, fresh water and
wastewater must bill the same volume, and the volume must match the readings.
Anything that doesn't add up goes in `bill.problems`, `trustworthy` is `False`,
and `price_per_m3` / `standing_charge_per_year` return `None` instead of a
possibly wrong figure.

> Bills include the account holder's name, address and bank details. Parse them
> in memory; don't log or store the PDF.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Response shapes were confirmed against
live production responses; tests run on synthetic fixtures (no real account
data) with `aresponses`.

## License

MIT
