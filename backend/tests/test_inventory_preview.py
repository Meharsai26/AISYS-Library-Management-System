"""Phase 6 mock RFID inventory preview tests."""

from tests.test_auth import setup_auth
from tests.test_circulation_outbox import (
    authenticate,
    create_checkout,
    checkout,
)


def create_tagged_item(client, auth, epc):
    item_id, member_id = create_checkout(client, auth)

    assigned = client.post(
        "/api/v1/rfid/tags/assign",
        headers=auth,
        json={"item_id": item_id, "epc": epc},
    )
    assert assigned.status_code == 201, assigned.text

    return item_id, member_id


def test_inventory_preview_matches_available_tag(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    create_tagged_item(client, auth, "MOCK-EPC-INV001")

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={"scanned_epcs": ["MOCK-EPC-INV001"]},
    )

    assert response.status_code == 200, response.text
    result = response.json()

    assert "MOCK-EPC-INV001" in result["matched_epcs"]
    assert result["missing_epcs"] == []
    assert result["unknown_epcs"] == []


def test_inventory_preview_detects_missing_tag(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    create_tagged_item(client, auth, "MOCK-EPC-INV002")

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={"scanned_epcs": []},
    )

    assert response.status_code == 200, response.text
    assert "MOCK-EPC-INV002" in response.json()["missing_epcs"]


def test_inventory_preview_detects_unknown_tag(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={"scanned_epcs": ["MOCK-EPC-UNKNOWN-01"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["unknown_epcs"] == [
        "MOCK-EPC-UNKNOWN-01"
    ]


def test_inventory_preview_deduplicates_scans(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    create_tagged_item(client, auth, "MOCK-EPC-INV003")

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={
            "scanned_epcs": [
                "MOCK-EPC-INV003",
                "MOCK-EPC-INV003",
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["matched_epcs"] == [
        "MOCK-EPC-INV003"
    ]


def test_checked_out_item_not_expected_on_shelf(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    item_id, member_id = create_tagged_item(
        client, auth, "MOCK-EPC-INV004"
    )

    checked_out = checkout(client, auth, item_id, member_id)
    assert checked_out.status_code == 201

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={"scanned_epcs": []},
    )

    assert response.status_code == 200, response.text
    assert "MOCK-EPC-INV004" not in response.json()["missing_epcs"]


def test_inventory_preview_requires_authentication(setup_auth):
    client, _, _, _ = setup_auth

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        json={"scanned_epcs": []},
    )

    assert response.status_code == 401


def test_known_checked_out_tag_classification(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    item_id, member_id = create_tagged_item(
        client, auth, "MOCK-EPC-INV-CHECKEDOUT"
    )

    checked_out = checkout(client, auth, item_id, member_id)
    assert checked_out.status_code == 201

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={
            "scanned_epcs": ["MOCK-EPC-INV-CHECKEDOUT"]
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()

    assert result["unknown_epcs"] == []
    assert result["unexpected_known_epcs"] == [
        "MOCK-EPC-INV-CHECKEDOUT"
    ]


def test_inventory_preview_permission_denied(setup_auth):
    client, _, _, librarian = setup_auth

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": librarian,
            "password": "SyntheticLibrarianPass123!",
        },
    )
    assert response.status_code == 200

    auth = {
        "Authorization": (
            "Bearer " + response.json()["access_token"]
        )
    }

    preview = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={"scanned_epcs": []},
    )

    assert preview.status_code == 403


def test_inventory_preview_rejects_invalid_payload(setup_auth):
    client, _, admin, _ = setup_auth
    auth = authenticate(client, admin)

    response = client.post(
        "/api/v1/inventory/reconcile/mock",
        headers=auth,
        json={"scanned_epcs": "not-a-list"},
    )

    assert response.status_code == 422