import allure
import pytest

from framework.api.models import CreateUserRequest, UpdateUserRequest
from framework.api.services import UserService
from framework.api.validators import ResponseValidator


@allure.feature("API - User Management")
@pytest.mark.api
@pytest.mark.regression
class TestUserCrudRegression:
    def test_list_users_returns_paginated_collection(self, user_service: UserService) -> None:
        with allure.step("List first 5 users"):
            listing = user_service.list_users(limit=5)

        with allure.step("Verify pagination and schema"):
            ResponseValidator(user_service.last_response).expect_status(200).expect_collection_size(
                "users", exact=5
            ).expect_schema("user_list_schema")
            assert listing.limit == 5
            assert len(listing.users) == 5

    def test_get_single_user_by_id(self, user_service: UserService) -> None:
        with allure.step("Get user id=2"):
            user = user_service.get_user(2)

        with allure.step("Verify status, schema, and field values"):
            ResponseValidator(user_service.last_response).expect_status(200).expect_schema(
                "user_schema"
            ).expect_json_field("id", 2)
            assert user.id == 2
            assert user.first_name

    def test_create_user(self, user_service: UserService) -> None:
        request = CreateUserRequest(firstName="Ada", lastName="Lovelace", age=36)

        with allure.step("Create a new user"):
            created = user_service.create_user(request)

        with allure.step("Verify creation response"):
            ResponseValidator(user_service.last_response).expect_status(201)
            assert created.first_name == "Ada"
            assert created.last_name == "Lovelace"
            assert created.id > 0

    def test_update_user(self, user_service: UserService) -> None:
        with allure.step("Partially update user id=2"):
            updated = user_service.update_user(2, UpdateUserRequest(firstName="Updated"))

        with allure.step("Verify only the targeted field changed"):
            ResponseValidator(user_service.last_response).expect_status(200).expect_json_field(
                "firstName", "Updated"
            )
            assert updated.first_name == "Updated"
            assert updated.id == 2

    def test_delete_user(self, user_service: UserService) -> None:
        with allure.step("Delete user id=2"):
            deleted = user_service.delete_user(2)

        with allure.step("Verify soft-delete markers"):
            ResponseValidator(user_service.last_response).expect_status(200).expect_json_field(
                "isDeleted", True
            )
            assert deleted.is_deleted is True
            assert deleted.deleted_on
