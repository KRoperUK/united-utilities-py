"""Public exception hierarchy.

Kept small and HA-free so the integration can map errors to
ConfigEntryAuthFailed / UpdateFailed without importing Home Assistant here.
"""

from __future__ import annotations


class ClientError(Exception):
    """Base error for the client library."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class AuthError(ClientError):
    """Login was rejected — caller should re-authenticate, never retry blindly.

    ``attempts_remaining`` mirrors the server countdown; the account locks when
    it reaches zero.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        attempts_remaining: int | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.attempts_remaining = attempts_remaining


class NotLoggedInError(ClientError):
    """A data call was made before ``login()`` succeeded (or after a 401)."""


class AccountLockedError(AuthError):
    """HTTP 423: too many failed attempts; the service has locked the account.

    The app's copy says the lock lasts 60 minutes. Retrying during the lock does
    not help and may extend it.
    """
