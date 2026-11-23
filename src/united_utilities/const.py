"""Constants for the United Utilities mobile API.

Reverse-engineered from the "United Utilities: Your Water" app (build 102).
"""

from __future__ import annotations

BASE_URL = "https://prd-mobile-apigateway.unitedutilities.com"

# Static per-environment key baked into the app (production). Not a user secret;
# it gates the gateway, not an account.
API_KEY = "038649FA3CB9EC16786AF845A32337849850B5CC2E9EA3FA71A8B88077B481A3"

USER_AGENT = "consumerapp/4.8 (com.unitedutilities.consumer.app; build:102)"
