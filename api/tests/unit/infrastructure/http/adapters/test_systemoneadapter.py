from http import HTTPMethod
import json

import pytest

from api.domain.provider.entities import ProviderEndpoint, ProviderRequest, ProviderResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.domain.systemone.entities import CreateSystemOneBody, SystemOne
from api.infrastructure.http import HttpProviderRequest, HttpProviderResponse
from api.infrastructure.http.adapters.systemone import SystemOneAdapter
from api.infrastructure.http.adapters.systemone.colibri import ColibriSystemOneAdapter
from api.tests.integration.factories.systemone import SYSTEMONE_QUESTIONS, SYSTEMONE_STATE, SystemOneResponseFactory
from api.tests.unit.use_case.factories import ProviderFactory

ROUTER_NAME = "decision-router"


@pytest.fixture
def provider():
    return ProviderFactory(type=ProviderType.COLIBRI, url="https://colibri.test", model_name="qwen36", model_total_params=10, model_active_params=5)


@pytest.fixture
def adapter(provider) -> ColibriSystemOneAdapter:
    return ColibriSystemOneAdapter(provider=provider)


def _request(**extra) -> ProviderRequest:
    payload = CreateSystemOneBody.model_validate({"model": ROUTER_NAME, "state": SYSTEMONE_STATE, "questions": SYSTEMONE_QUESTIONS, **extra})
    return ProviderRequest(id="req-1", endpoint=ProviderEndpoint.SYSTEMONE, payload=payload)


class TestSystemOneAdapter:
    def test_should_target_the_systemone_route_of_the_provider(self, adapter):
        assert isinstance(adapter, SystemOneAdapter)
        assert adapter.SOURCE_ENDPOINT == ProviderEndpoint.SYSTEMONE
        assert adapter.TARGET_ENDPOINT_ROUTE == "/v1/systemone"
        assert adapter.TARGET_ENDPOINT_METHOD == HTTPMethod.POST

    @pytest.mark.parametrize("base_url", ["https://colibri.test", "https://colibri.test/", "https://gateway.test/colibri"])
    def test_should_build_the_url_from_the_provider_url(self, provider, base_url):
        adapter = ColibriSystemOneAdapter(provider=provider.model_copy(update={"url": base_url}))

        result = adapter.to_http_request(_request())

        assert result.url == base_url.rstrip("/") + "/v1/systemone"

    def test_should_relay_the_request_with_the_model_of_the_provider(self, adapter):
        result = adapter.to_http_request(_request())

        assert isinstance(result, HttpProviderRequest)
        assert result.method == HTTPMethod.POST
        assert result.body["model"] == "qwen36"
        assert result.body["state"] == SYSTEMONE_STATE
        assert result.body["questions"] == SYSTEMONE_QUESTIONS

    def test_should_relay_the_options_of_the_provider(self, adapter):
        result = adapter.to_http_request(_request(normalize="mean", pin_state=True))

        assert result.body["normalize"] == "mean"
        assert result.body["pin_state"] is True

    def test_should_send_a_body_that_can_be_serialized_as_json(self, adapter):
        result = adapter.to_http_request(_request(state={"ticket": [1, 2]}))

        assert json.loads(json.dumps(result.body))["state"] == {"ticket": [1, 2]}

    def test_should_answer_with_the_id_and_the_model_of_the_gateway(self, adapter):
        http_response = HttpProviderResponse(data=SystemOneResponseFactory())

        result = adapter.to_provider_response(http_response=http_response, request=_request())

        assert isinstance(result, ProviderResponse)
        assert isinstance(result.data, SystemOne)
        assert result.data.id == "req-1"
        assert result.data.model == ROUTER_NAME
        assert result.data.answers["department"].choice == "technical"

    def test_should_read_the_usage_of_the_provider_with_the_names_of_the_gateway(self, adapter):
        http_response = HttpProviderResponse(data=SystemOneResponseFactory(usage={"input_tokens": 86, "output_tokens": 3, "cost": 0}))

        result = adapter.to_provider_response(http_response=http_response, request=_request())

        assert "usage" in result.data.model_fields_set
        assert (result.data.usage.prompt_tokens, result.data.usage.completion_tokens, result.data.usage.total_tokens) == (86, 3, 89)
        assert result.data.usage.prompt_tokens_details.cached_tokens == 0

    @pytest.mark.parametrize("usage", [None, {}, {"cost": 0}, {"input_tokens": 86}, {"input_tokens": "86", "output_tokens": 0}, "86"])
    def test_should_let_the_gateway_count_the_tokens_when_the_usage_cannot_be_read(self, adapter, usage):
        body = SystemOneResponseFactory(usage=usage)

        result = adapter.to_provider_response(http_response=HttpProviderResponse(data=body), request=_request())

        assert isinstance(result, ProviderResponse)
        assert "usage" not in result.data.model_fields_set

    def test_should_let_the_gateway_count_the_tokens_when_the_provider_sends_no_usage(self, adapter):
        body = SystemOneResponseFactory()
        del body["usage"]

        result = adapter.to_provider_response(http_response=HttpProviderResponse(data=body), request=_request())

        assert "usage" not in result.data.model_fields_set

    def test_should_return_a_validation_error_when_the_provider_answer_is_invalid(self, adapter):
        http_response = HttpProviderResponse(data=SystemOneResponseFactory(answers={"urgency": {"type": "noul"}}))

        result = adapter.to_provider_response(http_response=http_response, request=_request())

        assert isinstance(result, ProviderAdapterValidationResponseError)
        assert result.provider_type == ProviderType.COLIBRI
