
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import mock_crm


def test_same_idempotency_key_returns_same_crm_id():
    mock_crm._seen.clear()
    client = TestClient(app)

    headers = {"Idempotency-Key": "ORD-IDEMPOTENCY-001"}
    payload = {
        "order_id": "ORD-IDEMPOTENCY-001",
        "customer_email": "test@example.com",
        "total_amount": "1500.00",
    }

    first = client.post(
        "/mock/crm/orders",
        json=payload,
        headers=headers,
    )
    second = client.post(
        "/mock/crm/orders",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["crm_id"] == second.json()["crm_id"]
