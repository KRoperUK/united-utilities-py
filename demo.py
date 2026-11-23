"""Quick manual check against a real account.

Reads credentials from the environment so nothing is committed:

    UU_CUSTOMER_ID=24000000 UU_PIN=000000 UU_ACCOUNT_NUMBER=4000000000 \\
        python demo.py

Remember the 3-strike login lockout: a wrong PIN counts.
"""

from __future__ import annotations

import asyncio
import os

from united_utilities import UnitedUtilitiesClient


async def main() -> None:
    customer_id = os.environ["UU_CUSTOMER_ID"]
    pin = os.environ["UU_PIN"]
    account_number = os.environ["UU_ACCOUNT_NUMBER"]

    async with UnitedUtilitiesClient(customer_id, pin, account_number) as uu:
        await uu.login()
        details = await uu.account_details()
        meter = await uu.meter_readings()
        try:
            print(f"balance: £{details.account_balance}")
            print(f"next payment: £{details.next_payment_due} on {details.next_payment_date}")
            if meter.latest:
                print(f"last meter read: {meter.latest.value} on {meter.latest.date}")
        finally:
            await uu.logout()


if __name__ == "__main__":
    asyncio.run(main())
