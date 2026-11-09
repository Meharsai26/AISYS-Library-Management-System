from sqlalchemy import select, func

from tests.test_auth import setup_auth, login, headers
from app.models.foundation import Member
from app.models.migration import ImportBatch, ImportStagingRow


ENDPOINT = "/api/v1/imports/members"


def admin_headers(client, username):
    response = login(client, username, "SyntheticAdminPass123!")
    assert response.status_code == 200
    return headers(response.json()["access_token"])


def test_import_requires_authentication(setup_auth):
    client, _, _, _ = setup_auth

    response = client.post(
        ENDPOINT,
        json={
            "filename": "members.csv",
            "csv_content": "card_number,display_name\nM101,Alice\n",
        },
    )

    assert response.status_code == 401


def test_import_requires_member_write_permission(setup_auth):
    client, factory, _, librarian = setup_auth

    auth = login(
        client, librarian, "SyntheticLibrarianPass123!"
    )
    assert auth.status_code == 200

    response = client.post(
        ENDPOINT,
        headers=headers(auth.json()["access_token"]),
        json={
            "filename": "members.csv",
            "csv_content": "card_number,display_name\nM101,Alice\n",
        },
    )

    assert response.status_code == 403

    with factory() as db:
        assert db.scalar(
            select(func.count()).select_from(ImportBatch)
        ) == 0


def test_admin_import_persists_and_reconciles(setup_auth):
    client, factory, admin, _ = setup_auth

    response = client.post(
        ENDPOINT,
        headers=admin_headers(client, admin),
        json={
            "filename": "synthetic_members.csv",
            "csv_content": (
                "card_number,display_name,status\n"
                "P5-API-001,Alice,ACTIVE\n"
                "P5-API-002,Bob,BLOCKED\n"
            ),
        },
    )

    assert response.status_code == 200, response.text

    result = response.json()
    assert result["source_count"] == 2
    assert result["inserted_count"] == 2
    assert result["rejected_count"] == 0
    assert result["reconciled"] is True

    with factory() as db:
        batch = db.get(ImportBatch, result["batch_id"])
        assert batch is not None
        assert batch.status == "COMPLETED"

        rows = db.scalars(
            select(ImportStagingRow).where(
                ImportStagingRow.batch_id == batch.id
            )
        ).all()

        assert len(rows) == 2

        for row in rows:
            assert row.status == "IMPORTED"
            member = db.get(Member, row.target_member_id)
            assert member is not None


def test_import_rejects_invalid_csv(setup_auth):
    client, factory, admin, _ = setup_auth

    auth_headers = admin_headers(client, admin)

    response = client.post(
        ENDPOINT,
        headers=auth_headers,
        json={
            "filename": "invalid.csv",
            "csv_content": "card_number\nM101\n",
        },
    )

    assert response.status_code == 400

    extension_response = client.post(
        ENDPOINT,
        headers=auth_headers,
        json={
            "filename": "invalid.txt",
            "csv_content": "card_number,display_name\nM101,Alice\n",
        },
    )

    assert extension_response.status_code == 400

    with factory() as db:
        assert db.scalar(
            select(func.count()).select_from(ImportBatch)
        ) == 0


def test_import_rejects_oversized_csv(setup_auth):
    client, factory, admin, _ = setup_auth

    response = client.post(
        ENDPOINT,
        headers=admin_headers(client, admin),
        json={
            "filename": "large.csv",
            "csv_content": "X" * (1024 * 1024 + 1),
        },
    )

    assert response.status_code == 413

    with factory() as db:
        assert db.scalar(
            select(func.count()).select_from(ImportBatch)
        ) == 0
