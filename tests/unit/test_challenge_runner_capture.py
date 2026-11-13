import httpx
from tests.integration.test_questions_challenge_20_live import _capture_http_response


def test_http_runner_preserves_non_json_failure_body() -> None:
    response = httpx.Response(500, text="Internal Server Error: provider refused the schema")
    record: dict[str, object] = {}

    assert _capture_http_response(record, response) is False
    assert record == {
        "http_status": 500,
        "technical_error": "HTTP 500",
        "response_body": "Internal Server Error: provider refused the schema",
    }
