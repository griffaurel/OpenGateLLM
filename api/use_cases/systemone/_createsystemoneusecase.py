from api.domain.provider.entities import ProviderEndpoint
from api.domain.router.entities import RouterType
from api.domain.systemone.entities import CreateSystemOneBody, SystemOne
from api.use_cases._providerrequestforwardingusecase import (
    ForwardingCommand,
    ProviderRequestForwardingUseCase,
    ProviderRequestForwardingUseCaseResult,
    ProviderRequestForwardingUseCaseSuccess,
)


class CreateSystemOneCommand(ForwardingCommand[CreateSystemOneBody]): ...


CreateSystemOneUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateSystemOneUseCase(ProviderRequestForwardingUseCase[CreateSystemOneCommand, ProviderRequestForwardingUseCaseResult[SystemOne]]):
    ROUTER_TYPE = RouterType.DECISION
    ENDPOINT = ProviderEndpoint.SYSTEMONE
