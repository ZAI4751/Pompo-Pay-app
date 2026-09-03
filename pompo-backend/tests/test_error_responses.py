"""Error-response contract tests.

Every error the API returns uses one shape — ``detail`` plus ``request_id`` —
so a client can distinguish failure modes by status code and render the
``detail`` directly. Validation failures additionally carry ``errors``.
"""

import pytest
from httpx import AsyncClient

from app.middleware.exception_handler import user_facing_validation_detail

# Not a real credential: a recognisable literal asserted to be ABSENT from
# responses and therefore from logs.
SENTINEL_PASSWORD = "sentinel-value-must-not-be-echoed"


@pytest.mark.asyncio
async def test_validation_error_uses_the_standard_shape(client: AsyncClient) -> None:
    """A 422 must be summarised, not returned in FastAPI's raw default shape.

    The default puts a list of objects in ``detail``; a client doing
    ``String(detail)`` on that renders "[object Object]".
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": SENTINEL_PASSWORD},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Email address is invalid"
    assert body["request_id"] != "unknown"
    assert isinstance(body["errors"], list)
    assert body["errors"], "a validation failure must report which field failed"
    assert body["errors"][0]["loc"] == ["body", "email"]
    assert SENTINEL_PASSWORD not in body["detail"]


def test_user_facing_validation_detail_maps_common_fields() -> None:
    assert (
        user_facing_validation_detail(
            [{"loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error"}]
        )
        == "Email address is invalid"
    )
    assert (
        user_facing_validation_detail(
            [{"loc": ["body", "password"], "msg": "String should have at least 8 characters", "type": "string_too_short"}]
        )
        == "Password does not meet requirements"
    )
    assert (
        user_facing_validation_detail(
            [{"loc": ["body", "full_name"], "msg": "Field required", "type": "missing"}]
        )
        == "Full name is required"
    )
    assert (
        user_facing_validation_detail(
            [{"loc": ["body", "phone"], "msg": "String should have at most 32 characters", "type": "string_too_long"}]
        )
        == "Phone number is invalid"
    )


@pytest.mark.asyncio
async def test_validation_error_does_not_echo_submitted_values(
    client: AsyncClient,
) -> None:
    """Pydantic includes the offending ``input`` in every error it raises.

    On a credential endpoint that would place the plaintext password into the
    response body and the structured logs, so only loc/msg/type are exposed.
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": SENTINEL_PASSWORD},
    )

    assert response.status_code == 422
    assert SENTINEL_PASSWORD not in response.text

    for error in response.json()["errors"]:
        assert set(error) == {"loc", "msg", "type"}


@pytest.mark.asyncio
async def test_http_exception_keeps_the_standard_shape(client: AsyncClient) -> None:
    """A deliberate 401 still returns detail + request_id."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Incorrect email or password"
    assert body["request_id"] != "unknown"


@pytest.mark.asyncio
async def test_not_found_route_returns_json_not_html(client: AsyncClient) -> None:
    """An unknown path must return the JSON contract so clients can parse it."""
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Not Found"
