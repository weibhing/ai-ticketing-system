import os

os.environ.setdefault("TICKET_DB_PATH", ":memory:")

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import TicketCreate, TicketFilters, TicketPriority, TicketStatus, TicketUpdate
from app.database import TicketNotFoundError, TicketRepository


def test_repository_crud_and_filters():
    repository = TicketRepository(":memory:")
    try:
        created = repository.create(
            TicketCreate(
                title="Email outage",
                description="The team cannot send email to customers.",
                requester="Taylor",
                priority=TicketPriority.urgent,
            )
        )

        updated = repository.update(created.id, TicketUpdate(status=TicketStatus.in_progress))
        assert updated.status is TicketStatus.in_progress
        assert repository.get(created.id).priority is TicketPriority.urgent

        status_matches = repository.list(TicketFilters(status=TicketStatus.in_progress))
        assert [ticket.id for ticket in status_matches] == [created.id]

        priority_matches = repository.list(TicketFilters(priority=TicketPriority.urgent))
        assert [ticket.id for ticket in priority_matches] == [created.id]

        search_matches = repository.list(TicketFilters(search="customers"))
        assert [ticket.id for ticket in search_matches] == [created.id]

        repository.delete(created.id)
        try:
            repository.get(created.id)
        except TicketNotFoundError:
            pass
        else:
            raise AssertionError("deleted ticket should not be returned")
    finally:
        repository.close()


def test_repository_seeding_runs_once():
    repository = TicketRepository(":memory:")
    try:
        repository.seed_defaults()
        assert len(repository.list()) == 3
        repository.seed_defaults()
        assert len(repository.list()) == 3
    finally:
        repository.close()


def test_api_routes_and_validation():
    app = create_app(database_path=":memory:", seed=False)
    with TestClient(app) as client:
        created = client.post(
            "/api/tickets",
            json={
                "title": "VPN issue",
                "description": "Remote access fails on hotel Wi-Fi.",
                "requester": "Robin",
                "priority": "high",
            },
        )
        assert created.status_code == 201
        body = created.json()
        assert body["id"] == 1
        assert body["status"] == "open"
        assert body["priority"] == "high"

        fetched = client.get("/api/tickets/1")
        assert fetched.status_code == 200
        assert fetched.json()["title"] == "VPN issue"

        filtered = client.get("/api/tickets", params={"status": "open", "priority": "high", "search": "hotel"})
        assert filtered.status_code == 200
        assert [ticket["id"] for ticket in filtered.json()] == [1]

        patched = client.patch("/api/tickets/1", json={"status": "resolved"})
        assert patched.status_code == 200
        assert patched.json()["status"] == "resolved"

        missing = client.get("/api/tickets/999")
        assert missing.status_code == 404

        invalid = client.post(
            "/api/tickets",
            json={"title": " ", "description": "ok", "requester": "R", "priority": "low"},
        )
        assert invalid.status_code == 422

        deleted = client.delete("/api/tickets/1")
        assert deleted.status_code == 204
        assert client.get("/api/tickets/1").status_code == 404

        bad_id = client.get("/api/tickets/0")
        assert bad_id.status_code == 422


def test_health_route():
    app = create_app(database_path=":memory:", seed=False)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_root_entrypoint_imports_work_with_app_package_layout():
    import importlib

    module = importlib.import_module("main")
    assert callable(module.create_app)
    assert module.app is not None
