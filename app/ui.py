from fastapi import FastAPI
from nicegui import ui
from pydantic import ValidationError

from database import TicketNotFoundError, TicketRepository
from models import Ticket, TicketCreate, TicketFilters, TicketPriority, TicketStatus, TicketUpdate

PRIORITY_VALUES = tuple(ticket_priority.value for ticket_priority in TicketPriority)
STATUS_VALUES = tuple(ticket_status.value for ticket_status in TicketStatus)


def _event_value(args: object) -> str:
    """Event value.

    Args:
        args (object): Description of args.

    Returns:
        str: Description of the return value.
    """
    if isinstance(args, dict):
        value = args.get("value")
    else:
        value = args
    return "" if value is None else str(value)


def _normalize_select_value(value: object, allowed_values: tuple[str, ...]) -> str:
    """Normalize select value.

    Args:
        value (object): Description of value.
        allowed_values (tuple[str, ...]): Description of allowed_values.

    Returns:
        str: Description of the return value.
    """
    raw_value = _event_value(value)
    if raw_value.isdigit():
        index = int(raw_value)
        if 0 <= index < len(allowed_values):
            return allowed_values[index]
    return raw_value


def build_ticket_dashboard(repository: TicketRepository) -> None:
    """Build ticket dashboard.

    Args:
        repository (TicketRepository): Description of repository.
    """
    with ui.column().classes("w-full gap-6 p-6"):
        with ui.row().classes("w-full items-end justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label("Ticket Desk").classes("text-4xl font-bold text-gray-900")
                ui.label("Create, triage, and resolve support tickets.").classes("text-gray-600")
            ui.button("Refresh", on_click=lambda: refresh()).props("outline").mark("refresh-button")

        with ui.card().classes("w-full rounded-lg border border-gray-200 shadow-sm"):
            ui.label("New ticket").classes("text-xl font-semibold")
            with ui.grid(columns=2).classes("w-full gap-4"):
                title = ui.input("Title").classes("w-full").mark("create-title")
                requester = ui.input("Requester").classes("w-full").mark("create-requester")
                priority = ui.select(
                    {ticket_priority: ticket_priority for ticket_priority in PRIORITY_VALUES},
                    value=TicketPriority.medium.value,
                    label="Priority",
                ).classes("w-full").mark("create-priority")
                description = ui.textarea("Description").classes("w-full col-span-2").mark("create-description")
            ui.button("Create ticket", on_click=lambda: create_ticket()).props("color=primary").mark("create-button")

        with ui.card().classes("w-full rounded-lg border border-gray-200 shadow-sm"):
            ui.label("Filters").classes("text-xl font-semibold")
            with ui.row().classes("w-full items-center gap-3"):
                status_filter = ui.select(
                    {"all": "all", **{ticket_status: ticket_status for ticket_status in STATUS_VALUES}},
                    value="all",
                    label="Status",
                ).classes("w-44").mark("status-filter")
                priority_filter = ui.select(
                    {"all": "all", **{ticket_priority: ticket_priority for ticket_priority in PRIORITY_VALUES}},
                    value="all",
                    label="Priority",
                ).classes("w-44").mark("priority-filter")
                search = ui.input("Search").props("clearable").classes("w-72").mark("search-input")
                ui.button("Clear filters", on_click=lambda: clear_filters()).props("flat").mark("clear-filters")

        tickets_container = ui.column().classes("w-full gap-3").mark("tickets-container")

        def current_filters() -> TicketFilters:
            """Current filters.

            Returns:
                TicketFilters: Description of the return value.
            """
            status_value = _normalize_select_value(status_filter.value, STATUS_VALUES)
            priority_value = _normalize_select_value(priority_filter.value, PRIORITY_VALUES)
            return TicketFilters(
                status=None if status_value == "all" else TicketStatus(status_value),
                priority=None if priority_value == "all" else TicketPriority(priority_value),
                search=search.value,
            )

        def refresh() -> None:
            """Refresh."""
            tickets_container.clear()
            with tickets_container:
                tickets = repository.list(current_filters())
                if not tickets:
                    ui.label("No tickets match the current filters.").classes("text-gray-500")
                    return
                for ticket in tickets:
                    render_ticket(ticket)

        def clear_filters() -> None:
            """Clear filters."""
            status_filter.value = "all"
            priority_filter.value = "all"
            search.value = ""
            refresh()

        def create_ticket() -> None:
            """Create ticket."""
            try:
                repository.create(
                    TicketCreate(
                        title=title.value,
                        description=description.value,
                        requester=requester.value,
                        priority=TicketPriority(_normalize_select_value(priority.value, PRIORITY_VALUES)),
                    )
                )
            except (ValidationError, ValueError) as error:
                ui.notify(f"Could not create ticket: {error}", color="negative")
                return
            title.value = ""
            description.value = ""
            requester.value = ""
            priority.value = TicketPriority.medium.value
            ui.notify("Ticket created", color="positive")
            refresh()

        def render_ticket(ticket: Ticket) -> None:
            """Render ticket.

            Args:
                ticket (Ticket): Description of ticket.
            """
            with ui.card().classes("w-full rounded-lg border border-gray-200 shadow-sm").mark(f"ticket-card-{ticket.id}"):
                with ui.row().classes("w-full items-start justify-between gap-4"):
                    with ui.column().classes("gap-1"):
                        ui.label(ticket.title).classes("text-lg font-semibold")
                        ui.label(ticket.description).classes("text-gray-700")
                        ui.label(f"Requester: {ticket.requester}").classes("text-sm text-gray-500")
                    with ui.column().classes("min-w-48 gap-2"):
                        status_select = ui.select(
                            {ticket_status: ticket_status for ticket_status in STATUS_VALUES},
                            value=ticket.status.value,
                            label="Status",
                        ).classes("w-full").mark(f"status-select-{ticket.id}").on(
                            "update:model-value",
                            lambda event, ticket_id=ticket.id: update_status(
                                ticket_id, _normalize_select_value(event.args, STATUS_VALUES)
                            ),
                        )
                        ui.button(
                            "Update status",
                            on_click=lambda ticket_id=ticket.id, selector=status_select: update_status(
                                ticket_id, _normalize_select_value(selector.value, STATUS_VALUES)
                            ),
                        ).props("flat").mark(f"update-status-{ticket.id}")
                        ui.label(f"Status: {ticket.status.value}").classes("text-sm text-gray-500").mark(
                            f"ticket-status-{ticket.id}"
                        )
                        ui.label(f"Priority: {ticket.priority.value}").classes("text-sm font-medium uppercase text-gray-500")

        def update_status(ticket_id: int, status_value: str) -> None:
            """Update status.

            Args:
                ticket_id (int): Description of ticket_id.
                status_value (str): Description of status_value.
            """
            try:
                repository.update(ticket_id, TicketUpdate(status=TicketStatus(status_value)))
            except (TicketNotFoundError, ValidationError, ValueError) as error:
                ui.notify(f"Could not update ticket: {error}", color="negative")
            else:
                ui.notify("Ticket updated", color="positive")
            refresh()

        status_filter.on("update:model-value", lambda _: refresh())
        priority_filter.on("update:model-value", lambda _: refresh())
        search.on("update:model-value", lambda _: refresh())

        refresh()

    ui.add_head_html(
        """
        <style>
            body { background: #f7f5ef; }
            .nicegui-content { max-width: 1180px; margin: 0 auto; }
            .q-field { transform: none; }
        </style>
        """
    )


def mount_ui(app: FastAPI, repository: TicketRepository, storage_secret: str | None = None) -> None:
    """Mount ui.

    Args:
        app (FastAPI): Description of app.
        repository (TicketRepository): Description of repository.
        storage_secret (str | None): Description of storage_secret.
    """
    ui.run_with(
        app,
        root=lambda: build_ticket_dashboard(repository),
        title="Ticketing System",
        favicon="T",
        storage_secret=storage_secret,
    )
