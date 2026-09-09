import pytest

from database import TicketNotFoundError, TicketRepository
from models import TicketCreate, TicketFilters, TicketPriority, TicketStatus, TicketUpdate


def _create_ticket(
    repository: TicketRepository,
    *,
    title: str,
    description: str,
    requester: str,
    priority: TicketPriority,
) -> int:
    return repository.create(
        TicketCreate(
            title=title,
            description=description,
            requester=requester,
            priority=priority,
        )
    ).id


def test_seed_defaults_only_seeds_empty_database(tmp_path) -> None:
    database_path = tmp_path / "tickets.duckdb"

    repository = TicketRepository(database_path)
    repository.seed_defaults()
    first_pass_titles = [ticket.title for ticket in repository.list()]
    repository.close()

    reopened = TicketRepository(database_path)
    reopened.seed_defaults()
    second_pass_titles = [ticket.title for ticket in reopened.list()]
    reopened.close()

    assert len(first_pass_titles) == 3
    assert second_pass_titles == first_pass_titles


def test_repository_round_trips_filters_updates_and_exact_delete() -> None:
    repository = TicketRepository(":memory:")
    try:
        vpn_id = _create_ticket(
            repository,
            title="Laptop cannot connect to VPN",
            description="Requester is blocked from internal systems.",
            requester="Avery Stone",
            priority=TicketPriority.high,
        )
        dashboard_id = _create_ticket(
            repository,
            title="Finance dashboard access",
            description="Need read-only dashboard access",
            requester="Mina Patel",
            priority=TicketPriority.medium,
        )
        room_id = _create_ticket(
            repository,
            title="Broken display",
            description="Conference room display is blank",
            requester="Jon Bell",
            priority=TicketPriority.low,
        )

        repository.update(vpn_id, TicketUpdate(status=TicketStatus.in_progress))

        vpn_ticket = repository.get(vpn_id)
        assert vpn_ticket.priority is TicketPriority.high
        assert vpn_ticket.status is TicketStatus.in_progress

        filtered = repository.list(
            TicketFilters(
                status=TicketStatus.in_progress,
                priority=TicketPriority.high,
                search="avery",
            )
        )
        assert [ticket.id for ticket in filtered] == [vpn_id]

        dashboard_ticket = repository.update(dashboard_id, TicketUpdate())
        assert dashboard_ticket.id == dashboard_id

        repository.delete(dashboard_id)
        remaining_ids = [ticket.id for ticket in repository.list()]
        assert remaining_ids == [vpn_id, room_id]

        with pytest.raises(TicketNotFoundError):
            repository.get(dashboard_id)

        with pytest.raises(TicketNotFoundError):
            repository.delete(9999)

        assert [ticket.id for ticket in repository.list()] == [vpn_id, room_id]
    finally:
        repository.close()
