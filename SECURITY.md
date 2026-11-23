# Security Policy

## Supported versions

Security fixes are made against the latest release only. Please update to the
newest version before reporting a suspected vulnerability.

## What this library handles

The client uses sensitive credentials on your behalf:

- Your United Utilities app **customer ID** and **PIN**.
- The short-lived **session token** returned by login.
- Your water **account number**, and the account data it returns (balance,
  payments, meter readings).

The library never logs credentials or tokens, and never persists them; storage
is the caller's responsibility (e.g. the Home Assistant config entry). Login is
never retried automatically because the service locks the account after three
failed PINs.

The `API_KEY` constant is the app's static gateway key, shipped in the public
app. It is not a user secret.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Instead, report privately via GitHub's
[private vulnerability reporting](https://github.com/KRoperUK/united-utilities-py/security/advisories/new)
("**Report a vulnerability**" on the repository's **Security** tab). This opens a
private advisory visible only to the maintainers.

Please include:

- A description of the issue and its impact.
- Steps to reproduce (or a proof of concept).
- The library version and Python version.

You can expect an initial acknowledgement within a few days. Once a fix is
available it will be released and, where appropriate, a security advisory will be
published crediting the reporter (unless you prefer to remain anonymous).

## Scope

This policy covers the client code in this repository. Vulnerabilities in the
United Utilities service itself should be reported to United Utilities.
