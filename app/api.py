from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from database import TicketNotFoundError, TicketRepository
from models import Ticket, TicketCreate, TicketFilters, TicketPriority, TicketStatus, TicketUpdate


def create_api_router(repository: TicketRepository) -> APIRouter:
    """Create api router.

    Args:
        repository (TicketRepository): Description of repository.

    Returns:
        APIRouter: Description of the return value.

    Raises:
        HTTPException: Description of when this is raised.
    """
    router = APIRouter(prefix="/api", tags=["tickets"])

    def get_repository() -> TicketRepository:
        """Get repository.

        Returns:
            TicketRepository: Description of the return value.
        """
        return repository

    @router.get("/tickets", response_model=list[Ticket])
    def list_tickets(
        status_filter: TicketStatus | None = Query(default=None, alias="status"),
        priority: TicketPriority | None = Query(default=None),
        search: str | None = Query(default=None),
        tickets: TicketRepository = Depends(get_repository),
    ) -> list[Ticket]:
        """List tickets.

        Args:
            status_filter (TicketStatus | None): Description of status_filter.
            priority (TicketPriority | None): Description of priority.
            search (str | None): Description of search.
            tickets (TicketRepository): Description of tickets.

        Returns:
            list[Ticket]: Description of the return value.
        """
        return tickets.list(TicketFilters(status=status_filter, priority=priority, search=search))

    @router.post("/tickets", response_model=Ticket, status_code=status.HTTP_201_CREATED)
    def create_ticket(ticket: TicketCreate, tickets: TicketRepository = Depends(get_repository)) -> Ticket:
        """Create ticket.

        Args:
            ticket (TicketCreate): Description of ticket.
            tickets (TicketRepository): Description of tickets.

        Returns:
            Ticket: Description of the return value.
        """
        return tickets.create(ticket)

    @router.get("/tickets/{ticket_id}", response_model=Ticket)
    def get_ticket(
        ticket_id: Annotated[int, Path(gt=0)],
        tickets: TicketRepository = Depends(get_repository),
    ) -> Ticket:
        """Get ticket.

        Args:
            ticket_id (Annotated[int, Path(gt=0)]): Description of ticket_id.
            tickets (TicketRepository): Description of tickets.

        Returns:
            Ticket: Description of the return value.

        Raises:
            HTTPException: Description of when this is raised.
        """
        try:
            return tickets.get(ticket_id)
        except TicketNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    @router.patch("/tickets/{ticket_id}", response_model=Ticket)
    def update_ticket(
        ticket_id: Annotated[int, Path(gt=0)],
        update: TicketUpdate,
        tickets: TicketRepository = Depends(get_repository),
    ) -> Ticket:
        """Update ticket.

        Args:
            ticket_id (Annotated[int, Path(gt=0)]): Description of ticket_id.
            update (TicketUpdate): Description of update.
            tickets (TicketRepository): Description of tickets.

        Returns:
            Ticket: Description of the return value.

        Raises:
            HTTPException: Description of when this is raised.
        """
        try:
            return tickets.update(ticket_id, update)
        except TicketNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    @router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_ticket(
        ticket_id: Annotated[int, Path(gt=0)],
        tickets: TicketRepository = Depends(get_repository),
    ) -> Response:
        """Delete ticket.

        Args:
            ticket_id (Annotated[int, Path(gt=0)]): Description of ticket_id.
            tickets (TicketRepository): Description of tickets.

        Returns:
            Response: Description of the return value.

        Raises:
            HTTPException: Description of when this is raised.
        """
        try:
            tickets.delete(ticket_id)
        except TicketNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
