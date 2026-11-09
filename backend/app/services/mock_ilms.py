"""Provider-neutral NCIP/SIP2 simulation for the AISYS prototype.

These adapters do not implement NCIP or SIP2 wire protocols.
They do not communicate with external library systems.
"""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class ILMSOperation(str, Enum):
    CHECKOUT = "CHECKOUT"
    CHECKIN = "CHECKIN"
    RENEW = "RENEW"


class ILMSOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ILMSRequest:
    operation: ILMSOperation
    loan_id: str
    member_id: str
    item_id: str
    correlation_id: str

    def __post_init__(self):
        for field_name in (
            "loan_id",
            "member_id",
            "item_id",
            "correlation_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a nonempty string"
                )

        try:
            UUID(self.correlation_id)
        except ValueError as exc:
            raise ValueError(
                "correlation_id must be a UUID"
            ) from exc


@dataclass(frozen=True)
class ILMSResult:
    provider: str
    operation: ILMSOperation
    outcome: ILMSOutcome
    correlation_id: str
    message: str


class BaseMockILMSAdapter:
    provider = "MOCK"

    def __init__(
        self,
        simulated_outcome: ILMSOutcome = ILMSOutcome.ACCEPTED,
    ):
        self.simulated_outcome = ILMSOutcome(
            simulated_outcome
        )

    def execute(self, request: ILMSRequest) -> ILMSResult:
        if not isinstance(request, ILMSRequest):
            raise TypeError("Expected ILMSRequest")

        messages = {
            ILMSOutcome.ACCEPTED:
                "Synthetic operation accepted",
            ILMSOutcome.REJECTED:
                "Synthetic operation rejected",
            ILMSOutcome.TIMEOUT:
                "Synthetic provider timeout",
            ILMSOutcome.UNAVAILABLE:
                "Synthetic provider unavailable",
        }

        return ILMSResult(
            provider=self.provider,
            operation=request.operation,
            outcome=self.simulated_outcome,
            correlation_id=request.correlation_id,
            message=messages[self.simulated_outcome],
        )


class MockNCIPAdapter(BaseMockILMSAdapter):
    provider = "MOCK_NCIP"


class MockSIP2Adapter(BaseMockILMSAdapter):
    provider = "MOCK_SIP2"
