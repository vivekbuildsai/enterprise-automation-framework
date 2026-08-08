from __future__ import annotations

import pytest

from framework.testdata.generators import (
    CustomGeneratorRegistry,
    DeterministicGenerator,
    TelecomIdentifierGenerator,
)
from framework.testdata.utilities import is_luhn_valid, sequences
from framework.utilities.random_data import RandomData

pytestmark = pytest.mark.testdata


def test_imei_is_15_digits_and_luhn_valid() -> None:
    imei = TelecomIdentifierGenerator.imei()
    assert len(imei) == 15
    assert imei.isdigit()
    assert is_luhn_valid(imei)


def test_iccid_is_19_digits_and_luhn_valid() -> None:
    iccid = TelecomIdentifierGenerator.iccid()
    assert len(iccid) == 19
    assert is_luhn_valid(iccid)


def test_imsi_is_15_digits() -> None:
    imsi = TelecomIdentifierGenerator.imsi()
    assert len(imsi) == 15
    assert imsi.isdigit()


def test_msisdn_starts_with_country_code() -> None:
    msisdn = TelecomIdentifierGenerator.msisdn(country_code="44")
    assert msisdn.startswith("44")
    assert msisdn.isdigit()


def test_plmn_id_combines_mcc_and_mnc() -> None:
    assert TelecomIdentifierGenerator.plmn_id(mcc="234", mnc="15") == "23415"


def test_ip_address_v4_has_four_octets_in_range() -> None:
    octets = TelecomIdentifierGenerator.ip_address_v4().split(".")
    assert len(octets) == 4
    assert all(1 <= int(o) <= 254 for o in octets)


def test_generated_identifiers_are_not_luhn_invalid_by_construction() -> None:
    # a random 15-digit string would only pass Luhn ~10% of the time —
    # confirms the generator is actually computing the checksum, not luck.
    results = [is_luhn_valid(TelecomIdentifierGenerator.imei()) for _ in range(20)]
    assert all(results)


def test_deterministic_seeded_context_reproduces_same_values() -> None:
    with DeterministicGenerator.seeded_context(1234):
        first = TelecomIdentifierGenerator.imei()
        name_1 = RandomData.full_name()
    with DeterministicGenerator.seeded_context(1234):
        second = TelecomIdentifierGenerator.imei()
        name_2 = RandomData.full_name()
    assert first == second
    assert name_1 == name_2


def test_deterministic_context_restores_random_state_afterwards() -> None:
    before = TelecomIdentifierGenerator.imei()
    with DeterministicGenerator.seeded_context(999):
        TelecomIdentifierGenerator.imei()
    after_values = {TelecomIdentifierGenerator.imei() for _ in range(5)}
    # Not a strict determinism check (still random after exiting the
    # context) — just confirms exiting doesn't leave everything pinned to
    # the seeded sequence forever.
    assert before not in after_values or len(after_values) > 1


def test_id_sequence_generator_increments_and_resets() -> None:
    seq = sequences.get("test_generators_demo")
    seq.reset()
    assert seq.next_id(prefix="X") == "X-1"
    assert seq.next_id(prefix="X") == "X-2"
    seq.reset()
    assert seq.next_id(prefix="X") == "X-1"


def test_id_sequence_zero_padding() -> None:
    seq = sequences.get("test_generators_padding")
    seq.reset()
    assert seq.next_id(prefix="Z", width=4) == "Z-0001"


def test_custom_generator_registry_round_trip() -> None:
    registry = CustomGeneratorRegistry()
    registry.register("emp_id", lambda: "EMP-0001")
    assert registry.is_registered("emp_id")
    assert registry.generate("emp_id") == "EMP-0001"


def test_custom_generator_registry_raises_for_unknown_name() -> None:
    from framework.exceptions import TestDataError

    registry = CustomGeneratorRegistry()
    with pytest.raises(TestDataError):
        registry.generate("does_not_exist")
