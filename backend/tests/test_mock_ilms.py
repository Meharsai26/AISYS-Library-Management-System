"""Tests for provider-neutral NCIP/SIP2 mock adapters."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.services.mock_ilms import (
    ILMSOperation,
    ILMSOutcome,
    ILMSRequest,
    MockNCIPAdapter,
    MockSIP2Adapter,
)


@pytest.mark.parametrize(
    "adapter_class",
    [MockNCIPAdapter, MockSIP2Adapter],
)
@pytest.mark.parametrize(
    "operation",
    list(ILMSOperation),
)
@pytest.mark.parametrize(
    "outcome",
    list(ILMSOutcome),
)
def test_mock_adapter_operation_outcomes(
    adapter_class, operation, outcome
):
    correlation_id = str(uuid4())

    request = ILMSRequest(
        operation=operation,
        loan_id="synthetic-loan",
        member_id="synthetic-member",
        item_id="synthetic-item",
        correlation_id=correlation_id,
    )

    adapter = adapter_class(
        simulated_outcome=outcome
    )

    result = adapter.execute(request)

    assert result.outcome == outcome
    assert result.operation == operation
    assert result.correlation_id == correlation_id
    assert result.provider == adapter_class.provider
    assert result.message


@pytest.mark.parametrize(
    "invalid_field",
    [
        "loan_id",
        "member_id",
        "item_id",
        "correlation_id",
    ],
)
def test_empty_request_fields_rejected(invalid_field):
    payload = {
        "operation": ILMSOperation.CHECKOUT,
        "loan_id": "loan-test",
        "member_id": "member-test",
        "item_id": "item-test",
        "correlation_id": str(uuid4()),
    }

    payload[invalid_field] = ""

    with pytest.raises(ValueError):
        ILMSRequest(**payload)


def test_invalid_correlation_id_rejected():
    with pytest.raises(ValueError):
        ILMSRequest(
            operation=ILMSOperation.CHECKOUT,
            loan_id="loan-test",
            member_id="member-test",
            item_id="item-test",
            correlation_id="not-a-uuid",
        )


def test_invalid_adapter_payload_rejected():
    adapter = MockNCIPAdapter()

    with pytest.raises(TypeError):
        adapter.execute({"operation": "CHECKOUT"})


def test_invalid_simulated_outcome_rejected():
    with pytest.raises(ValueError):
        MockSIP2Adapter(
            simulated_outcome="UNKNOWN"
        )


def test_request_is_immutable():
    request = ILMSRequest(
        operation=ILMSOperation.RENEW,
        loan_id="loan-test",
        member_id="member-test",
        item_id="item-test",
        correlation_id=str(uuid4()),
    )

    with pytest.raises(FrozenInstanceError):
        request.loan_id = "changed"
