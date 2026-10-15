from http import HTTPMethod

from api.domain.provider.entities import ProviderEndpoint
from api.domain.systemone.entities import SystemOne
from api.infrastructure.http.adapters import HttpProviderAdapter


class SystemOneAdapter(HttpProviderAdapter):
    """Relays the request as is: the provider already speaks the System One API (Jev, Colibrì...)."""

    SOURCE_ENDPOINT = ProviderEndpoint.SYSTEMONE
    TARGET_ENDPOINT_ROUTE = "/v1/systemone"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = SystemOne
