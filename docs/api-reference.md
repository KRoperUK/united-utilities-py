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
  account** (`423`, about 60 minutes per the app). Never retry automatically.

### `POST /api/account/logout`

Invalidates the session token. Needs a body: the gateway WAF returns `403` for
an empty POST, so send `{}`.

## Customer ID lookup (no login)

The app's "register again" flow, first two steps only. Neither sends an SMS or
changes the registration.

1. `POST /api/registration/find`, form body `accountNumber`, `postcode`
   (upper-case, no spaces) → `{registrationToken, address}`. `401` = no match,
   `423` = locked.
2. `GET /api/registration/check`, header `token: <registrationToken>` →
   `{customerId, validationToken}`. Null `customerId` = not registered in the app.

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
meter reading), the rest of `api/registration/*` (signup, SMS verification), `api/account/forgottenPin/*`,
`api/payment/request` (Cybersource payment).
