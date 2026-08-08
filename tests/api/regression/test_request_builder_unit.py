import pytest

from framework.api.builders import RequestBuilder
from framework.api.exceptions import ApiSchemaValidationError
from framework.api.models import LoginRequest
from framework.exceptions import ConfigurationError


@pytest.mark.api
@pytest.mark.regression
class TestRequestBuilder:
    def test_path_params_resolve_into_endpoint_template(self) -> None:
        spec = RequestBuilder("GET", "/users/{id}").path_param("id", 42).build()
        assert spec.resolved_path() == "/users/42"

    def test_missing_path_param_raises_clear_error(self) -> None:
        spec = RequestBuilder("GET", "/users/{id}").build()
        with pytest.raises(ValueError, match="id"):
            spec.resolved_path()

    def test_query_params_accumulate(self) -> None:
        spec = (
            RequestBuilder("GET", "/users")
            .query_param("limit", 5)
            .query_params({"skip": 10})
            .build()
        )
        assert spec.query_params == {"limit": 5, "skip": 10}

    def test_headers_accumulate(self) -> None:
        spec = (
            RequestBuilder("GET", "/users").header("X-Test", "1").headers({"X-Other": "2"}).build()
        )
        assert spec.headers == {"X-Test": "1", "X-Other": "2"}

    def test_json_body_accepts_dict(self) -> None:
        spec = RequestBuilder("POST", "/users").json_body({"name": "Ada"}).build()
        assert spec.json_body == {"name": "Ada"}
        assert spec.headers["Content-Type"] == "application/json"

    def test_json_body_accepts_pydantic_model(self) -> None:
        spec = (
            RequestBuilder("POST", "/login")
            .json_body(LoginRequest(username="a", password="b"))
            .build()
        )
        assert spec.json_body == {"username": "a", "password": "b"}

    def test_xml_body_sets_content_type(self) -> None:
        spec = RequestBuilder("POST", "/x").xml_body("<a>1</a>").build()
        assert spec.xml_body == "<a>1</a>"
        assert spec.headers["Content-Type"] == "application/xml"

    def test_form_data_sets_content_type(self) -> None:
        spec = RequestBuilder("POST", "/x").form_data({"a": "1"}).build()
        assert spec.form_data == {"a": "1"}
        assert spec.headers["Content-Type"] == "application/x-www-form-urlencoded"

    def test_multipart_files(self) -> None:
        spec = RequestBuilder("POST", "/upload").multipart({"file": ("a.txt", b"hello")}).build()
        assert spec.files == {"file": ("a.txt", b"hello")}

    def test_file_upload_reads_real_file(self, tmp_path) -> None:
        file_path = tmp_path / "report.csv"
        file_path.write_text("a,b\n1,2\n")

        spec = RequestBuilder("POST", "/upload").file_upload("file", file_path).build()

        assert spec.files is not None
        filename, content = spec.files["file"]
        assert filename == "report.csv"
        assert content == b"a,b\n1,2\n"

    @pytest.mark.parametrize(
        "first,second",
        [
            ("json_body", "form_data"),
            ("json_body", "xml_body"),
            ("form_data", "multipart"),
        ],
    )
    def test_mixing_body_types_is_rejected(self, first: str, second: str) -> None:
        builder = RequestBuilder("POST", "/x")
        args = {
            "json_body": ({"a": 1},),
            "xml_body": ("<a/>",),
            "form_data": ({"a": 1},),
            "multipart": ({"f": ("a.txt", b"x")},),
        }
        getattr(builder, first)(*args[first])
        with pytest.raises(ConfigurationError):
            getattr(builder, second)(*args[second])


@pytest.mark.api
@pytest.mark.regression
class TestSchemaRegistryErrors:
    def test_unknown_schema_name_raises_configuration_error(self) -> None:
        from framework.api.schemas import load_schema

        with pytest.raises(ConfigurationError):
            load_schema("does_not_exist")

    def test_validate_against_schema_raises_with_field_detail(self) -> None:
        from framework.api.schemas import validate_against_schema

        with pytest.raises(ApiSchemaValidationError, match="id"):
            validate_against_schema({"firstName": "Ada"}, "user_schema")
