from __future__ import annotations

import pytest

from framework.models import Brand, Subscriber, Tenant

pytestmark = pytest.mark.models


class TestBrand:
    def test_defaults_code_to_empty(self) -> None:
        brand = Brand(name="Acme Mobile")

        assert brand.code == ""


class TestReExportedModels:
    """`Subscriber`/`Tenant` are the existing framework.database.models
    classes, re-exported here rather than duplicated — this just confirms
    the re-export actually points at the same class, not a shadow copy.
    """

    def test_subscriber_is_the_database_models_class(self) -> None:
        from framework.database.models import Subscriber as DbSubscriber

        assert Subscriber is DbSubscriber

    def test_tenant_is_the_database_models_class(self) -> None:
        from framework.database.models import Tenant as DbTenant

        assert Tenant is DbTenant
