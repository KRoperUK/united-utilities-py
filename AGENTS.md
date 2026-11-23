# Agent notes (united-utilities-py)

- Keep this package free of Home Assistant dependencies.
- Prefer small, typed modules: client, models, exceptions, const.
- **Never retry `login()` on failure.** The gateway locks the account after 3
  bad PINs; `AuthError.attempts_remaining` is the only warning. A 401 on a data
  call clears the token and raises `NotLoggedInError` — callers re-login once.
- `apiKey` is the app's static per-environment key (gates the gateway, not an
  account). `customerId` + `pin` are the user's real secrets — never log them,
  never commit them, keep them out of fixtures.
- Response shapes were confirmed against live production responses (app build
  102). Tests run on synthetic fixtures via `aresponses` — no real data.
- Version bumps are via release-please only (do not hand-edit for releases).
