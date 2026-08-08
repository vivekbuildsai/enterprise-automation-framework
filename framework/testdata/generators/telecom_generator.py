from __future__ import annotations

import random

from framework.testdata.utilities.luhn import luhn_checksum

_DEFAULT_MCC = "234"  # UK — matches this repo's existing sample IMSI/MSISDN prefixes
_DEFAULT_MNC = "15"

# Every `random.randint` below generates a fake telecom identifier (IMEI/
# ICCID/IMSI/MSISDN/cell ID) for test data — never a token, password, or
# anything security-sensitive — so the standard, non-cryptographic `random`
# module is the correct choice, not a Bandit finding. `# nosec B311` on each
# call accordingly.


class TelecomIdentifierGenerator:
    """Generates syntactically valid telecom/network identifiers — IMEI and
    ICCID are Luhn-checksummed exactly like real devices/SIMs, IMSI/MSISDN
    follow the real digit-count and MCC/MNC structuring rules. None of these
    correspond to a real, allocated device/subscriber — they're
    structurally valid, not real-world registered.
    """

    @staticmethod
    def imei() -> str:
        """15 digits: 8-digit TAC + 6-digit serial number + 1 Luhn check
        digit (3GPP TS 23.003).
        """
        tac = f"{random.randint(0, 99_999_999):08d}"  # nosec B311
        serial = f"{random.randint(0, 999_999):06d}"  # nosec B311
        body = tac + serial
        return body + str(luhn_checksum(body))

    @staticmethod
    def imsi(*, mcc: str = _DEFAULT_MCC, mnc: str = _DEFAULT_MNC) -> str:
        """Up to 15 digits: MCC (3) + MNC (2-3) + MSIN (fills the rest),
        per 3GPP TS 23.003.
        """
        msin_length = 15 - len(mcc) - len(mnc)
        msin = f"{random.randint(0, 10**msin_length - 1):0{msin_length}d}"  # nosec B311
        return mcc + mnc + msin

    @staticmethod
    def iccid(*, issuer_identifier: str = "8944") -> str:
        """19 digits: issuer identifier (industry "89" + country code,
        default "8944" = telecom + UK) + account identification + 1 Luhn
        check digit, per ITU-T E.118.
        """
        account_length = 18 - len(issuer_identifier)
        account = f"{random.randint(0, 10**account_length - 1):0{account_length}d}"  # nosec B311
        body = issuer_identifier + account
        return body + str(luhn_checksum(body))

    @staticmethod
    def msisdn(*, country_code: str = "44") -> str:
        """E.164-style: country code + up to 12 subscriber digits (kept to
        10 here so the result is a realistic mobile-number length).
        """
        subscriber = f"{random.randint(0, 9_999_999_999):010d}"  # nosec B311
        return country_code + subscriber

    @staticmethod
    def plmn_id(*, mcc: str = _DEFAULT_MCC, mnc: str = _DEFAULT_MNC) -> str:
        """Public Land Mobile Network identifier: MCC + MNC."""
        return mcc + mnc

    @staticmethod
    def cell_id() -> str:
        """28-bit E-UTRAN Cell Identity, decimal, zero-padded to 9 digits."""
        return f"{random.randint(0, 2**28 - 1):09d}"  # nosec B311

    @staticmethod
    def tracking_area_code() -> str:
        """16-bit Tracking Area Code."""
        return f"{random.randint(0, 65_535):05d}"  # nosec B311

    @staticmethod
    def ip_address_v4() -> str:
        return ".".join(str(random.randint(1, 254)) for _ in range(4))  # nosec B311
