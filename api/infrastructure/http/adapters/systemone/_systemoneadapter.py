from http import HTTPMethod

from api.domain.provider.entities import ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.domain.systemone.entities import SystemOne
from api.infrastructure.http._httpproviderresponse import HttpProviderResponse
from api.infrastructure.http.adapters import HttpProviderAdapter


class SystemOneAdapter(HttpProviderAdapter):
    """Relays the request as is: the provider already speaks the System One API (Jev, Colibrì...)."""

    SOURCE_ENDPOINT = ProviderEndpoint.SYSTEMONE
    TARGET_ENDPOINT_ROUTE = "/v1/systemone"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = SystemOne

    def to_provider_response(
        self,
        http_response: HttpProviderResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        # the server names its usage input_tokens / output_tokens (Jev's names), OpenGateLLM reads prompt_tokens / completion_tokens
        body = dict(http_response.data)
        usage = body.pop("usage", None)
        if isinstance(usage, dict) and isinstance(usage.get("input_tokens"), int) and isinstance(usage.get("output_tokens"), int):
            prompt_tokens, completion_tokens = usage["input_tokens"], usage["output_tokens"]
            body["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        return super().to_provider_response(http_response=HttpProviderResponse(data=body), request=request)
