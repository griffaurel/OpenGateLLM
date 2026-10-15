from api.domain.provider.entities import ProviderEndpoint
from api.domain.router.entities import RouterType
from api.use_cases.systemone import CreateSystemOneUseCase


class TestCreateSystemOneUseCase:
    def test_should_use_decision_router_type(self):
        assert CreateSystemOneUseCase.ROUTER_TYPE == RouterType.DECISION

    def test_should_use_systemone_endpoint(self):
        assert CreateSystemOneUseCase.ENDPOINT == ProviderEndpoint.SYSTEMONE
