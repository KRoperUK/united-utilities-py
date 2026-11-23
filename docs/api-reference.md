# API reference

Base URL: `https://prd-mobile-apigateway.unitedutilities.com`

Every request carries header `apiKey: <static app key>`. Authenticated requests
additionally carry header `token: <sessionToken>`.

## Auth

### `POST /api/account/login`

Body (form-urlencoded): `customerId`, `pin`, `platform`.

```json
{ "sessionToken": "…", "certificateString": "…", "isWeakPIN": null }
```

- `401 {"attemptsRemaining": N}` on bad credentials. **3 strikes locks the
  account.** Never retry automatically.

### `POST /api/account/logout`

Invalidates the session token.

## Data (all require the `token` header)

| Path | Method | Body | Model |
| --- | --- | --- | --- |
| `/api/account/details` | POST | `{accountNumber}` | `AccountDetails` |
| `/api/reading/meterreading` | POST | `{accountNumber}` | `MeterReadings` |
| `/api/payment` | POST | `{accountNumber}` | `PaymentInfo` |
| `/api/statement` | POST | `{accountNumber}` | `StatementItem[]` (`history`) |
| `/api/account/preferences` | GET | — | `Preferences` |
| `/api/account/GetCustomerNotifications` | GET | — | `list` |

Account-scoped bodies accept JSON *or* form-encoding; this client sends JSON.

## Data quirks

- Dates are `DDMMYYYY` strings (e.g. `"21112026"` = 21 Nov 2026), sometimes
  empty/null → parsed to `datetime.date | None`.
- Meter readings arrive as numeric strings → parsed to `int | None`.
- Item type codes: `BI` = bill, `PA` = payment. Reading type: `C` = customer
  read, `R` = company read.

## Not yet wrapped

Observed in the app but not implemented here: `api/statement/getpdfbill`
(PDF bill download), `api/reading` + `api/reading/ValidateMeterRead` (submit a
meter reading), `api/registration/*`, `api/account/forgottenPin/*`,
`api/payment/request` (Cybersource payment).
