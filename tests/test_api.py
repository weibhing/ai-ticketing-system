from fastapi.testclient import TestClient

from main import create_app


def test_api_crud_filters_and_status_codes(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "api.duckdb", seed=False)

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        created = client.post(
            "/api/tickets",
            json={
                "title": "VPN issue",
                "description": "Cannot reach internal resources",
                "requester": "Avery Stone",
                "priority": "high",
            },
        )
        assert created.status_code == 201
        first_ticket = created.json()
        assert first_ticket["id"] == 1
        assert first_ticket["priority"] == "high"
        assert first_ticket["status"] == "open"

        second = client.post(
            "/api/tickets",
            json={
                "title": "Finance dashboard access",
                "description": "Need monthly reporting access",
                "requester": "Mina Patel",
                "priority": "medium",
            },
        )
        second_ticket = second.json()

        updated = client.patch(f"/api/tickets/{second_ticket['id']}", json={"status": "resolved"})
        assert updated.status_code == 200
        assert updated.json()["status"] == "resolved"

        fetched = client.get(f"/api/tickets/{first_ticket['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == first_ticket["id"]

        listed = client.get("/api/tickets", params={"status": "resolved", "priority": "medium", "search": "dashboard"})
        assert listed.status_code == 200
        assert [ticket["id"] for ticket in listed.json()] == [second_ticket["id"]]

        deleted = client.delete(f"/api/tickets/{first_ticket['id']}")
        assert deleted.status_code == 204
        assert deleted.text == ""

        assert client.get(f"/api/tickets/{first_ticket['id']}").status_code == 404
        assert client.get(f"/api/tickets/{second_ticket['id']}").status_code == 200


def test_api_validation_missing_records_and_failures_do_not_mutate_data(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "validation.duckdb", seed=False)

    with TestClient(app) as client:
        created = client.post(
            "/api/tickets",
            json={
                "title": "Printer issue",
                "description": "Paper jams every morning",
                "requester": "Sam Lee",
                "priority": "low",
            },
        )
        assert created.status_code == 201
        original = created.json()

        assert client.get("/api/tickets/999").status_code == 404
        assert client.patch("/api/tickets/999", json={"status": "closed"}).status_code == 404
        assert client.delete("/api/tickets/999").status_code == 404
        assert client.get("/api/tickets/0").status_code == 422
        assert client.get("/api/tickets", params={"priority": "bogus"}).status_code == 422
        assert client.post(
            "/api/tickets",
            json={
                "title": "   ",
                "description": "Valid description",
                "requester": "AB",
                "priority": "high",
            },
        ).status_code == 422
        assert client.patch(f"/api/tickets/{original['id']}", json={"status": None}).status_code == 422

        no_op = client.patch(f"/api/tickets/{original['id']}", json={})
        assert no_op.status_code == 200
        assert no_op.json() == original

        final_list = client.get("/api/tickets")
        assert final_list.status_code == 200
        assert final_list.json() == [original]
