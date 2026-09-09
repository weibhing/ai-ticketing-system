import pytest
from nicegui.testing import user_simulation

from database import TicketRepository
from models import TicketCreate, TicketPriority, TicketStatus, TicketUpdate
from ui import build_ticket_dashboard


@pytest.mark.anyio
async def test_ui_create_feedback_and_selected_priority() -> None:
    repository = TicketRepository(":memory:")
    try:
        async with user_simulation(root=lambda: build_ticket_dashboard(repository)) as user:
            await user.open("/")
            await user.should_see("Ticket Desk")
            await user.should_see("Create ticket")
            await user.should_see("Refresh")

            user.find(marker="create-title").type("   ")
            user.find(marker="create-requester").type("AB")
            user.find(marker="create-description").type("Valid description")
            user.find("Create ticket").click()
            await user.should_see("Could not create ticket:")
            assert repository.list() == []

            user.find(marker="create-title").clear().type("VPN issue")
            user.find(marker="create-requester").clear().type("Avery Stone")
            user.find(marker="create-description").clear().type("Cannot reach internal resources")
            user.find(marker="create-priority").click()
            user.find("high").click()
            user.find("Create ticket").click()

            await user.should_see("Ticket created")
            await user.should_see("VPN issue")
            await user.should_see("Requester: Avery Stone")
            await user.should_see("Priority: high")

            created_ticket = repository.list()[0]
            assert created_ticket.priority is TicketPriority.high
            assert created_ticket.requester == "Avery Stone"
            assert created_ticket.description == "Cannot reach internal resources"
    finally:
        repository.close()


@pytest.mark.anyio
async def test_ui_filters_clear_and_status_updates_use_exact_ticket_ids() -> None:
    repository = TicketRepository(":memory:")
    try:
        first = repository.create(
            TicketCreate(
                title="Laptop VPN issue",
                description="Requester cannot access VPN",
                requester="Avery Stone",
                priority=TicketPriority.high,
            )
        )
        second = repository.create(
            TicketCreate(
                title="Conference room display",
                description="Screen stays black",
                requester="Jon Bell",
                priority=TicketPriority.low,
            )
        )
        repository.update(first.id, TicketUpdate(status=TicketStatus.in_progress))

        async with user_simulation(root=lambda: build_ticket_dashboard(repository)) as user:
            await user.open("/")
            await user.should_see(first.title)
            await user.should_see(second.title)

            user.find(marker="search-input").type("avery")
            user.find(marker="refresh-button").click()
            await user.should_see(first.title)
            await user.should_not_see(second.title)

            user.find(marker="priority-filter").click()
            user.find("high").click()
            user.find(marker="refresh-button").click()
            await user.should_see(first.title)
            await user.should_not_see(second.title)

            user.find(marker="status-filter").click()
            user.find("in_progress").click()
            user.find(marker="refresh-button").click()
            await user.should_see(first.title)
            await user.should_not_see(second.title)

            user.find(marker="clear-filters").click()
            await user.should_see(first.title)
            await user.should_see(second.title)

            user.find(marker=f"status-select-{first.id}").click()
            user.find("resolved").click()
            user.find(marker=f"update-status-{first.id}").click()
            await user.should_see("Ticket updated")
            await user.should_see("Status: resolved")

            assert repository.get(first.id).status is TicketStatus.resolved
            assert repository.get(second.id).status is TicketStatus.open
    finally:
        repository.close()
