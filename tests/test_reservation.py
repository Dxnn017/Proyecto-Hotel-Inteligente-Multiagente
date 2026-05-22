import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from agents.reservation_agent import ReservationAgent

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    agent = ReservationAgent(memory, bus)
    return memory, bus, agent

def test_reservation_success(setup):
    memory, bus, agent = setup
    payload = {
        "action": "crear_reserva",
        "guest_name": "Test Guest",
        "room_type": "simple",
        "check_in_date": "2026-10-01",
        "check_out_date": "2026-10-05",
        "num_guests": 1
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert "reservation_id" in result
    assert result["room_type"] == "simple"
    
def test_reservation_no_availability(setup):
    memory, bus, agent = setup
    # Ocupar todas las suites
    for room in memory._rooms:
        if room["room_type"] == "suite":
            room["status"] = "ocupada"
            
    payload = {
        "action": "crear_reserva",
        "guest_name": "Test Guest 2",
        "room_type": "suite",
        "check_in_date": "2026-10-01",
        "check_out_date": "2026-10-05",
        "num_guests": 2
    }
    result = agent.process(payload)
    assert result["status"] == "failed"
    assert "no hay habitaciones" in result["response_message"].lower()
