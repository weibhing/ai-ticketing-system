import pytest
from pydantic import ValidationError

from models import TicketCreate, TicketFilters, TicketPriority, TicketUpdate


def test_ticket_create_trims_strings_and_accepts_seed_sized_values() -> None:
    ticket = TicketCreate(
        title="  Laptop cannot connect to VPN  ",
        description="  Requester is blocked from accessing internal systems while traveling.  ",
        requester="  Avery Stone  ",
        priority=TicketPriority.high,
    )

    assert ticket.title == "Laptop cannot connect to VPN"
    assert ticket.description == "Requester is blocked from accessing internal systems while traveling."
    assert ticket.requester == "Avery Stone"


@pytest.mark.parametrize(
    ("payload", "field_name"),
    [
        ({"title": "  ", "description": "Valid description", "requester": "AB"}, "title"),
        ({"title": "Valid title", "description": "  ", "requester": "AB"}, "description"),
        ({"title": "Valid title", "description": "Valid description", "requester": " "}, "requester"),
    ],
)
def test_ticket_create_rejects_whitespace_only_values(payload: dict[str, str], field_name: str) -> None:
    with pytest.raises(ValidationError) as error:
        TicketCreate(**payload)

    assert field_name in str(error.value)


def test_ticket_update_rejects_explicit_nulls_but_allows_omissions() -> None:
    assert TicketUpdate().model_dump(exclude_unset=True) == {}

    with pytest.raises(ValidationError) as error:
        TicketUpdate(title=None)

    assert "must not be null" in str(error.value)


def test_ticket_filters_strip_blank_search_terms() -> None:
    filters = TicketFilters(search="   ")

    assert filters.search is None
