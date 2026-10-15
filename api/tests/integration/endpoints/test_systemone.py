import json
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_systemone_use_case_factory
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import ProviderEndpoint, ProviderType
from api.domain.provider.errors import (
    NoAvailableProviderError,
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    UnsupportedProviderEndpointError,
)
from api.domain.role.entities import LimitType
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasNoAccessToRouterError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.conftest import override_global_context
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_systemone_responses
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.tests.integration.factories.systemone import SYSTEMONE_QUESTIONS, SYSTEMONE_STATE, SystemOneResponseFactory

URL = f"/v1{EndpointRoute.SYSTEMONE}"

DEFAULT_MODEL_NAME = "decision-router"
PROVIDER_MODEL_NAME = f"{DEFAULT_MODEL_NAME}_provider_1"  # RouterSQLFactory names its providers after the router
SAMPLE_VALIDATION_ERRORS = [{"type": "missing", "loc": ["state"], "msg": "Field required", "input": {}}]


def _valid_body(**overrides) -> dict:
    body = {"model": DEFAULT_MODEL_NAME, "state": SYSTEMONE_STATE, "questions": SYSTEMONE_QUESTIONS}
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateSystemOne:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [0] * 10
        with override_global_context(redis_pool=test_redis_pool, tokenizer=mock_tokenizer):
            yield

    def _router(self):
        return RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=RouterType.DECISION,
            providers=1,
            providers__type=ProviderType.OPENAI,
            providers__url=DEFAULT_PROVIDER_URL,
        )

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_systemone_key", user=self.router_owner)
        self._router()
        await db_session.flush()

        mock_systemone_responses(
            respx_mock=respx,
            provider_type=ProviderType.OPENAI,
            body=SystemOneResponseFactory(),
            status_code=SystemOneResponseFactory._status_code,
        )

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {admin_key.token}"}, json=_valid_body())

        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["id"]) == 32
        assert data["model"] == DEFAULT_MODEL_NAME
        assert data["answers"]["urgency"] == {"type": "noul", "noul": 0.847606}
        assert data["answers"]["department"]["choice"] == "technical"
        assert data["answers"]["department"]["probabilities"]["technical"] == 0.939983
        assert data["answers"]["severity"]["score"] == 2.831772
        assert data["answers"]["severity"]["legend"]["3"] == "losing money"

    @respx.mock
    async def test_counts_the_input_and_no_output(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_systemone_usage_key", user=self.router_owner)
        self._router()
        await db_session.flush()
        mock_systemone_responses(respx_mock=respx, provider_type=ProviderType.OPENAI, body=SystemOneResponseFactory(), status_code=200)

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {admin_key.token}"}, json=_valid_body())

        assert response.status_code == 200, response.text
        usage = response.json()["usage"]
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 10

    @respx.mock
    async def test_relays_the_request_to_the_provider_with_its_model_name(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_systemone_relay_key", user=self.router_owner)
        self._router()
        await db_session.flush()
        route = mock_systemone_responses(respx_mock=respx, provider_type=ProviderType.OPENAI, body=SystemOneResponseFactory(), status_code=200)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            json=_valid_body(normalize="mean"),
        )

        assert response.status_code == 200, response.text
        provider_json = json.loads(route.calls[0].request.content)
        assert provider_json["model"] == PROVIDER_MODEL_NAME
        assert provider_json["state"] == SYSTEMONE_STATE
        assert provider_json["questions"] == SYSTEMONE_QUESTIONS
        assert provider_json["normalize"] == "mean"
        assert None not in provider_json.values()

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (RouterNotFoundError(name=DEFAULT_MODEL_NAME), 404, f"Model {DEFAULT_MODEL_NAME} not found."),
            (RouterHasNoProvidersError(id=1), 404, f"Model {DEFAULT_MODEL_NAME} not found."),
            (UserHasNoAccessToRouterError(id=1), 404, f"Model {DEFAULT_MODEL_NAME} not found."),
            (
                RouterHasWrongTypeError(id=1, actual_type=RouterType.TEXT_GENERATION, expected_type=RouterType.DECISION),
                422,
                "Model has wrong type. Expected: decision. Actual: text-generation.",
            ),
            (NoAvailableProviderError(router_id=1), 503, "Model is too busy, please try again later."),
            (TooBusyModelError(status_code=503, detail="provider busy"), 503, "Model is too busy, please try again later."),
            (RouterRateLimitExceededError(id=1, limit_type=LimitType.RPM, headers={}), 429, "Request limit per minute exceeded."),
            (StatusCodeModelError(status_code=400, detail="bad request"), 400, "bad request"),
            (UnknownModelError(status_code=500, detail="upstream failure"), 500, "upstream failure"),
            (
                UnsupportedProviderEndpointError(endpoint=ProviderEndpoint.SYSTEMONE, provider_type=ProviderType.OPENAI),
                500,
                "Model provider type openai does not support the /systemone endpoint.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_systemone_use_case_factory] = lambda: mock_use_case

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {self.key.token}"}, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "use_case_result",
        [
            ProviderAdapterValidationRequestError(provider_type=ProviderType.OPENAI, errors=SAMPLE_VALIDATION_ERRORS),
            ProviderAdapterValidationResponseError(provider_type=ProviderType.OPENAI, errors=SAMPLE_VALIDATION_ERRORS),
        ],
    )
    async def test_adapter_validation_error_returns_422_with_errors(self, client: AsyncClient, app, use_case_result):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_systemone_use_case_factory] = lambda: mock_use_case

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {self.key.token}"}, json=_valid_body())

        assert response.status_code == 422
        assert response.json().get("detail") == SAMPLE_VALIDATION_ERRORS

    @pytest.mark.parametrize(
        "body",
        [
            {"model": DEFAULT_MODEL_NAME, "questions": SYSTEMONE_QUESTIONS},
            {"model": DEFAULT_MODEL_NAME, "state": SYSTEMONE_STATE},
            {"model": DEFAULT_MODEL_NAME, "state": SYSTEMONE_STATE, "questions": {}},
            {"model": DEFAULT_MODEL_NAME, "state": SYSTEMONE_STATE, "questions": {"q": {"type": "unknown"}}},
            {"model": DEFAULT_MODEL_NAME, "state": SYSTEMONE_STATE, "questions": {"q": {"type": "choice"}}},
            {"state": SYSTEMONE_STATE, "questions": SYSTEMONE_QUESTIONS},
        ],
        ids=["no-state", "no-questions", "empty-questions", "unknown-question-type", "choice-without-criteria", "no-model"],
    )
    async def test_invalid_body_returns_422(self, client: AsyncClient, body):
        response = await client.post(url=URL, headers={"Authorization": f"Bearer {self.key.token}"}, json=body)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
