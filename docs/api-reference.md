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
| `/api/statement/getpdfbill` | POST | `{AccountNumber, documentId}` (note the capital `A`) | bill PDF, base64 inside a JSON string |
| `/api/account/preferences` | GET | — | `Preferences` |
| `/api/account/GetCustomerNotifications` | GET | — | `list` |

Account-scoped bodies accept JSON *or* form-encoding; this client sends JSON.

## Bill PDFs

`documentId` is on each `BI` item from `/api/statement`. A bill is a 3–4 page
A4 PDF with real text (not a scan), around 90–165 KB. Itemised bills have:

- **Billing period** (`9 October 2026 - 21 November 2026`)
- Previous and current **readings** (`OUR READING` / `YOUR READING` /
  `ESTIMATED READING`) with dates, and the volume used (`10m³ (10,000 litres)`)
- **Your charges**: fresh water (left column) and wastewater (right), each with
  `Usage N m³ @ £r per m³ = £x` and `Standing charge D days @ £r a year = £x`.
  A bill spanning 1 April has one block per tariff, each headed
  `Charges for: <start> - <end>`.
- Optional `Direct Debit discount £5.00 (cr)`, then `Your new charges £x`

Payment-plan and bank-detail updates are also issued as bills, with only the
balance and Direct Debit schedule. The fresh water / wastewater columns only
stay paired on one line in pypdf's `layout` extraction mode, so `parse_bill`
uses that mode for charges and plain mode for everything else.

## Data quirks

- Dates are `DDMMYYYY` strings (e.g. `"21112026"` = 21 Nov 2026), sometimes
  empty/null → parsed to `datetime.date | None`.
- Meter readings arrive as numeric strings → parsed to `int | None`.
- Item type codes: `BI` = bill, `PA` = payment. Reading type: `C` = customer
  read, `R` = company read.

## Not yet wrapped

Observed in the app but not implemented here: `api/reading` +
`api/reading/ValidateMeterRead` (submit a meter reading), the rest of
`api/registration/*` (signup, SMS verification), `api/account/forgottenPin/*`,
`api/payment/request` (Cybersource payment).
