from fastapi.testclient import TestClient

from main import create_app


def test_create_app_instances_use_isolated_databases(tmp_path) -> None:
    app_one = create_app(database_path=tmp_path / "one.duckdb", seed=False)
    app_two = create_app(database_path=tmp_path / "two.duckdb", seed=False)

    with TestClient(app_one) as client_one:
        created = client_one.post(
            "/api/tickets",
            json={
                "title": "VPN issue",
                "description": "Cannot reach internal resources",
                "requester": "Avery Stone",
                "priority": "high",
            },
        )
        assert created.status_code == 201

    with TestClient(app_two) as client_two:
        listed = client_two.get("/api/tickets")
        assert listed.status_code == 200
        assert listed.json() == []
