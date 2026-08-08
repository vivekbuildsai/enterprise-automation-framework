from __future__ import annotations


def luhn_checksum(digits: str) -> int:
    """Computes the Luhn check digit for `digits` (all-but-the-last digit
    of the target number) — the algorithm IMEI and ICCID both validate
    against. Shared by the telecom generators (append the returned digit to
    produce a Luhn-valid number) and the format validators (recompute and
    compare to confirm one).
    """
    total = 0
    parity = len(digits) % 2
    for i, char in enumerate(digits):
        d = int(char)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def is_luhn_valid(number: str) -> bool:
    """True if `number` (the full number, including its own check digit)
    passes the Luhn checksum.
    """
    if not number.isdigit() or len(number) < 2:
        return False
    body, check_digit = number[:-1], int(number[-1])
    return luhn_checksum(body) == check_digit
